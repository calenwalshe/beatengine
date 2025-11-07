from __future__ import annotations

import csv
from pathlib import Path

from techno_engine.showcase import main as showcase_main


def test_showcase_metrics_within_ranges(tmp_path: Path):
    outdir = tmp_path / "showcase"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick"])
    assert rc == 0
    manifest = outdir / "manifest.csv"
    rows = list(csv.DictReader(manifest.open()))
    # Check that E_med and S_med are reasonable (broad ranges)
    assert rows
    for r in rows:
        E = float(r["E_med"]) if r.get("E_med") else 0.0
        S = float(r["S_med"]) if r.get("S_med") else 0.0
        assert 0.6 <= E <= 1.0
        assert 0.2 <= S <= 0.9
