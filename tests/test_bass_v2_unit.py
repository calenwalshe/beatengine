"""Unit tests for bass_v2 generator core components."""
import unittest
import random
from src.techno_engine.bass_v2_types import (
    DrumStep,
    DrumBar,
    SlotFeature,
    BarSlotGrid,
    TheoryContext,
    ScoredSlot,
    BassModeAssignment,
    ResolvedControls,
    BassNote,
)
from src.techno_engine.bass_v2_controls import (
    resolve_controls,
    select_mode_from_energy,
    BASS_MODE_PROFILES,
)
from src.techno_engine.bass_v2_pipeline import (
    drums_to_slot_grid,
    bass_mode_selection,
    step_scoring_and_selection,
    pitch_mapping_and_midi,
    validation_and_post_processing,
    parse_key_scale,
)
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums


class TestCoreDataStructures(unittest.TestCase):
    """Test core data structures."""

    def test_drum_step_creation(self):
        """Test DrumStep creation."""
        step = DrumStep(kick=True, hat=False, snare=False, velocity=100)
        self.assertTrue(step.kick)
        self.assertFalse(step.hat)
        self.assertEqual(step.velocity, 100)

    def test_drum_bar_default_16_steps(self):
        """Test DrumBar has 16 steps by default."""
        bar = DrumBar()
        self.assertEqual(len(bar.steps), 16)

    def test_slot_feature_flags(self):
        """Test SlotFeature flag creation."""
        slot = SlotFeature(index=0, is_downbeat=True, has_kick=True)
        self.assertEqual(slot.index, 0)
        self.assertTrue(slot.is_downbeat)
        self.assertTrue(slot.has_kick)


class TestControlResolution(unittest.TestCase):
    """Test control resolution layer from spec section 8."""

    def test_applies_mode_defaults_then_user_overrides(self):
        """Test that mode defaults are applied, then user overrides take precedence."""
        # Mode defaults
        resolved = resolve_controls(bass_mode_name="sub_anchor")
        # sub_anchor should have very low density
        self.assertLess(resolved.rhythm_controls.note_density, 0.2)

        # User override
        resolved = resolve_controls(
            bass_mode_name="sub_anchor",
            user_overrides={"rhythm_controls": {"note_density": 0.9}},
        )
        self.assertEqual(resolved.rhythm_controls.note_density, 0.9)

    def test_handles_missing_fields_with_safe_defaults(self):
        """Test that missing fields use safe defaults."""
        resolved = resolve_controls()
        self.assertIsNotNone(resolved.theory_controls)
        self.assertIsNotNone(resolved.rhythm_controls)
        self.assertIsNotNone(resolved.melody_controls)
        self.assertIsNotNone(resolved.articulation_controls)


class TestDrumsToSlotGrid(unittest.TestCase):
    """Test Step 1: drums_to_slot_grid from spec section 8."""

    def test_four_on_the_floor_detection(self):
        """Test four-on-the-floor kick pattern detection."""
        # Create drum bar with kicks at 0, 4, 8, 12
        steps = [DrumStep() for _ in range(16)]
        for i in [0, 4, 8, 12]:
            steps[i].kick = True

        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        self.assertEqual(len(grids), 1)
        grid = grids[0]

        # Check kick flags
        for i, slot in enumerate(grid.slots):
            if i in {0, 4, 8, 12}:
                self.assertTrue(slot.has_kick)
                self.assertTrue(slot.is_downbeat)
            else:
                self.assertFalse(slot.has_kick)

        # Check backbeats (4 and 12)
        self.assertTrue(grid.slots[4].is_backbeat)
        self.assertTrue(grid.slots[12].is_backbeat)

        # Energy should be >= 4 (4 kicks)
        self.assertGreaterEqual(grid.drum_energy_bar, 4.0)

    def test_gap_and_offbeat_labels(self):
        """Test gap and offbeat labeling."""
        # Hats on offbeats only
        steps = [DrumStep() for _ in range(16)]
        for i in [2, 6, 10, 14]:
            steps[i].hat = True

        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        grid = grids[0]
        # Check offbeat flags
        for i in [2, 6, 10, 14]:
            self.assertTrue(grid.slots[i].has_hat)
            self.assertTrue(grid.slots[i].is_offbeat)

        # Check gaps (steps with no hits)
        for i in [0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15]:
            self.assertTrue(grid.slots[i].is_gap)


class TestBassModeSelection(unittest.TestCase):
    """Test Step 2: bass_mode_selection from spec section 8."""

    def test_energy_band_to_mode_mapping(self):
        """Test that energy levels map to appropriate modes."""
        # Low energy -> sub_anchor
        self.assertEqual(select_mode_from_energy(2.0), "sub_anchor")

        # Medium energy -> root_fifth_driver
        self.assertEqual(select_mode_from_energy(6.0), "root_fifth_driver")

        # High energy -> rolling_ostinato
        self.assertEqual(select_mode_from_energy(10.0), "rolling_ostinato")

    def test_explicit_mode_override_wins(self):
        """Test that explicit mode override takes precedence."""
        # Create low-energy grid
        steps = [DrumStep(kick=True) if i == 0 else DrumStep() for i in range(16)]
        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        # Force offbeat_stabs mode
        assignments = bass_mode_selection(
            grids,
            global_controls={
                "mode_and_behavior_controls": {
                    "strategy": "fixed_mode",
                    "fixed_mode": "offbeat_stabs",
                }
            },
        )

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].mode_name, "offbeat_stabs")


class TestStepScoringAndSelection(unittest.TestCase):
    """Test Step 3: step_scoring_and_selection from spec section 8."""

    def test_respects_note_density_target(self):
        """Test that selection respects note density target."""
        # Create grid
        steps = [DrumStep(kick=True) if i in {0, 4, 8, 12} else DrumStep() for i in range(16)]
        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        # Create assignment with density=0.25 (4 notes per 16 steps)
        assignments = bass_mode_selection(grids)
        assignment = assignments[0]
        assignment.resolved_controls.rhythm_controls.note_density = 0.25

        scored = step_scoring_and_selection(grids[0], assignment)
        selected = [s for s in scored if s.selected]

        # Should have ~4 notes (allow ±1 for rounding)
        self.assertGreaterEqual(len(selected), 3)
        self.assertLessEqual(len(selected), 5)

    def test_sub_anchor_kick_avoid_behavior(self):
        """Test sub_anchor mode avoids kick steps."""
        # Four-on-the-floor
        steps = [DrumStep(kick=True) if i in {0, 4, 8, 12} else DrumStep() for i in range(16)]
        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        # Force sub_anchor mode
        assignments = bass_mode_selection(
            grids,
            global_controls={
                "mode_and_behavior_controls": {
                    "strategy": "fixed_mode",
                    "fixed_mode": "sub_anchor",
                }
            },
        )

        scored = step_scoring_and_selection(grids[0], assignments[0])
        selected = [s for s in scored if s.selected]

        # No selected slots should have kicks
        kick_indices = {0, 4, 8, 12}
        selected_indices = {s.slot.index for s in selected}
        collision = selected_indices & kick_indices
        self.assertEqual(len(collision), 0, "sub_anchor should avoid kick steps")


class TestPitchMappingAndMidi(unittest.TestCase):
    """Test Step 4: pitch_mapping_and_midi from spec section 8."""

    def test_all_notes_in_key_when_no_chords(self):
        """Test that all notes are in the specified key."""
        slots = [SlotFeature(i) for i in range(16)]
        scored = [ScoredSlot(slot=slots[i], selected=True) for i in [0, 4, 8, 12]]

        assignment = BassModeAssignment(
            bar_index=0, mode_name="root_fifth_driver", resolved_controls=ResolvedControls()
        )

        theory = TheoryContext(key_scale="C_minor")
        notes = pitch_mapping_and_midi(scored, assignment, theory)

        # Parse key to get valid pitches
        root, scale = parse_key_scale("C_minor")
        valid_intervals = set(scale)

        for note in notes:
            # Check if note is in C minor scale
            interval = (note.pitch - root) % 12
            self.assertIn(interval, valid_intervals, f"Note {note.pitch} not in C minor")

    def test_root_emphasis_respected(self):
        """Test root_note_emphasis creates mostly root notes."""
        slots = [SlotFeature(i) for i in range(16)]
        scored = [ScoredSlot(slot=slots[i], selected=True) for i in range(8)]

        assignment = BassModeAssignment(
            bar_index=0, mode_name="sub_anchor", resolved_controls=ResolvedControls()
        )
        assignment.resolved_controls.melody_controls.root_note_emphasis = 0.99

        theory = TheoryContext(key_scale="A_minor")
        rng = random.Random(42)
        notes = pitch_mapping_and_midi(scored, assignment, theory, rng=rng)

        # Count root notes (A=45 and octaves)
        root_midi = 45
        root_count = sum(1 for n in notes if (n.pitch - root_midi) % 12 == 0)

        # Should be > 60% root notes (with high emphasis)
        self.assertGreater(root_count / len(notes), 0.6)


class TestValidationAndPostProcessing(unittest.TestCase):
    """Test Step 5: validation_and_post_processing from spec section 8."""

    def test_kick_collision_removal_in_sub_anchor(self):
        """Test that kick collisions are removed in sub_anchor mode."""
        # Create notes at kick positions
        notes = [
            BassNote(pitch=45, start_beat=0.0, duration_beats=0.25, velocity=100),
            BassNote(pitch=45, start_beat=1.0, duration_beats=0.25, velocity=100),
            BassNote(pitch=45, start_beat=2.0, duration_beats=0.25, velocity=100),
        ]

        # Create grid with kicks
        steps = [DrumStep(kick=True) if i in {0, 4, 8} else DrumStep() for i in range(16)]
        drum_bars = [DrumBar(steps=steps)]
        grids = drums_to_slot_grid(drum_bars)

        assignment = BassModeAssignment(
            bar_index=0, mode_name="sub_anchor", resolved_controls=ResolvedControls()
        )
        assignment.resolved_controls.rhythm_controls.kick_interaction_mode = "avoid_kick"

        theory = TheoryContext()
        adjusted, metadata = validation_and_post_processing(notes, grids[0], assignment, theory)

        # Should have removed some notes
        self.assertLess(len(adjusted), len(notes))


class TestEndToEndIntegration(unittest.TestCase):
    """Integration tests with full pipeline."""

    def test_generate_from_simple_drum_pattern(self):
        """Test full generation from simple four-on-the-floor pattern."""
        m4_drum_output = {
            "bars": [
                {
                    "steps": [
                        {"kick": i in {0, 4, 8, 12}, "hat": i % 2 == 1, "snare": i in {4, 12}}
                        for i in range(16)
                    ]
                }
                for _ in range(4)
            ]
        }

        theory = TheoryContext(key_scale="A_minor", tempo_bpm=128.0)
        clip = generate_bass_midi_from_drums(m4_drum_output, theory, seed=42)

        self.assertEqual(clip.length_bars, 4)
        self.assertGreater(len(clip.notes), 0)
        self.assertIn("mode_per_bar", clip.metadata)

        # All notes should be in valid range
        for note in clip.notes:
            self.assertGreaterEqual(note.pitch, 28)
            self.assertLessEqual(note.pitch, 60)
            self.assertGreaterEqual(note.velocity, 1)
            self.assertLessEqual(note.velocity, 127)

    def test_different_modes_produce_different_results(self):
        """Test that different modes produce different bass patterns."""
        m4_drum_output = {
            "bars": [
                {
                    "steps": [
                        {"kick": i in {0, 4, 8, 12}, "hat": i % 2 == 1, "snare": False}
                        for i in range(16)
                    ]
                }
            ]
        }

        theory = TheoryContext(key_scale="A_minor")

        # Generate with sub_anchor
        clip1 = generate_bass_midi_from_drums(
            m4_drum_output,
            theory,
            global_controls={
                "mode_and_behavior_controls": {"strategy": "fixed_mode", "fixed_mode": "sub_anchor"}
            },
            seed=42,
        )

        # Generate with rolling_ostinato
        clip2 = generate_bass_midi_from_drums(
            m4_drum_output,
            theory,
            global_controls={
                "mode_and_behavior_controls": {
                    "strategy": "fixed_mode",
                    "fixed_mode": "rolling_ostinato",
                }
            },
            seed=42,
        )

        # Rolling ostinato should have more notes
        self.assertGreater(len(clip2.notes), len(clip1.notes))


if __name__ == "__main__":
    unittest.main()
