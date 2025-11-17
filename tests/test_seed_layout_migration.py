from __future__ import annotations
from dataclasses import asdict

import json
from pathlib import Path

from techno_engine.seeds import SeedMetadata, rebuild_index


def _make_legacy_seed(tmp_path: Path) -> Path:
    seeds_root = tmp_path / "seeds"
    seed_id = "legacy_seed_1"
    seed_dir = seeds_root / seed_id
    seed_dir.mkdir(parents=True, exist_ok=True)

    # Legacy render in out/ path (outside seed folder)
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    legacy_mid = out_dir / "legacy.mid"
    legacy_mid.write_bytes(b"MThd")  # minimal bytes; we never parse

    meta = SeedMetadata(
        seed_id=seed_id,
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=128.0,
        bars=4,
        ppq=480,
        rng_seed=1,
        config_path="config.json",
        render_path=str(legacy_mid),  # legacy absolute/outer path
        log_path=None,
        prompt=None,
        prompt_context=None,
        summary="legacy seed",
        tags=["legacy"],
        assets=[],
        parent_seed_id=None,
        file_version=1,
    )

    # Minimal config.json just to satisfy loader expectations if needed.
    cfg = {
        "mode": "m4",
        "bpm": 128.0,
        "ppq": 480,
        "bars": 4,
        "seed": 1,
        "out": str(legacy_mid),
    }
    (seed_dir / "config.json").write_text(json.dumps(cfg))
    (seed_dir / "metadata.json").write_text(json.dumps(asdict(meta), indent=2, sort_keys=True))
    return seeds_root


def test_rebuild_index_migrates_legacy_render_to_drums_main(tmp_path: Path, monkeypatch) -> None:
    # Use tmp_path as CWD so relative resolution matches legacy behaviour.
    monkeypatch.chdir(tmp_path)
    seeds_root = _make_legacy_seed(tmp_path)

    metas = rebuild_index(seeds_root=seeds_root)
    assert metas
    meta = [m for m in metas if m.seed_id.startswith("legacy_seed_1")][0]

    seed_dir = seeds_root / meta.seed_id
    drums_main = seed_dir / "drums" / "main.mid"

    # After migration, render_path should be canonical and file should exist.
    assert meta.render_path == "drums/main.mid"
    assert drums_main.is_file()

    # There must be a main/midi asset pointing to drums/main.mid.
    assert meta.assets
    main_assets = [a for a in meta.assets if a.role == "main" and a.kind == "midi"]
    assert main_assets
    assert main_assets[0].path == "drums/main.mid"
