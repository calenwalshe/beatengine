from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .timebase import ticks_per_bar
from .midi_writer import MidiEvent


@dataclass(frozen=True)
class Notes:
    kick: int = 36
    hat_c: int = 42
    snare: int = 38
    clap: int = 39


def _bar_and_step_ticks(ppq: int) -> Tuple[int, int]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    return bar_ticks, step_ticks


def build_backbone_events(bpm: float, ppq: int, bars: int, notes: Dict[str, int] | None = None) -> List[MidiEvent]:
    """
    Deterministic backbone per M1:
      - Kick: 4/4 (steps 0,4,8,12)
      - Hat-C: straight 16ths (0..15)
      - Snare & Clap: backbeats (steps 4,12)
    """
    n = Notes()
    if notes:
        n = Notes(
            kick=int(notes.get("kick", n.kick)),
            hat_c=int(notes.get("hat_c", n.hat_c)),
            snare=int(notes.get("snare", n.snare)),
            clap=int(notes.get("clap", n.clap)),
        )

    bar_ticks, step_ticks = _bar_and_step_ticks(ppq)
    events: List[MidiEvent] = []

    # Velocity choices
    hat_pattern = [80, 65, 75, 65]  # staircase per 4 steps
    kick_vel = 110
    snare_vel = 96
    clap_vel = 96
    dur = max(1, step_ticks // 2)

    for bar in range(bars):
        bar_start = bar * bar_ticks
        # Kick 4/4
        for step in (0, 4, 8, 12):
            t = bar_start + step * step_ticks
            events.append(MidiEvent(note=n.kick, vel=kick_vel, start_abs_tick=t, dur_tick=dur))
        # Hats 16ths
        for step in range(16):
            t = bar_start + step * step_ticks
            vel = hat_pattern[step % 4]
            events.append(MidiEvent(note=n.hat_c, vel=vel, start_abs_tick=t, dur_tick=dur))
        # Backbeats (snare + clap) on 2 and 4
        for step in (4, 12):
            t = bar_start + step * step_ticks
            events.append(MidiEvent(note=n.snare, vel=snare_vel, start_abs_tick=t, dur_tick=dur))
            events.append(MidiEvent(note=n.clap, vel=clap_vel, start_abs_tick=t, dur_tick=dur))

    return events


def _steps_from_events(events: List[MidiEvent], ppq: int) -> Dict[str, List[int]]:
    """Utility: bucket event start steps per note name for 16-step grid.
    Returns dict keyed by synthetic names (kick, hat_c, snare, clap) when possible.
    """
    # Reverse lookup by GM-808 defaults
    note2name = {36: "kick", 42: "hat_c", 38: "snare", 39: "clap"}
    bar_ticks, step_ticks = _bar_and_step_ticks(ppq)
    out: Dict[str, List[int]] = {"kick": [], "hat_c": [], "snare": [], "clap": []}
    for ev in events:
        name = note2name.get(ev.note)
        if not name:
            continue
        step_in_bar = (ev.start_abs_tick % bar_ticks) // step_ticks
        out[name].append(int(step_in_bar))
    return out


def compute_E_S(events: List[MidiEvent], ppq: int) -> Tuple[float, float]:
    """
    Minimal entrainment (E) and syncopation (S) metrics for M1 checks.
    - E: average regularity on 4-beat and 16th grids on union of {kick, hat_c}.
         For this deterministic backbone, this evaluates to 1.0.
    - S: average of per-step syncopation weights on the union across all layers,
         with weights: beat=0.0, offbeat=0.25, other=0.5, yielding ~0.3125 here.
    """
    buckets = _steps_from_events(events, ppq)
    # Build union masks per bar for 16 steps (assume consistent across bars)
    union_beat_layers = set(buckets["kick"]) | set(buckets["hat_c"])
    # Regularity on 4-beat grid: all beats must be present
    beats = {0, 4, 8, 12}
    has_all_beats = beats.issubset(union_beat_layers)
    # Regularity on 16th grid: presence on all 16 steps
    has_all_16 = len(union_beat_layers) == 16

    E = 0.0
    if has_all_beats and has_all_16:
        E = 1.0
    elif has_all_beats:
        E = 0.75
    elif has_all_16:
        E = 0.9
    else:
        E = 0.5

    # Syncopation S via weighted average on union across all layers
    union_all = set(buckets["kick"]) | set(buckets["hat_c"]) | set(buckets["snare"]) | set(buckets["clap"])
    weights = {"beat": 0.0, "off": 0.25, "other": 0.5}
    def step_class(i: int) -> str:
        if i in beats:
            return "beat"
        if i in {2, 6, 10, 14}:
            return "off"
        return "other"

    if union_all:
        s_val = sum(weights[step_class(i)] for i in union_all) / 16.0
    else:
        s_val = 0.0
    S = max(0.0, min(1.0, s_val))
    return E, S

