from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from techno_engine.terminal.schemas import RenderSessionInput, CreateConfigInput, ReadConfigInput, WriteConfigInput
from techno_engine.terminal import tools


def _use_tmp_dirs(tmp_path: Path):
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = str(tmp_path / "configs")
    os.environ["TECH_ENGINE_OUT_DIR"] = str(tmp_path / "out")


def test_render_session_with_inline_creates_mid(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    inp = RenderSessionInput(config_path=None, inline_config={"mode": "m1", "bpm": 132, "ppq": 1920, "bars": 4})
    out = tools.render_session(inp)
    assert out.path.endswith(".mid")
    p = Path(out.path)
    assert p.exists() and p.stat().st_size > 0


def test_create_and_list_configs(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    # create
    params = {"mode": "m1", "bpm": 130, "bars": 8}
    resp = tools.create_config(CreateConfigInput(name="demo.json", params=params))
    path = Path(resp["path"])
    assert path.exists()
    # list
    listed = tools.list_configs()
    assert "demo.json" in listed.items


def test_read_and_write_config(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    cfg_name = "demo2.json"
    body = json.dumps({"mode": "m1", "bpm": 128, "bars": 8})
    tools.write_config(WriteConfigInput(name=cfg_name, body=body))
    resp = tools.read_config(ReadConfigInput(name=cfg_name))
    assert Path(resp["path"]).exists()
    parsed = json.loads(resp["body"])
    assert parsed["bpm"] == 128


def test_write_config_rejects_invalid_json(tmp_path: Path):
    _use_tmp_dirs(tmp_path)
    with pytest.raises(ValueError):
        tools.write_config(WriteConfigInput(name="bad.json", body="{not:json}"))

