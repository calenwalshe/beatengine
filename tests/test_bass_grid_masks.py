from __future__ import annotations

from techno_engine.bassline import build_swung_grid, kick_forbid_mask, prekick_ghost_offsets


def test_grid_quantization_16th_32nd_ticks():
    g = build_swung_grid(bpm=120.0, ppq=1920)
    # 120 BPM, PPQ 1920 ⇒ 1 beat = 1920 ticks; 1 bar = 4*1920 = 7680
    assert g.bar_ticks == 7680
    assert g.step_ticks == g.bar_ticks // 16
    assert g.half_step_ticks * 2 == g.step_ticks


def test_kick_forbid_exact_matches():
    m = kick_forbid_mask(steps=16, kick_steps=[0, 4, 8, 12], window=0)
    assert m == [1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0]


def test_prekick_ghost_exact_offset():
    offs = prekick_ghost_offsets([0, 4, 8, 12])
    # Each kick step should map to (step, -1)
    assert offs == [(0, -1), (4, -1), (8, -1), (12, -1)]

