from __future__ import annotations

import math
import random
from pathlib import Path

from techno_engine.parametric import LayerConfig, build_layer, collect_closed_hat_ticks, compute_dispersion
from techno_engine.timebase import ticks_per_bar


def _first_bar_step_ticks(ppq: int, steps: int = 16):
    bar_ticks = ticks_per_bar(ppq, 4)
    return [int(round(i * (bar_ticks / steps))) for i in range(steps)]


def test_swing_delay_for_odd_16ths():
    bpm, ppq, bars = 132, 1920, 1
    # Build a straight 16th hat layer with swing 0.55, no beat-bins
    cfg = LayerConfig(steps=16, fills=16, rot=0, note=42, velocity=80, swing_percent=0.55)
    events = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=cfg)

    # Compute expected swing delay in ticks: (ppq/8) * 0.05
    expected_delay = int(round((ppq / 8.0) * 0.05))

    # Extract first bar step starts
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16

    # Map step index -> observed start tick (closest)
    step_start = {}
    for ev in events:
        step = (ev.start_abs_tick % bar_ticks) // step_ticks
        # pick earliest occurrence per step (should be one)
        step_start.setdefault(int(step), ev.start_abs_tick)

    # Assert odd steps are delayed by expected amount
    for i in range(16):
        nominal = i * step_ticks
        observed = step_start[i]
        if i % 2 == 1:
            assert observed - nominal == expected_delay
        else:
            assert observed - nominal == 0


def test_beat_bins_sampling_and_cap():
    bpm, ppq, bars = 132, 1920, 8
    rng = random.Random(123)
    bins = [-10, -6, -2, 0]
    probs = [0.4, 0.35, 0.2, 0.05]
    cap_ms = 12
    cfg = LayerConfig(
        steps=16,
        fills=16,
        note=42,
        velocity=80,
        swing_percent=None,
        beat_bins_ms=bins,
        beat_bins_probs=probs,
        beat_bin_cap_ms=cap_ms,
    )
    events = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=cfg, rng=rng)

    # Check that implied micro offsets used are within bins: we infer by comparing to nominal grid
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    offsets_ms = []
    for ev in events[:128]:  # first 8 bars * 16 steps
        # Nearest nominal step boundary in this bar
        bar_idx = ev.start_abs_tick // bar_ticks
        candidates = []
        for b in (bar_idx - 1, bar_idx, bar_idx + 1):
            bstart = b * bar_ticks
            candidates.extend([bstart + i * step_ticks for i in range(16)])
        nominal = min(candidates, key=lambda t: abs(ev.start_abs_tick - t))
        delta_ticks = ev.start_abs_tick - nominal
        # swing is None, so all delta comes from micro; convert to ms
        ticks_per_ms = (ppq * bpm) / 60000.0
        ms = delta_ticks / ticks_per_ms
        offsets_ms.append(ms)
        # Should be approximately one of the bins (allow small rounding drift)
        assert min(abs(ms - b) for b in bins) < 0.5

    # RMS should be <= cap
    rms = math.sqrt(sum(m * m for m in offsets_ms) / len(offsets_ms))
    assert rms <= cap_ms + 1e-6


def test_choke_open_hat_with_closed_hat():
    bpm, ppq, bars = 132, 1920, 1
    # Closed hat: 16ths
    closed_cfg = LayerConfig(steps=16, fills=16, note=42, velocity=80)
    closed_events = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=closed_cfg)
    ch_map = collect_closed_hat_ticks(closed_events, ppq=ppq, closed_hat_note=42)

    # Open hat: offbeats, long duration, but choked by next closed hat tick
    open_cfg = LayerConfig(
        steps=16,
        fills=16,
        note=46,
        velocity=80,
        offbeats_only=True,
        choke_with_note=42,
    )
    open_events = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=open_cfg, closed_hat_ticks_by_bar=ch_map)

    # For each open hat, ensure its duration is truncated to next closed hat onset
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    for ev in open_events:
        step = (ev.start_abs_tick % bar_ticks) // step_ticks
        assert step % 4 == 2  # offbeats
        # Next closed hat is at step+1 (16th later)
        next_closed = ev.start_abs_tick + step_ticks
        assert ev.dur_tick <= step_ticks and ev.start_abs_tick + ev.dur_tick <= next_closed


def test_dispersion_relationship_with_ratchets():
    bpm, ppq, bars = 132, 1920, 8
    # Kick: Euclid 4 on 16 (4/4) → equal IOIs
    kick_cfg = LayerConfig(steps=16, fills=4, note=36, velocity=110)
    k = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=kick_cfg)
    # Closed hat: straight 16ths
    hatc_cfg = LayerConfig(steps=16, fills=16, note=42, velocity=80)
    hc = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=hatc_cfg)
    # Open hat: offbeats with ratchets to increase IOI variance
    hato_cfg = LayerConfig(steps=16, fills=16, note=46, velocity=80, offbeats_only=True, ratchet_prob=0.5, ratchet_repeat=3)
    ho = build_layer(bpm=bpm, ppq=ppq, bars=bars, cfg=hato_cfg)

    events = k + hc + ho
    D_kick = compute_dispersion(events, ppq, note=36)
    D_hatc = compute_dispersion(events, ppq, note=42)
    D_hato = compute_dispersion(events, ppq, note=46)

    assert D_kick < 1e-6
    assert D_hatc < D_hato
