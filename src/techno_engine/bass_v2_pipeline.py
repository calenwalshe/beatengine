"""5-stage pipeline implementation for bass_v2 generator."""
from __future__ import annotations

import random
from typing import List, Dict, Optional, Tuple

from .bass_v2_types import (
    DrumBar,
    BarSlotGrid,
    SlotFeature,
    BassModeAssignment,
    ScoredSlot,
    BassNote,
    TheoryContext,
    ResolvedControls,
)
from .bass_v2_controls import resolve_controls, select_mode_from_energy


# ============================================================================
# STEP 1: drums_to_slot_grid
# ============================================================================

def drums_to_slot_grid(drum_bars: List[DrumBar]) -> List[BarSlotGrid]:
    """Convert drum bars to slot grids with rhythm-aware features.

    - Create 16 slots per bar
    - Mark musical labels: downbeat, backbeat, offbeat, gap
    - Compute energy metrics
    """
    grids: List[BarSlotGrid] = []

    for bar_idx, drum_bar in enumerate(drum_bars):
        slots: List[SlotFeature] = []
        drum_energy = 0.0

        for i in range(16):
            step = drum_bar.steps[i] if i < len(drum_bar.steps) else None
            if not step:
                step = drum_bar.steps[0].__class__()  # Create empty step

            slot = SlotFeature(index=i)
            slot.has_kick = step.kick
            slot.has_hat = step.hat
            slot.has_snare = step.snare

            # Musical labels (assuming 4/4, 16 steps per bar)
            # Beats are at 0, 4, 8, 12
            slot.is_downbeat = i in {0, 4, 8, 12}
            # Backbeats are beats 2 and 4 (steps 4 and 12)
            slot.is_backbeat = i in {4, 12}
            # Offbeats are 8th-note positions between beats
            slot.is_offbeat = i in {2, 6, 10, 14}
            # Gap = no drum hits
            slot.is_gap = not (step.kick or step.hat or step.snare)

            # Local energy (count of hits, or use velocity if available)
            local_energy = 0.0
            if step.kick:
                local_energy += step.velocity if step.velocity else 1.0
            if step.hat:
                local_energy += (step.velocity if step.velocity else 1.0) * 0.5
            if step.snare:
                local_energy += (step.velocity if step.velocity else 1.0) * 0.8

            slot.drum_energy_local = local_energy
            drum_energy += local_energy

            slots.append(slot)

        grid = BarSlotGrid(bar_index=bar_idx, slots=slots, drum_energy_bar=drum_energy)
        grids.append(grid)

    return grids


# ============================================================================
# STEP 2: bass_mode_selection
# ============================================================================

def bass_mode_selection(
    slot_grids: List[BarSlotGrid],
    style_or_genre_preset: Optional[Dict] = None,
    global_controls: Optional[Dict] = None,
) -> List[BassModeAssignment]:
    """Select bass mode per bar based on energy and controls.

    Returns one BassModeAssignment per bar with resolved controls.
    """
    assignments: List[BassModeAssignment] = []
    mode_strategy = "auto_from_drums"
    fixed_mode = None
    per_bar_modes = None

    if global_controls:
        mode_config = global_controls.get("mode_and_behavior_controls", {})
        mode_strategy = mode_config.get("strategy", "auto_from_drums")
        fixed_mode = mode_config.get("fixed_mode")
        per_bar_modes = mode_config.get("per_bar_modes")

    for grid in slot_grids:
        # Determine mode for this bar
        if mode_strategy == "fixed_mode" and fixed_mode:
            mode_name = fixed_mode
        elif mode_strategy == "per_bar_explicit" and per_bar_modes:
            mode_name = per_bar_modes[grid.bar_index % len(per_bar_modes)]
        else:
            # Auto from drums energy
            mode_name = select_mode_from_energy(grid.drum_energy_bar)

        # Resolve controls for this bar
        resolved = resolve_controls(
            style_or_genre_preset=style_or_genre_preset,
            bass_mode_name=mode_name,
            user_overrides=global_controls,
        )

        assignment = BassModeAssignment(
            bar_index=grid.bar_index,
            mode_name=mode_name,
            resolved_controls=resolved,
        )
        assignments.append(assignment)

    return assignments


# ============================================================================
# STEP 3: step_scoring_and_selection
# ============================================================================

def step_scoring_and_selection(
    grid: BarSlotGrid,
    assignment: BassModeAssignment,
    rng: Optional[random.Random] = None,
) -> List[ScoredSlot]:
    """Score each slot and select top-N based on mode, density, and kick-avoid rules."""
    if rng is None:
        rng = random.Random(42)

    controls = assignment.resolved_controls
    rhythm = controls.rhythm_controls
    drum_interaction = controls.drum_interaction_controls

    # Compute scores for each slot
    scored_slots: List[ScoredSlot] = []
    for slot in grid.slots:
        score = 0.0

        # Downbeat/backbeat priority
        if slot.is_downbeat:
            score += 0.8
        if slot.is_backbeat:
            score += 0.6

        # Offbeat syncopation
        if slot.is_offbeat:
            score += rhythm.rhythmic_complexity * 0.7

        # Kick interaction
        if slot.has_kick:
            if rhythm.kick_interaction_mode == "avoid_kick":
                score -= drum_interaction.kick_avoid_strength * 2.0
            elif rhythm.kick_interaction_mode == "reinforce_kick":
                score += 0.5

        # Hat sync
        if slot.has_hat:
            score += drum_interaction.hat_sync_strength * 0.5

        # Snare/backbeat
        if slot.has_snare:
            score += drum_interaction.snare_backbeat_preference * 0.4

        # Gap preference (for offbeat_stabs mode)
        if slot.is_gap:
            if assignment.mode_name == "offbeat_stabs":
                score += 0.9

        # Apply onbeat/offbeat balance
        if rhythm.onbeat_offbeat_balance > 0 and slot.is_offbeat:
            score += rhythm.onbeat_offbeat_balance
        elif rhythm.onbeat_offbeat_balance < 0 and slot.is_downbeat:
            score += abs(rhythm.onbeat_offbeat_balance)

        scored_slots.append(ScoredSlot(slot=slot, score=score, selected=False))

    # Determine target number of notes
    target_notes = int(round(16 * rhythm.note_density))
    target_notes = max(1, min(16, target_notes))

    # Sort by score and select top-N
    scored_slots.sort(key=lambda s: s.score, reverse=True)

    # Apply forbidden masks
    forbidden_indices = set()
    if rhythm.kick_interaction_mode == "avoid_kick":
        for ss in scored_slots:
            if ss.slot.has_kick and drum_interaction.kick_avoid_strength > 0.5:
                forbidden_indices.add(ss.slot.index)

    # Select top-N non-forbidden
    selected_count = 0
    for ss in scored_slots:
        if ss.slot.index not in forbidden_indices and selected_count < target_notes:
            ss.selected = True
            selected_count += 1

    return scored_slots


# ============================================================================
# STEP 4: pitch_mapping_and_midi
# ============================================================================

# Simple scale definitions (semitones from root)
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],  # Natural minor
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}


def parse_key_scale(key_scale: str) -> Tuple[int, List[int]]:
    """Parse key_scale string like 'A_minor' -> (root_midi, scale_intervals)."""
    parts = key_scale.split("_")
    if len(parts) < 2:
        # Default to A minor
        return (45, SCALES["minor"])

    key_name = parts[0].strip()
    mode_name = parts[1].strip().lower()

    # Simple MIDI note mapping (A=45 for bass octave 2)
    note_map = {"C": 36, "D": 38, "E": 40, "F": 41, "G": 43, "A": 45, "B": 47}
    root_midi = note_map.get(key_name, 45)

    scale_intervals = SCALES.get(mode_name, SCALES["minor"])
    return (root_midi, scale_intervals)


def pitch_mapping_and_midi(
    scored_slots: List[ScoredSlot],
    assignment: BassModeAssignment,
    theory_context: TheoryContext,
    prev_note: Optional[BassNote] = None,
    rng: Optional[random.Random] = None,
) -> List[BassNote]:
    """Map selected slots to pitches and create BassNote objects."""
    if rng is None:
        rng = random.Random(42)

    controls = assignment.resolved_controls
    melody = controls.melody_controls
    articulation = controls.articulation_controls
    rhythm = controls.rhythm_controls

    root_midi, scale_intervals = parse_key_scale(theory_context.key_scale)
    # Shift base octave (slider 1-3) relative to default octave 2 root map
    root_midi += int((melody.base_octave - 2) * 12)

    notes: List[BassNote] = []
    selected_slots = [ss for ss in scored_slots if ss.selected]

    for ss in selected_slots:
        # Select scale degree
        chose_root = False
        if rng.random() < melody.root_note_emphasis:
            # Root note
            degree_offset = 0
            chose_root = True
        else:
            # Choose from scale with melodic intensity bias toward wider leaps
            if melody.melodic_intensity > 0.65 and len(scale_intervals) > 4:
                degree_offset = rng.choice(scale_intervals[2:])  # favor upper degrees
            else:
                degree_offset = rng.choice(scale_intervals)

        # Apply interval jump magnitude
        if prev_note and not chose_root and rng.random() > melody.interval_jump_magnitude:
            # Stay close to previous note (stepwise)
            degree_offset = scale_intervals[rng.randint(0, min(2, len(scale_intervals) - 1))]
        elif prev_note and not chose_root and melody.melodic_intensity > 0.5:
            # Allow bigger leaps when intensity is high
            leap_choices = scale_intervals[-3:] if len(scale_intervals) > 3 else scale_intervals
            degree_offset = rng.choice(leap_choices)

        # Calculate pitch within octave range
        base_pitch = root_midi + degree_offset
        max_octaves = max(0, melody.note_range_octaves - 1)
        # Higher melodic intensity increases chance of jumping up octaves
        if max_octaves > 0 and rng.random() < melody.melodic_intensity:
            octave_shift = rng.randint(0, max_octaves)
        else:
            octave_shift = rng.randint(0, max(0, max_octaves - 1))
        pitch = base_pitch + (octave_shift * 12)

        # Clamp to reasonable bass range
        pitch = max(28, min(60, pitch))

        # Velocity with accent patterns and humanization
        accent_bias = articulation.accent_chance
        if articulation.accent_pattern_mode == "offbeat_focused":
            accent_bias = articulation.accent_chance + (0.35 if ss.slot.is_offbeat else -0.1)
        elif articulation.accent_pattern_mode == "downbeat_focused":
            accent_bias = articulation.accent_chance + (0.35 if ss.slot.is_downbeat or ss.slot.is_backbeat else -0.05)

        use_accent = rng.random() < max(0.0, min(1.0, accent_bias))
        velocity = articulation.velocity_accent if use_accent else articulation.velocity_normal

        if articulation.humanize_velocity > 0:
            jitter = int((rng.random() - 0.5) * 20 * articulation.humanize_velocity)
            velocity = max(1, min(127, velocity + jitter))

        # Duration (gate length)
        step_duration = 0.25  # 16th note = 0.25 beats
        duration = step_duration * articulation.gate_length

        # Start time (in beats) with swing, groove, and humanization
        start_beat = assignment.bar_index * 4.0 + (ss.slot.index * step_duration)

        if rhythm.swing_amount > 0 and ss.slot.index % 2 == 1:
            # Push late on off-16ths by up to half a 16th note
            start_beat += rhythm.swing_amount * (step_duration * 0.5)

        if rhythm.groove_depth > 0:
            if ss.slot.is_offbeat:
                start_beat += rhythm.groove_depth * 0.04  # subtle late push
            elif ss.slot.is_downbeat:
                start_beat -= rhythm.groove_depth * 0.02

        if articulation.humanize_timing > 0:
            jitter = (rng.random() - 0.5) * 0.06 * articulation.humanize_timing
            start_beat += jitter
            start_beat = max(assignment.bar_index * 4.0, start_beat)

        note = BassNote(
            pitch=pitch,
            start_beat=start_beat,
            duration_beats=duration,
            velocity=velocity,
            metadata={"slot_index": ss.slot.index, "score": ss.score},
        )
        # Tie notes: extend previous note if contiguous slot and same pitch
        if articulation.tie_notes and prev_note:
            prev_slot_idx = int((prev_note.start_beat - assignment.bar_index * 4.0) / step_duration)
            if ss.slot.index == prev_slot_idx + 1 and prev_note.pitch == note.pitch:
                prev_note.duration_beats = max(prev_note.duration_beats, (start_beat - prev_note.start_beat) + duration)
                prev_note.metadata["tied"] = True
                prev_note.metadata["score"] = max(prev_note.metadata.get("score", 0), ss.score)
                continue

        notes.append(note)
        prev_note = note

    return notes


# ============================================================================
# STEP 5: validation_and_post_processing
# ============================================================================

def validation_and_post_processing(
    notes: List[BassNote],
    grid: BarSlotGrid,
    assignment: BassModeAssignment,
    theory_context: TheoryContext,
) -> Tuple[List[BassNote], Dict]:
    """Validate and adjust notes for mix safety, density, and key/chord adherence."""
    controls = assignment.resolved_controls
    rhythm = controls.rhythm_controls
    output = controls.output_controls

    adjusted_notes = notes.copy()
    metadata = {
        "warnings": [],
        "adjustments": [],
    }

    # 1. Kick collision check
    if rhythm.kick_interaction_mode == "avoid_kick":
        kick_slots = {slot.index for slot in grid.slots if slot.has_kick}
        notes_to_remove = []
        for note in adjusted_notes:
            # Convert start_beat back to slot index
            bar_beat = note.start_beat - (assignment.bar_index * 4.0)
            slot_idx = int(bar_beat / 0.25)
            if slot_idx in kick_slots:
                notes_to_remove.append(note)
                metadata["adjustments"].append(f"Removed note at slot {slot_idx} due to kick collision")

        for note in notes_to_remove:
            adjusted_notes.remove(note)

    # 2. Density check
    target_density = int(round(16 * rhythm.note_density))
    if len(adjusted_notes) > target_density * 1.5:
        # Too many notes, prune lowest-scoring
        adjusted_notes.sort(key=lambda n: n.metadata.get("score", 0), reverse=True)
        adjusted_notes = adjusted_notes[:int(target_density * 1.2)]
        metadata["adjustments"].append(f"Pruned notes to match density target")

    # 3. Max notes per bar check
    if len(adjusted_notes) > output.max_notes_per_bar:
        adjusted_notes = adjusted_notes[:output.max_notes_per_bar]
        metadata["warnings"].append(f"Clamped to max_notes_per_bar: {output.max_notes_per_bar}")

    # 4. Key validation (ensure all notes are in scale)
    root_midi, scale_intervals = parse_key_scale(theory_context.key_scale)
    valid_pitches = set()
    for octave in range(-2, 4):  # Cover wide range
        for interval in scale_intervals:
            valid_pitches.add(root_midi + interval + (octave * 12))

    for note in adjusted_notes:
        if note.pitch not in valid_pitches:
            # Snap to nearest in-scale pitch
            closest = min(valid_pitches, key=lambda p: abs(p - note.pitch))
            metadata["adjustments"].append(f"Adjusted pitch {note.pitch} -> {closest} to fit key")
            note.pitch = closest

    return adjusted_notes, metadata
