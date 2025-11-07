from __future__ import annotations

from typing import List

from techno_engine.bassline import generate_mvp, build_swung_grid
from techno_engine.midi_writer import MidiEvent


def _starts_by_bar(events: List[MidiEvent], bar_ticks: int) -> list[list[MidiEvent]]:
    bars = 0
    for ev in events:
        bars = max(bars, (ev.start_abs_tick // bar_ticks) + 1)
    buckets: list[list[MidiEvent]] = [[] for _ in range(bars)]
    for ev in events:
        buckets[ev.start_abs_tick // bar_ticks].append(ev)
    return buckets


def test_mvp_emits_events():
    ev = generate_mvp(bpm=120.0, ppq=1920, bars=4, seed=1, root_note=45)
    g = build_swung_grid(120.0, 1920)
    by_bar = _starts_by_bar(ev, g.bar_ticks)
    # At least one event per bar (anchor)
    assert all(len(bar) >= 1 for bar in by_bar)


def test_mvp_no_note_on_kick():
    ev = generate_mvp(bpm=120.0, ppq=1920, bars=2, seed=1, root_note=45)
    g = build_swung_grid(120.0, 1920)
    kick_steps = [0, 4, 8, 12]
    kick_ticks = set()
    for bar in range(2):
        bar_start = bar * g.bar_ticks
        for ks in kick_steps:
            kick_ticks.add(bar_start + ks * g.step_ticks)
    starts = {e.start_abs_tick for e in ev}
    assert not (starts & kick_ticks)


def test_mvp_register_bounds():
    ev = generate_mvp(bpm=120.0, ppq=1920, bars=4, seed=2, root_note=45,
                      register_lo=34, register_hi=52)
    assert all(34 <= e.note <= 52 for e in ev)


def test_mvp_roundtrip_hash_stable():
    # canonical representation for hashing: (note, start, dur)
    def canon(events: List[MidiEvent]):
        return sorted([(e.note, e.start_abs_tick, e.dur_tick) for e in events])
    a = canon(generate_mvp(120.0, 1920, 4, seed=999, root_note=43))
    b = canon(generate_mvp(120.0, 1920, 4, seed=999, root_note=43))
    assert a == b

