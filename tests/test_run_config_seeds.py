from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_cli


def test_run_config_saves_seed(tmp_path: Path, monkeypatch) -> None:
    cfg = {
        "mode": "m1",
        "bpm": 132,
        "ppq": 1920,
        "bars": 4,
        "seed": 1234,
        "out": str(tmp_path / "m1.mid"),
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    # Run in a temporary working directory so seeds/ is isolated
    monkeypatch.chdir(tmp_path)

    rc = run_cli(
        [
            "--config",
            str(cfg_path),
            "--save-seed",
            "--prompt-text",
            "warehouse m1 groove",
            "--tags",
            "m1,test",
            "--summary",
            "unit test seed",
        ]
    )
    assert rc == 0

    seeds_root = tmp_path / "seeds"
    assert seeds_root.is_dir()

    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) == 1

    seed_dir = seed_dirs[0]
    meta_path = seed_dir / "metadata.json"
    cfg_copy_path = seed_dir / "config.json"

    assert meta_path.is_file()
    assert cfg_copy_path.is_file()

    meta = json.loads(meta_path.read_text())
    assert meta["engine_mode"] == cfg["mode"]
    assert meta["bpm"] == cfg["bpm"]
    assert meta["bars"] == cfg["bars"]
    assert meta["rng_seed"] == cfg["seed"]
    assert meta["tags"] == ["m1", "test"]
    assert meta["prompt"] == "warehouse m1 groove"
    assert meta["summary"] == "unit test seed"
