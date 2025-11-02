from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from techno_engine.backbone import build_backbone_events, compute_E_S
from techno_engine.midi_writer import write_midi


def _filter_by_note(events, note):
    return [e for e in events if e.note == note]


def _steps(events, ppq):
    # Derive steps from absolute ticks
    from techno_engine.timebase import ticks_per_bar

    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    return [int((e.start_abs_tick % bar_ticks) // step_ticks) for e in events]


def test_backbone_structure_and_counts(tmp_path: Path):
    bpm, ppq, bars = 132, 1920, 8
    notes = {"kick": 36, "hat_c": 42, "snare": 38, "clap": 39}
    events = build_backbone_events(bpm=bpm, ppq=ppq, bars=bars, notes=notes)

    # Counts per bar
    kicks = _filter_by_note(events, 36)
    hats = _filter_by_note(events, 42)
    snares = _filter_by_note(events, 38)
    claps = _filter_by_note(events, 39)

    assert len(kicks) == 4 * bars
    assert len(hats) == 16 * bars
    assert len(snares) == 2 * bars
    assert len(claps) == 2 * bars

    # Kick steps exactly {0,4,8,12}
    ksteps = set(_steps(kicks[:4], ppq))
    assert ksteps == {0, 4, 8, 12}

    # Hats cover all 16 steps in first bar
    hsteps = sorted(_steps(hats[:16], ppq))
    assert hsteps == list(range(16))

    # Snare/Clap on backbeats (4,12)
    ssteps = set(_steps(snares[:2], ppq))
    csteps = set(_steps(claps[:2], ppq))
    assert ssteps == {4, 12}
    assert csteps == {4, 12}


def test_metrics_E_S_reasonable():
    bpm, ppq, bars = 132, 1920, 8
    events = build_backbone_events(bpm=bpm, ppq=ppq, bars=bars)
    E, S = compute_E_S(events, ppq)

    assert E >= 0.9
    assert 0.2 <= S <= 0.35

