from __future__ import annotations

"""
Fred-again style groove builder per user spec.

Generates:
 - Drums: 4-on-floor kick, offbeat hats with micro/pitch-ish variety, clap/snare backbeats, ghost rims.
 - Bass: scored against drums with swing; heavy sidechain (via CC11 Expression) to kick.
 - Chords: 4-chord, 2-bar each (8 bars total); subtle sidechain.
 - Melody: call/response with strong swing and velocity-driven brightness (via CC74 per note).

All timing uses absolute ticks; swing ~0.60 by default. MIDI channels:
  drums=9 (GM channel 10), bass=1, chords=2, melody=3.
"""

from dataclasses import dataclass
from typing import List, Sequence, Tuple
import random

from .midi_writer import MidiEvent, CCEvent, write_midi_with_controls
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks, apply_choke
from .scores import union_mask_for_bar
from .bassline import generate_scored
from .timebase import ticks_per_bar, ms_to_ticks


@dataclass
class Spec:
    bpm: float = 120.0
    ppq: int = 1920
    bars: int = 8
    swing_percent: float = 0.60  # 60% swing
    key_root_midi: int = 59  # B3 default


def _postprocess_hats(events: List[MidiEvent], ppq: int, bpm: float, rng: random.Random) -> List[MidiEvent]:
    """Randomize closed-hat flavour and length slightly.

    - Switch some 42->44 (pedal) to emulate pitch/character changes.
    - Nudge durations within 40–70% of a 16th.
    """
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    out: List[MidiEvent] = []
    for ev in events:
        if ev.note == 42:  # closed hat
            note = 44 if (rng.random() < 0.18) else 42
            # 2% chance open-hat on an offbeat
            if ((ev.start_abs_tick % bar_ticks) // step_ticks) % 4 == 2 and rng.random() < 0.02:
                note = 46
            # Dur range 40–70% 16th
            dur = int(round(step_ticks * rng.uniform(0.40, 0.70)))
            vel = max(50, min(115, int(round(random.gauss(ev.vel, 6)))))
            out.append(MidiEvent(note=note, vel=vel, start_abs_tick=ev.start_abs_tick, dur_tick=max(1, dur), channel=ev.channel))
        else:
            out.append(ev)
    # Choke any open-hats (46) at the next closed-hat tick
    ch_map = collect_closed_hat_ticks([e for e in out if e.note in (42, 44)], ppq, 42)
    out = apply_choke(out, ppq, ch_map)
    return out


def _build_drums(spec: Spec, rng: random.Random) -> List[MidiEvent]:
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    # Kick 4/4
    kick = LayerConfig(steps=16, fills=4, rot=0, note=36, velocity=116)
    # Closed hats on offbeats with strong swing and micro bins
    hatc = LayerConfig(
        steps=16, fills=16, offbeats_only=True, note=42, velocity=84,
        swing_percent=spec.swing_percent,
        beat_bins_ms=[-8, -4, 0, 4], beat_bins_probs=[0.35, 0.35, 0.25, 0.05], beat_bin_cap_ms=10
    )
    # Subtle open-hat ratchets on offbeats (choked later)
    hato = LayerConfig(
        steps=16, fills=16, offbeats_only=True, note=46, velocity=82,
        ratchet_prob=0.10, ratchet_repeat=3, swing_percent=spec.swing_percent,
        beat_bins_ms=[-2, 0, 2], beat_bins_probs=[0.3, 0.5, 0.2], beat_bin_cap_ms=10, choke_with_note=42
    )
    # Snare/clap backbeats (2 and 4)
    snare = LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=98)
    clap = LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)

    ev_k = build_layer(bpm, ppq, bars, kick, rng)
    ev_hc = build_layer(bpm, ppq, bars, hatc, rng)
    ch_map = collect_closed_hat_ticks(ev_hc, ppq, 42)
    ev_ho = build_layer(bpm, ppq, bars, hato, rng, closed_hat_ticks_by_bar=ch_map)
    ev_sn = build_layer(bpm, ppq, bars, snare, rng)
    ev_cl = build_layer(bpm, ppq, bars, clap, rng)

    # Ghost details: rims (37) near upbeat, light velocity and slight random micro in tick
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    ghosts: List[MidiEvent] = []
    for b in range(bars):
        bar_start = b * bar_ticks
        for step in (1, 5, 9, 13):  # between beats
            if rng.random() < 0.45:
                t = bar_start + step * step_ticks + int(round(rng.uniform(-0.12, 0.08) * step_ticks))
                ghosts.append(MidiEvent(note=37, vel=62, start_abs_tick=t, dur_tick=max(1, step_ticks // 3), channel=9))
        # occasional micro side-kick before beat 3 or 4
        for s in (7, 11, 15):
            if rng.random() < 0.25:
                t = bar_start + s * step_ticks + int(round(rng.uniform(-0.08, 0.05) * step_ticks))
                ghosts.append(MidiEvent(note=36, vel=70, start_abs_tick=t, dur_tick=max(1, step_ticks // 4), channel=9))

    drums = ev_k + _postprocess_hats(ev_hc, ppq, spec.bpm, rng) + ev_ho + ev_sn + ev_cl + ghosts
    return drums


def _build_chords(spec: Spec, rng: random.Random) -> List[MidiEvent]:
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    # 4 chords, 2 bars each -> 8 bars total
    # Progression in B minor flavour: Bm9, Gmaj7, Dmaj9, A6
    chords = [
        [59, 62, 66, 71],   # B3, D4, F#4, B4 (Bm9-ish without the 9 explicitly)
        [55, 62, 67, 71],   # G3, D4, G4, B4
        [57, 62, 69, 74],   # A3-> actually Dmaj9 flavour: D4(62), F#4(66) -> adjust to D/F# A...
        [57, 61, 69, 73],   # A3, C#4(61), A4(69), C#5(73) -> A6 colour
    ]
    # Correct Dmaj9 voicing to be warmer
    chords[2] = [50, 62, 66, 71]  # D3, D4, F#4, B4 (add9 colour via B)

    out: List[MidiEvent] = []
    for i, notes in enumerate(chords):
        start_bar = i * 2
        start_tick = start_bar * bar_ticks
        dur = bar_ticks * 2 - int(0.05 * bar_ticks)
        for n in notes:
            out.append(MidiEvent(note=n, vel=84, start_abs_tick=start_tick, dur_tick=dur, channel=2))
    return out


def _ducking_cc(spec: Spec, channel: int, depth: int) -> List[CCEvent]:
    """Generate CC11 Expression ducking envelopes keyed to each kick (every beat).

    depth: how low to dip from 127 (e.g., 50 for chords subtle, 90 for bass heavy).
    """
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    beat_ticks = ppq  # quarter note
    total_beats = bars * 4
    out: List[CCEvent] = []
    base = 127
    min_val = max(0, base - depth)
    # Ensure initial base
    out.append(CCEvent(cc=11, value=base, tick=0, channel=channel))
    for b in range(total_beats):
        t0 = b * beat_ticks
        # Attack: immediate dip on kick
        out.append(CCEvent(cc=11, value=min_val, tick=t0, channel=channel))
        # Release curve: 50ms -> 120ms -> 240ms back to base
        for ms, val in ((50, min_val + int(0.35 * (base - min_val))),
                        (120, min_val + int(0.70 * (base - min_val))),
                        (240, base)):
            out.append(CCEvent(cc=11, value=val, tick=t0 + ms_to_ticks(ms, ppq, bpm), channel=channel))
    # Final base reset at end
    out.append(CCEvent(cc=11, value=base, tick=bars * bar_ticks - 1, channel=channel))
    return out


def _build_bass(spec: Spec, drum_events: Sequence[MidiEvent]) -> List[MidiEvent]:
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    # Build per-bar masks for kick/hat/clap from drum events
    def filter_note(evs: Sequence[MidiEvent], note: int) -> list[MidiEvent]:
        return [e for e in evs if e.note == note]
    bar_ticks = ticks_per_bar(ppq, 4)
    kick_mask_by_bar = []
    hat_mask_by_bar = []
    clap_mask_by_bar = []
    for b in range(bars):
        start = b * bar_ticks
        end = start + bar_ticks
        slice_evs = [e for e in drum_events if start <= e.start_abs_tick < end]
        kick_mask_by_bar.append(union_mask_for_bar(filter_note(slice_evs, 36), ppq))
        hat_evs = filter_note(slice_evs, 42) + filter_note(slice_evs, 46)
        hat_mask_by_bar.append(union_mask_for_bar(hat_evs, ppq))
        clap_mask_by_bar.append(union_mask_for_bar(filter_note(slice_evs, 39), ppq))

    root_note = 47  # B2 for bass
    bass = generate_scored(
        bpm=bpm, ppq=ppq, bars=bars, root_note=root_note,
        kick_masks_by_bar=kick_mask_by_bar, hat_masks_by_bar=hat_mask_by_bar,
        clap_masks_by_bar=clap_mask_by_bar, density_target=0.38, min_dur_steps=0.5,
        swing_percent=spec.swing_percent, degree_mode="minor", motif="root_fifth_octave"
    )
    # Ensure bass uses channel 1
    out: List[MidiEvent] = []
    for ev in bass:
        out.append(MidiEvent(note=ev.note, vel=ev.vel, start_abs_tick=ev.start_abs_tick, dur_tick=ev.dur_tick, channel=1))
    return out


def _minor_scale(root_midi: int) -> List[int]:
    """Return pitch classes for natural minor relative to root."""
    intervals = [0, 2, 3, 5, 7, 8, 10, 12]
    return [root_midi + i for i in intervals]


def _nearest_in_scale(p: int, scale: Sequence[int]) -> int:
    pcs = [n % 12 for n in scale]
    target = p % 12
    if target in pcs:
        return p
    # search up/down small steps
    for d in range(1, 3):
        if ((p + d) % 12) in pcs:
            return p + d
        if ((p - d) % 12) in pcs:
            return p - d
    return p


def _build_melody(spec: Spec, rng: random.Random) -> Tuple[List[MidiEvent], List[CCEvent]]:
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    swing = spec.swing_percent
    # B minor scale around C4(60)
    scale = _minor_scale(59)  # B3

    events: List[MidiEvent] = []
    cc: List[CCEvent] = []

    def place(bar: int, step_idx: int, dur_steps: float, base_note: int, vel: int) -> None:
        # swing: push odd 16ths by (swing-0.5)*step
        start = bar * bar_ticks + step_idx * step
        if step_idx % 2 == 1:
            start += int(round((swing - 0.5) * step))
        dur = max(1, int(round(dur_steps * step)))
        note = _nearest_in_scale(base_note, scale)
        events.append(MidiEvent(note=note, vel=vel, start_abs_tick=start, dur_tick=dur, channel=3))
        # CC74 mapped to velocity to drive filter brightness
        cc_val = max(0, min(127, int(round(vel))))
        cc.append(CCEvent(cc=74, value=cc_val, tick=start, channel=3))

    # Call and response: 2-bar cells repeated across 8 bars
    # Call: sparse motif on bars 0,2,4,6; Response: denser syncopated on bars 1,3,5,7
    call_steps = [0, 5, 8, 12]        # rhythmic anchors
    resp_steps = [2, 3, 6, 7, 10, 11, 14]  # quirky syncopations
    base_line = [62, 64, 66, 69]  # D4, E4, F#4, A4 as seeds
    for bar in range(bars):
        is_call = (bar % 2 == 0)
        if is_call:
            for i, s in enumerate(call_steps):
                note = base_line[i % len(base_line)] + (0 if bar < 4 else 12*(rng.random() < 0.25))
                vel = int(rng.uniform(64, 112))
                place(bar, s, 0.5, note, vel)
        else:
            for i, s in enumerate(resp_steps):
                note = base_line[i % len(base_line)] + (12 if i % 5 == 0 and rng.random() < 0.3 else 0)
                vel = int(rng.uniform(48, 120))
                place(bar, s, 0.375 if (i % 3 == 0) else 0.5, note, vel)

    return events, cc


def _add_passing_notes_every_other_cycle(notes: List[MidiEvent], ppq: int, bpm: float, bars: int, rng: random.Random) -> List[MidiEvent]:
    """Add small passing tones only in bars 9-16 when bars==16.

    Applies to chord channel (2) and bass channel (1): short grace notes into downbeats.
    """
    if bars < 16:
        return notes
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16
    out = notes[:]
    # For bars 8..15 (0-indexed), add quick approach notes 1/16 before the bar's first beat
    for bar in range(8, 16):
        t = bar * bar_ticks
        # Bass: a semitone approach to root
        out.append(MidiEvent(note=44, vel=78, start_abs_tick=t - step, dur_tick=step // 2, channel=1))
        # Chords: a brief upper neighbour on top voice
        out.append(MidiEvent(note=75, vel=72, start_abs_tick=t - step, dur_tick=step // 2, channel=2))
    return out


def build_song(spec: Spec, seed: int = 6061, add_passing_every_other: bool = False):
    rng = random.Random(seed)
    drums = _build_drums(spec, rng)
    chords = _build_chords(spec, rng)
    bass = _build_bass(spec, drums)
    mel, mel_cc = _build_melody(spec, rng)

    # Ducking: subtle on chords, heavy on bass
    cc = []
    cc += _ducking_cc(spec, channel=2, depth=50)
    cc += _ducking_cc(spec, channel=1, depth=95)
    cc += mel_cc

    # Very light overall reverb send on drums (CC91) set once
    cc.append(CCEvent(cc=91, value=24, tick=0, channel=9))

    notes = []
    notes.extend(drums)
    notes.extend(chords)
    notes.extend(bass)
    notes.extend(mel)
    if add_passing_every_other:
        notes = _add_passing_notes_every_other_cycle(notes, ppq=spec.ppq, bpm=spec.bpm, bars=spec.bars, rng=rng)
    return notes, cc


def render_to_file(out_path: str, spec: Spec | None = None, seed: int = 6061, variant_every_other: bool = False):
    spec = spec or Spec()
    notes, cc = build_song(spec, seed=seed, add_passing_every_other=variant_every_other)
    write_midi_with_controls(notes=notes, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=cc)
