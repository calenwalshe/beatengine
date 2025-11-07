from __future__ import annotations

from typing import List

from techno_engine.bassline import build_swung_grid
from techno_engine.bass_validate import validate_bass
from techno_engine.midi_writer import MidiEvent


def _make_collision_case(ppq=1920, bpm=120.0):
    g = build_swung_grid(bpm, ppq)
    # Place notes exactly at kick ticks in bar 0: steps 0,4,8,12
    notes: List[MidiEvent] = []
    for s in [0, 4, 8, 12]:
        notes.append(MidiEvent(note=45, vel=100, start_abs_tick=s * g.step_ticks, dur_tick=g.step_ticks // 2, channel=1))
    return notes, g


def test_validator_removes_kick_collisions():
    events, g = _make_collision_case()
    res = validate_bass(events, ppq=1920, bpm=120.0, bars=1, density_target=None)
    starts = {e.start_abs_tick for e in res.events}
    kick_ticks = {0, 4 * g.step_ticks, 8 * g.step_ticks, 12 * g.step_ticks}
    assert not (starts & kick_ticks)


def test_validator_density_tight():
    # Start sparse: only one anchor per bar (simulate)
    g = build_swung_grid(120.0, 1920)
    events = [MidiEvent(note=45, vel=100, start_abs_tick=b * g.bar_ticks, dur_tick=g.step_ticks, channel=1) for b in range(4)]
    res = validate_bass(events, ppq=1920, bpm=120.0, bars=4, density_target=0.5, density_tol=0.03)
    target = round(16 * 0.5)
    tol = int(round(16 * 0.03))  # ≈ 0–1
    per_bar = []
    for b in range(4):
        c = sum(1 for e in res.events if (e.start_abs_tick // g.bar_ticks) == b)
        per_bar.append(c)
    assert all(abs(c - target) <= max(1, tol) for c in per_bar)


def test_validator_single_pass_only_and_summaries_short():
    g = build_swung_grid(120.0, 1920)
    events = [
        MidiEvent(note=60, vel=100, start_abs_tick=0, dur_tick=g.step_ticks * 2, channel=1),  # out of register, overlaps
        MidiEvent(note=45, vel=100, start_abs_tick=1 * g.step_ticks, dur_tick=g.step_ticks, channel=1),
    ]
    res1 = validate_bass(events, ppq=1920, bpm=120.0, bars=1, density_target=0.5, density_tol=0.03)
    res2 = validate_bass(res1.events, ppq=1920, bpm=120.0, bars=1, density_target=0.5, density_tol=0.03)
    a = sorted((e.note, e.start_abs_tick, e.dur_tick) for e in res1.events)
    b = sorted((e.note, e.start_abs_tick, e.dur_tick) for e in res2.events)
    assert a == b  # idempotent second pass
    # Summaries: each ≤ 3 sentences (count by periods)
    assert all(sum(1 for ch in s if ch in ".!?") <= 3 for s in res1.summaries)

