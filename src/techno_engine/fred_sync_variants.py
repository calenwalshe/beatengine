from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
import random

from .fred_spec import Spec, _build_drums, _build_chords, _build_bass, _ducking_cc
from .midi_writer import MidiEvent, CCEvent, PitchBendEvent, write_midi_with_controls
from .timebase import ticks_per_bar


@dataclass
class SyncParams:
    swing_melody: float = 0.61
    swing_bass: float = 0.60
    bass_density: float = 0.48
    glide_prob: float = 0.35
    glide_range_semitones: int = 2  # assumed synth pitch bend range


def _nearest_in_scale(p: int, pcs: Sequence[int]) -> int:
    tgt = p % 12
    if tgt in pcs:
        return p
    for d in range(1, 3):
        if (p + d) % 12 in pcs:
            return p + d
        if (p - d) % 12 in pcs:
            return p - d
    return p


def _b_minor_pcs() -> List[int]:
    # B natural minor: B C# D E F# G A
    return [11, 1, 2, 4, 6, 7, 9]


def _build_melody_syncopated(spec: Spec, rng: random.Random, params: SyncParams) -> Tuple[List[MidiEvent], List[CCEvent], List[PitchBendEvent]]:
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    swing = params.swing_melody

    base_line = [62, 64, 66, 69]  # D4, E4, F#4, A4
    pcs = _b_minor_pcs()

    events: List[MidiEvent] = []
    cc: List[CCEvent] = []
    pb: List[PitchBendEvent] = []

    def place(bar: int, s: int, dur_steps: float, note: int, vel: int) -> int:
        start = bar * bar_ticks + s * step
        if s % 2 == 1:
            start += int(round((swing - 0.5) * step))
        dur = max(1, int(round(dur_steps * step)))
        n = _nearest_in_scale(note, pcs)
        events.append(MidiEvent(note=n, vel=vel, start_abs_tick=start, dur_tick=dur, channel=3))
        cc.append(CCEvent(cc=74, value=max(0, min(127, vel)), tick=start, channel=3))
        return start

    def add_glide(start_tick: int, span_ticks: int, semitones: int) -> None:
        # Simple linear glide via pitch wheel. Assume ±2 semitone range.
        rng_span = max(1, span_ticks)
        # Normalize semitones into wheel range
        max_semi = max(1, params.glide_range_semitones)
        target = int(max(-8192, min(8191, int(8191 * (semitones / max_semi)))))
        # Three-point ramp: 0 -> target -> 0
        pb.append(PitchBendEvent(pitch=0, tick=start_tick, channel=3))
        pb.append(PitchBendEvent(pitch=target, tick=start_tick + rng_span // 2, channel=3))
        pb.append(PitchBendEvent(pitch=0, tick=start_tick + rng_span - 1, channel=3))

    # Syncopated step pools
    call_steps = [0, 3, 7, 10]
    resp_steps = [2, 5, 6, 9, 11, 14, 15]

    prev_note = None
    prev_on = None
    for bar in range(bars):
        is_call = (bar % 2 == 0)
        steps = call_steps if is_call else resp_steps
        for i, s in enumerate(steps):
            base = base_line[(i + bar) % len(base_line)]
            # Occasional octave lift on responses
            if not is_call and (i % 4 == 0) and rng.random() < 0.35:
                base += 12
            vel = int(rng.uniform(56, 120))
            dur = 0.5 if is_call else (0.375 if (i % 3 == 0) else 0.5)
            on = place(bar, s, dur, base, vel)
            # Glide from previous note with some probability
            if prev_note is not None and prev_on is not None and rng.random() < params.glide_prob:
                semi = (base - prev_note)
                # Limit glides to small intervals to keep musical
                if abs(semi) <= params.glide_range_semitones:
                    add_glide(prev_on, on - prev_on, semi)
            prev_note = base
            prev_on = on

    return events, cc, pb


def build_song_sync_variant(spec: Spec, seed: int, heavy_duck: bool = True, params: SyncParams | None = None):
    rng = random.Random(seed)
    params = params or SyncParams()
    # Base drums unchanged for continuity
    drums = _build_drums(spec, rng)
    # Chords unchanged (long pads) for pumping context
    chords = _build_chords(spec, rng)
    # Slightly denser bass with same engine
    bass = _build_bass(Spec(bpm=spec.bpm, ppq=spec.ppq, bars=spec.bars, swing_percent=params.swing_bass), drums)
    # Melody: syncopated with occasional glides
    mel, mel_cc, pb = _build_melody_syncopated(spec, rng, params)

    notes: List[MidiEvent] = []
    notes.extend(drums)
    notes.extend(chords)
    notes.extend(bass)
    notes.extend(mel)

    # Ducking envelopes
    cc: List[CCEvent] = []
    if heavy_duck:
        cc += _ducking_cc(spec, channel=2, depth=90)
        cc += _ducking_cc(spec, channel=1, depth=110)
        cc += _ducking_cc(spec, channel=3, depth=70)
    cc += mel_cc
    return notes, cc, pb


def render_sync_variants(out_prefix: str, spec: Spec | None = None, seed_base: int = 9301, count: int = 3,
                         heavy_duck: bool = True) -> List[str]:
    spec = spec or Spec()
    outs: List[str] = []
    for i in range(count):
        seed = seed_base + i
        notes, cc, pb = build_song_sync_variant(spec, seed=seed, heavy_duck=heavy_duck)
        out_path = f"{out_prefix}_{i+1:02d}.mid"
        write_midi_with_controls(notes=notes, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=cc, pitch_bends=pb)
        outs.append(out_path)
    return outs

