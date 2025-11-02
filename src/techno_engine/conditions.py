from __future__ import annotations

import random
from typing import Iterable, List, Sequence


def every_n(bar_idx: int, n: int, offset: int = 0) -> bool:
    """Return True when bar (1-indexed) matches the EVERY_N schedule.

    Fires on bars: offset, offset+n, offset+2n, ... (1-indexed offset).
    For example, n=4, offset=2 → 2, 6, 10, ...
    """
    if n <= 0:
        return False
    if bar_idx < max(1, offset):
        return False
    return ((bar_idx - offset) % n) == 0


def mask_from_steps(steps_on: Iterable[int], steps: int = 16) -> List[int]:
    m = [0] * steps
    for s in steps_on:
        if 0 <= s < steps:
            m[s] = 1
    return m


def steps_from_mask(mask: Sequence[int]) -> List[int]:
    return [i for i, v in enumerate(mask) if v]


def mute_near_kick(mask: List[int], kick_mask: Sequence[int], window: int = 1) -> List[int]:
    """Zero out steps within ±window of any kick step where kick_mask==1."""
    steps = len(mask)
    kick_idx = [i for i, v in enumerate(kick_mask) if v]
    to_zero = set()
    for k in kick_idx:
        for d in range(-window, window + 1):
            idx = (k + d) % steps
            to_zero.add(idx)
    out = mask[:]
    for i in to_zero:
        out[i] = 0
    return out


def refractory(mask: List[int], refractory_steps: int) -> List[int]:
    """Remove onsets that violate a minimal gap (in steps) since last onset."""
    if refractory_steps <= 0:
        return mask
    out = mask[:]
    last = -10_000
    for i, v in enumerate(mask):
        if v:
            if i - last <= refractory_steps:
                out[i] = 0
            else:
                last = i
    return out


def thin_probs_near_kick(
    base_prob: float,
    steps: int,
    kick_mask: Sequence[int],
    window: int = 1,
    bias: float = -0.5,
) -> List[float]:
    """Return per-step probabilities thinned near kicks by adding bias (clamped).

    bias negative reduces probability at steps within ±window of kick steps.
    """
    probs = [base_prob] * steps
    kick_idx = [i for i, v in enumerate(kick_mask) if v]
    for k in kick_idx:
        for d in range(-window, window + 1):
            idx = (k + d) % steps
            probs[idx] = max(0.0, min(1.0, probs[idx] + bias))
    return probs
