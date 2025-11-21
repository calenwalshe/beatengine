import os
from pathlib import Path

import mido

from techno_engine.drum_analysis import extract_drum_anchors
from techno_engine.leads.lead_engine import generate_lead
from techno_engine.seeds import SeedMetadata


def _make_meta(tags=None) -> SeedMetadata:
    return SeedMetadata(
        seed_id="debug_seed",
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=130.0,
        bars=2,
        ppq=1920,
        rng_seed=1,
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


def _write_drums(tmp_path: Path) -> Path:
    mid = mido.MidiFile(ticks_per_beat=1920)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", note=36, velocity=0, time=0))
    path = tmp_path / "drums.mid"
    mid.save(path)
    return path


def test_generate_lead_debug_hook_does_not_crash(tmp_path, monkeypatch, capsys):
    midi_path = _write_drums(tmp_path)
    anchors = extract_drum_anchors(midi_path, ppq=1920)
    meta = _make_meta()

    monkeypatch.setenv("BEATENGINE_LEAD_DEBUG", "1")
    events = generate_lead(anchors, meta)
    assert events, "expected some events"

    out, err = capsys.readouterr()
    # We only assert that some debug text was printed; exact text may change.
    assert "lead-debug" in out
