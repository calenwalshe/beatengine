from __future__ import annotations

from pathlib import Path

import mido
import pytest

from techno_engine.drum_analysis import extract_drum_anchors
from techno_engine.leads.lead_engine import generate_lead, NoteEvent
from techno_engine.seeds import SeedMetadata


def _write_four_four_drums(tmp_path: Path, bars: int) -> Path:
    mid = mido.MidiFile(ticks_per_beat=1920)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    for bar in range(bars):
        delta = 0 if bar == 0 else 1920 * 4
        track.append(mido.Message("note_on", note=36, velocity=100, time=delta))
        track.append(mido.Message("note_off", note=36, velocity=0, time=0))
        track.append(mido.Message("note_on", note=38, velocity=100, time=1920))
        track.append(mido.Message("note_off", note=38, velocity=0, time=0))
    midi_path = tmp_path / "drums.mid"
    mid.save(midi_path)
    return midi_path


def _make_meta(bars: int, tags: list[str]) -> SeedMetadata:
    return SeedMetadata(
        seed_id="v2_integration",
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=130.0,
        bars=bars,
        ppq=1920,
        rng_seed=777,
        config_path="config.json",
        render_path="drums/main.mid",
        log_path=None,
        prompt=None,
        prompt_context=None,
        summary=None,
        tags=tags,
        assets=[],
        parent_seed_id=None,
        file_version=1,
    )


@pytest.mark.parametrize(
    "tags,register,bars",
    [
        (["minimal"], (64, 76), 2),
        (["lyrical"], (64, 88), 4),
        (["techno"], (70, 82), 4),
    ],
)
def test_generate_lead_v2_modes(tmp_path: Path, monkeypatch, tags: list[str], register: tuple[int, int], bars: int):
    midi_path = _write_four_four_drums(tmp_path, bars=bars)
    anchors = extract_drum_anchors(midi_path, ppq=1920)
    meta = _make_meta(bars=bars, tags=tags)

    monkeypatch.setenv("BEATENGINE_LEAD_ENGINE", "v2")
    events = generate_lead(anchors, meta)

    assert events, f"expected events for tags={tags}"
    assert all(isinstance(ev, NoteEvent) for ev in events)
    assert all(register[0] <= ev.pitch <= register[1] for ev in events)
    starts = [ev.start_tick for ev in events]
    assert starts == sorted(starts)
