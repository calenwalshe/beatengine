from __future__ import annotations

from techno_engine.bass_tools import (
    bass_generate,
    bass_validate_lock,
    BassGenerateInput,
    BassValidateInput,
    API_VERSION,
)


def test_generate_schema_contract():
    res = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, mode="mvp", density=0.4))
    assert res.get("code") == "OK"
    assert res.get("version") == API_VERSION
    ev = res.get("events")
    assert isinstance(ev, list) and len(ev) >= 1
    for item in ev:
        assert set(["note", "vel", "start_abs_tick", "dur_tick", "channel"]).issubset(item.keys())


def test_validate_lock_schema_contract():
    g = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, mode="mvp", density=0.4))
    res = bass_validate_lock(BassValidateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, density=0.4, events=g["events"]))
    assert res.get("code") == "OK"
    assert res.get("version") == API_VERSION
    assert isinstance(res.get("events"), list)
    assert isinstance(res.get("summaries"), list)


def test_error_on_infeasible_density():
    bad = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, mode="mvp", density=1.5))
    assert bad.get("code") == "BAD_CONFIG"
    bad2 = bass_validate_lock(BassValidateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, density=-0.1, events=[]))
    assert bad2.get("code") == "BAD_CONFIG"


def test_version_mismatch_rejected():
    res = bass_generate(BassGenerateInput(version="v0", bpm=120.0, ppq=1920, bars=4))
    assert res.get("code") == "VERSION_MISMATCH"
    res2 = bass_validate_lock(BassValidateInput(version="v0", bpm=120.0, ppq=1920, bars=4, events=[]))
    assert res2.get("code") == "VERSION_MISMATCH"


def test_style_table_swap_deterministic():
    # Two known styles produce deterministic outputs and differ from each other
    g1 = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, style="sparse_root"))
    g2 = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, style="offbeat_scored", kick_masks_by_bar=[[0]*16 for _ in range(4)]))
    assert g1["code"] == "OK" and g2["code"] == "OK"
    e1a = g1["events"]
    e1b = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, style="sparse_root"))["events"]
    assert e1a == e1b
    # Ensure style change results in a different event set (very likely given mode/density change)
    assert e1a != g2["events"]
