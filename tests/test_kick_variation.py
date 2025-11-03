from __future__ import annotations

from collections import Counter

from techno_engine.controller import run_session, Guard
from techno_engine.parametric import LayerConfig
from techno_engine.timebase import ticks_per_bar


def _bar_step(ev, ppq):
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    return (ev.start_abs_tick % bar_ticks) // step_ticks


def test_kick_remains_regular_when_guard_immutable():
    bpm, ppq, bars = 132, 1920, 32
    res = run_session(bpm=bpm, ppq=ppq, bars=bars)
    bar_ticks = ticks_per_bar(ppq, 4)
    counts = [0] * bars
    steps = Counter()
    for ev in res.events_by_layer["kick"]:
        idx = ev.start_abs_tick // bar_ticks
        counts[idx] += 1
        steps[int(_bar_step(ev, ppq))] += 1
    assert all(c == 4 for c in counts)
    assert set(steps.keys()) <= {0, 4, 8, 12}


def test_kick_variation_introduces_ghosts_and_displacements():
    bpm, ppq, bars = 132, 1920, 64
    kick_cfg = LayerConfig(
        steps=16,
        fills=4,
        rot=1,
        note=36,
        velocity=110,
        rotation_rate_per_bar=0.05,
        ghost_pre1_prob=0.25,
        displace_into_2_prob=0.2,
    )
    res = run_session(
        bpm=bpm,
        ppq=ppq,
        bars=bars,
        guard=Guard(kick_immutable=False),
        kick_layer_cfg=kick_cfg,
    )

    bar_ticks = ticks_per_bar(ppq, 4)
    counts = [0] * bars
    displaced_present = False
    ghost_present = False
    for ev in res.events_by_layer["kick"]:
        bar_idx = ev.start_abs_tick // bar_ticks
        counts[bar_idx] += 1
        step = int(_bar_step(ev, ppq))
        if step in {1, 3, 5, 7, 9, 11, 13, 15}:
            ghost_present = True
        if step in {2, 6, 10, 14}:
            displaced_present = True

    assert any(c > 4 for c in counts)  # ghost hits add density
    assert any(c == 4 for c in counts)  # not every bar changes
    assert displaced_present
    assert ghost_present


def test_kick_rotation_shifts_primary_hits_over_time():
    bpm, ppq, bars = 132, 1920, 64
    kick_cfg = LayerConfig(
        steps=16,
        fills=4,
        rot=1,
        note=36,
        velocity=110,
        rotation_rate_per_bar=0.08,
        ghost_pre1_prob=0.0,
        displace_into_2_prob=0.0,
    )
    res = run_session(
        bpm=bpm,
        ppq=ppq,
        bars=bars,
        guard=Guard(kick_immutable=False),
        kick_layer_cfg=kick_cfg,
    )

    bar_ticks = ticks_per_bar(ppq, 4)
    first_hits = []
    for bar in range(bars):
        bar_events = [ev for ev in res.events_by_layer["kick"] if ev.start_abs_tick // bar_ticks == bar]
        if not bar_events:
            continue
        first_step = min(int(_bar_step(ev, ppq)) for ev in bar_events)
        first_hits.append(first_step)

    assert len(set(first_hits)) > 1  # rotation introduces variety
