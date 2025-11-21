from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Set, Optional
from random import Random

from .theory import LeadNoteLogical, LeadNoteEvent


@dataclass
class SlotChoice:
    bar_index: int
    step_in_bar: int
    score: float


def score_slot(slot_tags: List[str], role: str, slot_prefs: Dict[str, float]) -> float:
    """Score a slot based on tags and role-specific preferences.

    This scaffolding provides a simple additive score. The full implementation
    should also include anchor matches, density, and overlap penalties.
    """
    score = 0.0
    for tag in slot_tags:
        score += slot_prefs.get(tag, 0.0)
    return score


def align_to_slots(
    logical_note: LeadNoteLogical,
    anchors: Any,
    role_slot_prefs: Dict[str, Dict[str, float]],
    steps_per_bar: int,
    step_ticks: int,
    duration_steps: int,
    pitch: int,
    velocity: int,
    occupied_steps: Dict[int, Set[int]],
    rng: Random,
    max_step_jitter: Optional[int] = None,
) -> LeadNoteEvent:
    """Align a logical note to the best slot near its metric position."""

    bar_count = max(1, getattr(anchors, "bar_count", 1))
    bar_idx = min(max(logical_note.metric_position.bar_index, 0), bar_count - 1)
    base_step = max(0, min(steps_per_bar - 1, logical_note.metric_position.step_in_bar))

    jitter_sources = [
        logical_note.slot_jitter,
        max_step_jitter,
    ]
    jitter = max([j for j in jitter_sources if j is not None] or [0])
    if logical_note.role == "RESP":
        jitter = max(jitter, 2)

    candidates = []
    for delta in range(-jitter, jitter + 1):
        step = base_step + delta
        if 0 <= step < steps_per_bar:
            candidates.append(step)
    if not candidates:
        candidates = [base_step]

    slot_tags_grid = getattr(anchors, "slot_tags", None)
    role_prefs = role_slot_prefs.get(logical_note.role, role_slot_prefs.get("DEFAULT", {}))

    best_choice: Optional[SlotChoice] = None
    best_score = float("-inf")

    occupied = occupied_steps.setdefault(bar_idx, set())
    min_gap = max(1, logical_note.min_gap_steps or 1)

    for step in candidates:
        tags = slot_tags_grid[bar_idx][step] if slot_tags_grid else []
        score = 0.0
        for tag in tags:
            score += role_prefs.get(tag, 0.0)
        if logical_note.beat_strength == "strong":
            if step % 4 == 0:
                score += 0.4
            elif step % 2 == 0:
                score += 0.1
        else:
            if step % 4 == 0:
                score += 0.1
        if logical_note.anchor_type:
            if logical_note.anchor_type in tags:
                score += 0.8
            else:
                score -= 0.2
        if "hat" in tags:
            score += 0.05
        if logical_note.phrase_position == "end" and step >= steps_per_bar - 2:
            score += 0.2

        clash_penalty = 0.0
        for occ in occupied:
            delta = abs(occ - step)
            if delta == 0:
                clash_penalty += 2.0
            elif delta < min_gap:
                clash_penalty += 0.5
        score -= clash_penalty
        score += rng.random() * 0.01  # deterministic tie breaker

        if score > best_score:
            best_score = score
            best_choice = SlotChoice(bar_index=bar_idx, step_in_bar=step, score=score)

    if best_choice is None:
        best_choice = SlotChoice(bar_index=bar_idx, step_in_bar=base_step, score=0.0)

    occupied.add(best_choice.step_in_bar)

    start_tick = (best_choice.bar_index * steps_per_bar + best_choice.step_in_bar) * step_ticks
    actual_duration_steps = max(1, min(duration_steps, steps_per_bar - best_choice.step_in_bar))
    duration_ticks = max(step_ticks, actual_duration_steps * step_ticks)

    for extra in range(1, actual_duration_steps):
        occ_step = best_choice.step_in_bar + extra
        if occ_step < steps_per_bar:
            occupied.add(occ_step)

    slot_tags = slot_tags_grid[best_choice.bar_index][best_choice.step_in_bar] if slot_tags_grid else []
    tags = {
        "phrase_end": logical_note.phrase_position == "end",
        "slot_score": best_choice.score,
        "slot_tags": sorted(slot_tags) if slot_tags else [],
        "jitter_applied": best_choice.step_in_bar - base_step,
        "tone_category": logical_note.tone_category,
    }

    return LeadNoteEvent(
        pitch=pitch,
        velocity=velocity,
        start_tick=start_tick,
        duration=duration_ticks,
        phrase_id=logical_note.phrase_id,
        role=logical_note.role,
        degree=logical_note.degree or 1,
        tags=tags,
    )
