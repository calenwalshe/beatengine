from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .timebase import ticks_per_bar
from .midi_writer import MidiEvent
from .bass_score import SyncWeights, score_steps, select_steps_by_score


PHRASE_PATTERNS = {
    "rise": [0, 5, 7, 12],
    "bounce": [0, 10, 0, 7],
    "fall": [0, -2, -4, -7],
    "surge": [0, 12, 7, 14],
    "collapse": [0, -5, -7, -12],
}

MOTIF_PRESETS = {
    "root_only": [0],
    "root_fifth": [0, 7],
    "root_fifth_octave": [0, 7, 12],
    "root_b7": [0, 10],
    "pentatonic_bounce": [0, 7, 12, 7],
    "dorian_sway": [0, 9, 7, 14],
}


@dataclass
class Grid:
    bar_ticks: int
    step_ticks: int  # 16th
    half_step_ticks: int  # 32nd


def build_swung_grid(bpm: float, ppq: int) -> Grid:
    """Return timing grid with 16th and 32nd resolution.

    Swing is handled in scheduling; here we provide precise tick sizes.
    """
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    half_step_ticks = step_ticks // 2
    return Grid(bar_ticks=bar_ticks, step_ticks=step_ticks, half_step_ticks=half_step_ticks)


def kick_forbid_mask(steps: int, kick_steps: Iterable[int], window: int = 0) -> List[int]:
    """Return a 0/1 mask of steps to forbid around kick positions.

    window=0 forbids exactly the kick steps; window=1 forbids ±1 steps as well.
    """
    forbid = [0] * steps
    for k in kick_steps:
        for d in range(-window, window + 1):
            idx = (int(k) + d) % steps
            forbid[idx] = 1
    return forbid


def prekick_ghost_offsets(kick_steps: Sequence[int]) -> List[Tuple[int, int]]:
    """Return list of (step_idx, offset_32nds) indicating pre-kick ghost positions.

    A pre-kick ghost sits one 32nd (half a 16th) before the kick step.
    offset_32nds is -1 for a position half-step before the kick's 16th step.
    """
    return [((int(k) % 16), -1) for k in kick_steps]


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _schedule_note(bar_idx: int, step_idx: int, grid: Grid, swing_percent: float = 0.54,
                   half_32nd_offset: int = 0, dur_steps: float = 0.5, note: int = 45,
                   vel: int = 96, channel: int = 0) -> MidiEvent:
    bar_start = bar_idx * grid.bar_ticks
    base = bar_start + step_idx * grid.step_ticks
    # swing: delay odd 16th steps by (swing_percent-0.5) * 16th
    swing = 0
    if step_idx % 2 == 1:
        swing = int(round((swing_percent - 0.5) * grid.step_ticks))
    micro = half_32nd_offset * grid.half_step_ticks
    start = base + swing + micro
    dur = max(1, int(round(dur_steps * grid.step_ticks)))
    return MidiEvent(note=_clamp(note, 0, 127), vel=_clamp(vel, 1, 127), start_abs_tick=start, dur_tick=dur, channel=channel)


def generate_mvp(bpm: float, ppq: int, bars: int, seed: int = 1234,
                 root_note: int = 45, register_lo: int = 34, register_hi: int = 52,
                 swing_percent: float = 0.54, avoid_kick: bool = True,
                 density_target: float | None = None, density_tol: float = 0.05,
                 min_dur_steps: float = 0.5,
                 degree_mode: str | None = None,
                 motif: str | None = None,
                 phrase: str | None = None) -> List[MidiEvent]:
    """Generate a minimal bassline: per-bar anchor + offbeat pulses.

    - Anchor on step 0 alternating root/fifth by bar.
    - Offbeats on {2,6,10,14} when not colliding with kick.
    - Clamp to [register_lo, register_hi].
    """
    grid = build_swung_grid(bpm, ppq)
    events: List[MidiEvent] = []
    steps = 16
    kick_steps = [0, 4, 8, 12]  # assume 4/4 for MVP
    forbid = kick_forbid_mask(steps, kick_steps, window=0) if avoid_kick else [0]*steps

    root = _clamp(root_note, register_lo, register_hi)
    phrase_offsets = None
    if phrase:
        phrase_offsets = PHRASE_PATTERNS.get(phrase.strip().lower())

    rng = math  # placeholder to keep deterministic feel (no random used currently)
    offbeats = [2, 6, 10, 14]
    for bar in range(bars):
        phrase_interval = phrase_offsets[bar % len(phrase_offsets)] if phrase_offsets else 0
        bar_root = _clamp(root + phrase_interval, register_lo, register_hi)
        bar_fifth = _clamp(bar_root + 7, register_lo, register_hi)
        anchor_note = bar_root if (bar % 2 == 0) else bar_fifth
        # anchor sustain slightly longer; pre-kick ghost offset (-1 half-step) to avoid exact kick time
        anchor = _schedule_note(bar, 0, grid, swing_percent, -1, dur_steps=max(1.0, min_dur_steps), note=anchor_note, vel=100, channel=1)
        events.append(anchor)

        # decide how many additional pulses to meet density target if provided
        desired_notes = None
        if density_target is not None:
            # target count per bar (notes, not including ties)
            desired_notes = _clamp(int(round(steps * density_target)), 1, steps)
            # account for anchor
            desired_pulses = max(0, desired_notes - 1)
        else:
            desired_pulses = None

        # Build candidate steps: prioritize classic offbeats, then remaining non-kick, non-anchor steps
        base_candidates = [s for s in offbeats if not forbid[s]]
        others = [s for s in range(steps) if s not in {0,4,8,12} and s not in offbeats and not forbid[s]]
        candidates = base_candidates + others
        added = 0
        # Resolve motif sequence
        motif_seq: List[int]
        motif_seq = MOTIF_PRESETS.get(motif or "", None)
        if motif_seq is None:
            if motif is None and degree_mode == "minor":
                motif_seq = MOTIF_PRESETS["root_b7"]
            elif motif is None and degree_mode == "dorian":
                motif_seq = MOTIF_PRESETS["dorian_sway"]
            else:
                motif_seq = MOTIF_PRESETS["root_only"]
        for idx, s in enumerate(candidates):
            if desired_pulses is not None and added >= desired_pulses:
                break
            interval = motif_seq[idx % len(motif_seq)]
            note_base = bar_root
            note_use = _clamp(note_base + interval, register_lo, register_hi)
            pulse = _schedule_note(bar, s, grid, swing_percent, 0, dur_steps=max(min_dur_steps, 0.5), note=note_use, vel=90, channel=1)
            events.append(pulse)
            added += 1

    return events


def generate_scored(
    bpm: float,
    ppq: int,
    bars: int,
    root_note: int,
    kick_masks_by_bar: List[List[int]],
    hat_masks_by_bar: List[List[int]] | None = None,
    clap_masks_by_bar: List[List[int]] | None = None,
    density_target: float | None = 0.4,
    min_dur_steps: float = 0.5,
    swing_percent: float = 0.54,
    register_lo: int = 34,
    register_hi: int = 52,
    weights: SyncWeights | None = None,
    degree_mode: str | None = None,
    motif: str | None = None,
    phrase: str | None = None,
) -> List[MidiEvent]:
    """Generate bass using drum-aware scoring per bar.

    - Always place an anchor at step 0 with pre-kick offset (-1/32).
    - Pick additional pulses by highest score (hat/clap bonuses, kick penalty).
    - Avoid exact kick steps.
    """
    grid = build_swung_grid(bpm, ppq)
    events: List[MidiEvent] = []
    steps = 16
    weights = weights or SyncWeights()

    root = _clamp(root_note, register_lo, register_hi)
    phrase_offsets = PHRASE_PATTERNS.get(phrase.strip().lower()) if phrase else None
    base_forbidden = {0, 4, 8, 12}

    for bar in range(bars):
        phrase_interval = phrase_offsets[bar % len(phrase_offsets)] if phrase_offsets else 0
        bar_root = _clamp(root + phrase_interval, register_lo, register_hi)
        bar_fifth = _clamp(bar_root + 7, register_lo, register_hi)
        # anchor alternating root/fifth
        anchor_note = bar_root if (bar % 2 == 0) else bar_fifth
        events.append(_schedule_note(bar, 0, grid, swing_percent, -1, dur_steps=max(1.0, min_dur_steps), note=anchor_note, vel=100, channel=1))

        if density_target is None:
            continue
        target = _clamp(int(round(steps * density_target)), 1, steps)
        desired_pulses = max(0, target - 1)
        if desired_pulses == 0:
            continue

        kick_mask = kick_masks_by_bar[bar] if bar < len(kick_masks_by_bar) else [1 if i in base_forbidden else 0 for i in range(steps)]
        hat_mask = hat_masks_by_bar[bar] if (hat_masks_by_bar and bar < len(hat_masks_by_bar)) else [0] * steps
        clap_mask = clap_masks_by_bar[bar] if (clap_masks_by_bar and bar < len(clap_masks_by_bar)) else [0] * steps
        scores = score_steps(steps, kick_mask, hat_mask, clap_mask, weights)
        forbidden = {i for i, v in enumerate(kick_mask) if v}
        forbidden.add(0)  # don't double-place with anchor
        chosen = select_steps_by_score(scores, forbidden, desired_pulses)
        # Resolve motif sequence
        motif_seq = MOTIF_PRESETS.get(motif or "", None)
        if motif_seq is None:
            if motif is None and degree_mode == "minor":
                motif_seq = MOTIF_PRESETS["root_b7"]
            elif motif is None and degree_mode == "dorian":
                motif_seq = MOTIF_PRESETS["dorian_sway"]
            else:
                motif_seq = MOTIF_PRESETS["root_fifth"]
        for j, s in enumerate(chosen):
            interval = motif_seq[j % len(motif_seq)]
            note_use = _clamp(bar_root + interval, register_lo, register_hi)
            events.append(_schedule_note(bar, s, grid, swing_percent, 0, dur_steps=max(min_dur_steps, 0.5), note=note_use, vel=90, channel=1))

    return events
