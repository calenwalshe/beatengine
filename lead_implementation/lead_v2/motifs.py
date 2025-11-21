from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from random import Random

from .theory import MetricPosition, LeadNoteLogical


@dataclass
class RhythmEvent:
    step_offset: int
    length_steps: int
    accent: float
    anchor_type: Optional[str] = None  # 'kick' | 'snare_zone' | 'hat' | 'offbeat' | None


@dataclass
class RhythmTemplate:
    id: str
    role: str
    bars: int
    events: List[RhythmEvent]
    max_step_jitter: int
    min_inter_note_gap_steps: int
    mode_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    energy: str = "medium"


@dataclass
class ContourTemplate:
    id: str
    role: str
    degree_intervals: List[int]
    emphasis_indices: List[int]
    shape_type: str
    tension_profile: List[str]
    mode_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    energy: str = "medium"


@dataclass
class MotifPlan:
    phrase_id: int
    role: str
    bar_indices: List[int]
    notes: List[LeadNoteLogical] = field(default_factory=list)


def fuse_rhythm_contour(
    phrase_id: int,
    role: str,
    bar_indices: List[int],
    rhythm: RhythmTemplate,
    contour: ContourTemplate,
    steps_per_bar: int,
    rng: Random,
    *,
    degree_transpose: int = 0,
    invert_contour: bool = False,
) -> MotifPlan:
    """Fuse a rhythm and contour template into a MotifPlan.

    For now this function simply maps rhythm events onto contour indices
    in order, and annotates basic phrase/metric metadata. The actual
    alignment to drum slots and function-aware degree assignment happens later.

    TODO: incorporate tension_profile, beat strength, phrase_position, etc.
    """
    notes: List[LeadNoteLogical] = []
    contour_len = max(1, len(contour.degree_intervals))
    contour_steps = contour.degree_intervals or [0]
    if invert_contour:
        contour_steps = [-val for val in contour_steps]

    cumulative_offsets: List[int] = []
    current = 0
    for idx, delta in enumerate(contour_steps):
        if idx == 0:
            current = delta
        else:
            current += delta
        cumulative_offsets.append(current + degree_transpose)

    total_bars = len(bar_indices)
    template_ref = {"rhythm_id": rhythm.id, "contour_id": contour.id}

    for i, ev in enumerate(rhythm.events):
        step_global = ev.step_offset
        bar_choice = min(step_global // steps_per_bar, total_bars - 1)
        bar_idx = bar_indices[bar_choice]
        step_in_bar = step_global % steps_per_bar

        mp = MetricPosition(bar_index=bar_idx, step_in_bar=step_in_bar)
        if i == 0:
            phrase_position = "start"
        elif i == len(rhythm.events) - 1:
            phrase_position = "end"
        else:
            phrase_position = "inner"

        tension_label = contour.tension_profile[min(i, len(contour.tension_profile) - 1)]
        contour_degree = cumulative_offsets[i % len(cumulative_offsets)]
        beat_strength = "strong" if step_in_bar % 4 == 0 or ev.anchor_type in {"kick", "snare_zone"} else "weak"

        ln = LeadNoteLogical(
            phrase_id=phrase_id,
            metric_position=mp,
            role=role,
            phrase_position=phrase_position,
            beat_strength=beat_strength,
            tension_label=tension_label,
            contour_index=i % contour_len,
        )
        ln.contour_degree = contour_degree
        ln.duration_steps = max(1, ev.length_steps)
        ln.accent = max(0.0, min(1.0, ev.accent))
        ln.anchor_type = ev.anchor_type
        ln.min_gap_steps = rhythm.min_inter_note_gap_steps
        ln.slot_jitter = rhythm.max_step_jitter
        ln.template_refs = template_ref
        notes.append(ln)

    return MotifPlan(phrase_id=phrase_id, role=role, bar_indices=bar_indices, notes=notes)
