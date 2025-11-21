from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from lead_implementation.lead_v2.generate import LeadModeConfig
from lead_implementation.lead_v2.motifs import (
    RhythmTemplate,
    RhythmEvent,
    ContourTemplate,
)
from lead_implementation.lead_v2.phrases import PhraseConfig


def _read_json(path: Path) -> Optional[object]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None


def _coerce_list(payload: object) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        # Support either {"modes": [...]} or {"id": {...}} styles.
        if "modes" in payload and isinstance(payload["modes"], list):
            return [item for item in payload["modes"] if isinstance(item, dict)]
        if all(isinstance(v, dict) for v in payload.values()):
            return [dict(v, id=k) if "id" not in v else v for k, v in payload.items()]
    return []


def load_lead_modes_v2(path: Path) -> Dict[str, LeadModeConfig]:
    payload = _read_json(path)
    if not payload:
        return {}

    modes: Dict[str, LeadModeConfig] = {}
    for idx, entry in enumerate(_coerce_list(payload)):
        phrase_data = entry.get("phrase", {})
        phrase_cfg = PhraseConfig(
            min_bars=int(phrase_data.get("min_bars", 4)),
            max_bars=int(phrase_data.get("max_bars", 4)),
            call_response_pattern=str(phrase_data.get("call_response_pattern", "CR")),
            phrase_forms=list(phrase_data.get("phrase_forms", ["A"])),
            phrase_end_resolution_degrees=list(phrase_data.get("phrase_end_resolution_degrees", [1])),
        )
        scale_data = entry.get("scale", {})
        register_data = entry.get("register", {})
        density = dict(entry.get("density", {}))
        slot_preferences = dict(entry.get("slot_preferences", {}))
        bass_interaction = dict(entry.get("bass_interaction", {}))
        variation = dict(entry.get("variation", {}))
        contour_cfg = dict(entry.get("contour", {}))
        function_profiles = dict(entry.get("function_profiles", {}))
        degree_weights = dict(entry.get("degree_weights", {}))
        harmony_cycle = list(entry.get("harmony_cycle", []))

        mode_id = entry.get("id") or entry.get("name") or f"mode_{idx}"
        cfg = LeadModeConfig(
            id=str(mode_id),
            tags=list(entry.get("tags", [])),
            scale_type=str(scale_data.get("scale_type", "aeolian")),
            default_root_pc=int(scale_data.get("default_root_pc", 9)),
            allow_key_from_seed_tag=bool(scale_data.get("allow_key_from_seed_tag", True)),
            register_low=int(register_data.get("low", 60)),
            register_high=int(register_data.get("high", 76)),
            register_gravity_center=int(register_data.get("gravity_center", (register_data.get("low", 60) + register_data.get("high", 76)) // 2)),
            phrase_cfg=phrase_cfg,
            density=density,
            slot_preferences=slot_preferences,
            bass_interaction=bass_interaction,
            function_profiles=function_profiles,
            degree_weights=degree_weights,
            contour=contour_cfg,
            variation=variation,
            harmony_functions=harmony_cycle,
        )
        modes[cfg.id] = cfg
    return modes


def load_rhythm_templates_v2(path: Path) -> List[RhythmTemplate]:
    payload = _read_json(path)
    if not payload:
        return []
    templates: List[RhythmTemplate] = []
    for entry in _coerce_list(payload):
        events = []
        for raw in entry.get("events", []):
            if not isinstance(raw, dict):
                continue
            events.append(
                RhythmEvent(
                    step_offset=int(raw.get("step_offset", raw.get("step", 0))),
                    length_steps=int(raw.get("length_steps", raw.get("length", 1))),
                    accent=float(raw.get("accent", 0.8)),
                    anchor_type=raw.get("anchor_type"),
                )
            )
        templates.append(
            RhythmTemplate(
                id=str(entry.get("id")),
                role=str(entry.get("role", "CALL")).upper(),
                bars=int(entry.get("bars", 1)),
                events=events,
                max_step_jitter=int(entry.get("max_step_jitter", 1)),
                min_inter_note_gap_steps=int(entry.get("min_inter_note_gap_steps", 1)),
                mode_ids=list(entry.get("modes", entry.get("mode_ids", [])) or []),
                tags=list(entry.get("tags", [])),
                energy=str(entry.get("energy", "medium")),
            )
        )
    return templates


def load_contour_templates_v2(path: Path) -> List[ContourTemplate]:
    payload = _read_json(path)
    if not payload:
        return []
    templates: List[ContourTemplate] = []
    for entry in _coerce_list(payload):
        templates.append(
            ContourTemplate(
                id=str(entry.get("id")),
                role=str(entry.get("role", "CALL")).upper(),
                degree_intervals=list(entry.get("degree_intervals", entry.get("intervals", [0]))),
                emphasis_indices=list(entry.get("emphasis_indices", [])),
                shape_type=str(entry.get("shape_type", entry.get("shape", "arch"))),
                tension_profile=list(entry.get("tension_profile", ["low", "medium", "resolve"])),
                mode_ids=list(entry.get("modes", entry.get("mode_ids", [])) or []),
                tags=list(entry.get("tags", [])),
                energy=str(entry.get("energy", "medium")),
            )
        )
    return templates


def select_lead_mode_v2(
    tags: Optional[List[str]],
    modes: Dict[str, LeadModeConfig],
    override: Optional[str] = None,
) -> LeadModeConfig:
    if not modes:
        raise ValueError("lead_v2: no modes are available")

    if override:
        override_lower = override.lower()
        for mode_id in modes:
            if mode_id.lower() == override_lower:
                return modes[mode_id]

    tags_lower = {t.lower() for t in (tags or [])}
    if tags_lower:
        for mode in modes.values():
            mode_tags = {tag.lower() for tag in mode.tags or []}
            if tags_lower & mode_tags:
                return mode
        for mode in modes.values():
            mode_tags = {tag.lower() for tag in mode.tags or []}
            if any(any(alias in seed_tag for seed_tag in tags_lower) for alias in mode_tags):
                return mode

    # Deterministic fallback to first alphabetic id.
    first_key = sorted(modes.keys())[0]
    return modes[first_key]


@dataclass
class LeadV2Assets:
    modes: Dict[str, LeadModeConfig]
    rhythm_templates: List[RhythmTemplate]
    contour_templates: List[ContourTemplate]


def load_lead_v2_assets(config_dir: Path) -> Optional[LeadV2Assets]:
    modes = load_lead_modes_v2(config_dir / "lead_modes_v2.json")
    rhythms = load_rhythm_templates_v2(config_dir / "lead_rhythm_templates_v2.json")
    contours = load_contour_templates_v2(config_dir / "lead_contour_templates_v2.json")
    if not modes or not rhythms or not contours:
        return None
    return LeadV2Assets(modes=modes, rhythm_templates=rhythms, contour_templates=contours)
