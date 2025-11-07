from __future__ import annotations

import os
from pathlib import Path

from techno_engine.terminal import tools


def _use_tmp_dirs(tmp_path: Path):
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = str(tmp_path / "configs")
    os.environ["TECH_ENGINE_OUT_DIR"] = str(tmp_path / "out")


def test_bass_generate_mvp_and_validate(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    res = tools.bass_generate({"bpm": 120.0, "ppq": 1920, "bars": 4, "mode": "mvp", "root_note": 45, "density": 0.4})
    assert res.get("code") == "OK"
    val = tools.bass_validate({"bpm": 120.0, "ppq": 1920, "bars": 4, "density": 0.4, "events": res["events"]})
    assert val.get("code") == "OK"
    assert isinstance(val.get("events"), list)


def test_bass_generate_scored_requires_masks(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    bad = tools.bass_generate({"bpm": 120.0, "ppq": 1920, "bars": 4, "mode": "scored", "root_note": 45, "density": 0.4})
    assert bad.get("code") == "BAD_CONFIG"

