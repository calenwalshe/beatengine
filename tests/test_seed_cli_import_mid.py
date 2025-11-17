from __future__ import annotations

import json
from pathlib import Path

from techno_engine.seed_cli import main as seed_main


def test_seed_cli_import_mid_creates_seed(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    midi_path = tmp_path / "demo_import.mid"
    midi_path.write_bytes(b"MThd")  # minimal bytes; we don't parse MIDI

    rc = seed_main(
        [
            "import-mid",
            str(midi_path),
            "--mode",
            "external",
            "--bpm",
            "128",
            "--bars",
            "16",
            "--tags",
            "external,import_cli",
            "--summary",
            "imported demo midi",
        ]
    )
    assert rc == 0

    out, err = capsys.readouterr()
    assert "Imported" in out

    seeds_root = Path("seeds")
    assert seeds_root.is_dir()
    seed_dirs = [p for p in seeds_root.iterdir() if p.is_dir()]
    assert len(seed_dirs) == 1

    seed_dir = seed_dirs[0]
    meta_path = seed_dir / "metadata.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text())

    # Canonical drum location for imported MIDI.
    assert meta["render_path"] == "drums/main.mid"
    assert (seed_dir / meta["render_path"]).is_file()
    assert meta["engine_mode"] == "external"
    assert meta["tags"] == ["external", "import_cli"]
    assert meta["summary"] == "imported demo midi"

