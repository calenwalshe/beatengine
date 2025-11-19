import json
from pathlib import Path

from techno_engine.leads.lead_modes import load_lead_modes
from techno_engine.leads.lead_templates import (
    load_contour_templates,
    load_rhythm_templates,
)


def test_lead_modes_config_parses_minimal_stub(tmp_path):
    cfg_path = tmp_path / "lead_modes.json"
    raw = {
        "Minimal Stab Lead": {
            "target_notes_per_bar": [2, 4],
            "max_consecutive_notes": 2,
            "register_low": 64,
            "register_high": 76,
            "rhythmic_personality": "stabs",
            "preferred_slot_weights": {"is_offbeat_8th": 2.0},
            "phrase_length_bars": 4,
            "contour_profiles": ["arch"],
            "call_response_style": "mild",
        }
    }
    cfg_path.write_text(json.dumps(raw))

    loaded = json.loads(cfg_path.read_text())
    modes = load_lead_modes(loaded)
    assert "Minimal Stab Lead" in modes
    m = modes["Minimal Stab Lead"]
    assert m.target_notes_per_bar == (2, 4)
    assert m.max_consecutive_notes == 2
    assert m.register_low == 64
    assert m.register_high == 76
    assert m.rhythmic_personality == "stabs"
    assert m.preferred_slot_weights["is_offbeat_8th"] == 2.0
    assert m.phrase_length_bars == 4
    assert m.contour_profiles == ["arch"]
    assert m.call_response_style == "mild"


def test_lead_rhythm_and_contour_templates_parse(tmp_path):
    # rhythm
    rhythm_raw = {
        "Minimal Stab Lead": {
            "CALL": [
                {
                    "id": "msl_call_1",
                    "events": [
                        {"step": 2, "length": 1, "anchor_type": "offbeat", "accent": True},
                        {"step": 10, "length": 1, "anchor_type": "snare_zone", "accent": False},
                    ],
                }
            ]
        }
    }
    rhythm_path = tmp_path / "lead_rhythm_templates.json"
    rhythm_path.write_text(json.dumps(rhythm_raw))

    loaded_rhythm = json.loads(rhythm_path.read_text())
    r_templates = load_rhythm_templates(loaded_rhythm)
    assert len(r_templates) == 1
    rt = r_templates[0]
    assert rt.mode_name == "Minimal Stab Lead"
    assert rt.motif_role == "CALL"
    assert len(rt.events) == 2
    assert rt.events[0].step == 2
    assert rt.events[0].anchor_type == "offbeat"

    # contour
    contour_raw = {
        "Minimal Stab Lead": {
            "CALL": [
                {
                    "id": "msl_contour_1",
                    "intervals": [0, 2, -1],
                    "emphasis_indices": [0],
                    "shape": "arch",
                }
            ]
        }
    }
    contour_path = tmp_path / "lead_contour_templates.json"
    contour_path.write_text(json.dumps(contour_raw))

    loaded_contour = json.loads(contour_path.read_text())
    c_templates = load_contour_templates(loaded_contour)
    assert len(c_templates) == 1
    ct = c_templates[0]
    assert ct.mode_name == "Minimal Stab Lead"
    assert ct.motif_role == "CALL"
    assert ct.intervals == [0, 2, -1]
    assert ct.emphasis_indices == [0]
    assert ct.shape == "arch"
