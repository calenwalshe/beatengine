from __future__ import annotations

from statistics import median

from techno_engine.controller import run_session
from techno_engine.timebase import ticks_per_bar


def test_markov_sync_converges_to_band():
    bpm, ppq, bars = 132, 1920, 128
    res = run_session(bpm=bpm, ppq=ppq, bars=bars)

    tail = res.S_by_bar[bars // 2 :]
    assert 0.35 <= median(tail) <= 0.55
    assert max(tail) - min(tail) < 0.3


def test_markov_density_and_kick_stability():
    bpm, ppq, bars = 132, 1920, 64
    res = run_session(bpm=bpm, ppq=ppq, bars=bars)

    bar_ticks = ticks_per_bar(ppq, 4)
    hatc_counts = [0] * bars
    hato_counts = [0] * bars
    kick_counts = [0] * bars
    for ev in res.events_by_layer["hat_c"]:
        hatc_counts[ev.start_abs_tick // bar_ticks] += 1
    for ev in res.events_by_layer["hat_o"]:
        hato_counts[ev.start_abs_tick // bar_ticks] += 1
    for ev in res.events_by_layer["kick"]:
        kick_counts[ev.start_abs_tick // bar_ticks] += 1

    for count in hatc_counts:
        assert 9 <= count <= 13
    for count in hato_counts:
        assert 2 <= count <= 7
    for count in kick_counts:
        assert count == 4
