from __future__ import annotations

import json
from pathlib import Path

from techno_engine.combo_cli import main as combo_main


def test_combo_cli_outputs_two_files(tmp_path: Path):
    # Use an existing drum config and write to tmp files
    # Resolve config path relative to repo root
    if Path("techno_rhythm_engine/configs/m4_95bpm.json").exists():
        drum_cfg = "techno_rhythm_engine/configs/m4_95bpm.json"
    else:
        drum_cfg = "configs/m4_95bpm.json"
    drum_out = tmp_path / "drums.mid"
    bass_out = tmp_path / "bass.mid"
    rc = combo_main([
        "--drum", drum_cfg,
        "--drum_out", str(drum_out),
        "--bass_out", str(bass_out),
        "--root_note", "43",
        # defaults: bass_mode=scored, validate=True
    ])
    assert rc == 0
    assert drum_out.exists()
    assert bass_out.exists()
