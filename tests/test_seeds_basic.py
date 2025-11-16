from __future__ import annotations

import json
from pathlib import Path

from techno_engine.config import engine_config_from_dict
from techno_engine.seeds import load_seed, save_seed


def test_seed_save_and_load_roundtrip(tmp_path: Path) -> None:
    seeds_root = tmp_path / "seeds"

    raw_cfg = {
        "mode": "m4",
        "bpm": 130.0,
        "ppq": 1920,
        "bars": 8,
        "seed": 42,
        "out": "out/test_seed.mid",
    }

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_cfg))

    cfg = engine_config_from_dict(raw_cfg)
    render_path = str(tmp_path / "render.mid")

    meta = save_seed(
        cfg,
        config_path=str(config_path),
        render_path=render_path,
        prompt="test prompt",
        summary="short summary",
        tags=["test", "m4"],
        seeds_root=seeds_root,
    )

    # Basic metadata sanity checks
    assert meta.seed_id
    assert meta.engine_mode == "m4"
    assert meta.bpm == raw_cfg["bpm"]
    assert meta.bars == raw_cfg["bars"]
    assert meta.rng_seed == raw_cfg["seed"]
    assert meta.tags == ["test", "m4"]

    seed_dir = seeds_root / meta.seed_id
    assert seed_dir.is_dir()
    assert (seed_dir / "config.json").is_file()
    assert (seed_dir / "metadata.json").is_file()

    loaded_cfg, loaded_meta = load_seed(meta.seed_id, seeds_root=seeds_root)

    assert loaded_meta.seed_id == meta.seed_id
    assert loaded_meta.engine_mode == meta.engine_mode
    assert loaded_cfg.bpm == cfg.bpm
    assert loaded_cfg.bars == cfg.bars
    assert loaded_cfg.ppq == cfg.ppq
    assert loaded_cfg.seed == cfg.seed

