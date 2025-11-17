from __future__ import annotations

from pathlib import Path

import mido

from techno_engine.drum_analysis import extract_drum_anchors
from techno_engine.groove_bass import choose_mode, generate_groove_bass


def _make_kick_snare_hat_bar(path: Path, ppq: int) -> None:
    """1-bar drum pattern with kicks, snares, and hats for testing.

    - Kicks at steps 0 and 8
    - Snares at steps 4 and 12
    - Hats at every 4th step
    """
    mid = mido.MidiFile(ticks_per_beat=ppq)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    bar_ticks = ppq * 4
    step_ticks = bar_ticks // 16

    events = []
    events.append((0 * step_ticks, 36))   # kick
    events.append((8 * step_ticks, 36))   # kick
    events.append((4 * step_ticks, 38))   # snare
    events.append((12 * step_ticks, 38))  # snare
    for s in (0, 4, 8, 12):               # hats
        events.append((s * step_ticks, 42))

    events.sort(key=lambda x: x[0])
    last_tick = 0
    for tick, note in events:
        delta = tick - last_tick
        last_tick = tick
        track.append(mido.Message("note_on", note=note, velocity=100, time=delta))

    mid.save(path)


def _steps_from_events(events, ppq: int, bars: int = 1) -> list[int]:
    from techno_engine.bassline import build_swung_grid

    grid = build_swung_grid(128.0, ppq)
    steps: list[int] = []
    bar_ticks = grid.bar_ticks
    step_ticks = grid.step_ticks
    for ev in events:
        bar_local = ev.start_abs_tick % bar_ticks
        step = round(bar_local / step_ticks)
        steps.append(int(step))
    return steps


def test_choose_mode_from_tags_energy() -> None:
    anchors = type("A", (), {"bar_kick_steps": [[0, 8]], "bar_hat_steps": [[0, 4, 8, 12]], "bar_count": 1})
    mode = choose_mode(["warehouse", "urgent"], energy=10.0)
    assert mode.name in {"pocket_groove", "root_fifth", "rolling_ostinato"}

    mode_minimal = choose_mode(["minimal"], energy=1.0)
    assert mode_minimal.name == "sub_anchor"


def test_sub_anchor_avoids_kicks_and_is_sparse(tmp_path: Path) -> None:
    ppq = 480
    midi_path = tmp_path / "drums.mid"
    _make_kick_snare_hat_bar(midi_path, ppq)
    anchors = extract_drum_anchors(midi_path, ppq=ppq)

    events = generate_groove_bass(anchors, bpm=128.0, ppq=ppq, tags=["minimal"], mode="sub_anchor", bars=1)
    steps = _steps_from_events(events, ppq)

    # Expect 1-4 notes with anchor on or near step 0 and no notes on kick step 8.
    assert 1 <= len(steps) <= 4
    assert any(s == 0 for s in steps)
    assert all(s != 8 for s in steps if s != 0)


def test_offbeat_stabs_only_offbeats(tmp_path: Path) -> None:
    ppq = 480
    midi_path = tmp_path / "drums2.mid"
    _make_kick_snare_hat_bar(midi_path, ppq)
    anchors = extract_drum_anchors(midi_path, ppq=ppq)

    events = generate_groove_bass(anchors, bpm=128.0, ppq=ppq, tags=["minimal"], mode="offbeat_stabs", bars=1)
    steps = _steps_from_events(events, ppq)

    # All notes should sit on 8th offbeats (2,6,10,14); keep it very sparse.
    assert 1 <= len(steps) <= 3
    for s in steps:
        assert s % 4 == 2
