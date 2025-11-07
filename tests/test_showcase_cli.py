from __future__ import annotations

from pathlib import Path

from techno_engine.showcase import main as showcase_main


def test_showcase_cli_smoke(tmp_path: Path, monkeypatch):
    # Render into temp outdir; relies on existing configs
    outdir = tmp_path / "showcase"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick"])
    assert rc == 0
    # Expect at least two files present
    files = list(outdir.glob("*.mid"))
    assert len(files) >= 2


def test_showcase_with_key_mode(tmp_path: Path):
    outdir = tmp_path / "showcase2"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick", "--key", "A", "--mode", "minor"])
    assert rc == 0
    manifest = outdir / "manifest.csv"
    header = manifest.read_text().splitlines()[0].lower()
    assert "key" in header and "mode" in header


def test_showcase_scenario_filter(tmp_path: Path):
    outdir = tmp_path / "showcase3"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick", "--scenario", "syncopated_layers"])
    assert rc == 0
    manifest = outdir / "manifest.csv"
    rows = manifest.read_text().strip().splitlines()[1:]
    assert len(rows) == 1
    assert rows[0].split(",")[0].startswith("syncopated_layers")
