"""Bass V2 Generator - Public API implementing bass_v1.json specification.

This module provides a comprehensive bass generator that consumes m4 drum output
and produces music-theory-aware MIDI basslines through a 5-stage pipeline.
"""
from __future__ import annotations

import random
from typing import List, Dict, Optional, Any

from .bass_v2_types import (
    DrumBar,
    DrumStep,
    BassNote,
    BassMidiClip,
    TheoryContext,
)
from .bass_v2_pipeline import (
    drums_to_slot_grid,
    bass_mode_selection,
    step_scoring_and_selection,
    pitch_mapping_and_midi,
    validation_and_post_processing,
)


def generate_bass_midi_from_drums(
    m4_drum_output: Dict[str, Any],
    theory_context: Optional[TheoryContext] = None,
    global_controls: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> BassMidiClip:
    """Main function that wires the whole pipeline: drums -> slot grid -> mode selection -> step scoring -> pitch mapping -> validation.

    Args:
        m4_drum_output: Drum pattern data with structure:
            {
                "bars": [
                    {
                        "steps": [
                            {"kick": bool, "hat": bool, "snare": bool, "velocity": int},
                            ... (16 steps)
                        ]
                    },
                    ... (N bars)
                ]
            }
        theory_context: Musical context (key, chords, tempo)
        global_controls: User configuration overrides
        seed: Random seed for deterministic generation

    Returns:
        BassMidiClip with notes and metadata
    """
    if theory_context is None:
        theory_context = TheoryContext()

    if global_controls is None:
        global_controls = {}

    rng = random.Random(seed if seed is not None else 42)

    # Parse drum output into DrumBar structures
    drum_bars = _parse_drum_output(m4_drum_output)

    # STEP 1: Convert drums to slot grids
    slot_grids = drums_to_slot_grid(drum_bars)

    # STEP 2: Select bass mode per bar
    assignments = bass_mode_selection(
        slot_grids,
        style_or_genre_preset=global_controls.get("style_preset"),
        global_controls=global_controls,
    )

    # STEP 3-5: Per-bar processing
    all_notes: List[BassNote] = []
    all_metadata: Dict[str, Any] = {
        "mode_per_bar": [],
        "scoring_debug": [],
        "control_snapshot": [],
    }

    prev_note = None
    for grid, assignment in zip(slot_grids, assignments):
        # STEP 3: Score and select steps
        scored_slots = step_scoring_and_selection(grid, assignment, rng)

        # STEP 4: Map to pitches
        notes = pitch_mapping_and_midi(scored_slots, assignment, theory_context, prev_note, rng)

        if notes:
            prev_note = notes[-1]

        # STEP 5: Validate and adjust
        adjusted_notes, validation_metadata = validation_and_post_processing(
            notes, grid, assignment, theory_context
        )

        all_notes.extend(adjusted_notes)

        # Collect metadata
        all_metadata["mode_per_bar"].append(assignment.mode_name)
        all_metadata["scoring_debug"].append({
            "bar": grid.bar_index,
            "selected_slots": [ss.slot.index for ss in scored_slots if ss.selected],
            "validation": validation_metadata,
        })

    # Create output clip
    clip = BassMidiClip(
        notes=all_notes,
        length_bars=len(drum_bars),
        metadata=all_metadata,
    )

    return clip


def _parse_drum_output(m4_drum_output: Dict[str, Any]) -> List[DrumBar]:
    """Parse m4 drum output dict into DrumBar structures."""
    drum_bars: List[DrumBar] = []

    bars_data = m4_drum_output.get("bars", [])
    for bar_data in bars_data:
        steps_data = bar_data.get("steps", [])
        drum_steps: List[DrumStep] = []

        for step_data in steps_data:
            step = DrumStep(
                kick=step_data.get("kick", False),
                hat=step_data.get("hat", False),
                snare=step_data.get("snare", False),
                velocity=step_data.get("velocity"),
            )
            drum_steps.append(step)

        # Pad to 16 steps if needed
        while len(drum_steps) < 16:
            drum_steps.append(DrumStep())

        drum_bar = DrumBar(steps=drum_steps[:16])
        drum_bars.append(drum_bar)

    return drum_bars


def convert_to_midi_events(clip: BassMidiClip, ppq: int = 480, channel: int = 1):
    """Convert BassMidiClip to MIDI events compatible with existing midi_writer.

    Args:
        clip: BassMidiClip with notes
        ppq: Pulses per quarter note
        channel: MIDI channel

    Returns:
        List of MidiEvent objects
    """
    from .midi_writer import MidiEvent

    events: List[MidiEvent] = []

    for note in clip.notes:
        # Convert beats to ticks
        ticks_per_beat = ppq
        start_tick = int(note.start_beat * ticks_per_beat)
        duration_tick = int(note.duration_beats * ticks_per_beat)

        event = MidiEvent(
            note=note.pitch,
            vel=note.velocity,
            start_abs_tick=start_tick,
            dur_tick=max(1, duration_tick),
            channel=channel,
        )
        events.append(event)

    return events
