from __future__ import annotations

from typing import List, Sequence


def enforce_density(mask: List[int], target_ratio: float, tol: float, metric_w: Sequence[float] | None = None) -> List[int]:
    """Clamp number of onsets in mask to target ± tol*len(mask).

    If too many: prune weakest (lowest metric weight) first; default weight=1.
    If too few: add strongest silent positions first.
    """
    n = len(mask)
    target = int(round(n * target_ratio))
    allow = int(round(tol * n))
    idx_on = [i for i, v in enumerate(mask) if v == 1]
    if metric_w is None:
        metric_w = [1.0] * n

    if len(idx_on) > target + allow:
        # prune weakest
        idx_on_sorted = sorted(idx_on, key=lambda i: metric_w[i])
        to_prune = len(idx_on) - (target + allow)
        for i in idx_on_sorted[:to_prune]:
            mask[i] = 0
    elif len(idx_on) < max(0, target - allow):
        idx_off = [i for i, v in enumerate(mask) if v == 0]
        idx_off_sorted = sorted(idx_off, key=lambda i: -metric_w[i])
        to_add = min(len(idx_off_sorted), (target - allow) - len(idx_on))
        for i in idx_off_sorted[:to_add]:
            mask[i] = 1
    return mask

