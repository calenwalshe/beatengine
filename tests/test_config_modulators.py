from __future__ import annotations

import json
from pathlib import Path

from techno_engine.config import load_engine_config
from techno_engine.controller import run_session


def test_load_engine_config_parses_modulators_and_conditions(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "mode": "m4",
        "bpm": 132,
        "ppq": 1920,
        "bars": 16,
        "seed": 42,
        "log_path": str(tmp_path / "log.csv"),
        "layers": {
            "hat_c": {
                "steps": 16,
                "fills": 12,
                "conditions": [
                    {"kind": "EVERY_N", "n": 4, "offset": 2}
                ]
            }
        },
        "guard": {"kick_immutable": False, "min_E": 0.7},
        "modulators": [
            {
                "name": "hat_swing",
                "param_path": "hat_c.swing_percent",
                "mod": {
                    "mode": "ou",
                    "min_val": 0.53,
                    "max_val": 0.57,
                    "step_per_bar": 0.01,
                    "max_delta_per_bar": 0.01,
                    "tau": 16
                }
            }
        ]
    }))

    cfg = load_engine_config(str(config_path))
    assert cfg.modulators and cfg.modulators[0].param_path == "hat_c.swing_percent"
    assert cfg.guard.kick_immutable is False
    assert cfg.hat_c and cfg.hat_c.conditions[0].kind.name == "EVERY_N"

    res = run_session(
        bpm=cfg.bpm,
        ppq=cfg.ppq,
        bars=cfg.bars,
        guard=cfg.guard,
        hat_c_cfg=cfg.hat_c,
        param_mods=cfg.modulators,
        log_path=cfg.log_path,
    )
    assert res.hatc_prob_series
    log_file = Path(cfg.log_path)
    assert log_file.exists()
