from __future__ import annotations

from random import Random

from techno_engine.accent import AccentProfile, apply_accent
from techno_engine.midi_writer import MidiEvent
from techno_engine.timebase import ticks_per_bar


def _make_events_for_steps(ppq: int, bar: int, steps: list[int], note: int, vel: int, dur_ratio: float = 0.5):
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    events = []
    for s in steps:
        start = bar * bar_ticks + s * step_ticks
        dur = max(1, int(round(step_ticks * dur_ratio)))
        events.append(MidiEvent(note=note, vel=vel, start_abs_tick=start, dur_tick=dur))
    return events


def test_accent_applies_velocity_and_length_scaling():
    ppq = 1920
    # Build a simple 1-bar pattern: kick on 0,4,8,12; hats every 16th; snare on 4,12
    events = []
    events += _make_events_for_steps(ppq, bar=0, steps=[0, 4, 8, 12], note=36, vel=100)
    events += _make_events_for_steps(ppq, bar=0, steps=list(range(16)), note=42, vel=80)
    events += _make_events_for_steps(ppq, bar=0, steps=[4, 12], note=38, vel=90)

    # Accent on steps 1,5,9,13 (1-indexed), guaranteed (prob=1.0)
    profile = AccentProfile(steps_1idx=[1, 5, 9, 13], prob=1.0, velocity_scale=1.2, length_scale=1.5)
    acc = apply_accent(events, ppq=ppq, profile=profile, rng=Random(0))

    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16

    def step_of(ev):
        return int((ev.start_abs_tick % bar_ticks) // step_ticks)

    for orig, new in zip(events, acc):
        s = step_of(orig)
        if s in (0, 4, 8, 12):  # accent steps (0-indexed)
            assert new.vel == min(127, int(round(orig.vel * 1.2)))
            assert new.dur_tick == max(1, int(round(orig.dur_tick * 1.5)))
        else:
            assert new.vel == orig.vel
            assert new.dur_tick == orig.dur_tick


def test_accent_prob_zero_no_effect():
    ppq = 1920
    events = _make_events_for_steps(ppq, bar=0, steps=[0, 4, 8, 12], note=36, vel=100)
    profile = AccentProfile(steps_1idx=[1, 5, 9, 13], prob=0.0, velocity_scale=2.0, length_scale=2.0)
    acc = apply_accent(events, ppq=ppq, profile=profile, rng=Random(123))
    assert [(e.vel, e.dur_tick) for e in events] == [(e.vel, e.dur_tick) for e in acc]

