"""Bass generator API wrapper for Flask backend.

Provides high-level wrapper around bass_v2 generator that:
- Accepts simplified parameters from web UI
- Handles drum pattern lookup/parsing
- Calls bass_v2 generator
- Converts output to MIDI files
- Returns structured results
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import random

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext
from src.techno_engine.simple_midi_writer import write_simple_midi
from web_ui.backend.drum_patterns import DRUM_PATTERNS


def generate_bass_with_params(
    drum_pattern_name: str = "berlin_syncopated",
    theory_params: Optional[Dict[str, Any]] = None,
    control_params: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate bass MIDI from simplified parameters.

    Args:
        drum_pattern_name: Name of drum pattern from DRUM_PATTERNS, or "custom"
        theory_params: Dictionary with key_scale, tempo_bpm, chord_progression
        control_params: Dictionary of bass_v2 control parameters
        output_dir: Directory to save MIDI file (defaults to current dir)
        seed: Random seed for reproducibility

    Returns:
        Dictionary with:
        - success: bool
        - filename: str (MIDI filename)
        - filepath: str (full path to MIDI file)
        - metadata: dict (generation metadata)
        - preview: dict (note count, pitch range, etc.)
        - error: str (if success=False)
    """
    try:
        # 1. Get drum pattern
        if drum_pattern_name in DRUM_PATTERNS:
            drum_pattern = DRUM_PATTERNS[drum_pattern_name]
        else:
            # Assume custom pattern provided in control_params
            drum_pattern = control_params.get("custom_drum_pattern")
            if not drum_pattern:
                return {
                    "success": False,
                    "error": f"Unknown drum pattern: {drum_pattern_name}"
                }

        # 2. Build theory context
        theory_params = theory_params or {}
        theory_context = TheoryContext(
            key_scale=theory_params.get("key_scale", "D_minor"),
            tempo_bpm=theory_params.get("tempo_bpm", 130.0),
            chord_progression=theory_params.get("chord_progression"),
        )

        # 3. Generate bass
        clip = generate_bass_midi_from_drums(
            m4_drum_output=drum_pattern,
            theory_context=theory_context,
            global_controls=control_params or {},
            seed=seed or random.randint(1, 999999),
        )

        # 4. Convert to MIDI tuples for simple_midi_writer
        # simple_midi_writer expects: List[Tuple[note_number, start_tick, duration_tick, velocity]]
        ppq = 480
        midi_tuples = []
        for note in clip.notes:
            ticks_per_beat = ppq
            start_tick = int(note.start_beat * ticks_per_beat)
            duration_tick = int(note.duration_beats * ticks_per_beat)
            midi_tuples.append((note.pitch, start_tick, max(1, duration_tick), note.velocity))

        # 5. Write MIDI file
        if output_dir is None:
            output_dir = Path.cwd()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_name = clip.metadata.get("mode_per_bar", ["unknown"])[0]
        filename = f"bass_{timestamp}_{mode_name}.mid"
        filepath = output_dir / filename

        write_simple_midi(midi_tuples, theory_context.tempo_bpm, str(filepath))

        # 6. Build preview info
        preview = {
            "note_count": len(clip.notes),
            "length_bars": clip.length_bars,
            "length_seconds": round((clip.length_bars * 4.0 / theory_context.tempo_bpm) * 60, 2),
            "pitch_range": {
                "min": min(n.pitch for n in clip.notes) if clip.notes else 0,
                "max": max(n.pitch for n in clip.notes) if clip.notes else 0,
            },
            "velocity_range": {
                "min": min(n.velocity for n in clip.notes) if clip.notes else 0,
                "max": max(n.velocity for n in clip.notes) if clip.notes else 0,
            },
            "modes_used": clip.metadata.get("mode_per_bar", []),
        }

        # 7. Return result
        return {
            "success": True,
            "filename": filename,
            "filepath": str(filepath),
            "metadata": clip.metadata,
            "preview": preview,
            "theory_context": {
                "key_scale": theory_context.key_scale,
                "tempo_bpm": theory_context.tempo_bpm,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def get_default_controls() -> Dict[str, Any]:
    """Return default control parameters for web UI initialization."""
    return {
        "mode_and_behavior_controls": {
            "strategy": "auto_from_drums",
            "fixed_mode": None,
            "per_bar_modes": None,
        },
        "rhythm_controls": {
            "rhythmic_complexity": 0.5,
            "note_density": 0.5,
            "onbeat_offbeat_balance": 0.0,
            "kick_interaction_mode": "avoid_kick",
            "swing_amount": 0.0,
            "groove_depth": 0.5,
            "use_triplets": False,
            "pattern_length_bars": 2,
        },
        "melody_controls": {
            "note_range_octaves": 1,
            "base_octave": 2,
            "root_note_emphasis": 0.8,
            "scale_degree_bias": None,
            "interval_jump_magnitude": 0.4,
            "melodic_intensity": 0.5,
        },
        "articulation_controls": {
            "velocity_normal": 80,
            "velocity_accent": 110,
            "accent_chance": 0.3,
            "accent_pattern_mode": "offbeat_focused",
            "gate_length": 0.5,
            "tie_notes": False,
            "slide_chance": 0.1,
            "humanize_timing": 0.1,
            "humanize_velocity": 0.1,
        },
        "theory_controls": {
            "key_scale": "D_minor",
            "chord_progression": None,
            "harmonic_strictness": 0.9,
            "chord_tone_priority": 0.8,
            "minorness": 0.5,
        },
        "drum_interaction_controls": {
            "kick_avoid_strength": 0.8,
            "snare_backbeat_preference": 0.5,
            "hat_sync_strength": 0.5,
        },
        "output_controls": {
            "max_notes_per_bar": 16,
            "return_debug_metadata": False,
            "pattern_memory_slot": None,
        }
    }


def get_control_schema() -> Dict[str, Any]:
    """Return schema describing all available controls for web UI rendering.

    Each control includes:
    - type: "slider", "toggle", "select", "text"
    - min/max: for sliders
    - options: for selects
    - default: default value
    - description: help text
    """
    return {
        "mode_and_behavior_controls": {
            "strategy": {
                "type": "select",
                "options": ["auto_from_drums", "fixed_mode", "per_bar_explicit"],
                "default": "auto_from_drums",
                "description": "How to select bass mode: auto from drum energy, fixed mode, or per-bar explicit"
            },
            "fixed_mode": {
                "type": "select",
                "options": [None, "sub_anchor", "root_fifth_driver", "pocket_groove", "rolling_ostinato", "offbeat_stabs", "lead_ish"],
                "default": None,
                "description": "Fixed bass mode (when strategy=fixed_mode)"
            }
        },
        "rhythm_controls": {
            "rhythmic_complexity": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Rhythmic complexity: higher = more syncopation and offbeat notes"
            },
            "note_density": {
                "type": "slider",
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Note density: 0.1 = very sparse, 1.0 = every 16th note"
            },
            "onbeat_offbeat_balance": {
                "type": "slider",
                "min": -1.0,
                "max": 1.0,
                "step": 0.1,
                "default": 0.0,
                "description": "Onbeat/offbeat balance: -1 = all onbeat, +1 = all offbeat"
            },
            "kick_interaction_mode": {
                "type": "select",
                "options": ["avoid_kick", "reinforce_kick", "balanced"],
                "default": "avoid_kick",
                "description": "How bass interacts with kick drum"
            },
            "swing_amount": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.0,
                "description": "Swing/shuffle amount"
            },
            "groove_depth": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Groove depth: timing micro-adjustments"
            },
            "use_triplets": {
                "type": "toggle",
                "default": False,
                "description": "Allow triplet rhythms"
            },
            "pattern_length_bars": {
                "type": "slider",
                "min": 1,
                "max": 8,
                "step": 1,
                "default": 2,
                "description": "Pattern length in bars"
            }
        },
        "melody_controls": {
            "note_range_octaves": {
                "type": "slider",
                "min": 1,
                "max": 3,
                "step": 1,
                "default": 1,
                "description": "Octave range for bass notes"
            },
            "base_octave": {
                "type": "slider",
                "min": 1,
                "max": 3,
                "step": 1,
                "default": 2,
                "description": "Base octave (1=very low, 3=higher bass)"
            },
            "root_note_emphasis": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.8,
                "description": "Root note emphasis: higher = more root notes"
            },
            "interval_jump_magnitude": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.4,
                "description": "Interval jump size: higher = bigger melodic leaps"
            },
            "melodic_intensity": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Melodic intensity: higher = more melodic movement"
            }
        },
        "articulation_controls": {
            "velocity_normal": {
                "type": "slider",
                "min": 30,
                "max": 127,
                "step": 1,
                "default": 80,
                "description": "Normal note velocity"
            },
            "velocity_accent": {
                "type": "slider",
                "min": 30,
                "max": 127,
                "step": 1,
                "default": 110,
                "description": "Accent note velocity"
            },
            "accent_chance": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.3,
                "description": "Accent probability"
            },
            "accent_pattern_mode": {
                "type": "select",
                "options": ["random", "offbeat_focused", "downbeat_focused"],
                "default": "offbeat_focused",
                "description": "Accent pattern mode"
            },
            "gate_length": {
                "type": "slider",
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Note gate length: 0.1 = very short, 1.0 = full length"
            },
            "tie_notes": {
                "type": "toggle",
                "default": False,
                "description": "Tie notes together"
            },
            "slide_chance": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.1,
                "description": "Slide/glide probability"
            },
            "humanize_timing": {
                "type": "slider",
                "min": 0.0,
                "max": 0.5,
                "step": 0.05,
                "default": 0.1,
                "description": "Timing humanization amount"
            },
            "humanize_velocity": {
                "type": "slider",
                "min": 0.0,
                "max": 0.5,
                "step": 0.05,
                "default": 0.1,
                "description": "Velocity humanization amount"
            }
        },
        "theory_controls": {
            "key_scale": {
                "type": "select",
                "options": ["C_minor", "D_minor", "E_minor", "F_minor", "G_minor", "A_minor", "B_minor",
                           "C_major", "D_major", "E_major", "F_major", "G_major", "A_major", "B_major",
                           "D_dorian", "E_phrygian", "G_mixolydian"],
                "default": "D_minor",
                "description": "Key and scale"
            },
            "harmonic_strictness": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.9,
                "description": "Harmonic strictness: higher = stricter adherence to scale"
            },
            "chord_tone_priority": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.8,
                "description": "Chord tone priority (when chord progression provided)"
            },
            "minorness": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Minor feel intensity"
            }
        },
        "drum_interaction_controls": {
            "kick_avoid_strength": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.8,
                "description": "Kick avoidance strength (when mode=avoid_kick)"
            },
            "snare_backbeat_preference": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Snare/backbeat preference"
            },
            "hat_sync_strength": {
                "type": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "description": "Hi-hat sync strength"
            }
        }
    }
