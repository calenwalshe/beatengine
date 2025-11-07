from __future__ import annotations

from typing import List

from techno_engine.bass_score import SyncWeights, score_steps, select_steps_by_score, make_prekick_ghosts
from techno_engine.bassline import build_swung_grid


def _mask_from_steps(steps_on: list[int], steps: int = 16) -> list[int]:
    m = [0] * steps
    for s in steps_on:
        m[s % steps] = 1
    return m


def test_ghosts_end_before_kick():
    bpm, ppq, bars = 120.0, 1920, 2
    ghosts = make_prekick_ghosts(bpm=bpm, ppq=ppq, bars=bars, kick_steps=(0, 4, 8, 12), note=45)
    g = build_swung_grid(bpm, ppq)
    for bar in range(bars):
        base = bar * g.bar_ticks
        for ks in (0, 4, 8, 12):
            kick_t = base + ks * g.step_ticks
            # find ghost at this kick
            matches = [ev for ev in ghosts if ev.start_abs_tick == kick_t - g.half_step_ticks]
            assert matches, "missing ghost"
            ev = matches[0]
            assert ev.start_abs_tick + ev.dur_tick < kick_t


def test_clap_response_rate_minimum():
    steps = 16
    kick = _mask_from_steps([0, 4, 8, 12], steps)
    hats = _mask_from_steps([2, 6, 10, 14], steps)
    clap = _mask_from_steps([4, 12], steps)
    w = SyncWeights(kick_penalty=2.0, hat_bonus=0.2, clap_bonus=1.0, near_window=1)
    scores = score_steps(steps, kick, hats, clap, w)
    chosen = select_steps_by_score(scores, forbidden=[i for i,s in enumerate(kick) if s], k=4)
    # response = steps that are clap or adjacent
    clap_zone = set([3,4,5,11,12,13])
    responded = sum(1 for s in chosen if s in clap_zone)
    assert responded / max(1, len(chosen)) >= 0.20


def test_hat_sync_bonus_effect():
    steps = 16
    kick = _mask_from_steps([0, 4, 8, 12], steps)
    hats = _mask_from_steps([2, 6, 10, 14], steps)
    clap = _mask_from_steps([], steps)
    w0 = SyncWeights(kick_penalty=1.0, hat_bonus=0.0, clap_bonus=0.0, near_window=0)
    w1 = SyncWeights(kick_penalty=1.0, hat_bonus=0.8, clap_bonus=0.0, near_window=0)
    s0 = score_steps(steps, kick, hats, clap, w0)
    s1 = score_steps(steps, kick, hats, clap, w1)
    chosen0 = set(select_steps_by_score(s0, forbidden=[i for i,s in enumerate(kick) if s], k=4))
    chosen1 = set(select_steps_by_score(s1, forbidden=[i for i,s in enumerate(kick) if s], k=4))
    hat_set = {2, 6, 10, 14}
    base_hits = len(chosen0 & hat_set)
    bonus_hits = len(chosen1 & hat_set)
    assert bonus_hits >= base_hits

