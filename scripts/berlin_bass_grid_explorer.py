"""Berlin Techno Bass Grid Explorer - Parameter Space Analysis

Systematically explores 24 bass variations for modern Berlin techno.
Generates clip data and analysis without requiring MIDI export.

Run this to see the parameter space and then export specific favorites.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext, BassNote


# ============================================================================
# BERLIN DRUM PATTERN (Syncopated, 130 BPM, 4 bars)
# ============================================================================

def create_berlin_drum_pattern() -> Dict[str, Any]:
    """Create a syncopated Berlin techno drum pattern."""
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

BERLIN_BASE_CONFIG = {
    "rhythm_controls": {
        "kick_interaction_mode": "avoid_kick",
    },
    "melody_controls": {
        "root_note_emphasis": 0.6,
        "interval_jump_magnitude": 0.5,
        "note_range_octaves": 1,
    },
    "articulation_controls": {
        "velocity_normal": 95,
        "velocity_accent": 118,
        "slide_chance": 0.2,
    },
    "drum_interaction_controls": {
        "kick_avoid_strength": 0.8,
        "hat_sync_strength": 0.6,
        "snare_backbeat_preference": 0.5,
    },
}


def analyze_clip(clip, params: Dict) -> Dict[str, Any]:
    """Analyze a bass clip for characteristics."""
    notes = clip.notes

    # Basic stats
    note_count = len(notes)
    avg_velocity = sum(n.velocity for n in notes) / max(1, len(notes))

    # Pitch analysis
    pitches = [n.pitch for n in notes]
    pitch_range = max(pitches) - min(pitches) if pitches else 0
    unique_pitches = len(set(pitches))

    # Rhythm analysis
    durations = [n.duration_beats for n in notes]
    avg_duration = sum(durations) / max(1, len(durations))

    # Accent analysis (high velocity notes)
    accents = sum(1 for n in notes if n.velocity > 105)
    accent_ratio = accents / max(1, len(notes))

    return {
        "note_count": note_count,
        "notes_per_bar": note_count / 4,
        "avg_velocity": round(avg_velocity, 1),
        "pitch_range": pitch_range,
        "unique_pitches": unique_pitches,
        "avg_duration": round(avg_duration, 3),
        "accent_count": accents,
        "accent_ratio": round(accent_ratio, 2),
        "modes_used": clip.metadata.get("mode_per_bar", []),
    }


# ============================================================================
# GRID EXPLORATION
# ============================================================================

def explore_grid(drum_pattern: Dict[str, Any], bpm: float = 130.0, key: str = "D_minor"):
    """Explore all grid variations and return analysis."""

    theory = TheoryContext(key_scale=key, tempo_bpm=bpm)

    results = []
    variation_count = 0

    print()
    print("Generating variations...")
    print()

    for density_name, density_val in GRID_DIMENSIONS["density"].items():
        for syncopation_name, syncopation_val in GRID_DIMENSIONS["syncopation"].items():
            for mode_name, mode_val in GRID_DIMENSIONS["mode"].items():
                for artic_name, artic_val in GRID_DIMENSIONS["articulation"].items():

                    variation_count += 1

                    # Build controls
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
                        seed=42
                    )

                    # Analyze
                    analysis = analyze_clip(clip, {
                        "density": density_name,
                        "syncopation": syncopation_name,
                        "mode": mode_name,
                        "articulation": artic_name,
                    })

                    result = {
                        "id": variation_count,
                        "name": f"{density_name}/{syncopation_name}/{mode_name}_{artic_name}",
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
                        "analysis": analysis,
                        "clip": clip,  # Store for later export
                    }
                    results.append(result)

                    print(f"  [{variation_count:2d}/24] {result['name']:55s} "
                          f"{analysis['note_count']:2d} notes, "
                          f"{analysis['avg_velocity']:.0f} vel")

    return results


def print_summary_table(results: List[Dict]):
    """Print a summary table of all variations."""
    print()
    print("=" * 120)
    print("PARAMETER SPACE SUMMARY")
    print("=" * 120)
    print()

    # Group by dimensions
    print("📊 BY DENSITY:")
    for density in ["medium", "high", "very_high"]:
        filtered = [r for r in results if r["parameters"]["density"] == density]
        avg_notes = sum(r["analysis"]["note_count"] for r in filtered) / len(filtered)
        print(f"  {density:12s}: {len(filtered)} variations, avg {avg_notes:.1f} notes")

    print()
    print("🎵 BY MODE:")
    for mode in ["pocket_groove", "rolling_ostinato"]:
        filtered = [r for r in results if r["parameters"]["mode"] == mode]
        avg_notes = sum(r["analysis"]["note_count"] for r in filtered) / len(filtered)
        print(f"  {mode:18s}: {len(filtered)} variations, avg {avg_notes:.1f} notes")

    print()
    print("🎹 BY ARTICULATION:")
    for artic in ["punchy", "driving"]:
        filtered = [r for r in results if r["parameters"]["articulation"] == artic]
        avg_vel = sum(r["analysis"]["avg_velocity"] for r in filtered) / len(filtered)
        avg_accents = sum(r["analysis"]["accent_ratio"] for r in filtered) / len(filtered)
        print(f"  {artic:10s}: {len(filtered)} variations, avg vel {avg_vel:.1f}, "
              f"accent ratio {avg_accents:.2f}")

    print()
    print("🔥 TOP 5 BY NOTE COUNT (Most Dense):")
    sorted_by_notes = sorted(results, key=lambda r: r["analysis"]["note_count"], reverse=True)
    for i, r in enumerate(sorted_by_notes[:5], 1):
        print(f"  {i}. {r['name']:55s} {r['analysis']['note_count']:2d} notes")

    print()
    print("💎 TOP 5 BY VELOCITY (Most Aggressive):")
    sorted_by_vel = sorted(results, key=lambda r: r["analysis"]["avg_velocity"], reverse=True)
    for i, r in enumerate(sorted_by_vel[:5], 1):
        print(f"  {i}. {r['name']:55s} {r['analysis']['avg_velocity']:.0f} avg vel")

    print()


def save_analysis_json(results: List[Dict], output_path: Path):
    """Save analysis results to JSON (without clip objects)."""
    output_data = {
        "generated": datetime.now().isoformat(),
        "total_variations": len(results),
        "bpm": 130.0,
        "key": "D_minor",
        "bars": 4,
        "grid_dimensions": {
            "density": list(GRID_DIMENSIONS["density"].keys()),
            "syncopation": list(GRID_DIMENSIONS["syncopation"].keys()),
            "mode": list(GRID_DIMENSIONS["mode"].keys()),
            "articulation": list(GRID_DIMENSIONS["articulation"].keys()),
        },
        "variations": [
            {
                "id": r["id"],
                "name": r["name"],
                "parameters": r["parameters"],
                "analysis": r["analysis"],
            }
            for r in results
        ]
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)


def main():
    """Run the grid exploration."""
    print("=" * 120)
    print("BERLIN TECHNO BASS GRID EXPLORER")
    print("=" * 120)
    print()
    print("Target: Modern Berlin (Energetic, Rolling, Syncopated)")
    print("BPM: 130 | Key: D minor | Bars: 4 | Variations: 24")
    print()

    # Create drum pattern
    print("Creating syncopated Berlin drum pattern...")
    drum_pattern = create_berlin_drum_pattern()

    # Explore grid
    results = explore_grid(drum_pattern)

    # Print summary
    print_summary_table(results)

    # Save analysis
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "output" / "berlin_bass_grid"
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis_path = output_dir / "analysis.json"
    save_analysis_json(results, analysis_path)

    print(f"📄 Analysis saved: {analysis_path}")
    print()
    print("=" * 120)
    print()
    print("✅ Grid exploration complete!")
    print()
    print("Next steps:")
    print("  1. Review the analysis above to identify interesting parameter combinations")
    print("  2. Use the bass_v2 API to export specific variations to MIDI")
    print("  3. Example:")
    print("     from examples.bass_v2_integration import *")
    print("     # Then customize controls based on findings above")
    print()


if __name__ == "__main__":
    main()
