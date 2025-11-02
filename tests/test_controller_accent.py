from __future__ import annotations

from statistics import median

from techno_engine.controller import run_session
from techno_engine.accent import AccentProfile


def _step_of(ev, ppq):
    from techno_engine.timebase import ticks_per_bar
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    return int((ev.start_abs_tick % bar_ticks) // step_ticks)


def test_controller_applies_accent_globally_on_kick_steps():
    bpm, ppq, bars = 132, 1920, 1
    # Controller's kick pattern via Euclid(16,4) in this implementation hits steps 4,8,12,16 (1-indexed)
    profile = AccentProfile(steps_1idx=[4, 8, 12, 16], prob=1.0, velocity_scale=1.2, length_scale=1.0)
    res = run_session(bpm=bpm, ppq=ppq, bars=bars, accent_profile=profile)
    kicks = res.events_by_layer["kick"]
    # kick baseline vel=110, after accent with scale 1.2 → min(127, 132) = 127
    assert kicks and all(ev.vel == 127 for ev in kicks)


def test_controller_accent_prob_zero_no_effect_on_kick():
    bpm, ppq, bars = 132, 1920, 1
    profile = AccentProfile(steps_1idx=[4, 8, 12, 16], prob=0.0, velocity_scale=2.0, length_scale=2.0)
    res = run_session(bpm=bpm, ppq=ppq, bars=bars, accent_profile=profile)
    kicks = res.events_by_layer["kick"]
    assert kicks and all(ev.vel == 110 for ev in kicks)
