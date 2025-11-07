from __future__ import annotations

import json
from pathlib import Path

from techno_engine.showcase import main as showcase_main


def test_showcase_json_and_html(tmp_path: Path):
    outdir = tmp_path / "showcase"
    rc = showcase_main(["--pack", "default", "--outdir", str(outdir), "--quick"])
    assert rc == 0
    man_json = outdir / "manifest.json"
    idx_html = outdir / "index.html"
    assert man_json.exists() and idx_html.exists()
    data = json.loads(man_json.read_text())
    items = data.get("scenarios") or data.get("items")
    assert isinstance(items, list) and len(items) >= 1
    assert data.get("generated_at")
    first = items[0]
    for k in ["name", "bpm", "bars", "drums", "bass", "E_med", "S_med", "key", "mode", "description"]:
        assert k in first
    # HTML contains table header (with filters info) and at least one link
    body = idx_html.read_text()
    assert "<table" in body and "</table>" in body
    assert "Description</th>" in body and "Key</th>" in body and "Mode</th>" in body
    assert "<a href=" in body
