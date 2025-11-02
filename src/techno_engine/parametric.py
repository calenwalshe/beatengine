from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .euclid import bjorklund, rotate
from .micro import apply_swing_and_micro, sample_beat_bin
from .midi_writer import MidiEvent
from .timebase import ticks_per_bar


@dataclass
class LayerConfig:
    steps: int = 16
    fills: int = 8
    rot: int = 0
    note: int = 42
    velocity: int = 80
    swing_percent: Optional[float] = None
    beat_bins_ms: Optional[List[float]] = None
    beat_bins_probs: Optional[List[float]] = None
    beat_bin_cap_ms: Optional[float] = None
    micro_ms: float = 0.0
    offbeats_only: bool = False
    ratchet_prob: float = 0.0
    ratchet_repeat: int = 2
    choke_with_note: Optional[int] = None


def build_layer(
    bpm: float,
    ppq: int,
    bars: int,
    cfg: LayerConfig,
    rng: Optional[random.Random] = None,
    closed_hat_ticks_by_bar: Optional[Dict[int, List[int]]] = None,
) -> List[MidiEvent]:
    rng = rng or random
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = (bar_ticks * 16) // cfg.steps // 16  # per-16th-equivalent grid

    base = bjorklund(cfg.steps, cfg.fills)
    mask = rotate(base, cfg.rot)
    events: List[MidiEvent] = []

    for bar in range(bars):
        bar_start = bar * bar_ticks
        for step in range(cfg.steps):
            if mask[step] == 0:
                continue
            # optional offbeats-only mask (for open hat)
            if cfg.offbeats_only and step % 4 != 2:
                continue
            base_tick = bar_start + int(round(step * (bar_ticks / cfg.steps)))

            # micro via beat-bins or constant micro_ms
            micro_ms = cfg.micro_ms
            if cfg.beat_bins_ms and cfg.beat_bins_probs:
                micro_ms = sample_beat_bin(cfg.beat_bins_ms, cfg.beat_bins_probs, rng)

            start_tick = apply_swing_and_micro(
                step_idx=step,
                base_tick=base_tick,
                swing_percent=cfg.swing_percent,
                micro_ms=micro_ms,
                bpm=bpm,
                ppq=ppq,
                cap_ms=cfg.beat_bin_cap_ms,
            )

            # nominal duration: 1/2 step
            dur = max(1, int(round((bar_ticks / cfg.steps) * 0.5)))

            # ratchets: split duration into repeats
            if cfg.ratchet_prob > 0 and rng.random() < cfg.ratchet_prob:
                rep = max(2, cfg.ratchet_repeat)
                sub = max(1, dur // rep)
                for r in range(rep):
                    t = start_tick + r * sub
                    events.append(MidiEvent(note=cfg.note, vel=cfg.velocity, start_abs_tick=t, dur_tick=sub))
            else:
                events.append(MidiEvent(note=cfg.note, vel=cfg.velocity, start_abs_tick=start_tick, dur_tick=dur))

    # Choke behavior: if this layer is to be choked by a closed-hat note,
    # truncate events that overlap the next closed-hat onset in the same bar.
    if cfg.choke_with_note is not None and closed_hat_ticks_by_bar:
        ch_note = cfg.choke_with_note
        # Build a list by bar of next choke tick after each event
        adjusted: List[MidiEvent] = []
        for ev in events:
            bar_idx = ev.start_abs_tick // bar_ticks
            choke_ticks = closed_hat_ticks_by_bar.get(bar_idx, [])
            next_choke = None
            for ct in choke_ticks:
                if ct > ev.start_abs_tick:
                    next_choke = ct
                    break
            if next_choke is not None:
                new_dur = min(ev.dur_tick, max(1, next_choke - ev.start_abs_tick))
                adjusted.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=ev.start_abs_tick, dur_tick=new_dur, channel=ev.channel))
            else:
                adjusted.append(ev)
        events = adjusted

    return events


def collect_closed_hat_ticks(events: List[MidiEvent], ppq: int, closed_hat_note: int = 42) -> Dict[int, List[int]]:
    """Return mapping bar_idx -> sorted list of closed-hat onset ticks."""
    bar_ticks = ticks_per_bar(ppq, 4)
    by_bar: Dict[int, List[int]] = {}
    for ev in events:
        if ev.note != closed_hat_note:
            continue
        b = ev.start_abs_tick // bar_ticks
        by_bar.setdefault(b, []).append(ev.start_abs_tick)
    for b in by_bar:
        by_bar[b].sort()
    return by_bar


def compute_dispersion(events: List[MidiEvent], ppq: int, note: int) -> float:
    """Compute normalized IOI variance for a note layer across the whole clip."""
    # Collect onset ticks for this note
    ticks = sorted(ev.start_abs_tick for ev in events if ev.note == note)
    if len(ticks) < 3:
        return 0.0
    iois = [b - a for a, b in zip(ticks[:-1], ticks[1:])]
    mean = sum(iois) / len(iois)
    if mean <= 0:
        return 0.0
    var = sum((x - mean) ** 2 for x in iois) / len(iois)
    # normalize by mean^2 to make it scale-independent
    return var / (mean * mean)

