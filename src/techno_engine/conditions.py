from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
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


def apply_step_conditions(mask: List[int], bar_idx: int, conditions: Sequence[StepCondition], rng: random.Random) -> List[int]:
    if not conditions:
        return mask
    out = mask[:]
    prev_on = 0
    prev_raw = 0
    bar_1idx = bar_idx + 1
    for step in range(len(out)):
        raw_val = mask[step]
        if out[step] == 0 and raw_val == 0:
            prev_on = 0
            prev_raw = raw_val
            continue
        allowed = True
        for cond in conditions:
            result = True
            if cond.kind == CondType.PROB:
                result = rng.random() < cond.p
            elif cond.kind == CondType.PRE:
                result = prev_raw == 1
            elif cond.kind == CondType.NOT_PRE:
                result = prev_raw == 0
            elif cond.kind == CondType.FILL:
                if cond.n <= 0:
                    result = False
                else:
                    result = every_n(bar_1idx, cond.n, cond.offset)
            elif cond.kind == CondType.EVERY_N:
                if cond.n <= 0:
                    result = False
                else:
                    result = every_n(bar_1idx, cond.n, cond.offset)
            if cond.negate:
                result = not result
            if not result:
                allowed = False
                break
        if not allowed:
            out[step] = 0
            prev_on = 0
        else:
            prev_on = 1
        prev_raw = raw_val
    return out
class CondType(Enum):
    PROB = auto()
    PRE = auto()
    NOT_PRE = auto()
    FILL = auto()
    EVERY_N = auto()


@dataclass
class StepCondition:
    kind: CondType
    p: float = 1.0
    n: int = 0
    offset: int = 0
    negate: bool = False
