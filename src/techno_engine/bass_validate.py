from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .midi_writer import MidiEvent
from .bassline import build_swung_grid, kick_forbid_mask


@dataclass
class ValidationResult:
    events: List[MidiEvent]
    summaries: List[str]


def _by_bar(events: List[MidiEvent], bar_ticks: int, bars_hint: int | None = None) -> List[List[MidiEvent]]:
    bars = 0
    for ev in events:
        bars = max(bars, (ev.start_abs_tick // bar_ticks) + 1)
    if bars_hint is not None and bars < bars_hint:
        bars = bars_hint
    buckets: List[List[MidiEvent]] = [[] for _ in range(bars)]
    for ev in events:
        buckets[ev.start_abs_tick // bar_ticks].append(ev)
    for b in buckets:
        b.sort(key=lambda e: e.start_abs_tick)
    return buckets


def _count_per_bar(events: List[MidiEvent], bar_ticks: int) -> List[int]:
    buckets = _by_bar(events, bar_ticks)
    return [len(b) for b in buckets]


def validate_bass(
    events: List[MidiEvent],
    ppq: int,
    bpm: float,
    bars: int,
    density_target: float | None = None,
    density_tol: float = 0.03,
    register: Tuple[int, int] = (34, 52),
    kick_steps: Tuple[int, int, int, int] = (0, 4, 8, 12),
    kick_window: int = 0,
) -> ValidationResult:
    """Single-pass validator/corrector: kick → register → density → monophony.

    Returns possibly-adjusted events and short summaries of applied corrections.
    """
    grid = build_swung_grid(bpm, ppq)
    bar_ticks = grid.bar_ticks
    step_ticks = grid.step_ticks
    summaries: List[str] = []

    # 1) Kick collisions: drop any event starting exactly at forbidden kick steps.
    forbid_mask = kick_forbid_mask(16, kick_steps, window=kick_window)
    kick_ticks = set()
    for bar in range(bars):
        base = bar * bar_ticks
        for s, v in enumerate(forbid_mask):
            if v:
                kick_ticks.add(base + s * step_ticks)

    before = len(events)
    kept: List[MidiEvent] = [ev for ev in events if ev.start_abs_tick not in kick_ticks]
    removed = before - len(kept)
    if removed > 0:
        summaries.append(f"Removed {removed} bass notes colliding with kick; preserved anchors elsewhere. Avoiding exact kick ticks improves clarity.")

    # 2) Register clamp
    lo, hi = register
    clamped: List[MidiEvent] = []
    clamp_changes = 0
    for ev in kept:
        n = ev.note
        if n < lo:
            clamp_changes += 1
            n = lo
        elif n > hi:
            clamp_changes += 1
            n = hi
        if n != ev.note:
            clamped.append(MidiEvent(note=n, vel=ev.vel, start_abs_tick=ev.start_abs_tick, dur_tick=ev.dur_tick, channel=ev.channel))
        else:
            clamped.append(ev)
    if clamp_changes > 0:
        summaries.append(f"Clamped {clamp_changes} notes to register [{lo},{hi}] to keep bass focused and mix-safe.")

    # 3) Density correction per bar (target notes per bar)
    corrected: List[MidiEvent] = []
    if density_target is not None:
        target = max(1, int(round(16 * density_target)))
        tol_count = max(0, int(round(16 * density_tol)))
        by_bar = _by_bar(clamped, bar_ticks, bars_hint=bars)
        adjustments = 0
        for bar_idx, bucket in enumerate(by_bar):
            c = len(bucket)
            if c > target + tol_count:
                # prune from weakest positions: keep earliest (anchor), drop latest first
                keep_first = bucket[0:1]
                rest = bucket[1:]
                # drop surplus from end
                surplus = c - (target + tol_count)
                rest = rest[: max(0, len(rest) - surplus)]
                corrected.extend(keep_first + rest)
                adjustments += surplus
            elif c < target - tol_count:
                # start with existing notes
                corrected.extend(bucket)
                # add short pulses at available non-forbidden steps
                existing_steps = {((ev.start_abs_tick - bar_idx * bar_ticks) // step_ticks) for ev in bucket}
                candidates = [s for s in range(16) if s not in existing_steps and forbid_mask[s] == 0]
                need = (target - tol_count) - c
                for s in candidates[:need]:
                    start = bar_idx * bar_ticks + s * step_ticks
                    corrected.append(MidiEvent(note=max(lo, min(hi, bucket[0].note if bucket else lo)), vel=88, start_abs_tick=start, dur_tick=max(1, step_ticks // 2), channel=1))
                    adjustments += 1
            else:
                corrected.extend(bucket)
        if adjustments > 0:
            summaries.append(f"Adjusted density with {adjustments} edits to fit target ±{tol_count} notes per bar; preserving anchors first.")
    else:
        corrected = clamped

    # 4) Monophony: ensure no overlaps within a bar by trimming durations up to next onset
    mono_edits = 0
    by_bar_final = _by_bar(corrected, bar_ticks, bars_hint=bars)
    final_events: List[MidiEvent] = []
    for bucket in by_bar_final:
        for i, ev in enumerate(bucket):
            if i + 1 < len(bucket):
                next_ev = bucket[i + 1]
                end_tick = ev.start_abs_tick + ev.dur_tick
                if end_tick > next_ev.start_abs_tick:
                    new_dur = max(1, next_ev.start_abs_tick - ev.start_abs_tick)
                    if new_dur != ev.dur_tick:
                        mono_edits += 1
                    final_events.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=ev.start_abs_tick, dur_tick=new_dur, channel=ev.channel))
                else:
                    final_events.append(ev)
            else:
                final_events.append(ev)
    if mono_edits > 0:
        summaries.append("Trimmed overlapping notes to enforce monophony; phrases remain intact.")

    return ValidationResult(events=final_events, summaries=summaries)
