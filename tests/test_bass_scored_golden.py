from __future__ import annotations

from typing import List, Tuple

from techno_engine.bassline import generate_scored
from techno_engine.bass_seed import audit_hash


def _mask_from_steps(steps_on: list[int], steps: int = 16) -> list[int]:
    m = [0] * steps
    for s in steps_on:
        m[s % steps] = 1
    return m


def _canon(events) -> list[tuple[int,int,int]]:
    return sorted([(e.note, e.start_abs_tick, e.dur_tick) for e in events])


def test_scored_golden_mask_based():
    # 4 bars, 120bpm, simple masks; density 0.4, minor colouring
    bpm, ppq, bars = 120.0, 1920, 4
    kick = _mask_from_steps([0,4,8,12])
    hats = _mask_from_steps([2,6,10,14])
    clap = _mask_from_steps([12])
    ev = generate_scored(bpm=bpm, ppq=ppq, bars=bars, root_note=45,
                         kick_masks_by_bar=[kick]*bars, hat_masks_by_bar=[hats]*bars, clap_masks_by_bar=[clap]*bars,
                         density_target=0.4, degree_mode="minor")
    h = audit_hash(_canon(ev))
    # Golden hash for stability
    assert h == "54b368fe4092a6ca31666b7970cfa2c4f92ee9a156295f2311e62aaf1e8dd639"
