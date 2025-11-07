from __future__ import annotations

import json
from pathlib import Path

from techno_engine.bass_cli import main as bass_main


def test_cli_smoke(tmp_path: Path):
    cfg = {
        "bpm": 118,
        "ppq": 1920,
        "bars": 4,
        "seed": 123,
        "root_note": 45,
        "out": str(tmp_path / "bass_cli.mid"),
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))
    rc = bass_main(["--config", str(cfg_path)])
    assert rc == 0
    assert (tmp_path / "bass_cli.mid").exists()

