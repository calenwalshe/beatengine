from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..drum_analysis import DrumAnchors
from ..seeds import SeedMetadata
from .lead_modes import LeadMode, load_lead_modes, select_lead_mode
from .lead_templates import (
    ContourTemplate,
    RhythmTemplate,
    load_contour_templates,
    load_rhythm_templates,
)
from .lead_phrase import build_phrase_roles
from .lead_validation import LeadNote


@dataclass
class NoteEvent:
    pitch: int
    velocity: int
    start_tick: int
    duration: int


@dataclass
class LeadContext:
    anchors: DrumAnchors
    seed_meta: SeedMetadata
    tags: List[str]
    modes: Dict[str, LeadMode]
    rhythm_templates: List[RhythmTemplate]
    contour_templates: List[ContourTemplate]


def build_lead_context(
    anchors: DrumAnchors,
    seed_meta: SeedMetadata,
    *,
    modes_raw: Dict[str, Dict[str, Any]] | None = None,
    rhythm_raw: Dict[str, Dict[str, Any]] | None = None,
    contour_raw: Dict[str, Dict[str, Any]] | None = None,
) -> LeadContext:
    """Build a minimal LeadContext for use in tests and generation.

    The full implementation will eventually load JSON configs from disk;
    this helper keeps tests fast and deterministic by allowing in-memory
    dictionaries to be supplied.
    """

    modes = load_lead_modes(modes_raw or {})
    r_templ = load_rhythm_templates(rhythm_raw or {})
    c_templ = load_contour_templates(contour_raw or {})
    tags = list(seed_meta.tags or [])
    return LeadContext(
        anchors=anchors,
        seed_meta=seed_meta,
        tags=tags,
        modes=modes,
        rhythm_templates=r_templ,
        contour_templates=c_templ,
    )


def generate_lead(
    drum_slots: DrumAnchors,
    seed_metadata: SeedMetadata,
    bass_notes: Optional[List[NoteEvent]] = None,
    rng: Optional[Any] = None,
    lead_mode_override: Optional[str] = None,
) -> List[NoteEvent]:
    """Produce deterministic lead-line MIDI note events.

    This is a first-pass implementation that follows the high-level design:

    - Load lead modes, rhythm templates, and contour templates from JSON.
    - Select a mode from seed tags (or override).
    - Build a simple rhythmic skeleton using the first matching template per
      bar and align events to the drum slot grid using weighted scores.
    - Apply a basic contour to generate pitches within the mode register.

    The implementation is intentionally conservative but fully deterministic
    and suitable for unit testing. It can be extended with richer behaviour
    without breaking the public API.
    """

    import json
    from pathlib import Path
    import random

    # Deterministic RNG: use provided rng or seed from metadata.
    if rng is None:
        rng = random.Random(int(getattr(seed_metadata, 'rng_seed', 0)))

    # Load configs from disk.
    cfg_dir = Path(__file__).resolve().parents[3] / 'configs'
    modes_raw: Dict[str, Dict[str, Any]] = {}
    rhythm_raw: Dict[str, Dict[str, Any]] = {}
    contour_raw: Dict[str, Dict[str, Any]] = {}
    try:
        modes_raw = json.loads((cfg_dir / 'lead_modes.json').read_text())
    except FileNotFoundError:
        modes_raw = {}
    try:
        rhythm_raw = json.loads((cfg_dir / 'lead_rhythm_templates.json').read_text())
    except FileNotFoundError:
        rhythm_raw = {}
    try:
        contour_raw = json.loads((cfg_dir / 'lead_contour_templates.json').read_text())
    except FileNotFoundError:
        contour_raw = {}

    ctx = build_lead_context(drum_slots, seed_metadata, modes_raw=modes_raw, rhythm_raw=rhythm_raw, contour_raw=contour_raw)

    # Select mode.
    if lead_mode_override and lead_mode_override in ctx.modes:
        mode = ctx.modes[lead_mode_override]
    else:
        mode = select_lead_mode(ctx.tags, ctx.modes)

    anchors = ctx.anchors
    bar_ticks = anchors.bar_ticks
    step_ticks = anchors.step_ticks
    total_bars = max(1, min(seed_metadata.bars, anchors.bar_count))

    # Phrase roles across bars.
    phrase_roles = build_phrase_roles(mode.phrase_length_bars, total_bars)

    # Build simple bass occupancy map for collision avoidance.
    bass_occ: List[set[int]] = [set() for _ in range(total_bars)]
    if bass_notes:
        for ev in bass_notes:
            bar = ev.start_tick // bar_ticks
            if bar < 0 or bar >= total_bars:
                continue
            tick_in_bar = ev.start_tick - bar * bar_ticks
            step = int(round(tick_in_bar / step_ticks))
            if 0 <= step < 16:
                bass_occ[bar].add(step)

    def score_slot(bar_idx: int, step: int) -> float:
        tags = anchors.slot_tags[bar_idx][step] if bar_idx < anchors.bar_count else set()
        score = 0.0
        for label, weight in mode.preferred_slot_weights.items():
            if label == 'is_offbeat_8th':
                if step in {2, 6, 10, 14}:
                    score += weight
            else:
                if label in tags:
                    score += weight
        # Light preference for hat activity.
        if step in anchors.bar_hat_steps[bar_idx]:
            score += 0.1
        # Mild penalty for sharing a slot with bass.
        if step in bass_occ[bar_idx]:
            score -= 1.0
        return score

    # Select templates grouped by (mode_name, role) for quick lookup.
    rhythm_by_role: Dict[tuple[str, str], List[RhythmTemplate]] = {}
    for rt in ctx.rhythm_templates:
        key = (rt.mode_name, rt.motif_role)
        rhythm_by_role.setdefault(key, []).append(rt)

    contour_by_role: Dict[tuple[str, str], List[ContourTemplate]] = {}
    for ct in ctx.contour_templates:
        key = (ct.mode_name, ct.motif_role)
        contour_by_role.setdefault(key, []).append(ct)

    # Skeleton: (bar, step, length, accent)
    skeleton: List[tuple[int, int, int, bool]] = []

    for pr in phrase_roles:
        bar = pr.bar_index
        role = pr.role
        key = (mode.name, role)
        templates = rhythm_by_role.get(key)
        if not templates:
            # Fallback: reuse CALL templates for other roles.
            templates = rhythm_by_role.get((mode.name, 'CALL'))
        if not templates:
            continue
        templ = templates[0]
        for ev in templ.events:
            base_step = max(0, min(15, ev.step))
            best_step = base_step
            best_score = score_slot(bar, base_step)
            for delta in (-2, -1, 1, 2):
                cand = base_step + delta
                if not 0 <= cand < 16:
                    continue
                s = score_slot(bar, cand)
                if s > best_score:
                    best_score = s
                    best_step = cand
            skeleton.append((bar, best_step, max(1, ev.length), bool(ev.accent)))

    # Enforce a soft density constraint by trimming if needed.
    per_bar: Dict[int, List[int]] = {}
    for idx, (bar, step, length, accent) in enumerate(skeleton):
        per_bar.setdefault(bar, []).append(idx)
    lo, hi = mode.target_notes_per_bar
    pruned: List[tuple[int, int, int, bool]] = []
    for bar in range(total_bars):
        idxs = per_bar.get(bar, [])
        if not idxs:
            continue
        if len(idxs) > hi:
            idxs = idxs[:hi]
        for idx in idxs:
            pruned.append(skeleton[idx])
    skeleton = pruned

    # Choose a simple scale: treat intervals as semitone offsets from root.
    root = 48
    # Fold root into register.
    while root < mode.register_low:
        root += 12
    while root > mode.register_high:
        root -= 12

    # Choose a contour template (CALL) for pitch intervals.
    contour_key = (mode.name, 'CALL')
    contour_list = contour_by_role.get(contour_key, [])
    intervals: List[int] = []
    if contour_list:
        intervals = contour_list[0].intervals
    if not intervals:
        intervals = [0]

    events: List[NoteEvent] = []
    for idx, (bar, step, length, accent) in enumerate(skeleton):
        interval = intervals[idx % len(intervals)]
        pitch = root + int(interval)
        # Fold into register.
        while pitch < mode.register_low:
            pitch += 12
        while pitch > mode.register_high:
            pitch -= 12
        start_tick = bar * bar_ticks + step * step_ticks
        duration = max(1, length * step_ticks)
        velocity = 100 if accent else 90
        events.append(NoteEvent(pitch=pitch, velocity=velocity, start_tick=start_tick, duration=duration))

    # Ensure final event (if any) resolves to root or octave.
    if events:
        final = events[-1]
        resolve_pitch = root
        if resolve_pitch < mode.register_low:
            resolve_pitch += 12
        if resolve_pitch > mode.register_high:
            resolve_pitch -= 12
        final.pitch = resolve_pitch

    return events
