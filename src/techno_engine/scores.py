from __future__ import annotations

import math
from statistics import median
from typing import Dict, Iterable, List, Sequence, Tuple

from .midi_writer import MidiEvent
from .timebase import ticks_per_bar


def steps_in_bar(events: Iterable[MidiEvent], ppq: int, steps: int = 16) -> List[int]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // steps
    out = []
    for ev in events:
        s = (ev.start_abs_tick % bar_ticks) // step_ticks
        out.append(int(s))
    return out


def union_mask_for_bar(events: Iterable[MidiEvent], ppq: int, steps: int = 16) -> List[int]:
    mask = [0] * steps
    for s in steps_in_bar(events, ppq, steps):
        if 0 <= s < steps:
            mask[s] = 1
    return mask


def compute_E_S_from_mask(mask: Sequence[int]) -> Tuple[float, float]:
    steps = len(mask)
    # E: average regularity on 4-beat and 16th grids
    beats = [0, steps // 4, steps // 2, 3 * steps // 4]
    has_all_beats = all(mask[i] == 1 for i in beats)
    has_all_16 = sum(mask) == steps
    if has_all_beats and has_all_16:
        E = 1.0
    elif has_all_beats:
        E = 0.9
    elif has_all_16:
        E = 0.85
    else:
        # weight by presence on beats with a higher floor to prefer entrainment
        E = 0.7 + 0.3 * (sum(mask[i] for i in beats) / 4.0)

    # S: weighted average by tier (beat=0.0, off=0.25, other=0.5), normalized to [0,1]
    offbeats = {steps // 8, 3 * steps // 8, 5 * steps // 8, 7 * steps // 8}
    weights = {"beat": 0.0, "off": 0.4, "other": 0.65}
    total = 0.0
    active = 0
    for i, v in enumerate(mask):
        if not v:
            continue
        active += 1
        if i in beats:
            total += weights["beat"]
        elif i in offbeats:
            total += weights["off"]
        else:
            total += weights["other"]
    S = (total / active) if active > 0 else 0.0
    return (max(0.0, min(1.0, E)), max(0.0, min(1.0, S)))


def shannon_entropy(mask: Sequence[int]) -> float:
    # Bernoulli entropy normalized by max 1 bit
    n = len(mask)
    p = sum(mask) / max(1, n)
    if p in (0.0, 1.0):
        return 0.0
    return - (p * math.log2(p) + (1 - p) * math.log2(1 - p))


def entropy_from_mask(mask: Sequence[int]) -> float:
    return shannon_entropy(mask)


def micro_offsets_ms_for_layer(events: List[MidiEvent], ppq: int, bpm: float, note: int, steps: int = 16) -> List[float]:
    """Approximate per-event micro offsets by comparing to nearest 16th grid point.
    Includes swing contribution; suitable for RMS checks against caps.
    """
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // steps
    tps = (ppq * bpm) / 60_000  # ticks per ms
    ms: List[float] = []
    for ev in events:
        if ev.note != note:
            continue
        b = ev.start_abs_tick // bar_ticks
        within = ev.start_abs_tick - b * bar_ticks
        # nearest step boundary in this and neighboring bars to guard rounding
        candidates = []
        for bb in (b - 1, b, b + 1):
            base = bb * bar_ticks
            for i in range(steps):
                candidates.append(base + i * step_ticks)
        nominal = min(candidates, key=lambda t: abs(ev.start_abs_tick - t))
        delta_ticks = ev.start_abs_tick - nominal
        ms.append(delta_ticks / tps)
    return ms


def rms(vals: Sequence[float]) -> float:
    if not vals:
        return 0.0
    return math.sqrt(sum(v * v for v in vals) / len(vals))


def compute_scores_by_bar(layers: Dict[str, List[MidiEvent]], ppq: int, bpm: float) -> Dict[str, List[Tuple[float, float]]]:
    """Return per-bar (E,S) for the union across layers and per-layer micro RMS."""
    # Build per-bar event lists
    bar_ticks = ticks_per_bar(ppq, 4)
    by_bar: Dict[int, List[MidiEvent]] = {}
    for name, evs in layers.items():
        for ev in evs:
            b = ev.start_abs_tick // bar_ticks
            by_bar.setdefault(b, []).append(ev)

    # Compute E,S per bar on union
    bars = sorted(by_bar.keys())
    es: List[Tuple[float, float]] = []
    for b in bars:
        mask = union_mask_for_bar(by_bar[b], ppq)
        E, S = compute_E_S_from_mask(mask)
        es.append((E, S))
    return {"union": es}
