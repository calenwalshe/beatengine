from __future__ import annotations

import random
from collections import Counter

from techno_engine.conditions import every_n, mask_from_steps, steps_from_mask, mute_near_kick, refractory, thin_probs_near_kick
from techno_engine.density import enforce_density


def test_every_n_schedule():
    # Bars are 1-indexed; with n=4, offset=2 → bars 2,6,10,... fire
    fired = [i for i in range(1, 21) if every_n(i, n=4, offset=2)]
    assert fired == [2, 6, 10, 14, 18]


def test_mute_near_kick_snare_removal():
    # Kick on 0,4,8,12 then mute within ±1 → indices 3,5,11,13 should be removed
    steps = 16
    kick = mask_from_steps([0, 4, 8, 12], steps)
    snare = [0] * steps
    for i in range(steps):
        snare[i] = 1  # start with all onsets
    snare_muted = mute_near_kick(snare, kick, window=1)
    removed = {3, 5, 11, 13}
    for r in removed:
        assert snare_muted[r] == 0


def test_enforce_density_within_tolerance():
    steps = 16
    # Start with random onsets, enforce target 0.5 ± 0.1 → 8 ± 1.6 → 6..10 acceptable
    mask = [1 if i % 2 == 0 else 0 for i in range(steps)]  # 8 on
    # Make it too dense first
    mask_too_dense = [1] * steps
    out = enforce_density(mask_too_dense, target_ratio=0.5, tol=0.1, metric_w=[1.0] * steps)
    count = sum(out)
    assert 6 <= count <= 10
    # Make it too sparse
    mask_sparse = [0] * steps
    out2 = enforce_density(mask_sparse, target_ratio=0.5, tol=0.1, metric_w=[1.0] * steps)
    count2 = sum(out2)
    assert 6 <= count2 <= 10


def test_hat_thinning_near_kick_statistically():
    steps = 16
    kick = mask_from_steps([0, 4, 8, 12], steps)
    base_p = 0.5
    window = 1
    bias = -0.4
    probs = thin_probs_near_kick(base_p, steps, kick, window=window, bias=bias)

    rng = random.Random(2024)
    # simulate 64 bars of Bernoulli draws per step
    counts = [0] * steps
    bars = 64
    for _ in range(bars):
        for i, p in enumerate(probs):
            if rng.random() < p:
                counts[i] += 1

    near = set()
    for k in [0, 4, 8, 12]:
        for d in (-1, 0, 1):
            near.add((k + d) % steps)
    far_counts = [counts[i] for i in range(steps) if i not in near]
    near_counts = [counts[i] for i in range(steps) if i in near]

    # Near windows should be thinned (lower mean) than far positions
    assert sum(near_counts) / len(near_counts) < sum(far_counts) / len(far_counts)


def test_refractory_removes_doublets():
    steps = 16
    # Build a mask with clustered onsets
    mask = [0] * steps
    for i in [0, 1, 4, 5, 8, 9]:
        mask[i] = 1
    out = refractory(mask, refractory_steps=1)
    # After refractory of 1, immediate neighbors should be cleared
    # Expect only steps 0,4,8 remain
    assert steps_from_mask(out) == [0, 4, 8]

