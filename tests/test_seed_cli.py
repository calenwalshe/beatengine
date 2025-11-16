from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_config_main
from techno_engine.seed_cli import main as seed_main


def _make_seed(tmp_path: Path) -> str:
    cfg = {
        "mode": "m1",
        "bpm": 130,
        "ppq": 1920,
        "bars": 4,
        "seed": 123,
        "out": str(tmp_path / "m1.mid"),
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))

    # Run under tmp_path so seeds/ is local
    run_rc = run_config_main(
        [
            "--config",
            str(cfg_path),
            "--save-seed",
            "--prompt-text",
            "test prompt",
            "--tags",
            "m1,test",
            "--summary",
            "test seed from CLI",
        ]
    )
    assert run_rc == 0

    seeds_root = Path("seeds")
    assert seeds_root.is_dir()
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) == 1
    return seed_dirs[0].name


def test_seed_cli_list_and_show(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    seed_id = _make_seed(tmp_path)

    # List should show our seed
    rc_list = seed_main(["list"])
    assert rc_list == 0
    out, err = capsys.readouterr()
    assert seed_id in out

    # Show should print JSON metadata
    rc_show = seed_main(["show", seed_id])
    assert rc_show == 0
    out, err = capsys.readouterr()
    data = json.loads(out)
    assert data["seed_id"] == seed_id
    assert data["engine_mode"] == "m1"


def test_seed_cli_clone_creates_new_seed(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    seed_id = _make_seed(tmp_path)

    # Clone the seed with a new BPM and out path
    out_path = tmp_path / "clone.mid"
    rc_clone = seed_main([
        "clone",
        seed_id,
        "--bpm",
        "135",
        "--out",
        str(out_path),
        "--tags",
        "m1,clone",
        "--summary",
        "cloned seed",
    ])
    assert rc_clone == 0

    # We should now have at least two seed directories
    seeds_root = Path("seeds")
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) >= 2

    # The cloned output MIDI should exist
    assert out_path.exists()

