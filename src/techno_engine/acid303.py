from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
import random

from .midi_writer import MidiEvent, CCEvent, PitchBendEvent, write_midi_with_controls
from .fred_spec import Spec, _build_drums
from .timebase import ticks_per_bar


@dataclass
class AcidParams:
    channel: int = 4  # channel 5 one-indexed
    root: int = 47    # B2
    pool: Sequence[int] = (0, 2, 3, 5, 7, 10)  # minor-ish intervals
    octave_prob: float = 0.25
    rest_prob: float = 0.15
    accent_prob: float = 0.45
    slide_prob: float = 0.35
    gate_lo: float = 0.35
    gate_hi: float = 0.75
    cutoff_base: int = 78
    cutoff_accent: int = 115
    resonance: int = 100
    bend_semitones: int = 2  # synth bend range assumed


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _bend_for_semi(semi: int, bend_range: int) -> int:
    # Map semitone to 14-bit pitch wheel value (-8192..8191)
    semi = max(-bend_range, min(bend_range, semi))
    return int(max(-8192, min(8191, round(8191 * (semi / max(1, bend_range))))))


def generate_acid(spec: Spec, seed: int = 1203, params: AcidParams | None = None) -> Tuple[List[MidiEvent], List[CCEvent], List[PitchBendEvent]]:
    rng = random.Random(seed)
    p = params or AcidParams()
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16

    notes: List[MidiEvent] = []
    ccs: List[CCEvent] = []
    pbs: List[PitchBendEvent] = []

    def add_note(bar: int, s: int, dur_steps: float, note: int, vel: int, accent: bool) -> int:
        start = bar * bar_ticks + s * step
        dur = max(1, int(round(dur_steps * step)))
        n = _clamp(note, 24, 96)
        notes.append(MidiEvent(note=n, vel=vel, start_abs_tick=start, dur_tick=dur, channel=p.channel))
        cc74 = _clamp(int(p.cutoff_base if not accent else p.cutoff_accent), 0, 127)
        ccs.append(CCEvent(cc=74, value=cc74, tick=start, channel=p.channel))
        return start

    # Set a high resonance at start (many 303 emus listen to CC71)
    ccs.append(CCEvent(cc=71, value=_clamp(p.resonance, 0, 127), tick=0, channel=p.channel))

    prev_note = None
    prev_on = None
    for bar in range(bars):
        for s in range(16):
            # occasional rests
            if rng.random() < p.rest_prob:
                prev_note = None
                prev_on = None
                continue
            interval = rng.choice(p.pool)
            note = p.root + interval
            if rng.random() < p.octave_prob:
                note += 12 if rng.random() < 0.5 else -12
            accent = rng.random() < p.accent_prob
            gate = rng.uniform(p.gate_lo, p.gate_hi)
            vel = 96 if accent else 80
            on = add_note(bar, s, gate, note, vel, accent)
            if prev_note is not None and prev_on is not None and rng.random() < p.slide_prob:
                semi = note - prev_note
                if abs(semi) <= p.bend_semitones:
                    # glide from prev to current over the rest of the interval
                    pbs.append(PitchBendEvent(pitch=0, tick=prev_on, channel=p.channel))
                    span = max(1, on - prev_on)
                    pbs.append(PitchBendEvent(pitch=_bend_for_semi(semi, p.bend_semitones), tick=prev_on + span // 2, channel=p.channel))
                    pbs.append(PitchBendEvent(pitch=0, tick=on - 1, channel=p.channel))
            prev_note = note
            prev_on = on

        # small end-of-bar flourish: raise cutoff briefly
        ccs.append(CCEvent(cc=74, value=_clamp(p.cutoff_accent - 5, 0, 127), tick=(bar+1) * bar_ticks - step, channel=p.channel))

    return notes, ccs, pbs


def render_303_over_drums(out_path: str, spec: Spec | None = None, seed: int = 1203, drum_seed: int = 6061, params: AcidParams | None = None) -> None:
    spec = spec or Spec()
    rng = random.Random(drum_seed)
    drums = _build_drums(spec, rng)
    acid_notes, acid_ccs, acid_pbs = generate_acid(spec, seed=seed, params=params)

    notes = drums + acid_notes
    ccs = [CCEvent(cc=91, value=24, tick=0, channel=9)] + acid_ccs
    write_midi_with_controls(notes=notes, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs, pitch_bends=acid_pbs)

