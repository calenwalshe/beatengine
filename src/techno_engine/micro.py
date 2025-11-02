from __future__ import annotations

import random as _random
from typing import List, Optional

from .timebase import ms_to_ticks


def sample_beat_bin(bins_ms: List[float], probs: List[float], rng: Optional[_random.Random] = None) -> float:
    """Sample a micro offset (ms) from discrete bins using provided probabilities."""
    rng = rng or _random
    r = rng.random()
    acc = 0.0
    for i, p in enumerate(probs):
        acc += p
        if r <= acc:
            return float(bins_ms[i])
    return float(bins_ms[-1])


def apply_swing_and_micro(
    step_idx: int,
    base_tick: int,
    swing_percent: Optional[float],
    micro_ms: float,
    bpm: float,
    ppq: int,
    cap_ms: Optional[float] = None,
) -> int:
    """Apply even-16th swing (odd steps delayed) and micro offset (ms) to base tick.

    swing_percent: 0.5 = straight; 0.55 → delay odd 16ths by (0.05 * ppq/8) ticks.
    micro_ms: signed milliseconds; clamped to cap_ms if provided.
    """
    tick = base_tick

    # Swing: only if provided
    if swing_percent is not None:
        # odd steps (1,3,5,...) delayed relative to even 16ths
        if step_idx % 2 == 1:
            swing_ticks = int(round((swing_percent - 0.5) * (ppq / 8.0)))
            tick += max(0, swing_ticks)

    # Clamp micro
    if cap_ms is not None:
        if micro_ms > 0:
            micro_ms = min(micro_ms, cap_ms)
        else:
            micro_ms = max(micro_ms, -cap_ms)

    tick += ms_to_ticks(micro_ms, ppq=ppq, bpm=bpm)
    return tick

