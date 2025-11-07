from __future__ import annotations

import json
from typing import List, Tuple

from techno_engine.bassline import generate_mvp
from techno_engine.bass_seed import audit_hash
from techno_engine.midi_writer import MidiEvent


def _canon(events: List[MidiEvent]) -> List[Tuple[int, int, int]]:
    return sorted([(e.note, e.start_abs_tick, e.dur_tick) for e in events])


def test_e2e_golden_simple():
    ev = generate_mvp(120.0, 1920, 4, seed=4242, root_note=45)
    h = audit_hash(_canon(ev))
    assert h == "f1b97d1ffb1ccd47717ed605470734d0daf7fba5006790fe1bdda646e8b51a94"


def test_seed_replay():
    a = audit_hash(_canon(generate_mvp(120.0, 1920, 4, seed=1, root_note=45)))
    b = audit_hash(_canon(generate_mvp(120.0, 1920, 4, seed=1, root_note=45)))
    assert a == b

