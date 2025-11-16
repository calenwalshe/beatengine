from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_config_main
from techno_engine.seed_explorer import main as explorer_main, demo_output


def _make_seed(tmp_path: Path, mode: str, bpm: float, tag: str) -> str:
    cfg = {
        "mode": mode,
        "bpm": bpm,
        "ppq": 1920,
        "bars": 4,
        "seed": 42,
        "out": str(tmp_path / f"{mode}_{int(bpm)}.mid"),
    }
    cfg_path = tmp_path / f"cfg_{mode}_{int(bpm)}.json"
    cfg_path.write_text(json.dumps(cfg))

    rc = run_config_main(
        [
            "--config",
            str(cfg_path),
            "--save-seed",
            "--prompt-text",
            f"prompt {mode} {bpm}",
            "--tags",
            f"{mode},{tag}",
            "--summary",
            f"summary {mode} {bpm}",
        ]
    )
    assert rc == 0

    seeds_root = Path("seeds")
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert seed_dirs
    return seed_dirs[-1].name


def test_seed_explorer_demo_output(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    sid1 = _make_seed(tmp_path, mode="m1", bpm=128.0, tag="alpha")
    sid2 = _make_seed(tmp_path, mode="m4", bpm=132.0, tag="beta")

    text = demo_output(seeds_root=Path("seeds"), limit=None)
    assert "Seed Explorer Demo" in text
    assert sid1 in text
    assert sid2 in text

    # CLI-level demo mode
    rc = explorer_main(["--demo"])
    assert rc == 0
    out, err = capsys.readouterr()
    assert "Seed Explorer Demo" in out
    assert sid1 in out
    assert sid2 in out

