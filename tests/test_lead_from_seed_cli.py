from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_config_main
from techno_engine.seed_cli import main as seed_main


def _make_m1_cfg(tmp_path: Path) -> Path:
    cfg = {
        "mode": "m1",
        "bpm": 128.0,
        "ppq": 480,
        "bars": 4,
        "seed": 999,
        "out": str(tmp_path / "drums.mid"),
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))
    return cfg_path


def test_lead_from_seed_creates_lead_asset(tmp_path: Path, monkeypatch) -> None:
    cfg_path = _make_m1_cfg(tmp_path)

    # First render drums and save a seed.
    monkeypatch.chdir(tmp_path)
    rc = run_config_main(
        [
            "--config",
            str(cfg_path),
            "--save-seed",
            "--prompt-text",
            "lead-from-seed test",
            "--tags",
            "m1,lead_seed,minimal",
            "--summary",
            "seed for lead-from-seed",
        ]
    )
    assert rc == 0

    seeds_root = tmp_path / "seeds"
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) == 1
    seed_id = seed_dirs[0].name

    # Now call lead-from-seed on that seed.
    rc2 = seed_main(
        [
            "lead-from-seed",
            seed_id,
            "--root",
            str(seeds_root),
            "--mode",
            "Minimal Stab Lead",
            "--description",
            "test lead asset",
        ]
    )
    assert rc2 == 0

    meta_path = seeds_root / seed_id / "metadata.json"
    meta = json.loads(meta_path.read_text())
    assets = meta.get("assets") or []
    roles = {a.get("role") for a in assets if isinstance(a, dict)}
    assert "lead" in roles

    lead_assets = [a for a in assets if isinstance(a, dict) and a.get("role") == "lead"]
    assert lead_assets
    lead_rel = Path(lead_assets[0]["path"])
    assert str(lead_rel).startswith("leads/")
    lead_abs = (seeds_root / seed_id / lead_rel).resolve()
    assert lead_abs.is_file()
