from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from .midi_writer import MidiEvent
from .timebase import ticks_per_bar


@dataclass
class AccentProfile:
    steps_1idx: List[int]
    prob: float = 1.0
    velocity_scale: float = 1.0
    length_scale: float = 1.0


def apply_accent(events: List[MidiEvent], ppq: int, profile: AccentProfile, rng: Optional[random.Random] = None) -> List[MidiEvent]:
    """Apply a global accent lane to events.

    On accent steps (1-indexed), with probability `prob`, scale velocity and length
    for all events on that step in each bar. Velocities are clipped at 127; duration
    is clamped to at least 1 tick.
    """
    rng = rng or random
    steps_0idx = {max(0, int(s) - 1) for s in profile.steps_1idx}
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16

    out: List[MidiEvent] = []
    # Decide for each bar and each accent step whether it’s active (prob gate)
    # Build a cache: (bar_idx, step0) -> bool
    gate_cache = {}
    for ev in events:
        bar_idx = ev.start_abs_tick // bar_ticks
        step0 = int((ev.start_abs_tick % bar_ticks) // step_ticks)
        key = (bar_idx, step0)
        if key not in gate_cache:
            if step0 in steps_0idx:
                gate_cache[key] = (rng.random() < profile.prob)
            else:
                gate_cache[key] = False

    for ev in events:
        bar_idx = ev.start_abs_tick // bar_ticks
        step0 = int((ev.start_abs_tick % bar_ticks) // step_ticks)
        gated = gate_cache.get((bar_idx, step0), False)
        if gated:
            new_vel = min(127, int(round(ev.vel * profile.velocity_scale)))
            new_dur = max(1, int(round(ev.dur_tick * profile.length_scale)))
            out.append(MidiEvent(note=ev.note, vel=new_vel, start_abs_tick=ev.start_abs_tick, dur_tick=new_dur, channel=ev.channel))
        else:
            out.append(ev)
    return out

