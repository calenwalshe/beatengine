"""Core data structures for bass_v2 generator (from bass_v1.json spec)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class DrumStep:
    """Represents a single 16th-note step in a drum pattern."""
    kick: bool = False
    hat: bool = False
    snare: bool = False
    velocity: Optional[int] = None


@dataclass
class DrumBar:
    """16-step bar of drum pattern."""
    steps: List[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])


@dataclass
class SlotFeature:
    """Rich feature set for a single slot/step in the bar grid."""
    index: int
    has_kick: bool = False
    has_hat: bool = False
    has_snare: bool = False
    is_downbeat: bool = False
    is_backbeat: bool = False
    is_offbeat: bool = False
    is_gap: bool = False
    drum_energy_local: float = 0.0


@dataclass
class BarSlotGrid:
    """16-step slot grid with computed features for one bar."""
    bar_index: int
    slots: List[SlotFeature] = field(default_factory=lambda: [SlotFeature(i) for i in range(16)])
    drum_energy_bar: float = 0.0


@dataclass
class TheoryControls:
    """Music theory controls."""
    key_scale: str = "A_minor"
    chord_progression: Optional[List[str]] = None
    harmonic_strictness: float = 0.9
    chord_tone_priority: float = 0.8
    minorness: float = 0.5


@dataclass
class RhythmControls:
    """Rhythm and density controls."""
    rhythmic_complexity: float = 0.5
    note_density: float = 0.5
    onbeat_offbeat_balance: float = 0.0  # -1=onbeat, 1=offbeat
    kick_interaction_mode: str = "avoid_kick"  # avoid_kick, reinforce_kick, balanced
    swing_amount: float = 0.0
    groove_depth: float = 0.5
    use_triplets: bool = False
    pattern_length_bars: int = 2


@dataclass
class MelodyControls:
    """Pitch range and melodic behavior controls."""
    note_range_octaves: int = 1
    base_octave: int = 2
    root_note_emphasis: float = 0.8
    scale_degree_bias: Optional[Dict[str, float]] = None
    interval_jump_magnitude: float = 0.4
    melodic_intensity: float = 0.5


@dataclass
class ArticulationControls:
    """Velocity, gate, accents, and slides."""
    velocity_normal: int = 80
    velocity_accent: int = 110
    accent_chance: float = 0.3
    accent_pattern_mode: str = "offbeat_focused"  # random, offbeat_focused, downbeat_focused
    gate_length: float = 0.5
    tie_notes: bool = False
    slide_chance: float = 0.1
    humanize_timing: float = 0.1
    humanize_velocity: float = 0.1


@dataclass
class PatternVariationControls:
    """Pattern variation and randomization."""
    variation_amount: float = 0.5
    regeneration_mode: str = "one_shot"  # one_shot, infinity_mode
    notes_to_change_per_regen: int = 4
    randomize_pitch: bool = True
    randomize_rhythm: bool = True
    randomize_velocity: bool = True
    randomize_density: bool = True
    lock_steps: List[int] = field(default_factory=list)
    lock_notes: List[Any] = field(default_factory=list)


@dataclass
class DrumInteractionControls:
    """Drum interaction strengths."""
    kick_avoid_strength: float = 0.8
    snare_backbeat_preference: float = 0.5
    hat_sync_strength: float = 0.5


@dataclass
class ModeAndBehaviorControls:
    """High-level bass mode controls."""
    strategy: str = "auto_from_drums"  # auto_from_drums, fixed_mode, per_bar_explicit
    fixed_mode: Optional[str] = None
    per_bar_modes: Optional[List[str]] = None


@dataclass
class OutputControls:
    """Output configuration."""
    max_notes_per_bar: int = 16
    return_debug_metadata: bool = False
    pattern_memory_slot: Optional[int] = None


@dataclass
class AdvancedOverrides:
    """Expert-only overrides."""
    step_scoring_weights: Optional[Dict[str, float]] = None
    mode_profile_overrides: Optional[Dict[str, Any]] = None


@dataclass
class ResolvedControls:
    """Final resolved control set after merging presets, mode defaults, and user overrides."""
    theory_controls: TheoryControls = field(default_factory=TheoryControls)
    rhythm_controls: RhythmControls = field(default_factory=RhythmControls)
    melody_controls: MelodyControls = field(default_factory=MelodyControls)
    articulation_controls: ArticulationControls = field(default_factory=ArticulationControls)
    pattern_variation_controls: PatternVariationControls = field(default_factory=PatternVariationControls)
    drum_interaction_controls: DrumInteractionControls = field(default_factory=DrumInteractionControls)
    mode_and_behavior_controls: ModeAndBehaviorControls = field(default_factory=ModeAndBehaviorControls)
    output_controls: OutputControls = field(default_factory=OutputControls)
    advanced_overrides: AdvancedOverrides = field(default_factory=AdvancedOverrides)


@dataclass
class BassModeAssignment:
    """Bass mode and resolved controls for a specific bar."""
    bar_index: int
    mode_name: str
    resolved_controls: ResolvedControls


@dataclass
class ScoredSlot:
    """Step with computed score and selection flag."""
    slot: SlotFeature
    score: float = 0.0
    selected: bool = False


@dataclass
class BassNote:
    """A single bass note event."""
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TheoryContext:
    """Music theory context for generation."""
    key_scale: str = "A_minor"
    chord_progression: Optional[List[str]] = None
    tempo_bpm: float = 128.0


@dataclass
class BassMidiClip:
    """Output bass MIDI clip."""
    notes: List[BassNote] = field(default_factory=list)
    length_bars: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
