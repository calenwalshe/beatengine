from __future__ import annotations

from pathlib import Path

from techno_engine.showcase import main as showcase_main


def test_showcase_manifest(tmp_path: Path):
    outdir = tmp_path / "showcase"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick"])
    assert rc == 0
    manifest = outdir / "manifest.csv"
    assert manifest.exists()
    body = manifest.read_text().strip().splitlines()
    assert len(body) >= 2  # header + at least one row
    header = body[0].split(",")
    assert header == ["name", "bpm", "bars", "drums", "bass", "E_med", "S_med", "key", "mode", "description"]
