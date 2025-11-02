from __future__ import annotations

from typing import List


def bjorklund(steps: int, pulses: int) -> List[int]:
    """Return a Euclidean rhythm mask of length `steps` with `pulses` ones.
    Simple Bjorklund implementation yielding a 0/1 list.
    """
    if pulses <= 0:
        return [0] * steps
    if pulses >= steps:
        return [1] * steps

    counts = []
    remainders = []
    divisor = steps - pulses
    remainders.append(pulses)
    level = 0
    while True:
        counts.append(divisor // remainders[level])
        remainders.append(divisor % remainders[level])
        divisor = remainders[level]
        level += 1
        if remainders[level] <= 1:
            break
    counts.append(divisor)

    def build(level):
        if level == -1:
            return [0]
        if level == -2:
            return [1]
        res = []
        for _ in range(counts[level]):
            res += build(level - 1)
        if remainders[level] != 0:
            res += build(level - 2)
        return res

    pattern = build(level)
    # pattern may be shorter than steps; repeat and trim
    out = (pattern * (steps // len(pattern) + 1))[:steps]
    return out


def rotate(mask: List[int], rot: int) -> List[int]:
    steps = len(mask)
    if steps == 0:
        return mask
    r = rot % steps
    return mask[-r:] + mask[:-r] if r else mask[:]

