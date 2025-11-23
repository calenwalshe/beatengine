"""Control resolution and bass mode profiles for bass_v2 generator."""
from __future__ import annotations

from typing import Dict, Any, Optional
from .bass_v2_types import (
    ResolvedControls,
    TheoryControls,
    RhythmControls,
    MelodyControls,
    ArticulationControls,
    PatternVariationControls,
    DrumInteractionControls,
    ModeAndBehaviorControls,
    OutputControls,
    AdvancedOverrides,
)

# Qualitative-to-quantitative mapping table
QUALITATIVE_MAP = {
    "very_low": 0.1,
    "low": 0.25,
    "medium_low": 0.35,
    "medium": 0.5,
    "medium_high": 0.7,
    "high": 0.8,
    "very_high": 0.95,
}


def map_qualitative(value: Any) -> Any:
    """Map qualitative strings to numeric values."""
    if isinstance(value, str) and value in QUALITATIVE_MAP:
        return QUALITATIVE_MAP[value]
    return value


# Bass mode profiles from bass_v1.json spec
BASS_MODE_PROFILES = {
    "sub_anchor": {
        "description": "Low, solid sub lines that mostly reinforce the root on strong beats, with minimal movement.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.1,
                "note_density": 0.1,
                "onbeat_offbeat_balance": -0.8,  # onbeat_heavy
                "pattern_length_bars": 1,
            },
            "melody_controls": {
                "note_range_octaves": 1,
                "interval_jump_magnitude": 0.25,
                "root_note_emphasis": 0.95,
            },
            "articulation_controls": {
                "velocity_normal": 80,
                "velocity_accent": 90,
                "accent_chance": 0.25,
                "gate_length": 0.8,
                "slide_chance": 0.1,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.95,
            "downbeat_priority": 0.95,
            "offbeat_syncopation": 0.1,
        },
    },
    "root_fifth_driver": {
        "description": "Classic EDM driver patterns emphasizing root and fifth, moderate movement and energy.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.5,
                "note_density": 0.5,
                "onbeat_offbeat_balance": 0.0,  # balanced
                "pattern_length_bars": 2,
            },
            "melody_controls": {
                "note_range_octaves": 1,
                "interval_jump_magnitude": 0.5,
                "root_note_emphasis": 0.8,
            },
            "articulation_controls": {
                "velocity_normal": 80,
                "velocity_accent": 100,
                "accent_chance": 0.5,
                "gate_length": 0.5,
                "slide_chance": 0.1,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.5,
            "downbeat_priority": 0.8,
            "offbeat_syncopation": 0.5,
        },
    },
    "pocket_groove": {
        "description": "Groovy patterns that sit in the pocket with drums, focusing on syncopation and interaction with hats/snare.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.7,
                "note_density": 0.7,
                "onbeat_offbeat_balance": 0.5,  # offbeat_favored
                "pattern_length_bars": 2,
            },
            "melody_controls": {
                "note_range_octaves": 1,
                "interval_jump_magnitude": 0.4,
                "root_note_emphasis": 0.5,
            },
            "articulation_controls": {
                "velocity_normal": 80,
                "velocity_accent": 115,
                "accent_chance": 0.8,
                "gate_length": 0.4,
                "slide_chance": 0.5,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.7,
            "downbeat_priority": 0.5,
            "offbeat_syncopation": 0.8,
            "hat_sync": 0.8,
        },
    },
    "rolling_ostinato": {
        "description": "Continuous rolling bass patterns (often 1/8 or 1/16 based) that drive the track forward.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.8,
                "note_density": 0.8,
                "onbeat_offbeat_balance": 0.2,  # balanced_or_offbeat
                "pattern_length_bars": 4,
            },
            "melody_controls": {
                "note_range_octaves": 2,
                "interval_jump_magnitude": 0.7,
                "root_note_emphasis": 0.5,
            },
            "articulation_controls": {
                "velocity_normal": 85,
                "velocity_accent": 105,
                "accent_chance": 0.5,
                "gate_length": 0.6,
                "slide_chance": 0.7,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.5,
            "downbeat_priority": 0.5,
            "offbeat_syncopation": 0.7,
        },
    },
    "offbeat_stabs": {
        "description": "Sparse, punchy stabs placed mostly on offbeats or gaps in the drums.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.5,
                "note_density": 0.25,
                "onbeat_offbeat_balance": 0.9,  # strongly_offbeat
                "pattern_length_bars": 1,
            },
            "melody_controls": {
                "note_range_octaves": 1,
                "interval_jump_magnitude": 0.5,
                "root_note_emphasis": 0.8,
            },
            "articulation_controls": {
                "velocity_normal": 105,
                "velocity_accent": 120,
                "accent_chance": 0.8,
                "gate_length": 0.3,
                "slide_chance": 0.1,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.95,
            "downbeat_priority": 0.2,
            "offbeat_syncopation": 0.95,
            "gap_preference": 0.95,
        },
    },
    "lead_ish": {
        "description": "Bass that behaves almost like a lead: melodic, wide range, and expressive.",
        "default_control_targets": {
            "rhythm_controls": {
                "rhythmic_complexity": 0.8,
                "note_density": 0.7,
                "onbeat_offbeat_balance": 0.0,  # balanced
                "pattern_length_bars": 4,
            },
            "melody_controls": {
                "note_range_octaves": 2,
                "interval_jump_magnitude": 0.8,
                "root_note_emphasis": 0.4,
            },
            "articulation_controls": {
                "velocity_normal": 80,
                "velocity_accent": 105,
                "accent_chance": 0.7,
                "gate_length": 0.6,
                "slide_chance": 0.8,
            },
        },
        "step_scoring_bias": {
            "kick_avoid": 0.5,
            "downbeat_priority": 0.5,
            "offbeat_syncopation": 0.8,
        },
    },
}


def resolve_controls(
    style_or_genre_preset: Optional[Dict[str, Any]] = None,
    bass_mode_name: Optional[str] = None,
    user_overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedControls:
    """Resolve controls following the spec's control resolution order.

    Order: style_preset -> bass_mode_profile defaults -> user_overrides -> final ResolvedControls.
    """
    # Start with default controls
    result = ResolvedControls()

    # Apply style/genre preset
    if style_or_genre_preset:
        _apply_dict_to_controls(result, style_or_genre_preset)

    # Apply bass mode profile defaults
    if bass_mode_name and bass_mode_name in BASS_MODE_PROFILES:
        profile = BASS_MODE_PROFILES[bass_mode_name]
        targets = profile.get("default_control_targets", {})
        _apply_dict_to_controls(result, targets)

    # Apply user overrides (highest priority)
    if user_overrides:
        _apply_dict_to_controls(result, user_overrides)

    return result


def _apply_dict_to_controls(controls: ResolvedControls, config: Dict[str, Any]) -> None:
    """Apply a config dict to ResolvedControls, mapping qualitative values."""
    for group_name, group_values in config.items():
        if not isinstance(group_values, dict):
            continue

        # Get the corresponding control group
        if hasattr(controls, group_name):
            control_group = getattr(controls, group_name)
            for key, value in group_values.items():
                if hasattr(control_group, key):
                    # Map qualitative to quantitative
                    mapped_value = map_qualitative(value)
                    setattr(control_group, key, mapped_value)


def select_mode_from_energy(drum_energy_bar: float) -> str:
    """Select a bass mode based on drum energy.

    Low energy (< 4): sub_anchor
    Medium energy (4-8): root_fifth_driver or pocket_groove
    High energy (> 8): rolling_ostinato or lead_ish
    """
    if drum_energy_bar < 4:
        return "sub_anchor"
    elif drum_energy_bar < 8:
        return "root_fifth_driver"
    else:
        return "rolling_ostinato"
