from __future__ import annotations

import random

from techno_engine.conditions import StepCondition, CondType, apply_step_conditions
from techno_engine.parametric import LayerConfig, build_layer


def test_prob_condition_allows_full_or_none():
    rng = random.Random(0)
    mask = [1] * 16
    cond = StepCondition(kind=CondType.PROB, p=0.0)
    result = apply_step_conditions(mask, bar_idx=0, conditions=[cond], rng=rng)
    assert sum(result) == 0

    cond_full = StepCondition(kind=CondType.PROB, p=1.0)
    result_full = apply_step_conditions(mask, bar_idx=0, conditions=[cond_full], rng=rng)
    assert result_full == mask


def test_pre_and_not_pre_conditions():
    rng = random.Random(1)
    mask = [1, 1, 0, 1]
    cond_pre = StepCondition(kind=CondType.PRE)
    res = apply_step_conditions(mask, 0, [cond_pre], rng)
    assert res == [0, 1, 0, 0]

    cond_not_pre = StepCondition(kind=CondType.NOT_PRE)
    res_not = apply_step_conditions(mask, 0, [cond_not_pre], rng)
    assert res_not == [1, 0, 0, 1]


def test_fill_and_every_n_schedule():
    cfg = LayerConfig(
        steps=16,
        fills=16,
        note=42,
        velocity=80,
        conditions=[StepCondition(kind=CondType.FILL, n=4, offset=4)],
    )
    rng = random.Random(0)
    # Bars 4,8,... should have hats; others cleared
    events = build_layer(bpm=132, ppq=1920, bars=8, cfg=cfg, rng=rng)
    bar_counts = [0] * 8
    bar_ticks = (1920 * 4)
    for ev in events:
        bar_counts[ev.start_abs_tick // bar_ticks] += 1
    assert bar_counts[:4] == [0, 0, 0, 16]
    assert bar_counts[4:] == [0, 0, 0, 16]


def test_conditions_combined_with_prob_and_schedule():
    rng = random.Random(3)
    mask = [1] * 16
    conds = [
        StepCondition(kind=CondType.PROB, p=0.5),
        StepCondition(kind=CondType.EVERY_N, n=2, offset=2),
    ]
    keep = apply_step_conditions(mask, bar_idx=1, conditions=conds, rng=rng)
    assert 0 < sum(keep) < len(mask)

    # Offset bar should block due to EVERY_N schedule
    blocked = apply_step_conditions(mask, bar_idx=0, conditions=conds, rng=rng)
    assert sum(blocked) == 0
