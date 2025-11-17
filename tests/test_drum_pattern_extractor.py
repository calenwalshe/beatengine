from __future__ import annotations

from pathlib import Path

import mido

from techno_engine.seed_explorer import _extract_drum_pattern, _summarise_midi


def _make_basic_midi(tmp_path: Path) -> Path:
    step_ticks = 120  # 16th-notes when ticks_per_beat=480
    events = [
        (0, 36),
        (4, 36),
        (8, 36),
        (12, 36),
        (4, 38),
        (12, 38),
    ]
    for i in range(16):
        events.append((i, 42))

    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    prev_tick = 0
    for step, note in sorted(events, key=lambda t: t[0]):
        tick = step * step_ticks
        delta = tick - prev_tick
        track.append(mido.Message("note_on", note=note, velocity=100, time=delta))
        prev_tick = tick

    midi_path = tmp_path / "beat.mid"
    mid.save(midi_path)
    return midi_path


def test_extract_drum_pattern_simple(tmp_path: Path) -> None:
    midi_path = _make_basic_midi(tmp_path)
    pattern = _extract_drum_pattern(midi_path, ppq=480)
    assert pattern is not None
    assert pattern == "\n".join([
        "kick : x...x...x...x...",
        "snare: ....x.......x...",
        "hat  : xxxxxxxxxxxxxxxx",
    ])


def test_summarise_midi(tmp_path: Path) -> None:
    midi_path = _make_basic_midi(tmp_path)
    summary = _summarise_midi(midi_path, ppq=480)
    assert summary == (
        "notes: C2,D2,F#2 | hits: 22 | length: 3.75 beats | first: 0.00 | last: 3.75"
    )
