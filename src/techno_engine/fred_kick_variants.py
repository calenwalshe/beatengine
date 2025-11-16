from __future__ import annotations

from typing import List, Tuple
import random

from .midi_writer import MidiEvent, CCEvent, write_midi_with_controls
from .fred_spec import Spec, build_song, _ducking_cc
from .timebase import ticks_per_bar, ms_to_ticks


def _split_kick_other(events: List[MidiEvent]) -> Tuple[List[MidiEvent], List[MidiEvent]]:
    kicks = [e for e in events if e.note == 36]
    other = [e for e in events if e.note != 36]
    return kicks, other


def _ensure_quarter_presence(kicks: List[MidiEvent], ppq: int, bars: int) -> None:
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    base_positions = [0, 4, 8, 12]
    by_bar: dict[int, List[int]] = {}
    for ev in kicks:
        b = ev.start_abs_tick // bar_ticks
        pos = int((ev.start_abs_tick % bar_ticks) // step)
        by_bar.setdefault(b, []).append(pos)
    for b in range(bars):
        present = set(by_bar.get(b, []))
        for base in base_positions:
            if base not in present:
                t = b * bar_ticks + base * step
                kicks.append(MidiEvent(note=36, vel=110, start_abs_tick=t, dur_tick=step // 2, channel=9))


def _vary_ghost_pre(kicks: List[MidiEvent], ppq: int, bars: int, rng: random.Random) -> List[MidiEvent]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    out = kicks[:]
    for ev in kicks:
        # one 32nd before
        t = ev.start_abs_tick - step // 2
        if t < (ev.start_abs_tick // bar_ticks) * bar_ticks:
            continue
        if rng.random() < 0.55:
            out.append(MidiEvent(note=36, vel=max(60, ev.vel - 40), start_abs_tick=t, dur_tick=max(1, ev.dur_tick // 2), channel=ev.channel))
    _ensure_quarter_presence(out, ppq, bars)
    return out


def _vary_late_push(kicks: List[MidiEvent], ppq: int, bpm: float, bars: int, rng: random.Random) -> List[MidiEvent]:
    bar_ticks = ticks_per_bar(ppq, 4)
    out: List[MidiEvent] = []
    # pick one kick per bar to push late by ~8-16ms
    for b in range(bars):
        # collect kicks in this bar
        bar_k = [e for e in kicks if (e.start_abs_tick // bar_ticks) == b]
        if not bar_k:
            continue
        idx = rng.randrange(len(bar_k))
        for j, ev in enumerate(bar_k):
            if j == idx:
                ms = rng.uniform(8.0, 16.0)
                out.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=ev.start_abs_tick + ms_to_ticks(ms, ppq, bpm), dur_tick=ev.dur_tick, channel=ev.channel))
            else:
                out.append(ev)
    _ensure_quarter_presence(out, ppq, bars)
    return out


def _vary_displace_inside_quarter(kicks: List[MidiEvent], ppq: int, bars: int, rng: random.Random) -> List[MidiEvent]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    out: List[MidiEvent] = []
    base_positions = [0, 4, 8, 12]
    for b in range(bars):
        target_quarter = rng.choice([0, 1, 2, 3])  # which of the four beats to tweak
        shifted = False
        for ev in [e for e in kicks if (e.start_abs_tick // bar_ticks) == b]:
            pos = int((ev.start_abs_tick % bar_ticks) // step)
            q = pos // 4
            if not shifted and q == target_quarter and rng.random() < 0.7:
                # move to pos+2 within the quarter (stay in-bounds)
                new_pos = min(q * 4 + 3, pos + 2)
                new_t = b * bar_ticks + new_pos * step
                out.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=new_t, dur_tick=ev.dur_tick, channel=ev.channel))
                shifted = True
            else:
                out.append(ev)
        # ensure at least one hit in the chosen quarter
        window_start = b * bar_ticks + target_quarter * 4 * step
        window_end = window_start + 4 * step
        has_in_q = any(window_start <= e.start_abs_tick < window_end for e in out if (e.start_abs_tick // bar_ticks) == b)
        if not has_in_q:
            pos = target_quarter * 4
            out.append(MidiEvent(note=36, vel=110, start_abs_tick=b * bar_ticks + pos * step, dur_tick=step // 2, channel=9))
    _ensure_quarter_presence(out, ppq, bars)
    return out


def build_kick_variants(out_prefix: str, spec: Spec | None = None, seed_base: int = 9701, count: int = 3, heavy_duck: bool = True) -> List[str]:
    spec = spec or Spec()
    outs: List[str] = []
    modes = ["ghost_pre", "late_push", "displace"]
    for i in range(min(count, len(modes))):
        seed = seed_base + i
        rng = random.Random(seed)
        notes, mel_cc = build_song(spec, seed=seed)
        # collect kicks and others
        kicks, others = _split_kick_other(notes)
        if modes[i] == "ghost_pre":
            new_kicks = _vary_ghost_pre(kicks, ppq=spec.ppq, bars=spec.bars, rng=rng)
        elif modes[i] == "late_push":
            new_kicks = _vary_late_push(kicks, ppq=spec.ppq, bpm=spec.bpm, bars=spec.bars, rng=rng)
        else:
            new_kicks = _vary_displace_inside_quarter(kicks, ppq=spec.ppq, bars=spec.bars, rng=rng)

        # Recompose
        combined = others + new_kicks

        # Apply ducking (heavy optional): replace default ducks
        ccs: List[CCEvent] = []  # type: ignore[name-defined]
        if heavy_duck:
            ccs += _ducking_cc(spec, channel=2, depth=90)
            ccs += _ducking_cc(spec, channel=1, depth=115)
            ccs += _ducking_cc(spec, channel=3, depth=75)
        ccs += mel_cc

        out_path = f"{out_prefix}_{i+1:02d}_{modes[i]}.mid"
        write_midi_with_controls(notes=combined, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        outs.append(out_path)
    return outs


def _kicks_by_bar_quarter(kicks: List[MidiEvent], ppq: int, bars: int) -> List[List[MidiEvent]]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    grouped: List[List[MidiEvent]] = [[None, None, None, None] for _ in range(bars)]  # type: ignore
    for ev in kicks:
        b = ev.start_abs_tick // bar_ticks
        if b < 0 or b >= bars:
            continue
        pos = int((ev.start_abs_tick % bar_ticks) // step)
        q = max(0, min(3, pos // 4))
        # pick earliest within quarter
        if grouped[b][q] is None or ev.start_abs_tick < grouped[b][q].start_abs_tick:  # type: ignore
            grouped[b][q] = ev
    # fill any missing with synthetic beat kicks at quarter start
    for b in range(bars):
        bar_start = b * bar_ticks
        for q in range(4):
            if grouped[b][q] is None:  # type: ignore
                t = bar_start + q * 4 * step
                grouped[b][q] = MidiEvent(note=36, vel=110, start_abs_tick=t, dur_tick=step // 2, channel=9)
    return grouped  # type: ignore


def _apply_quarter_offsets(grouped: List[List[MidiEvent]], ppq: int, bpm: float, offsets: List[Tuple[int,int,int,int]], micros_ms: List[Tuple[float,float,float,float]]) -> List[MidiEvent]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    out: List[MidiEvent] = []
    bars = len(grouped)
    for b in range(bars):
        offs = offsets[min(b, len(offsets)-1)]
        mics = micros_ms[min(b, len(micros_ms)-1)]
        for q in range(4):
            ev = grouped[b][q]
            base_t = b * bar_ticks + q * 4 * step
            o = max(0, min(3, int(offs[q])))
            micro = int(ms_to_ticks(float(mics[q]), ppq, bpm))
            new_t = base_t + o * step + micro
            out.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=new_t, dur_tick=ev.dur_tick, channel=ev.channel))
    # ensure sorted order
    out.sort(key=lambda e: e.start_abs_tick)
    return out


def build_kick_density_preserving_variants(out_prefix: str, spec: Spec | None = None, seed_base: int = 9801, heavy_duck: bool = True) -> List[str]:
    """Produce three options where each bar keeps exactly 4 kicks (one per quarter)
    but adjusts their placements mildly inside the quarter or via micro.
    """
    spec = spec or Spec()
    outs: List[str] = []
    names = ["inside_step", "third_beat_shift", "micro_pull"]
    # Patterns repeat every bar; can be varied later per-bar if needed
    inside_offsets = [(0,1,0,1)] * spec.bars
    inside_micros = [(-2.0, 0.0, -2.0, 0.0)] * spec.bars

    third_offsets = [(0,0,2,0)] * spec.bars
    third_micros = [(0.0, 0.0, 4.0, 0.0)] * spec.bars

    micro_offsets = [(0,0,0,0)] * spec.bars
    micro_micros = [(-10.0, -6.0, -8.0, -6.0)] * spec.bars

    patterns = list(zip(names, [inside_offsets, third_offsets, micro_offsets], [inside_micros, third_micros, micro_micros]))

    for i, (name, off_pat, mic_pat) in enumerate(patterns, start=1):
        seed = seed_base + i
        notes, mel_cc = build_song(spec, seed=seed)
        kicks, others = _split_kick_other(notes)
        grouped = _kicks_by_bar_quarter(kicks, ppq=spec.ppq, bars=spec.bars)
        new_kicks = _apply_quarter_offsets(grouped, ppq=spec.ppq, bpm=spec.bpm, offsets=off_pat, micros_ms=mic_pat)
        combined = others + new_kicks
        ccs: List[CCEvent] = []  # type: ignore[name-defined]
        if heavy_duck:
            ccs += _ducking_cc(spec, channel=2, depth=90)
            ccs += _ducking_cc(spec, channel=1, depth=115)
            ccs += _ducking_cc(spec, channel=3, depth=70)
        ccs += mel_cc
        out_path = f"{out_prefix}_{i:02d}_{name}.mid"
        write_midi_with_controls(notes=combined, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        outs.append(out_path)
    return outs
