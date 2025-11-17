from __future__ import annotations

import json
from pathlib import Path

from techno_engine.paired_render_cli import main as paired_main


def test_paired_render_creates_seed_with_drum_and_bass(tmp_path: Path, monkeypatch) -> None:
    cfg = {
        "mode": "m1",
        "bpm": 128.0,
        "ppq": 480,
        "bars": 4,
        "seed": 4242,
        "out": "drums.mid",
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    monkeypatch.chdir(tmp_path)

    rc = paired_main(
        [
            "--config",
            str(cfg_path),
            "--prompt-text",
            "paired render test",
            "--tags",
            "m1,paired_test",
            "--summary",
            "paired drums+bass seed",
        ]
    )
    assert rc == 0

    # Check MIDI outputs
    drums_path = tmp_path / "drums.mid"
    bass_path = tmp_path / "drums_bass.mid"
    assert drums_path.is_file()
    assert bass_path.is_file()

    # Check seed directory and metadata
    seeds_root = tmp_path / "seeds"
    assert seeds_root.is_dir()
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) == 1

    seed_dir = seed_dirs[0]
    meta_path = seed_dir / "metadata.json"
    assert meta_path.is_file()

    meta = json.loads(meta_path.read_text())
    assert meta["engine_mode"] == cfg["mode"]
    assert meta["bpm"] == cfg["bpm"]
    assert meta["bars"] == cfg["bars"]
    assert meta["tags"] == ["m1", "paired_test"]

    assets = meta.get("assets") or []
    roles = {a.get("role") for a in assets if isinstance(a, dict)}
    assert "main" in roles
    assert "bass" in roles

    # The bass asset path should point to an existing file.
    bass_assets = [a for a in assets if isinstance(a, dict) and a.get("role") == "bass"]
    assert bass_assets
    bass_asset_path = Path(bass_assets[0]["path"])
    if not bass_asset_path.is_absolute():
        bass_asset_path = (tmp_path / bass_asset_path).resolve()
    assert bass_asset_path.is_file()
