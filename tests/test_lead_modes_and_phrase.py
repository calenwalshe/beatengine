from techno_engine.leads.lead_modes import LeadMode, load_lead_modes, select_lead_mode
from techno_engine.leads.lead_phrase import build_phrase_roles
from techno_engine.leads.lead_engine import build_lead_context
from techno_engine.drum_analysis import DrumAnchors
from techno_engine.seeds import SeedMetadata


def _dummy_anchors() -> DrumAnchors:
    # Minimal single-bar anchors object for context tests.
    return DrumAnchors(
        ppq=1920,
        bar_count=1,
        bar_ticks=1920 * 4,
        step_ticks=(1920 * 4) // 16,
        kick_steps=[],
        backbeat_steps=[],
        bar_kick_steps=[[]],
        bar_snare_steps=[[]],
        bar_hat_steps=[[]],
        slot_tags=[[set() for _ in range(16)]],
    )


def _dummy_meta(tags=None) -> SeedMetadata:
    return SeedMetadata(
        seed_id="test_seed",
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=130.0,
        bars=4,
        ppq=1920,
        rng_seed=123,
        config_path="config.json",
        render_path="drums/main.mid",
        log_path=None,
        prompt=None,
        prompt_context=None,
        summary=None,
        tags=tags or [],
        assets=[],
        parent_seed_id=None,
        file_version=1,
    )


def test_select_lead_mode_from_tags():
    raw_modes = {
        "Minimal Stab Lead": {
            "target_notes_per_bar": [2, 4],
            "max_consecutive_notes": 2,
            "register_low": 64,
            "register_high": 76,
            "rhythmic_personality": "stabs",
            "preferred_slot_weights": {},
            "phrase_length_bars": 4,
            "contour_profiles": ["arch"],
            "call_response_style": "mild",
        },
        "Lyrical Call/Response Lead": {
            "target_notes_per_bar": [4, 8],
            "max_consecutive_notes": 4,
            "register_low": 60,
            "register_high": 84,
            "rhythmic_personality": "lyrical",
            "preferred_slot_weights": {},
            "phrase_length_bars": 4,
            "contour_profiles": ["arch"],
            "call_response_style": "medium",
        },
    }
    modes = load_lead_modes(raw_modes)

    # lyrical tag should prefer Lyrical Call/Response Lead
    m1 = select_lead_mode(["lyrical"], modes)
    assert m1.name == "Lyrical Call/Response Lead"

    # minimal tag should fall back to Minimal Stab Lead
    m2 = select_lead_mode(["minimal"], modes)
    assert m2.name == "Minimal Stab Lead"

    # no tags uses Minimal Stab Lead as default
    m3 = select_lead_mode([], modes)
    assert m3.name == "Minimal Stab Lead"


def test_build_phrase_roles_for_2_and_4_bars():
    # 2-bar phrase
    roles_2 = build_phrase_roles(2, total_bars=4)
    assert [r.role for r in roles_2] == ["CALL", "CALL_VAR", "CALL", "CALL_VAR"]

    # 4-bar phrase
    roles_4 = build_phrase_roles(4, total_bars=4)
    assert [r.role for r in roles_4] == ["CALL", "CALL_VAR", "RESP", "RESP_VAR"]


def test_build_lead_context_uses_seed_metadata_tags():
    anchors = _dummy_anchors()
    meta = _dummy_meta(tags=["minimal", "warehouse"])

    raw_modes = {
        "Minimal Stab Lead": {
            "target_notes_per_bar": [2, 4],
            "max_consecutive_notes": 2,
            "register_low": 64,
            "register_high": 76,
            "rhythmic_personality": "stabs",
            "preferred_slot_weights": {},
            "phrase_length_bars": 4,
            "contour_profiles": ["arch"],
            "call_response_style": "mild",
        }
    }

    ctx = build_lead_context(
        anchors,
        meta,
        modes_raw=raw_modes,
        rhythm_raw={},
        contour_raw={},
    )

    assert ctx.seed_meta.seed_id == "test_seed"
    assert ctx.tags == ["minimal", "warehouse"]
    assert "Minimal Stab Lead" in ctx.modes
    assert ctx.anchors.bar_count == 1
