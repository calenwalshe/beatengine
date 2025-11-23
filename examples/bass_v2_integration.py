"""Example integration: Generate bass using bass_v2 with m4 drum output."""
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums, convert_to_midi_events
from src.techno_engine.bass_v2_types import TheoryContext
from src.techno_engine.midi_writer import write_midi


def example_basic_generation():
    """Basic example: Generate bass for a simple 4-bar house pattern."""
    # Create a simple four-on-the-floor drum pattern
    m4_drum_output = {
        "bars": [
            {
                "steps": [
                    {
                        "kick": i in {0, 4, 8, 12},
                        "hat": i % 2 == 1,  # 8th note hats
                        "snare": i in {4, 12},  # Backbeats
                        "velocity": 100 if i in {0, 4, 8, 12} else 80,
                    }
                    for i in range(16)
                ]
            }
            for _ in range(4)
        ]
    }

    # Set musical context
    theory = TheoryContext(key_scale="A_minor", tempo_bpm=128.0)

    # Generate bass with default settings
    clip = generate_bass_midi_from_drums(m4_drum_output, theory, seed=42)

    print(f"Generated {len(clip.notes)} bass notes for {clip.length_bars} bars")
    print(f"Modes used: {clip.metadata['mode_per_bar']}")

    # Convert to MIDI events and write file
    events = convert_to_midi_events(clip, ppq=480, channel=1)
    write_midi("output_basic_bass.mid", events, tempo_bpm=128.0, ppq=480)
    print("Wrote output_basic_bass.mid")


def example_mode_override():
    """Example: Force specific bass mode (offbeat_stabs)."""
    m4_drum_output = {
        "bars": [
            {
                "steps": [
                    {"kick": i in {0, 4, 8, 12}, "hat": i % 2 == 1, "snare": i in {4, 12}}
                    for i in range(16)
                ]
            }
            for _ in range(2)
        ]
    }

    theory = TheoryContext(key_scale="D_minor", tempo_bpm=130.0)

    # Force offbeat_stabs mode
    global_controls = {
        "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": "offbeat_stabs"}
    }

    clip = generate_bass_midi_from_drums(m4_drum_output, theory, global_controls, seed=42)

    print(f"\nOffbeat stabs: {len(clip.notes)} notes")
    print(f"Modes: {clip.metadata['mode_per_bar']}")

    events = convert_to_midi_events(clip, ppq=480, channel=1)
    write_midi("output_offbeat_stabs.mid", events, tempo_bpm=130.0, ppq=480)
    print("Wrote output_offbeat_stabs.mid")


def example_custom_controls():
    """Example: Customize density and articulation controls."""
    m4_drum_output = {
        "bars": [
            {
                "steps": [
                    {"kick": i in {0, 4, 8, 12}, "hat": i % 4 == 2, "snare": i == 12}
                    for i in range(16)
                ]
            }
            for _ in range(4)
        ]
    }

    theory = TheoryContext(key_scale="G_minor", tempo_bpm=125.0)

    # Custom controls: high density, aggressive articulation
    global_controls = {
        "rhythm_controls": {"note_density": 0.75, "rhythmic_complexity": 0.8},
        "articulation_controls": {
            "velocity_normal": 95,
            "velocity_accent": 120,
            "accent_chance": 0.6,
            "slide_chance": 0.3,
        },
        "melody_controls": {"note_range_octaves": 2, "root_note_emphasis": 0.5},
    }

    clip = generate_bass_midi_from_drums(m4_drum_output, theory, global_controls, seed=42)

    print(f"\nCustom controls: {len(clip.notes)} notes")
    print(f"Average velocity: {sum(n.velocity for n in clip.notes) / len(clip.notes):.1f}")

    events = convert_to_midi_events(clip, ppq=480, channel=1)
    write_midi("output_custom_bass.mid", events, tempo_bpm=125.0, ppq=480)
    print("Wrote output_custom_bass.mid")


if __name__ == "__main__":
    print("Bass V2 Generator Integration Examples")
    print("=" * 50)

    example_basic_generation()
    example_mode_override()
    example_custom_controls()

    print("\n✓ All examples completed successfully!")
