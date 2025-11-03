from __future__ import annotations

from statistics import mean

from techno_engine.controller import run_session
from techno_engine.modulate import Modulator, ParamModSpec


def test_param_modulators_adjust_hat_swing_and_thin_bias():
    swing_mod = ParamModSpec(
        name="hat_swing",
        param_path="hat_c.swing_percent",
        modulator=Modulator(name="sw", mode="ou", min_val=0.53, max_val=0.57, step_per_bar=0.01, tau=24.0, max_delta_per_bar=0.01),
    )
    thin_mod = ParamModSpec(
        name="thin_bias",
        param_path="thin_bias",
        modulator=Modulator(name="thin", mode="random_walk", min_val=-0.6, max_val=-0.1, step_per_bar=0.03, max_delta_per_bar=0.03),
    )

    res = run_session(bpm=132, ppq=1920, bars=48, param_mods=[swing_mod, thin_mod])

    assert max(res.swing_series) <= 0.58 + 1e-6
    assert min(res.swing_series) >= 0.51 - 1e-6
    assert min(res.thin_bias_series) >= -0.6 - 1e-6
    assert max(res.thin_bias_series) <= 0.0 + 1e-6
    assert len(set(round(x, 4) for x in res.swing_series)) > 1
    assert len(set(round(x, 4) for x in res.thin_bias_series)) > 1
