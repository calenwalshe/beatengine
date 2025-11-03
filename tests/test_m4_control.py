from __future__ import annotations

from statistics import median

from techno_engine.controller import run_session, Targets, Guard
from techno_engine.scores import micro_offsets_ms_for_layer, rms


def test_m4_metrics_and_continuity():
    bpm, ppq, bars = 132, 1920, 64
    res = run_session(bpm=bpm, ppq=ppq, bars=bars)

    # Check last quarter bars for S band and E target
    last = slice(bars - bars // 4, bars)
    S_med = median(res.S_by_bar[last])
    E_min = min(res.E_by_bar[last])
    assert 0.35 <= S_med <= 0.55
    assert E_min >= 0.7

    # Continuity of modulators: per-bar deltas within caps
    def max_delta(seq):
        return max(abs(b - a) for a, b in zip(seq, seq[1:])) if len(seq) > 1 else 0.0
    assert max_delta(res.swing_series) <= 0.011
    assert max_delta(res.thin_bias_series) <= 0.031
    assert max_delta(res.rot_rate_series) <= 0.021

    # Hat probabilities respect continuity caps and bounds
    rescue_edges = set(res.rescue_bars)

    hatc_steps = list(zip(*res.hatc_prob_series)) if res.hatc_prob_series else []
    for step_hist in hatc_steps:
        for idx, (a, b) in enumerate(zip(step_hist, step_hist[1:])):
            if idx in rescue_edges:
                continue
            assert abs(b - a) <= 0.031
        assert all(0.25 - 1e-6 <= p <= 0.95 + 1e-6 for p in step_hist)

    hato_steps = list(zip(*res.hato_prob_series)) if res.hato_prob_series else []
    for step_hist in hato_steps:
        for idx, (a, b) in enumerate(zip(step_hist, step_hist[1:])):
            if idx in rescue_edges:
                continue
            assert abs(b - a) <= 0.031
        assert all(0.05 - 1e-6 <= p <= 0.75 + 1e-6 for p in step_hist)


def test_m4_micro_caps_and_guard_rescue():
    bpm, ppq, bars = 132, 1920, 64
    res = run_session(bpm=bpm, ppq=ppq, bars=bars)

    # Micro RMS per layer should be within reasonable caps (swing included)
    caps = {36: 10.0, 42: 12.0, 46: 12.0, 38: 15.0, 39: 15.0}
    for note, cap in caps.items():
        # gather all events
        all_events = []
        for evs in res.events_by_layer.values():
            all_events.extend(evs)
        ms = micro_offsets_ms_for_layer(all_events, ppq=ppq, bpm=bpm, note=note)
        if not ms:
            continue
        assert rms(ms) <= cap + 1e-6

    # Guard rescue: simulate low E for a few bars and ensure recovery within 8 bars
    res2 = run_session(bpm=bpm, ppq=ppq, bars=bars, inject_low_E_bars=(10, 12))
    assert res2.rescues >= 1
    # after the low-E window, check within next 8 bars E rises above guard
    window_end = 12
    recovery_window = res2.E_by_bar[window_end + 1: window_end + 9]
    assert recovery_window and max(recovery_window) >= 0.78
