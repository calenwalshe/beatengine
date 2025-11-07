from __future__ import annotations

import json
import os
from pathlib import Path

from techno_engine.terminal import tools


def _use_tmp_dirs(tmp_path: Path):
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = str(tmp_path / "configs")
    os.environ["TECH_ENGINE_OUT_DIR"] = str(tmp_path / "out")


def test_agent_ben_klock_variation(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    res = tools.agent_handle("Create a Ben Klock style groove at 125 bpm for 16 bars with more ghost variation on the kick. Save as klock_test.json")
    midi_path = Path(res["midi_path"])
    cfg_path = Path(res["config_path"])
    assert midi_path.exists()
    assert cfg_path.exists()
    cfg_inline = res["config"]
    cfg = json.loads(cfg_path.read_text())
    assert int(cfg["bpm"]) == 125
    assert int(cfg["bars"]) == 16
    assert int(cfg_inline["bpm"]) == 125
    assert int(cfg_inline["bars"]) == 16
    assert cfg.get("style", "").lower().replace(" ", "_") == "ben_klock"
    kick = cfg.get("layers", {}).get("kick", {})
    assert kick.get("ghost_pre1_prob", 0) >= 0.6


def test_agent_ghost_heavy(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    res = tools.agent_handle("I want tons of ghost pattern on the kick at 130 bpm for 32 bars")
    cfg = json.loads(Path(res["config_path"]).read_text())
    inline = res["config"]
    assert cfg.get("style", "").lower().replace(" ", "_") == "ghost_kick"
    assert cfg.get("bpm") == 130
    assert cfg.get("bars") == 32
    assert inline.get("bpm") == 130
    assert inline.get("bars") == 32
    kick = cfg.get("layers", {}).get("kick", {})
    assert kick.get("ghost_pre1_prob", 0) >= 0.6
