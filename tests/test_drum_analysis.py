from __future__ import annotations

from pathlib import Path

import mido

from techno_engine.drum_analysis import DrumAnchors, extract_drum_anchors


def _make_simple_drum_midi(path: Path, ppq: int) -> None:
    """Create a 1-bar 4/4 pattern with known anchors.

    - Kicks on steps 0 and 8
    - Snares on steps 4 and 12
    - Hats on every 4th step
    """

    mid = mido.MidiFile(ticks_per_beat=ppq)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    bar_ticks = ppq * 4
    step_ticks = bar_ticks // 16

    events = []
    # Kicks
    events.append((0 * step_ticks, 36))   # step 0
    events.append((8 * step_ticks, 36))   # step 8
    # Snares
    events.append((4 * step_ticks, 38))   # step 4
    events.append((12 * step_ticks, 38))  # step 12
    # Hats (quarter notes)
    for s in (0, 4, 8, 12):
        events.append((s * step_ticks, 42))

    events.sort(key=lambda x: x[0])

    last_tick = 0
    for tick, note in events:
        delta = tick - last_tick
        last_tick = tick
        track.append(mido.Message("note_on", note=note, velocity=100, time=delta))

    mid.save(path)


def test_extract_drum_anchors_basic(tmp_path: Path) -> None:
    ppq = 480
    midi_path = tmp_path / "drums.mid"
    _make_simple_drum_midi(midi_path, ppq=ppq)

    anchors = extract_drum_anchors(midi_path, ppq=ppq)
    assert isinstance(anchors, DrumAnchors)
    assert anchors.bar_count == 1

    # Kick positions in steps
    assert anchors.bar_kick_steps[0] == [0, 8]
    # Snare positions
    assert anchors.bar_snare_steps[0] == [4, 12]

    # Global kick/backbeat step tuples
    assert (0, 0) in anchors.kick_steps
    assert (0, 8) in anchors.kick_steps
    assert (0, 4) in anchors.backbeat_steps
    assert (0, 12) in anchors.backbeat_steps

    # Slot tags
    slots = anchors.slot_tags[0]
    assert "bar_start" in slots[0]
    assert "bar_end" in slots[15]

    # Near-kick tags around step 0 and 8
    assert "near_kick_post" in slots[1]
    assert "near_kick_pre" in slots[7]
    assert "near_kick_post" in slots[9]

    # Snare zones around step 4
    assert "snare_zone" in slots[4]
    assert "snare_zone" in slots[3]
    assert "snare_zone" in slots[5]
