from __future__ import annotations

import json
from pathlib import Path

import pytest

from techno_engine.run_config import main as run_cli


def test_run_config_m1_backbone(tmp_path: Path):
    cfg = {
        "mode": "m1",
        "bpm": 132,
        "ppq": 1920,
        "bars": 4,
        "seed": 1234,
        "out": str(tmp_path / "m1.mid"),
    }
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(cfg))

    # run CLI
    assert run_cli(["--config", str(p)]) == 0

    # Validate MIDI contents
    try:
        import mido  # type: ignore
    except Exception as e:  # pragma: no cover
        pytest.skip(f"mido not available: {e}")

    mid = mido.MidiFile(str(tmp_path / "m1.mid"))
    assert mid.ticks_per_beat == 1920
    tempos = [msg.tempo for tr in mid.tracks for msg in tr if msg.type == "set_tempo"]
    assert tempos
    bpm = 60_000_000 / tempos[0]
    assert abs(bpm - 132) < 1e-2

    on_msgs = [msg for tr in mid.tracks for msg in tr if msg.type == "note_on" and msg.velocity > 0]
    # For 4 bars: kick 4/bar + hat 16/bar + snare 2/bar + clap 2/bar = 24/bar
    assert len(on_msgs) == 4 * 24

