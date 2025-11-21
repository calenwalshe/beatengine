from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from random import Random

from .theory import (
    KeySpec,
    build_scale_degrees,
    build_harmony_track,
    clamp_degree,
    choose_register_pitch,
    LeadNoteLogical,
    LeadNoteEvent,
    degree_to_pitch_class,
)
from .phrases import PhraseConfig, plan_phrases
from .motifs import RhythmTemplate, ContourTemplate, MotifPlan, fuse_rhythm_contour
from .slots import align_to_slots
from .bass import apply_bass_interaction


NOTE_TO_PC = {
    "c": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
}

KEY_TAG_RE = re.compile(r"key_([a-g][b#]?)_([a-z]+)")

QUALITY_TO_SCALE = {
    "maj": "ionian",
    "major": "ionian",
    "mixolydian": "mixolydian",
    "lydian": "lydian",
    "min": "aeolian",
    "minor": "aeolian",
    "aeolian": "aeolian",
    "dorian": "dorian",
    "phrygian": "phrygian",
    "locrian": "locrian",
    "harmonic": "harmonic_minor",
    "melodic": "melodic_minor",
}


@dataclass
class LeadModeConfig:
    """Subset of the LeadMode v2 config required for generate_lead_v2."""

    id: str
    scale_type: str
    default_root_pc: int
    allow_key_from_seed_tag: bool
    register_low: int
    register_high: int
    register_gravity_center: int
    phrase_cfg: PhraseConfig
    density: Dict[str, Any]
    slot_preferences: Dict[str, Dict[str, float]]
    bass_interaction: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    function_profiles: Dict[str, Dict[str, float]] = field(default_factory=dict)
    degree_weights: Dict[str, Dict[str, float]] = field(default_factory=dict)
    contour: Dict[str, Any] = field(default_factory=dict)
    variation: Dict[str, Any] = field(default_factory=dict)
    harmony_functions: List[str] = field(default_factory=list)


def make_rng(seed_components: List[Any]) -> Random:
    """Create a deterministic RNG from a list of seed components."""
    s = "|".join(str(x) for x in seed_components)
    return Random(hash(s))


def derive_keyspec(seed_tags: List[str], bass_midi: Any, mode_cfg: LeadModeConfig) -> KeySpec:
    """Derive KeySpec from tags (preferred) or fall back to the mode defaults."""

    root_pc = mode_cfg.default_root_pc
    scale_name = mode_cfg.scale_type

    if mode_cfg.allow_key_from_seed_tag:
        for tag in seed_tags or []:
            if not isinstance(tag, str):
                continue
            tag_norm = tag.lower()
            match = KEY_TAG_RE.match(tag_norm)
            if not match:
                continue
            root_txt, quality = match.groups()
            pc = NOTE_TO_PC.get(root_txt)
            if pc is None:
                continue
            mapped_scale = QUALITY_TO_SCALE.get(quality, scale_name)
            root_pc = pc
            scale_name = mapped_scale
            break

    scale_degrees = build_scale_degrees(scale_name)
    return KeySpec(root_pc=root_pc, scale_type=scale_name, scale_degrees=scale_degrees)


def weighted_choice(weights: Dict[Any, float], rng: Random, default: Any = None) -> Any:
    """Return a key sampled from weights (any hashable type)."""
    if not weights:
        return default
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        return default
    threshold = rng.random() * total
    cumulative = 0.0
    for key, value in weights.items():
        w = max(0.0, float(value))
        cumulative += w
        if threshold <= cumulative:
            return key
    return default


def _prepare_degree_weights(raw: Dict[str, Dict[str, float]]) -> Dict[str, Dict[int, float]]:
    prepared: Dict[str, Dict[int, float]] = {}
    for tone_cat, items in (raw or {}).items():
        converted: Dict[int, float] = {}
        for degree_txt, weight in items.items():
            try:
                degree_val = int(degree_txt)
            except (TypeError, ValueError):
                continue
            converted[degree_val] = float(weight)
        prepared[tone_cat] = converted
    return prepared


def _group_templates_by_role(templates: Optional[List[Any]]) -> Dict[str, List[Any]]:
    grouped: Dict[str, List[Any]] = defaultdict(list)
    if not templates:
        return grouped
    for templ in templates:
        role = getattr(templ, "role", "CALL")
        grouped[role.upper()].append(templ)
    return grouped


def _resolve_steps_per_bar(anchors: Any) -> int:
    slot_tags = getattr(anchors, "slot_tags", None)
    if slot_tags and slot_tags[0]:
        return len(slot_tags[0])
    return 16


def _build_resolution_map(phrase_plan: Any) -> Dict[int, List[int]]:
    resolution: Dict[int, List[int]] = {}
    for seg in phrase_plan.segments:
        if seg.is_terminal and seg.bar_indices:
            resolution[seg.bar_indices[-1]] = list(seg.resolution_degrees or [])
    return resolution


def _group_phrase_runs(phrase_plan: Any) -> List[Tuple[int, str, List[int]]]:
    """Return a list of (phrase_id, role, ordered bar indices)."""
    grouped: Dict[int, List[PhraseSegment]] = defaultdict(list)
    for seg in phrase_plan.segments:
        grouped[seg.phrase_id].append(seg)

    runs: List[Tuple[int, str, List[int]]] = []
    for phrase_id, segs in grouped.items():
        ordered = sorted(segs, key=lambda s: s.bar_indices[0])
        idx = 0
        while idx < len(ordered):
            role = ordered[idx].role
            bars: List[int] = []
            while idx < len(ordered) and ordered[idx].role == role:
                bars.extend(ordered[idx].bar_indices)
                idx += 1
            runs.append((phrase_id, role, bars))
    return runs


def _normalize_slot_prefs(slot_prefs: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    normalized: Dict[str, Dict[str, float]] = {}
    for role, entries in (slot_prefs or {}).items():
        role_key = role.upper()
        normalized[role_key] = {tag: float(weight) for tag, weight in entries.items()}
    if "DEFAULT" not in normalized:
        normalized["DEFAULT"] = {}
    return normalized


def _desired_energy(mode_cfg: LeadModeConfig) -> str:
    target = mode_cfg.density.get("target_notes_per_bar") if mode_cfg.density else None
    if target is None:
        return "medium"
    try:
        target_val = float(target)
    except (TypeError, ValueError):
        return "medium"
    if target_val >= 6:
        return "high"
    if target_val <= 3:
        return "low"
    return "medium"


def _filter_templates_for_mode(
    templates: List[Any],
    role: str,
    mode_id: str,
    desired_energy: Optional[str],
) -> List[Any]:
    role_upper = role.upper()
    role_templates = [t for t in templates if getattr(t, "role", "").upper() == role_upper]
    if not role_templates:
        return []
    matching_mode = [
        t for t in role_templates if not getattr(t, "mode_ids", None) or mode_id in getattr(t, "mode_ids", [])
    ]
    if matching_mode:
        role_templates = matching_mode
    if desired_energy:
        energy_matched = [t for t in role_templates if getattr(t, "energy", "medium") == desired_energy]
        if energy_matched:
            role_templates = energy_matched
    return role_templates


def _merge_template_lists(primary: List[Any], fallback: List[Any]) -> List[Any]:
    merged = list(primary)
    for item in fallback:
        if item not in merged:
            merged.append(item)
    return merged


def _apply_rhythm_variation(notes: List[LeadNoteLogical], strength: float, rng: Random) -> List[LeadNoteLogical]:
    if strength <= 0:
        return notes
    kept: List[LeadNoteLogical] = []
    for note in notes:
        if note.phrase_position in ("start", "end"):
            kept.append(note)
            continue
        if rng.random() < strength:
            continue
        kept.append(note)
    return kept or notes


def _select_tone_category(
    note: LeadNoteLogical,
    function_profiles: Dict[str, Dict[str, float]],
    rng: Random,
) -> str:
    keys = [
        f"{note.role}.{note.phrase_position}.{note.beat_strength}",
        f"{note.role}.{note.phrase_position}",
        note.role,
        "DEFAULT",
    ]
    for key in keys:
        weights = function_profiles.get(key)
        if weights:
            choice = weighted_choice(weights, rng, default="chord_tone")
            if choice:
                return choice
    return "chord_tone"


def _velocity_for_note(note: LeadNoteLogical) -> int:
    base = 92 if note.role == "CALL" else 86
    if note.phrase_position == "start":
        base += 4
    elif note.phrase_position == "end":
        base -= 2
    accent_boost = int(round(note.accent * 24))
    velocity = base + accent_boost
    return max(40, min(127, velocity))


def _limit_density(events: List[LeadNoteEvent], density_cfg: Dict[str, Any], num_bars: int) -> List[LeadNoteEvent]:
    target = density_cfg.get("target_notes_per_bar") if density_cfg else None
    if not target:
        return events
    limit = int(target * num_bars)
    if limit <= 0 or len(events) <= limit:
        return events
    indexed = list(enumerate(events))
    indexed.sort(key=lambda pair: pair[1].velocity)
    to_remove = len(events) - limit
    remove_indices = {idx for idx, _ in indexed[:to_remove]}
    filtered = [ev for idx, ev in enumerate(events) if idx not in remove_indices]
    return filtered if filtered else events


def _select_degree(
    note: LeadNoteLogical,
    tone_category: str,
    degree_weights: Dict[str, Dict[int, float]],
    harmony_bar: Any,
    rng: Random,
    scale_size: int,
    contour_cfg: Dict[str, Any],
    previous_degree: Optional[int],
    resolution_targets: List[int],
) -> int:
    weights = dict(degree_weights.get(tone_category, degree_weights.get("chord_tone", {1: 1.0})))
    if tone_category == "chord_tone":
        for deg in harmony_bar.chord_tone_degrees:
            weights[deg] = weights.get(deg, 0.0) + 0.3
    elif tone_category == "color":
        for deg in harmony_bar.color_tone_degrees:
            weights[deg] = weights.get(deg, 0.0) + 0.2

    func_pref = []
    if harmony_bar.function_label == "predominant":
        func_pref = [2, 4, 6]
    elif harmony_bar.function_label == "dominant":
        func_pref = [5, 7, 2]
    else:
        func_pref = [1, 3, 5]
    for deg in func_pref:
        weights[deg] = weights.get(deg, 0.0) + 0.15

    if resolution_targets and note.phrase_position == "end":
        for deg in resolution_targets:
            weights[deg] = weights.get(deg, 0.0) + 0.5

    base_degree = weighted_choice(weights, rng, default=1) or 1
    contour_offset = note.contour_degree or 0
    degree = clamp_degree(base_degree + contour_offset, scale_size)

    max_leap = int(contour_cfg.get("max_leap_degrees", 4) or 4)
    step_bias = float(contour_cfg.get("step_bias", 0.0) or 0.0)

    if previous_degree is not None:
        delta = degree - previous_degree
        if abs(delta) > max_leap:
            degree = previous_degree + max_leap * (1 if delta > 0 else -1)
        elif abs(delta) > 1 and rng.random() < step_bias:
            degree = previous_degree + (1 if delta > 0 else -1)

    return clamp_degree(degree, scale_size)


def generate_lead_v2(
    anchors: Any,
    seed_metadata: Any,
    bass_midi: Optional[Any] = None,
    mode_cfg: Optional[LeadModeConfig] = None,
    call_templates: Optional[List[RhythmTemplate]] = None,
    resp_templates: Optional[List[RhythmTemplate]] = None,
    contour_call: Optional[List[ContourTemplate]] = None,
    contour_resp: Optional[List[ContourTemplate]] = None,
    rng_seed: int = 0,
) -> List[LeadNoteEvent]:
    """Theory-aware lead generation pipeline."""

    if mode_cfg is None:
        raise ValueError("mode_cfg must be provided to generate_lead_v2 scaffolding")

    rng = make_rng(
        [
            getattr(seed_metadata, "seed_id", "unknown"),
            mode_cfg.id,
            rng_seed,
            "lead_v2",
        ]
    )

    key = derive_keyspec(getattr(seed_metadata, "tags", []), bass_midi, mode_cfg)

    total_bars = max(1, int(getattr(seed_metadata, "bars", 4)))
    anchor_bars = max(1, int(getattr(anchors, "bar_count", total_bars)))
    num_bars = min(total_bars, anchor_bars)
    harmony = build_harmony_track(num_bars, key, mode_cfg.harmony_functions)

    phrase_plan = plan_phrases(num_bars, mode_cfg.phrase_cfg, rng)
    resolution_map = _build_resolution_map(phrase_plan)
    phrase_runs = _group_phrase_runs(phrase_plan)

    steps_per_bar = _resolve_steps_per_bar(anchors)
    step_ticks = getattr(anchors, "step_ticks", 120)

    variation = mode_cfg.variation or {}
    transpose_choices = variation.get("transposition_choices", [0]) or [0]
    invert_prob = float(variation.get("contour_inversion_prob", 0.0) or 0.0)
    rhythm_variation = float(variation.get("rhythm_variation_strength", 0.0) or 0.0)
    pitch_variation = float(variation.get("pitch_variation_strength", 0.0) or 0.0)

    desired_energy = _desired_energy(mode_cfg)
    call_rt = _merge_template_lists(
        _filter_templates_for_mode(call_templates or [], "CALL", mode_cfg.id, desired_energy),
        _filter_templates_for_mode(call_templates or [], "CALL", mode_cfg.id, None),
    )
    resp_rt = _merge_template_lists(
        _filter_templates_for_mode(resp_templates or [], "RESP", mode_cfg.id, desired_energy),
        _filter_templates_for_mode(resp_templates or [], "RESP", mode_cfg.id, None),
    )
    call_ct = _merge_template_lists(
        _filter_templates_for_mode(contour_call or [], "CALL", mode_cfg.id, desired_energy),
        _filter_templates_for_mode(contour_call or [], "CALL", mode_cfg.id, None),
    )
    resp_ct = _merge_template_lists(
        _filter_templates_for_mode(contour_resp or [], "RESP", mode_cfg.id, desired_energy),
        _filter_templates_for_mode(contour_resp or [], "RESP", mode_cfg.id, None),
    )

    if not call_rt and not resp_rt:
        raise ValueError("No rhythm templates provided to generate_lead_v2")
    if not call_ct and not resp_ct:
        raise ValueError("No contour templates provided to generate_lead_v2")

    motifs: List[MotifPlan] = []
    for phrase_id, role, bars in phrase_runs:
        role_key = role.upper()
        if role_key == "CALL":
            templates = call_rt or resp_rt
            contours = call_ct or resp_ct
        else:
            templates = resp_rt or call_rt
            contours = resp_ct or call_ct
        if not templates or not contours:
            continue

        bars_sorted = sorted(bars)
        cursor = 0
        while cursor < len(bars_sorted):
            available = len(bars_sorted) - cursor
            viable = [t for t in templates if t.bars <= available]
            if not viable:
                break
            rhythm = rng.choice(viable)
            contour = rng.choice(contours)
            bar_slice = bars_sorted[cursor : cursor + rhythm.bars]
            cursor += rhythm.bars

            transpose = rng.choice(transpose_choices)
            invert = rng.random() < invert_prob
            motif = fuse_rhythm_contour(
                phrase_id=phrase_id,
                role=role_key,
                bar_indices=bar_slice,
                rhythm=rhythm,
                contour=contour,
                steps_per_bar=steps_per_bar,
                rng=rng,
                degree_transpose=transpose,
                invert_contour=invert,
            )
            motifs.append(motif)

    degree_weights = _prepare_degree_weights(mode_cfg.degree_weights)
    slot_prefs = _normalize_slot_prefs(mode_cfg.slot_preferences)
    occupied_steps: Dict[int, set[int]] = defaultdict(set)
    events: List[LeadNoteEvent] = []
    harmony_bars = harmony.per_bar
    scale_size = len(key.scale_degrees)
    register_drift_per_phrase = int(variation.get("register_drift_per_phrase", 0) or 0)

    prev_degree: Optional[int] = None
    prev_pitch: Optional[int] = None

    for motif in motifs:
        phrase_drift = register_drift_per_phrase * motif.phrase_id
        varied_notes = _apply_rhythm_variation(motif.notes, rhythm_variation, rng)
        for note in varied_notes:
            bar_idx = min(note.metric_position.bar_index, len(harmony_bars) - 1)
            tone_category = _select_tone_category(note, mode_cfg.function_profiles, rng)
            note.tone_category = tone_category
            resolution_targets = resolution_map.get(bar_idx, [])
            degree = _select_degree(
                note=note,
                tone_category=tone_category,
                degree_weights=degree_weights,
                harmony_bar=harmony_bars[bar_idx],
                rng=rng,
                scale_size=scale_size,
                contour_cfg=mode_cfg.contour or {},
                previous_degree=prev_degree,
                resolution_targets=resolution_targets,
            )
            note.degree = degree

            if pitch_variation > 0 and rng.random() < pitch_variation:
                shift = 1 if rng.random() < 0.5 else -1
                degree = clamp_degree(degree + shift, scale_size)
                note.degree = degree

            pitch_class = degree_to_pitch_class(key, degree)
            pitch = choose_register_pitch(
                pitch_class,
                register_low=mode_cfg.register_low,
                register_high=mode_cfg.register_high,
                gravity_center=mode_cfg.register_gravity_center,
                drift=phrase_drift,
                previous_pitch=prev_pitch,
            )
            velocity = _velocity_for_note(note)

            event = align_to_slots(
                logical_note=note,
                anchors=anchors,
                role_slot_prefs=slot_prefs,
                steps_per_bar=steps_per_bar,
                step_ticks=step_ticks,
                duration_steps=note.duration_steps or 1,
                pitch=pitch,
                velocity=velocity,
                occupied_steps=occupied_steps,
                rng=rng,
            )
            events.append(event)
            prev_degree = degree
            prev_pitch = pitch

    events = _limit_density(events, mode_cfg.density, num_bars)

    if bass_midi and events and mode_cfg.bass_interaction.get("avoid_unison_with_bass", False):
        events = apply_bass_interaction(
            lead_events=events,
            bass_midi=bass_midi,
            key=key,
            register_low=mode_cfg.register_low,
            register_high=mode_cfg.register_high,
            min_semitone_distance=mode_cfg.bass_interaction.get("min_semitone_distance_from_bass", 3),
            avoid_root_on_bass_hits=mode_cfg.bass_interaction.get("avoid_root_on_bass_hits", False),
            rng=rng,
        )

    events.sort(key=lambda e: (e.start_tick, e.pitch))
    return events
