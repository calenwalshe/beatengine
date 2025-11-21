from __future__ import annotations

import json
from pathlib import Path
from random import Random
from types import SimpleNamespace
import unittest

from lead_implementation.lead_v2.generate import (
    LeadModeConfig,
    derive_keyspec,
    generate_lead_v2,
)
from lead_implementation.lead_v2.phrases import PhraseConfig, plan_phrases
from lead_implementation.lead_v2.motifs import RhythmTemplate, RhythmEvent, ContourTemplate
from lead_implementation.lead_v2.theory import (
    KeySpec,
    LeadNoteEvent,
    LeadNoteLogical,
    MetricPosition,
    is_in_scale,
)
from lead_implementation.lead_v2.bass import apply_bass_interaction
from lead_implementation.lead_v2.slots import align_to_slots


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"


class DummyAnchors:
    """Minimal DrumAnchors-shaped stub for tests."""

    def __init__(self, bars: int, step_ticks: int = 120) -> None:
        self.bar_count = bars
        self.step_ticks = step_ticks
        self.slot_tags = []
        self.bar_hat_steps = []
        for bar in range(bars):
            row = []
            hat_steps = []
            for step in range(16):
                tags = set()
                if step == 0:
                    tags.update({"bar_start", "kick"})
                if step in {4, 12}:
                    tags.add("snare_zone")
                if step % 2 == 0:
                    tags.add("hat")
                    hat_steps.append(step)
                row.append(tags)
            self.slot_tags.append(row)
            self.bar_hat_steps.append(hat_steps)


def _load_mode_config() -> LeadModeConfig:
    data = json.loads((CONFIG_DIR / "lead_modes_v2.example.json").read_text())[0]
    phrase_cfg = PhraseConfig(
        min_bars=data["phrase"]["min_bars"],
        max_bars=data["phrase"]["max_bars"],
        call_response_pattern=data["phrase"]["call_response_pattern"],
        phrase_forms=data["phrase"]["phrase_forms"],
        phrase_end_resolution_degrees=data["phrase"]["phrase_end_resolution_degrees"],
    )
    slot_prefs = {role.upper(): prefs for role, prefs in data.get("slot_preferences", {}).items()}
    return LeadModeConfig(
        id=data["id"],
        scale_type=data["scale"]["scale_type"],
        default_root_pc=data["scale"]["default_root_pc"],
        allow_key_from_seed_tag=data["scale"]["allow_key_from_seed_tag"],
        register_low=data["register"]["low"],
        register_high=data["register"]["high"],
        register_gravity_center=data["register"]["gravity_center"],
        phrase_cfg=phrase_cfg,
        density=data.get("density", {}),
        slot_preferences=slot_prefs,
        bass_interaction=data.get("bass_interaction", {}),
        function_profiles=data.get("function_profiles", {}),
        degree_weights=data.get("degree_weights", {}),
        contour=data.get("contour", {}),
        variation=data.get("variation", {}),
    )


def _load_rhythm_templates(role: str) -> list[RhythmTemplate]:
    data = json.loads((CONFIG_DIR / "lead_rhythm_templates_v2.example.json").read_text())
    templates = []
    for entry in data:
        if entry["role"].upper() != role.upper():
            continue
        events = [RhythmEvent(**ev) for ev in entry["events"]]
        templates.append(
            RhythmTemplate(
                id=entry["id"],
                role=entry["role"],
                bars=entry["bars"],
                events=events,
                max_step_jitter=entry["max_step_jitter"],
                min_inter_note_gap_steps=entry["min_inter_note_gap_steps"],
            )
        )
    return templates


def _load_contour_templates(role: str) -> list[ContourTemplate]:
    data = json.loads((CONFIG_DIR / "lead_contour_templates_v2.example.json").read_text())
    templates = []
    for entry in data:
        if entry["role"].upper() != role.upper():
            continue
        templates.append(
            ContourTemplate(
                id=entry["id"],
                role=entry["role"],
                degree_intervals=entry["degree_intervals"],
                emphasis_indices=entry["emphasis_indices"],
                shape_type=entry["shape_type"],
                tension_profile=entry["tension_profile"],
            )
        )
    return templates


class LeadV2Tests(unittest.TestCase):
    def test_phrase_planner_covers_bars_and_resolutions(self) -> None:
        cfg = PhraseConfig(
            min_bars=2,
            max_bars=4,
            call_response_pattern="CR",
            phrase_forms=["A", "B"],
            phrase_end_resolution_degrees=[1, 5],
        )
        plan = plan_phrases(num_bars=8, cfg=cfg, rng=Random(42))
        covered = sorted(b for seg in plan.segments for b in seg.bar_indices)
        self.assertEqual(covered, list(range(8)))
        terminals = [seg for seg in plan.segments if seg.is_terminal]
        self.assertTrue(terminals)
        self.assertTrue(all(seg.resolution_degrees == [1, 5] for seg in terminals))

    def test_generate_lead_v2_respects_scale_and_register(self) -> None:
        mode_cfg = _load_mode_config()
        anchors = DummyAnchors(bars=mode_cfg.phrase_cfg.max_bars or 4)
        seed_meta = SimpleNamespace(seed_id="unit-test", tags=["key_a_min"], bars=4)
        call_rt = _load_rhythm_templates("CALL")
        resp_rt = _load_rhythm_templates("RESP")
        call_ct = _load_contour_templates("CALL")
        resp_ct = _load_contour_templates("RESP")

        events = generate_lead_v2(
            anchors=anchors,
            seed_metadata=seed_meta,
            mode_cfg=mode_cfg,
            call_templates=call_rt,
            resp_templates=resp_rt,
            contour_call=call_ct,
            contour_resp=resp_ct,
            rng_seed=7,
        )

        self.assertTrue(events, "expected notes from the generator")
        key = derive_keyspec(seed_meta.tags, None, mode_cfg)

        for ev in events:
            self.assertGreaterEqual(ev.pitch, mode_cfg.register_low)
            self.assertLessEqual(ev.pitch, mode_cfg.register_high)
            self.assertTrue(is_in_scale(key, ev.pitch))
            self.assertIn("tone_category", ev.tags)

        starts = [ev.start_tick for ev in events]
        self.assertEqual(starts, sorted(starts))

    def test_bass_interaction_separates_notes(self) -> None:
        key = KeySpec(root_pc=9, scale_type="aeolian", scale_degrees=[0, 2, 3, 5, 7, 8, 10])
        lead = [
            LeadNoteEvent(
                pitch=57,
                velocity=100,
                start_tick=0,
                duration=480,
                phrase_id=0,
                role="CALL",
                degree=1,
            )
        ]
        bass = [{"pitch": 57, "start_tick": 0, "duration": 480}]
        adjusted = apply_bass_interaction(
            lead_events=lead,
            bass_midi=bass,
            key=key,
            register_low=48,
            register_high=84,
            min_semitone_distance=3,
            avoid_root_on_bass_hits=True,
            rng=Random(0),
        )

        self.assertNotEqual(adjusted[0].pitch, 57)
        self.assertTrue(adjusted[0].tags.get("bass_adjusted"))

    def test_align_to_slots_prefers_weighted_tags(self) -> None:
        anchors = DummyAnchors(bars=1)
        anchors.slot_tags[0][11].add("snare_zone")
        anchors.slot_tags[0][11].add("snare")
        anchors.slot_tags[0][12].discard("snare_zone")
        slot_prefs = {"CALL": {"snare_zone": 5.0}}
        logical = LeadNoteLogical(
            phrase_id=0,
            metric_position=MetricPosition(bar_index=0, step_in_bar=10),
            role="CALL",
            phrase_position="inner",
            beat_strength="weak",
            tension_label="medium",
            contour_index=0,
        )
        logical.duration_steps = 2
        logical.slot_jitter = 2
        event = align_to_slots(
            logical_note=logical,
            anchors=anchors,
            role_slot_prefs=slot_prefs,
            steps_per_bar=16,
            step_ticks=anchors.step_ticks,
            duration_steps=logical.duration_steps,
            pitch=72,
            velocity=100,
            occupied_steps={},
            rng=Random(0),
            max_step_jitter=2,
        )
        # Base target step is 2, but snare zone at step 3 should be preferred.
        self.assertEqual(event.start_tick, 11 * anchors.step_ticks)


if __name__ == "__main__":
    unittest.main()
