from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class LeadMode:
    """Configuration for a lead-line rhythmic/melodic personality."""

    name: str
    target_notes_per_bar: Tuple[int, int]
    max_consecutive_notes: int
    register_low: int
    register_high: int
    rhythmic_personality: str
    preferred_slot_weights: Dict[str, float]
    phrase_length_bars: int
    contour_profiles: List[str]
    call_response_style: str


def load_lead_modes(raw: Dict[str, Dict]) -> Dict[str, LeadMode]:
    """Construct LeadMode instances from JSON-loaded dict.

    The JSON file is expected to map mode names to configuration dicts.
    This helper keeps parsing logic in one place so tests can exercise it
    without touching the filesystem.
    """

    modes: Dict[str, LeadMode] = {}
    for name, cfg in (raw or {}).items():
        tnpb = cfg.get("target_notes_per_bar", [2, 4])
        if len(tnpb) != 2:
            tnpb = [2, 4]
        mode = LeadMode(
            name=name,
            target_notes_per_bar=(int(tnpb[0]), int(tnpb[1])),
            max_consecutive_notes=int(cfg.get("max_consecutive_notes", 3)),
            register_low=int(cfg.get("register_low", 60)),
            register_high=int(cfg.get("register_high", 84)),
            rhythmic_personality=str(cfg.get("rhythmic_personality", "generic")),
            preferred_slot_weights=dict(cfg.get("preferred_slot_weights", {})),
            phrase_length_bars=int(cfg.get("phrase_length_bars", 4)),
            contour_profiles=list(cfg.get("contour_profiles", [])),
            call_response_style=str(cfg.get("call_response_style", "mild")),
        )
        modes[name] = mode
    return modes


def select_lead_mode(tags: List[str], modes: Dict[str, LeadMode]) -> LeadMode:
    """Select a LeadMode given seed tags and available modes.

    This is a simple tag→mode heuristic that will be extended later, but we
    keep a basic implementation here so tests can verify behaviour early.
    """

    tags_lower = {t.lower() for t in (tags or [])}

    # Priority mapping from tags to mode names.
    priority = [
        ("lyrical", "Lyrical Call/Response Lead"),
        ("hypnotic", "Hypnotic Arp Lead"),
        ("rolling", "Rolling Arp Lead"),
        ("minimal", "Minimal Stab Lead"),
    ]
    for tag, mode_name in priority:
        if tag in tags_lower and mode_name in modes:
            return modes[mode_name]

    # Fallback: prefer Minimal Stab Lead if present, else any mode.
    if "Minimal Stab Lead" in modes:
        return modes["Minimal Stab Lead"]
    # Last resort: arbitrary first mode.
    if modes:
        return next(iter(modes.values()))

    # If no modes are defined at all, return a trivial default.
    return LeadMode(
        name="Default Lead",
        target_notes_per_bar=(2, 4),
        max_consecutive_notes=3,
        register_low=60,
        register_high=84,
        rhythmic_personality="generic",
        preferred_slot_weights={},
        phrase_length_bars=4,
        contour_profiles=["arch"],
        call_response_style="mild",
    )
