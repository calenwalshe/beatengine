from __future__ import annotations

import json
from pathlib import Path

import pytest

from techno_engine.timebase import ms_to_ticks
from techno_engine.cli import build_metronome_events
from techno_engine.midi_writer import write_midi


def test_ms_to_ticks_25ms_range():
    # 25 ms should be ~105.6 ticks at ppq=1920, bpm=132
    ticks = ms_to_ticks(25.0, ppq=1920, bpm=132.0)
    assert 100 <= ticks <= 110


def test_metronome_midi_header_and_clicks(tmp_path: Path):
    try:
        import mido  # type: ignore
    except Exception as e:  # pragma: no cover
        pytest.skip(f"mido not available: {e}")

    bpm = 132
    ppq = 1920
    bars = 8

    events = build_metronome_events(bpm=bpm, ppq=ppq, bars=bars)
    out = tmp_path / "metronome.mid"
    write_midi(events, ppq=ppq, bpm=bpm, out_path=str(out))

    mid = mido.MidiFile(str(out))

    # Header PPQ
    assert mid.ticks_per_beat == ppq

    # Tempo meta present and correct
    tempos = [msg.tempo for tr in mid.tracks for msg in tr if msg.type == "set_tempo"]
    assert tempos, "No tempo meta message found"
    tempo = tempos[0]
    computed_bpm = 60_000_000 / tempo
    # Allow tiny rounding error from integer microseconds/beat representation
    assert abs(computed_bpm - bpm) < 1e-2

    # Count clicks: 4 per bar across 8 bars
    on_msgs = [msg for tr in mid.tracks for msg in tr if msg.type == "note_on" and msg.velocity > 0]
    assert len(on_msgs) == bars * 4

    # Downbeat note 76 appears once per bar
    note76 = [m for m in on_msgs if m.note == 76]
    assert len(note76) == bars
