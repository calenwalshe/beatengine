from __future__ import annotations

import json
from pathlib import Path

from techno_engine.run_config import main as run_config_main
from techno_engine.seed_cli import main as seed_main
from techno_engine.seeds import rebuild_index


def _make_seed(tmp_path: Path, mode: str, bpm: float, tag: str) -> str:
    cfg = {
        "mode": mode,
        "bpm": bpm,
        "ppq": 1920,
        "bars": 4,
        "seed": 123,
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


def test_rebuild_index_and_json_list(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    seed_id_1 = _make_seed(tmp_path, mode="m1", bpm=128.0, tag="alpha")
    seed_id_2 = _make_seed(tmp_path, mode="m4", bpm=132.0, tag="beta")

    # Rebuild index and ensure it contains both seeds
    metas = rebuild_index(seeds_root=Path("seeds"))
    ids = {m.seed_id for m in metas}
    assert seed_id_1 in ids
    assert seed_id_2 in ids

    # Flush any prior stdout from run_config calls
    capsys.readouterr()

    # JSON list output
    rc = seed_main(["list", "--json"])
    assert rc == 0
    out, err = capsys.readouterr()
    payload = json.loads(out)
    assert isinstance(payload, list)
    listed_ids = {entry["seed_id"] for entry in payload}
    assert seed_id_1 in listed_ids
    assert seed_id_2 in listed_ids

    # JSON show output for one seed
    rc_show = seed_main(["show", seed_id_1, "--json"])
    assert rc_show == 0
    out, err = capsys.readouterr()
    obj = json.loads(out)
    assert obj["seed_id"] == seed_id_1
    assert obj["engine_mode"] in ("m1", "m4")

