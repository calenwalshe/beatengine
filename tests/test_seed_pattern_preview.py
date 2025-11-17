from __future__ import annotations

from pathlib import Path

import json
import mido

from techno_engine.config import engine_config_from_dict
from techno_engine.seeds import load_seed, rebuild_index, save_seed


def _make_drum_midi(path: Path, ppq: int) -> None:
    mid = mido.MidiFile(ticks_per_beat=ppq)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=36, velocity=100, time=0))
    track.append(mido.Message("note_on", note=38, velocity=100, time=ppq // 2))
    mid.save(path)


def test_seed_stores_drum_pattern_preview(tmp_path: Path) -> None:
    seeds_root = tmp_path / "seeds"
    render_path = tmp_path / "drum.mid"
    _make_drum_midi(render_path, ppq=480)

    raw_cfg = {
        "mode": "m4",
        "bpm": 128.0,
        "ppq": 480,
        "bars": 4,
        "seed": 999,
        "out": str(render_path),
    }
    cfg = engine_config_from_dict(raw_cfg)
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps(raw_cfg))

    meta = save_seed(
        cfg,
        config_path=str(config_path),
        render_path=str(render_path),
        prompt="test",
        summary="pattern preview",
        tags=["test"],
        seeds_root=seeds_root,
    )

    # Loaded metadata retains pattern preview
    _, loaded_meta = load_seed(meta.seed_id, seeds_root=seeds_root)
    assert loaded_meta.assets
    assert loaded_meta.assets[0].drum_pattern_preview

    # Rebuild index also preserves preview
    metas = rebuild_index(seeds_root=seeds_root)
    found = [m for m in metas if m.seed_id == meta.seed_id][0]
    assert found.assets[0].drum_pattern_preview
