from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .midi_writer import MidiEvent
from .timebase import ticks_per_bar


@dataclass
class SyncWeights:
    kick_penalty: float = 1.0
    hat_bonus: float = 0.5
    clap_bonus: float = 0.7
    near_window: int = 1  # adjacency window in 16th steps for bonuses/penalties


def score_steps(
    steps: int,
    kick_mask: Sequence[int],
    hat_mask: Sequence[int],
    clap_mask: Sequence[int],
    w: SyncWeights,
) -> List[float]:
    """Compute per-step scores: bonus for aligning near hats/claps, penalty for kick collisions.

    Scores are linear and can be used for greedy selection.
    """
    def near(idx: int, mask: Sequence[int]) -> bool:
        if w.near_window <= 0:
            return bool(mask[idx])
        for d in range(-w.near_window, w.near_window + 1):
            j = (idx + d) % steps
            if mask[j]:
                return True
        return False

    scores: List[float] = [0.0] * steps
    for i in range(steps):
        s = 0.0
        if kick_mask[i]:
            s -= w.kick_penalty
        if near(i, hat_mask):
            s += w.hat_bonus
        if near(i, clap_mask):
            s += w.clap_bonus
        scores[i] = s
    return scores


def select_steps_by_score(scores: Sequence[float], forbidden: Iterable[int], k: int) -> List[int]:
    """Pick k step indices with highest scores, skipping forbidden steps."""
    forb = set(int(x) for x in forbidden)
    idx = [i for i, _ in sorted(enumerate(scores), key=lambda t: (-t[1], t[0]))]
    out: List[int] = []
    for i in idx:
        if i in forb:
            continue
        out.append(i)
        if len(out) >= k:
            break
    return out


def make_prekick_ghosts(
    bpm: float,
    ppq: int,
    bars: int,
    kick_steps: Sequence[int] = (0, 4, 8, 12),
    note: int = 45,
    vel: int = 70,
    channel: int = 1,
) -> List[MidiEvent]:
    """Create pre-kick ghost notes one 32nd before each kick; end strictly before kick.

    Duration equals half a 16th minus 1 tick to guarantee end < kick tick.
    """
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    half_step_ticks = step_ticks // 2
    ev: List[MidiEvent] = []
    for bar in range(bars):
        base = bar * bar_ticks
        for ks in kick_steps:
            kick_t = base + ks * step_ticks
            start = kick_t - half_step_ticks
            dur = max(1, half_step_ticks - 1)
            ev.append(MidiEvent(note=note, vel=vel, start_abs_tick=start, dur_tick=dur, channel=channel))
    return ev
