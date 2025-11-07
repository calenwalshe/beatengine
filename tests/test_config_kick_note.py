from __future__ import annotations

from techno_engine.config import engine_config_from_dict


def test_kick_defaults_to_note36_when_omitted():
    raw = {
        "mode": "m4",
        "bpm": 130,
        "ppq": 1920,
        "bars": 8,
        "layers": {
            "kick": {"steps": 16, "fills": 4},  # no note provided
        },
    }
    cfg = engine_config_from_dict(raw)
    assert cfg.kick is not None
    assert cfg.kick.note == 36

