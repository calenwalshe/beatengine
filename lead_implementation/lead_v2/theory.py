from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class KeySpec:
    """Represents the musical key and scale configuration.

    Attributes:
        root_pc: Pitch class of root (0-11, C=0).
        scale_type: Name of scale ('aeolian', 'dorian', 'phrygian', 'minor_pent', etc.).
        scale_degrees: Semitone offsets (0-11) for the scale in one octave.
        default_root_octave: Reference octave for degree-to-midi mapping.
    """
    root_pc: int
    scale_type: str
    scale_degrees: List[int]
    default_root_octave: int = 4


@dataclass
class HarmonyBar:
    """Harmony information for a single bar.

    This version assumes static tonic minor harmony but allows
    future extension to more complex harmony per bar.
    """
    tonic_degree: int = 1
    chord_tone_degrees: List[int] = field(default_factory=lambda: [1, 3, 5, 7])
    color_tone_degrees: List[int] = field(default_factory=lambda: [2, 4, 6, 9, 11, 13])
    function_label: str = "tonic"


@dataclass
class HarmonyTrack:
    """Harmony for the entire lead section, per bar."""
    per_bar: List[HarmonyBar]


@dataclass
class MetricPosition:
    bar_index: int
    step_in_bar: int


@dataclass
class LeadNoteLogical:
    """Internal logical representation of a lead note before MIDI mapping."""
    phrase_id: int
    metric_position: MetricPosition
    role: str  # 'CALL' | 'RESP'
    phrase_position: str  # 'start' | 'inner' | 'end'
    beat_strength: str  # 'strong' | 'weak'
    tension_label: str  # 'low' | 'medium' | 'high' | 'resolve'
    contour_index: int

    tone_category: Optional[str] = None  # 'chord_tone' | 'color' | 'passing'
    degree: Optional[int] = None
    octave_offset: Optional[int] = None
    contour_degree: Optional[int] = None
    duration_steps: int = 1
    accent: float = 0.5
    anchor_type: Optional[str] = None
    min_gap_steps: int = 1
    slot_jitter: int = 1
    template_refs: Dict[str, str] = field(default_factory=dict)


@dataclass
class LeadNoteEvent:
    """Final MIDI-ready representation of a lead note event."""
    pitch: int
    velocity: int
    start_tick: int
    duration: int

    # Optional debug / structural metadata
    phrase_id: Optional[int] = None
    role: Optional[str] = None
    degree: Optional[int] = None
    tags: Dict[str, object] = field(default_factory=dict)


# --- Helper / placeholder functions ---


def build_scale_degrees(scale_type: str) -> List[int]:
    """Return semitone offsets for the given scale type.

    TODO: implement full mapping according to roadmap.
    """
    mapping = {
        "aeolian": [0, 2, 3, 5, 7, 8, 10],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "lydian": [0, 2, 4, 6, 7, 9, 11],
        "ionian": [0, 2, 4, 5, 7, 9, 11],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "locrian": [0, 1, 3, 5, 6, 8, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
        "minor_pent": [0, 3, 5, 7, 10],
        "blues_minor": [0, 3, 5, 6, 7, 10],
    }
    return mapping.get(scale_type, [0, 2, 4, 5, 7, 9, 11])


def degree_to_pitch_class(key: KeySpec, degree: int) -> int:
    """Map a scale degree to an absolute pitch class (0-11).

    This is a simplified helper; full implementation should handle 9/11/13
    and degrees beyond 7 by folding into base scale degrees.
    """
    idx = (degree - 1) % len(key.scale_degrees)
    return (key.root_pc + key.scale_degrees[idx]) % 12


def is_in_scale(key: KeySpec, midi_pitch: int) -> bool:
    """Return True if midi_pitch belongs to the given KeySpec scale.

    This checks pitch class membership only.
    """
    pc = midi_pitch % 12
    return pc in [(key.root_pc + d) % 12 for d in key.scale_degrees]


def build_harmony_track(num_bars: int, key: KeySpec, functions: Optional[List[str]] = None) -> HarmonyTrack:
    """Create a deterministic harmony track cycling through supplied functions."""
    if not functions:
        functions = ["tonic", "predominant", "dominant", "tonic"]
    bars: List[HarmonyBar] = []
    for i in range(num_bars):
        func = functions[i % len(functions)]
        if func == "tonic":
            chord = [1, 3, 5, 7]
        elif func == "predominant":
            chord = [2, 4, 6]
        else:
            chord = [5, 7, 2]
        bars.append(
            HarmonyBar(
                tonic_degree=1,
                chord_tone_degrees=chord,
                color_tone_degrees=[2, 4, 6, 9, 11, 13],
                function_label=func,
            )
        )
    return HarmonyTrack(per_bar=bars)


def allowed_pitch_classes(key: KeySpec) -> List[int]:
    """Return the pitch classes allowed by the key."""
    return [(key.root_pc + deg) % 12 for deg in key.scale_degrees]


def clamp_degree(degree: int, scale_size: int) -> int:
    """Clamp degree to a positive diatonic index."""
    if degree < 1:
        return 1
    if degree > scale_size:
        return ((degree - 1) % scale_size) + 1
    return degree


def choose_register_pitch(
    pitch_class: int,
    register_low: int,
    register_high: int,
    gravity_center: int,
    drift: int = 0,
    previous_pitch: Optional[int] = None,
) -> int:
    """Map a pitch class to an in-register MIDI note near gravity+drift."""
    candidates: List[int] = []
    for midi in range(register_low, register_high + 1):
        if midi % 12 == pitch_class:
            candidates.append(midi)
    if not candidates:
        return max(register_low, min(register_high, gravity_center + drift))

    target = gravity_center + drift

    def _score(val: int) -> Tuple[int, int]:
        primary = abs(val - target)
        secondary = abs(val - previous_pitch) if previous_pitch is not None else 0
        return (primary, secondary)

    candidates.sort(key=_score)
    return candidates[0]
