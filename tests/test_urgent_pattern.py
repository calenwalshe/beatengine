from __future__ import annotations

from statistics import median

from techno_engine.controller import run_session, Targets
from techno_engine.modulate import Modulator, ParamModSpec
from techno_engine.parametric import LayerConfig
from techno_engine.timebase import ticks_per_bar


def _hat_density_per_bar(res, ppq: int):
    bar_ticks = ticks_per_bar(ppq, 4)
    bars = len(res.E_by_bar)
    counts = [0] * bars
    for ev in res.events_by_layer["hat_c"]:
        counts[ev.start_abs_tick // bar_ticks] += 1
    return [c / 16.0 for c in counts]


def _ratchet_ratio(res, ppq: int):
    # proportion of bars where open-hat onsets exceed 4 (offbeats only), implying ratchets
    bar_ticks = ticks_per_bar(ppq, 4)
    bars = len(res.E_by_bar)
    counts = [0] * bars
    for ev in res.events_by_layer["hat_o"]:
        counts[ev.start_abs_tick // bar_ticks] += 1
    above = sum(1 for c in counts if c > 4)
    return above / max(1, bars)


def test_urgent_pattern_differs_from_baseline():
    bpm, ppq, bars = 132, 1920, 64

    # Baseline controller session
    base = run_session(bpm=bpm, ppq=ppq, bars=bars)
    base_S_med = median(base.S_by_bar[bars//2:])
    base_hat_density = sum(_hat_density_per_bar(base, ppq)) / bars
    base_ratchet_ratio = _ratchet_ratio(base, ppq)

    # Urgent: higher sync band, denser hats, more OH ratchets, offbeat accents
    urgent_targets = Targets(S_low=0.5, S_high=0.75, hat_density_target=0.85, hat_density_tol=0.05)
    urgent_mods = [
        ParamModSpec("oh_ratchet", "hat_o.ratchet_prob", Modulator(name="rat", mode="random_walk", min_val=0.1, max_val=0.25, step_per_bar=0.02, max_delta_per_bar=0.02)),
        ParamModSpec("thin_bias", "thin_bias", Modulator(name="thin", mode="ou", min_val=-0.4, max_val=-0.05, step_per_bar=0.02, tau=24.0, max_delta_per_bar=0.03)),
    ]
    urgent_hat_c = LayerConfig(steps=16, fills=14)  # slightly denser base
    urgent = run_session(bpm=bpm, ppq=ppq, bars=bars, targets=urgent_targets, hat_c_cfg=urgent_hat_c, param_mods=urgent_mods)

    urg_S_med = median(urgent.S_by_bar[bars//2:])
    urg_hat_density = sum(_hat_density_per_bar(urgent, ppq)) / bars
    urg_ratchet_ratio = _ratchet_ratio(urgent, ppq)

    # Assertions that capture musical difference
    # Syncopation should not decrease for the urgent pattern
    assert urg_S_med >= base_S_med
    # Hats should be at least as dense
    assert urg_hat_density >= base_hat_density
    assert urg_ratchet_ratio > base_ratchet_ratio + 0.05
