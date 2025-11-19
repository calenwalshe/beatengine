from pathlib import Path

from techno_engine.drum_analysis import extract_drum_anchors
from techno_engine.key_mode import key_to_midi
from techno_engine.leads.lead_engine import NoteEvent, generate_lead
from techno_engine.seeds import SeedMetadata


def _make_dummy_metadata(tags=None) -> SeedMetadata:
    return SeedMetadata(
        seed_id="lead_test_seed",
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=130.0,
        bars=2,
        ppq=1920,
        rng_seed=4242,
        config_path="config.json",
        render_path="drums/main.mid",
        log_path=None,
        prompt=None,
        prompt_context=None,
        summary=None,
        tags=tags or ["minimal"],
        assets=[],
        parent_seed_id=None,
        file_version=1,
    )


def test_generate_lead_produces_events_within_register(tmp_path):
    # Build a minimal drum MIDI with a kick on 1 and a snare on 2 to give
    # the slot grid some structure.
    import mido

    mid = mido.MidiFile(ticks_per_beat=1920)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # Kick on 1
    track.append(mido.Message("note_on", note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", note=36, velocity=0, time=0))
    # Snare on 2 (one beat later)
    track.append(mido.Message("note_on", note=38, velocity=100, time=1920))
    track.append(mido.Message("note_off", note=38, velocity=0, time=0))

    midi_path = tmp_path / "drums.mid"
    mid.save(midi_path)

    anchors = extract_drum_anchors(Path(midi_path), ppq=1920)
    meta = _make_dummy_metadata(tags=["minimal"])

    events = generate_lead(anchors, meta)
    # For the default minimal mode we expect at least one event.
    assert isinstance(events, list)
    assert all(isinstance(e, NoteEvent) for e in events)
    assert events, "no lead events generated"

    # Check register based on Minimal Stab Lead config (64..76 by default).
    for ev in events:
        assert 64 <= ev.pitch <= 76


def test_generate_lead_is_deterministic(tmp_path):
    # Same setup as above but call generate_lead twice.
    import mido

    mid = mido.MidiFile(ticks_per_beat=1920)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", note=36, velocity=0, time=0))
    midi_path = tmp_path / "drums.mid"
    mid.save(midi_path)

    anchors = extract_drum_anchors(Path(midi_path), ppq=1920)
    meta = _make_dummy_metadata(tags=["minimal"])

    ev1 = generate_lead(anchors, meta)
    ev2 = generate_lead(anchors, meta)

    assert [(e.pitch, e.start_tick, e.duration) for e in ev1] == [
        (e.pitch, e.start_tick, e.duration) for e in ev2
    ]
