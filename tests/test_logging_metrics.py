from __future__ import annotations

import csv
import tempfile

from techno_engine.controller import run_session


def test_run_session_writes_log(tmp_path):
    log_path = tmp_path / "session_log.csv"
    run_session(bpm=130, ppq=1920, bars=16, log_path=str(log_path))
    assert log_path.exists()

    with log_path.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows
    assert set(rows[0].keys()) == {"bar", "E", "S", "hat_density", "hat_entropy"}
