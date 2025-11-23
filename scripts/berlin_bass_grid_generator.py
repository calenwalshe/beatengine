"""Berlin Techno Bass Grid Generator - Systematic Parameter Exploration

Generates 24 bass variations exploring modern Berlin techno parameters:
- 3 density levels (medium, high, very high)
- 2 syncopation levels (medium, high)
- 2 bass modes (pocket_groove, rolling_ostinato)
- 2 articulation styles (punchy, driving)

All based on a syncopated Berlin-style drum groove at 130 BPM.
"""

import json
import os
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Any

from src.techno_engine.bass_v2 import generate_bass_midi_from_drums, convert_to_midi_events
from src.techno_engine.bass_v2_types import TheoryContext
from src.techno_engine.simple_midi_writer import write_simple_midi, write_multi_channel_midi


# ============================================================================
# BERLIN DRUM PATTERN (Syncopated, 130 BPM, 4 bars)
# ============================================================================

def create_berlin_drum_pattern() -> Dict[str, Any]:
    """Create a syncopated Berlin techno drum pattern.

    Characteristics:
    - Syncopated kick with ghost hits and offbeat placements
    - Offbeat hi-hats with Berlin swing feel
    - Sparse backbeat claps
    - 130 BPM, 4 bars
    """
    bars = []

    # Bar 1: Standard with syncopation
    bar1_kicks = {0, 4, 7, 12}  # Syncopated 3rd kick
    bar1_hats = {2, 6, 10, 14}  # Offbeats
    bar1_snares = {12}  # Backbeat

    # Bar 2: Add ghost kick
    bar2_kicks = {0, 3, 4, 8, 12}  # Ghost on 3
    bar2_hats = {2, 6, 10, 14}
    bar2_snares = {12}

    # Bar 3: More syncopation
    bar3_kicks = {0, 4, 6, 8, 12}  # Offbeat on 6
    bar3_hats = {2, 6, 10, 14}
    bar3_snares = {4, 12}  # Double clap

    # Bar 4: Return to driving
    bar4_kicks = {0, 4, 8, 12}  # Four on floor
    bar4_hats = {2, 6, 10, 14}
    bar4_snares = {12}

    patterns = [
        (bar1_kicks, bar1_hats, bar1_snares),
        (bar2_kicks, bar2_hats, bar2_snares),
        (bar3_kicks, bar3_hats, bar3_snares),
        (bar4_kicks, bar4_hats, bar4_snares),
    ]

    for kicks, hats, snares in patterns:
        steps = []
        for i in range(16):
            step = {
                "kick": i in kicks,
                "hat": i in hats,
                "snare": i in snares,
                "velocity": 110 if i in kicks else (85 if i in hats else 100)
            }
            steps.append(step)
        bars.append({"steps": steps})

    return {"bars": bars}


def export_drum_midi(drum_pattern: Dict[str, Any], output_path: str, bpm: float = 130.0):
    """Export drum pattern to MIDI for reference."""
    ppq = 480

    from src.techno_engine.timebase import ticks_per_bar

    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16

    # Collect notes for each channel
    kick_notes = []  # Channel 0
    hat_notes = []   # Channel 1
    snare_notes = []  # Channel 2

    for bar_idx, bar in enumerate(drum_pattern["bars"]):
        bar_start = bar_idx * bar_ticks
        for step_idx, step in enumerate(bar["steps"]):
            tick = bar_start + step_idx * step_ticks

            # Kick (note 36, channel 0)
            if step["kick"]:
                kick_notes.append((36, tick, step_ticks // 2, step.get("velocity", 100), 0))

            # Hat (note 42, channel 1)
            if step["hat"]:
                hat_notes.append((42, tick, step_ticks // 4, step.get("velocity", 80), 1))

            # Snare (note 38, channel 2)
            if step["snare"]:
                snare_notes.append((38, tick, step_ticks // 2, step.get("velocity", 100), 2))

    # Write multi-channel MIDI
    write_multi_channel_midi([kick_notes, hat_notes, snare_notes], bpm, output_path)


# ============================================================================
# PARAMETER GRID DEFINITION
# ============================================================================

GRID_DIMENSIONS = {
    "density": {
        "medium": 0.50,      # ~8 notes/bar
        "high": 0.65,        # ~10 notes/bar
        "very_high": 0.80,   # ~13 notes/bar
    },
    "syncopation": {
        "medium": 0.65,      # Groovy syncopation
        "high": 0.85,        # Heavily syncopated
    },
    "mode": {
        "pocket_groove": "pocket_groove",
        "rolling_ostinato": "rolling_ostinato",
    },
    "articulation": {
        "punchy": {"gate": 0.35, "accent_chance": 0.7},
        "driving": {"gate": 0.55, "accent_chance": 0.5},
    }
}

# Berlin base configuration (modern energetic style)
BERLIN_BASE_CONFIG = {
    "rhythm_controls": {
        "kick_interaction_mode": "avoid_kick",
        # note_density will be varied
        # rhythmic_complexity will be varied
    },
    "melody_controls": {
        "root_note_emphasis": 0.6,      # Some melodic movement
        "interval_jump_magnitude": 0.5,  # Balanced
        "note_range_octaves": 1,         # Focused bass register
    },
    "articulation_controls": {
        "velocity_normal": 95,
        "velocity_accent": 118,
        # accent_chance will be varied
        # gate_length will be varied
        "slide_chance": 0.2,
    },
    "drum_interaction_controls": {
        "kick_avoid_strength": 0.8,
        "hat_sync_strength": 0.6,        # Groove with offbeat hats
        "snare_backbeat_preference": 0.5,
    },
    "mode_and_behavior_controls": {
        "strategy": "fixed_mode",
        # fixed_mode will be varied
    }
}


# ============================================================================
# GRID GENERATION
# ============================================================================

def generate_grid_variations(
    drum_pattern: Dict[str, Any],
    output_dir: Path,
    bpm: float = 130.0,
    key: str = "D_minor"
) -> List[Dict[str, Any]]:
    """Generate all grid variations and return metadata."""

    theory = TheoryContext(key_scale=key, tempo_bpm=bpm)
    ppq = 480

    # Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    variation_count = 0

    # Iterate through all combinations
    for density_name, density_val in GRID_DIMENSIONS["density"].items():
        for syncopation_name, syncopation_val in GRID_DIMENSIONS["syncopation"].items():
            for mode_name, mode_val in GRID_DIMENSIONS["mode"].items():
                for artic_name, artic_val in GRID_DIMENSIONS["articulation"].items():

                    variation_count += 1

                    # Build controls for this variation
                    controls = {
                        **BERLIN_BASE_CONFIG,
                        "rhythm_controls": {
                            **BERLIN_BASE_CONFIG["rhythm_controls"],
                            "note_density": density_val,
                            "rhythmic_complexity": syncopation_val,
                        },
                        "articulation_controls": {
                            **BERLIN_BASE_CONFIG["articulation_controls"],
                            "gate_length": artic_val["gate"],
                            "accent_chance": artic_val["accent_chance"],
                        },
                        "mode_and_behavior_controls": {
                            "strategy": "fixed_mode",
                            "fixed_mode": mode_val,
                        }
                    }

                    # Generate bass
                    clip = generate_bass_midi_from_drums(
                        m4_drum_output=drum_pattern,
                        theory_context=theory,
                        global_controls=controls,
                        seed=42  # Deterministic
                    )

                    # Create filename and path
                    filename = f"{mode_name}_{artic_name}.mid"
                    subdir = output_dir / density_name / syncopation_name
                    subdir.mkdir(parents=True, exist_ok=True)
                    filepath = subdir / filename

                    # Convert and write MIDI
                    events = convert_to_midi_events(clip, ppq=ppq, channel=1)

                    # Convert MidiEvent objects to simple tuples
                    notes = [(e.note, e.start_abs_tick, e.dur_tick, e.vel) for e in events]
                    write_simple_midi(notes, bpm, str(filepath))

                    # Record metadata
                    metadata = {
                        "variation": variation_count,
                        "file": str(filepath.relative_to(output_dir.parent)),
                        "parameters": {
                            "density": density_name,
                            "density_value": density_val,
                            "syncopation": syncopation_name,
                            "syncopation_value": syncopation_val,
                            "mode": mode_name,
                            "articulation": artic_name,
                            "gate_length": artic_val["gate"],
                            "accent_chance": artic_val["accent_chance"],
                        },
                        "results": {
                            "note_count": len(clip.notes),
                            "bars": clip.length_bars,
                            "modes_used": clip.metadata.get("mode_per_bar", []),
                        },
                        "timestamp": datetime.now().isoformat(),
                    }
                    manifest.append(metadata)

                    print(f"✓ [{variation_count}/24] {density_name}/{syncopation_name}/{filename} "
                          f"({len(clip.notes)} notes)")

    return manifest


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Generate the complete Berlin bass grid exploration."""

    print("=" * 70)
    print("BERLIN TECHNO BASS GRID GENERATOR")
    print("=" * 70)
    print()
    print("Target: Modern Berlin (Energetic, Rolling, Syncopated)")
    print("BPM: 130")
    print("Key: D minor")
    print("Bars: 4")
    print("Variations: 24 (3 × 2 × 2 × 2)")
    print()

    # Setup paths
    project_root = Path(__file__).parent.parent
    output_base = project_root / "output" / "berlin_bass_grid"
    output_base.mkdir(parents=True, exist_ok=True)

    # Step 1: Create drum pattern
    print("Step 1: Creating syncopated Berlin drum pattern...")
    drum_pattern = create_berlin_drum_pattern()
    drums_path = output_base / "reference_drums.mid"
    export_drum_midi(drum_pattern, str(drums_path), bpm=130.0)
    print(f"✓ Exported drums: {drums_path}")
    print()

    # Step 2: Generate grid variations
    print("Step 2: Generating 24 bass variations...")
    print()
    manifest = generate_grid_variations(
        drum_pattern=drum_pattern,
        output_dir=output_base,
        bpm=130.0,
        key="D_minor"
    )
    print()

    # Step 3: Write manifest
    print("Step 3: Writing manifest.json...")
    manifest_path = output_base / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "total_variations": len(manifest),
            "bpm": 130.0,
            "key": "D_minor",
            "bars": 4,
            "grid_dimensions": {
                "density": list(GRID_DIMENSIONS["density"].keys()),
                "syncopation": list(GRID_DIMENSIONS["syncopation"].keys()),
                "mode": list(GRID_DIMENSIONS["mode"].keys()),
                "articulation": list(GRID_DIMENSIONS["articulation"].keys()),
            },
            "variations": manifest
        }, f, indent=2)
    print(f"✓ Manifest: {manifest_path}")
    print()

    # Summary
    print("=" * 70)
    print("GRID GENERATION COMPLETE!")
    print("=" * 70)
    print()
    print(f"📁 Output directory: {output_base}")
    print(f"📊 Total files: 24 bass variations + 1 drum reference")
    print(f"📄 Manifest: manifest.json")
    print()
    print("Directory structure:")
    print("  density_medium/")
    print("    syncopation_medium/ (4 files)")
    print("    syncopation_high/ (4 files)")
    print("  density_high/")
    print("    syncopation_medium/ (4 files)")
    print("    syncopation_high/ (4 files)")
    print("  density_very_high/")
    print("    syncopation_medium/ (4 files)")
    print("    syncopation_high/ (4 files)")
    print()
    print("Next steps:")
    print("1. Load MIDI files into your DAW")
    print("2. Apply same bass synth to all tracks")
    print("3. Import reference_drums.mid for timing")
    print("4. Audition variations and choose favorites!")
    print()


if __name__ == "__main__":
    main()
