import json
from pathlib import Path

from techno_engine.leads.lead_templates import load_rhythm_templates


def test_rhythm_templates_present_for_new_modes():
    cfg_path = Path('configs/lead_rhythm_templates.json')
    raw = json.loads(cfg_path.read_text())

    templates = load_rhythm_templates(raw)
    by_mode = {}
    for t in templates:
        by_mode.setdefault(t.mode_name, []).append(t)

    for mode_name in [
        'Minimal Stab Lead',
        'Rolling Arp Lead',
        'Hypnotic Arp Lead',
        'Lyrical Call/Response Lead',
    ]:
        assert mode_name in by_mode, f"no templates for mode {mode_name}"
        assert any(t.motif_role == 'CALL' for t in by_mode[mode_name])
