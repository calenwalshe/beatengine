from __future__ import annotations

import os
from pathlib import Path

from techno_engine.terminal import tools


def _tmp_dirs(tmp_path: Path):
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = str(tmp_path / "configs")
    os.environ["TECH_ENGINE_OUT_DIR"] = str(tmp_path / "out")


def test_make_bass_for_config_smoke(tmp_path: Path):
    _tmp_dirs(tmp_path)
    cfg = "techno_rhythm_engine/configs/m4_95bpm.json" if Path("techno_rhythm_engine/configs/m4_95bpm.json").exists() else "configs/m4_95bpm.json"
    res = tools.make_bass_for_config({"config_path": cfg, "key": "A", "mode": "minor", "density": 0.4, "save_prefix": "demo"})
    assert Path(res["drums"]).exists()
    assert Path(res["bass"]).exists()
    assert Path(res["drums"]).name.startswith("demo_")
    assert isinstance(res.get("summaries"), list)
    assert "E_med" in res and "S_med" in res
