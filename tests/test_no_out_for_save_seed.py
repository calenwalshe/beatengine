from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_config_main


def test_run_config_save_seed_does_not_use_out_folder(tmp_path: Path, monkeypatch) -> None:
    # Config with out pointing under out/
    cfg = {
        "mode": "m1",
        "bpm": 128.0,
        "ppq": 480,
        "bars": 4,
        "seed": 7,
        "out": "out/demo_drums.mid",
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    monkeypatch.chdir(tmp_path)

    rc = run_config_main([
        "--config",
        str(cfg_path),
        "--save-seed",
        "--prompt-text",
        "no-out test",
        "--tags",
        "m1,no_out",
        "--summary",
        "save-seed without out folder",
    ])
    assert rc == 0

    # out/ folder should not contain the rendered MIDI when saving a seed
    assert not (tmp_path / "out" / "demo_drums.mid").is_file()

    # A seed should exist with canonical drums/main.mid
    seeds_root = tmp_path / "seeds"
    assert seeds_root.is_dir()
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert seed_dirs
    seed_dir = seed_dirs[0]
    drums_main = seed_dir / "drums" / "main.mid"
    assert drums_main.is_file()
