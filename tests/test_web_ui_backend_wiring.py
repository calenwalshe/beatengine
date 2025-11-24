import pytest

from web_ui.backend import app as backend_app
from web_ui.backend.bass_generator_api import generate_bass_with_params
from web_ui.backend.drum_patterns import DRUM_PATTERNS
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext


def _slot_index(note):
    """Convert a note's start beat into a 0-15 slot index within its bar."""
    return int((note.start_beat % 4.0) / 0.25)


def test_generate_endpoint_wires_controls_and_writes_file(tmp_path, monkeypatch):
    # Patch output dir so tests don't write to repo
    monkeypatch.setattr(backend_app, "OUTPUT_DIR", tmp_path)
    backend_app.app.config["TESTING"] = True
    client = backend_app.app.test_client()

    payload = {
        "drum_pattern": "four_on_floor",
        "theory_context": {"key_scale": "C_minor", "tempo_bpm": 128},
        "controls": {
            "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": "sub_anchor"},
            "rhythm_controls": {"note_density": 0.35, "kick_interaction_mode": "avoid_kick"},
            "melody_controls": {"root_note_emphasis": 0.95},
            "articulation_controls": {"gate_length": 0.6},
            "theory_controls": {"harmonic_strictness": 0.9},
            "drum_interaction_controls": {"kick_avoid_strength": 0.9},
        },
    }

    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["success"] is True
    assert data["theory_context"]["key_scale"] == "C_minor"
    assert data["preview"]["note_count"] > 0
    assert (tmp_path / data["filename"]).exists()


def test_density_control_changes_note_count(tmp_path):
    low = generate_bass_with_params(
        drum_pattern_name="four_on_floor",
        theory_params={"key_scale": "D_minor", "tempo_bpm": 128},
        control_params={"rhythm_controls": {"note_density": 0.2}},
        output_dir=tmp_path,
        seed=1234,
    )

    high = generate_bass_with_params(
        drum_pattern_name="four_on_floor",
        theory_params={"key_scale": "D_minor", "tempo_bpm": 128},
        control_params={"rhythm_controls": {"note_density": 0.9}},
        output_dir=tmp_path,
        seed=1234,
    )

    assert high["success"] and low["success"]
    assert high["preview"]["note_count"] > low["preview"]["note_count"] * 1.5


def test_kick_interaction_controls_affect_slot_selection():
    pattern = DRUM_PATTERNS["four_on_floor"]
    theory = TheoryContext(key_scale="D_minor", tempo_bpm=128)

    avoid_clip = generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=theory,
        global_controls={
            "rhythm_controls": {"note_density": 0.65, "kick_interaction_mode": "avoid_kick"},
            "drum_interaction_controls": {"kick_avoid_strength": 1.0},
        },
        seed=42,
    )

    reinforce_clip = generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=theory,
        global_controls={
            "rhythm_controls": {"note_density": 0.65, "kick_interaction_mode": "reinforce_kick"},
            "drum_interaction_controls": {"kick_avoid_strength": 0.0},
        },
        seed=42,
    )

    kick_slots = {0, 4, 8, 12}
    avoid_collisions = [_slot_index(n) for n in avoid_clip.notes if _slot_index(n) in kick_slots]
    reinforce_collisions = [_slot_index(n) for n in reinforce_clip.notes if _slot_index(n) in kick_slots]

    assert avoid_clip.notes  # sanity: generation produced notes
    assert reinforce_clip.notes
    assert avoid_collisions == []
    assert len(reinforce_collisions) > 0


def test_fixed_mode_and_key_scale_propagate(tmp_path):
    mode_name = "lead_ish"
    pattern = DRUM_PATTERNS["berlin_syncopated"]

    result = generate_bass_with_params(
        drum_pattern_name="berlin_syncopated",
        theory_params={"key_scale": "G_major", "tempo_bpm": 128},
        control_params={
            "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": mode_name},
            "rhythm_controls": {"note_density": 0.6},
            "melody_controls": {"root_note_emphasis": 0.2, "note_range_octaves": 2},
        },
        output_dir=tmp_path,
        seed=900,
    )

    assert result["success"]
    assert result["metadata"]["mode_per_bar"] == [mode_name] * len(pattern["bars"])

    # Ensure key/scale changes pitch material (G_major vs default A_minor root)
    major_pitches = {n.pitch for n in generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=TheoryContext(key_scale="G_major", tempo_bpm=128),
        global_controls={
            "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": mode_name},
            "rhythm_controls": {"note_density": 0.6},
            "melody_controls": {"root_note_emphasis": 0.2, "note_range_octaves": 2},
        },
        seed=901,
    ).notes}

    minor_pitches = {n.pitch for n in generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=TheoryContext(key_scale="C_minor", tempo_bpm=128),
        global_controls={
            "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": mode_name},
            "rhythm_controls": {"note_density": 0.6},
            "melody_controls": {"root_note_emphasis": 0.2, "note_range_octaves": 2},
        },
        seed=901,
    ).notes}

    assert major_pitches != minor_pitches


def test_base_octave_slider_shifts_pitch_range():
    pattern = DRUM_PATTERNS["four_on_floor"]
    theory = TheoryContext(key_scale="A_minor", tempo_bpm=128)

    low = generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=theory,
        global_controls={
            "melody_controls": {"base_octave": 1, "note_range_octaves": 1},
            "rhythm_controls": {"note_density": 0.4},
        },
        seed=2024,
    )

    high = generate_bass_midi_from_drums(
        m4_drum_output=pattern,
        theory_context=theory,
        global_controls={
            "melody_controls": {"base_octave": 3, "note_range_octaves": 1},
            "rhythm_controls": {"note_density": 0.4},
        },
        seed=2024,
    )

    low_min = min(n.pitch for n in low.notes)
    high_min = min(n.pitch for n in high.notes)

    assert high_min - low_min >= 12
