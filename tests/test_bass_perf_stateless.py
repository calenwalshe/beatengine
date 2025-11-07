from __future__ import annotations

import time
from typing import List, Tuple

from techno_engine.bassline import generate_mvp, generate_scored
from techno_engine.midi_writer import MidiEvent


def _canon(events: List[MidiEvent]) -> List[Tuple[int, int, int]]:
    return sorted([(e.note, e.start_abs_tick, e.dur_tick) for e in events])


def test_stateless_reentrancy_and_determinism():
    # Same seed twice
    a1 = _canon(generate_mvp(120.0, 1920, 4, seed=111, root_note=45))
    a2 = _canon(generate_mvp(120.0, 1920, 4, seed=111, root_note=45))
    assert a1 == a2
    # Interleave different seed and verify no leakage
    _ = generate_mvp(120.0, 1920, 4, seed=999, root_note=45)
    a3 = _canon(generate_mvp(120.0, 1920, 4, seed=111, root_note=45))
    assert a1 == a3


def test_latency_budget_average_small():
    # Very light budget so CI variability doesn't fail: average < 10ms per call
    n = 100
    t0 = time.perf_counter()
    for i in range(n):
        _ = generate_mvp(120.0, 1920, 4, seed=i, root_note=45, density_target=0.4)
    dt = (time.perf_counter() - t0) / n
    assert dt < 0.01  # 10ms per call average


def test_scored_latency_budget():
    bpm = 120.0
    ppq = 1920
    bars = 4
    kick_masks = [[1 if i in (0, 4, 8, 12) else 0 for i in range(16)] for _ in range(bars)]
    hat_masks = [[1 if i in (2, 6, 10, 14) else 0 for i in range(16)] for _ in range(bars)]
    clap_masks = [[1 if i == 12 else 0 for i in range(16)] for _ in range(bars)]
    t0 = time.perf_counter()
    n = 40
    for i in range(n):
        generate_scored(bpm=bpm, ppq=ppq, bars=bars, root_note=45,
                        kick_masks_by_bar=kick_masks, hat_masks_by_bar=hat_masks,
                        clap_masks_by_bar=clap_masks, density_target=0.4)
    dt = (time.perf_counter() - t0) / n
    assert dt < 0.015  # 15ms average budget
