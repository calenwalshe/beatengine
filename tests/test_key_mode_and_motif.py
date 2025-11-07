from __future__ import annotations

from typing import List

from techno_engine.key_mode import key_to_midi, normalize_mode
from techno_engine.bassline import generate_mvp, build_swung_grid


def test_key_to_midi_mapping():
    assert key_to_midi("A") == 45
    assert key_to_midi("D#") == 39
    assert key_to_midi("Eb") == 39
    assert normalize_mode("Aeolian") == "minor"
    assert normalize_mode("dorian") == "dorian"
    assert normalize_mode("major") is None


def test_motif_minor_includes_b7():
    ev = generate_mvp(bpm=120.0, ppq=1920, bars=4, seed=7, root_note=45, density_target=0.5, degree_mode="minor", motif="root_b7", register_hi=57)
    notes = {e.note for e in ev}
    assert 45 in notes
    assert 55 in notes  # b7 = 45+10


def test_phrase_offsets_anchor_notes():
    ev = generate_mvp(bpm=120.0, ppq=1920, bars=4, seed=1, root_note=45, density_target=0.3, phrase="rise")
    grid = build_swung_grid(120.0, 1920)
    anchors = {}
    for e in ev:
        bar = e.start_abs_tick // grid.bar_ticks
        if bar not in anchors or e.start_abs_tick < anchors[bar].start_abs_tick:
            anchors[bar] = e
    assert anchors[0].note == 45
    assert anchors[1].note >= 50  # rise phrase lifts bar 2 anchor
