from __future__ import annotations

from typing import List

from techno_engine.bassline import generate_mvp, build_swung_grid
from techno_engine.midi_writer import MidiEvent


def _count_by_bar(events: List[MidiEvent], bar_ticks: int) -> list[int]:
    bars = 0
    for ev in events:
        bars = max(bars, (ev.start_abs_tick // bar_ticks) + 1)
    counts = [0 for _ in range(bars)]
    for ev in events:
        counts[ev.start_abs_tick // bar_ticks] += 1
    return counts


def test_density_within_loose_tolerance():
    bpm, ppq, bars = 120.0, 1920, 8
    g = build_swung_grid(bpm, ppq)
    rho = 0.5
    ev = generate_mvp(bpm=bpm, ppq=ppq, bars=bars, density_target=rho)
    per_bar = _count_by_bar(ev, g.bar_ticks)
    # expected notes per bar ~ 16 * rho
    target = round(16 * rho)
    # allow ±0.05*16 ≈ ±1 tolerance
    tol = int(round(16 * 0.05))
    assert all(abs(c - target) <= tol for c in per_bar)


def test_density_scales_with_config():
    bpm, ppq, bars = 120.0, 1920, 4
    g = build_swung_grid(bpm, ppq)
    ev_lo = generate_mvp(bpm=bpm, ppq=ppq, bars=bars, density_target=0.25)
    ev_hi = generate_mvp(bpm=bpm, ppq=ppq, bars=bars, density_target=0.6)
    c_lo = sum(_count_by_bar(ev_lo, g.bar_ticks))
    c_hi = sum(_count_by_bar(ev_hi, g.bar_ticks))
    assert c_hi >= c_lo


def test_min_duration_respected():
    bpm, ppq, bars = 120.0, 1920, 2
    g = build_swung_grid(bpm, ppq)
    min_steps = 0.375
    ev = generate_mvp(bpm=bpm, ppq=ppq, bars=bars, density_target=0.4, min_dur_steps=min_steps)
    min_ticks = int(round(min_steps * g.step_ticks))
    assert all(e.dur_tick >= min_ticks for e in ev)

