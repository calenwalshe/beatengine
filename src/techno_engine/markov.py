from __future__ import annotations

import random
from typing import Iterable, List, Sequence


DEFAULT_METRIC_WEIGHTS: List[float] = [
    0.0,  # 0 (beat)
    0.6,  # 1
    0.6,  # 2 (offbeat)
    0.6,  # 3
    0.0,  # 4 (beat)
    0.6,
    0.6,
    0.6,
    0.0,  # 8 (beat)
    0.6,
    0.6,
    0.6,
    0.0,  # 12 (beat)
    0.6,
    0.6,
    0.6,
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def update_probabilities(
    probs: Sequence[float],
    sync_error: float,
    metric_weights: Sequence[float],
    gain: float,
    delta_cap: float,
    p_floor: float,
    p_ceil: float,
) -> List[float]:
    updated: List[float] = []
    for prev, weight in zip(probs, metric_weights):
        target = prev + gain * sync_error * weight
        target = clamp(target, p_floor, p_ceil)
        delta = target - prev
        if delta > delta_cap:
            target = prev + delta_cap
        elif delta < -delta_cap:
            target = prev - delta_cap
        updated.append(clamp(target, p_floor, p_ceil))
    return updated


def sample_markov_mask(
    probs: Sequence[float],
    rng: random.Random,
    prev_state: int,
    *,
    offbeats_only: bool,
    stickiness: float,
    p_floor: float,
    p_ceil: float,
) -> tuple[List[int], int]:
    mask = [0] * len(probs)
    state = prev_state
    for idx, base_p in enumerate(probs):
        if offbeats_only and idx % 4 != 2:
            state = 0
            continue
        p_eff = clamp(base_p, p_floor, p_ceil)
        if state == 1:
            p_eff = clamp(p_eff * (1.0 - stickiness), p_floor, p_ceil)
        if rng.random() < p_eff:
            mask[idx] = 1
            state = 1
        else:
            state = 0
    return mask, state

