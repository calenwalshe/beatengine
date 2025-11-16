from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random

from .midi_writer import MidiEvent, CCEvent, write_midi_with_controls
from .parametric import LayerConfig, build_layer
from .timebase import ticks_per_bar
from .fred_spec import Spec


@dataclass
class BDVibe:
    name: str
    swing: float
    hat_note: int  # 42 closed, 82 shaker, 51 ride etc.
    hat_vel: int
    hat_density: int  # fills number (<=16)
    offbeats: bool
    include_kick: bool
    clap_strength: int
    snare_strength: int
    open_hat_prob: float


def _sched_roll(bar_start: int, step_ticks: int, channel: int, base_vel: int) -> List[MidiEvent]:
    # short crescendo roll over last half-beat of the bar (two 16ths of 32nd subdivisions)
    evs: List[MidiEvent] = []
    # position: steps 14.5 to 16.0 approx
    for i in range(6):
        t = bar_start + 14 * step_ticks + int((i * (step_ticks/12)))
        vel = min(127, base_vel - 10 + i * 4)
        evs.append(MidiEvent(note=38, vel=vel, start_abs_tick=t, dur_tick=max(1, step_ticks // 4), channel=9))
    return evs


def _build_breakdown_for_vibe(spec: Spec, vibe: BDVibe, seed: int) -> Tuple[List[MidiEvent], List[CCEvent]]:
    rng = random.Random(seed)
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16

    events: List[MidiEvent] = []

    # Hats/shakers/rides layer
    hat_cfg = LayerConfig(
        steps=16,
        fills=max(1, min(16, vibe.hat_density)),
        rot=0,
        note=vibe.hat_note,
        velocity=vibe.hat_vel,
        swing_percent=vibe.swing,
        offbeats_only=vibe.offbeats,
        beat_bins_ms=[-8, -4, 0, 4],
        beat_bins_probs=[0.35, 0.35, 0.25, 0.05],
        beat_bin_cap_ms=10,
    )
    ev_hat = build_layer(bpm, ppq, bars, hat_cfg, rng)
    # Longer ride tails if ride cymbal
    if vibe.hat_note == 51:
        for e in ev_hat:
            e.dur_tick = int(step * 3)
            e.vel = min(120, max(70, int(rng.gauss(vibe.hat_vel, 4))))
    events += ev_hat

    # Optional minimal kick (beat 1 only for air)
    if vibe.include_kick:
        for b in range(bars):
            t = b * bar_ticks
            events.append(MidiEvent(note=36, vel=90, start_abs_tick=t, dur_tick=step//2, channel=9))

    # Clap/Snare: sparse; clap on beat 4 with reverb space, snare halftime pulse on beat 3 in some vibes
    for b in range(bars):
        start = b * bar_ticks
        # Clap on beat 4 (step 12)
        events.append(MidiEvent(note=39, vel=vibe.clap_strength, start_abs_tick=start + 12*step, dur_tick=step//2, channel=9))
        # Halftime snare on beat 3 (step 8) if shaker/halftime feels
        if vibe.name in ("halftime_pulse", "sync_shaker"):
            events.append(MidiEvent(note=38, vel=vibe.snare_strength, start_abs_tick=start + 8*step, dur_tick=step//2, channel=9))

    # Snare roll lift at end for designated vibe
    if vibe.name == "snare_roll_lift":
        for b in range(bars):
            events += _sched_roll(b * bar_ticks, step, 9, base_vel=max(80, vibe.snare_strength))

    # Subtle reverb more prominent in breakdown
    ccs = [CCEvent(cc=91, value=40, tick=0, channel=9)]
    return events, ccs


def render_breakdown_vibes(out_prefix: str, spec: Spec | None = None, seed: int = 9101) -> List[str]:
    spec = spec or Spec()
    vibes = [
        BDVibe("no_kick_air", swing=0.60, hat_note=42, hat_vel=78, hat_density=8, offbeats=True, include_kick=False, clap_strength=88, snare_strength=92, open_hat_prob=0.02),
        BDVibe("halftime_pulse", swing=0.60, hat_note=42, hat_vel=80, hat_density=6, offbeats=True, include_kick=False, clap_strength=86, snare_strength=96, open_hat_prob=0.02),
        BDVibe("sync_shaker", swing=0.61, hat_note=82, hat_vel=84, hat_density=8, offbeats=True, include_kick=False, clap_strength=84, snare_strength=92, open_hat_prob=0.00),
        BDVibe("ride_wash", swing=0.58, hat_note=51, hat_vel=85, hat_density=4, offbeats=False, include_kick=False, clap_strength=82, snare_strength=86, open_hat_prob=0.00),
        BDVibe("rim_groove", swing=0.62, hat_note=37, hat_vel=76, hat_density=7, offbeats=False, include_kick=False, clap_strength=80, snare_strength=88, open_hat_prob=0.00),
        BDVibe("snare_roll_lift", swing=0.60, hat_note=42, hat_vel=80, hat_density=6, offbeats=True, include_kick=False, clap_strength=84, snare_strength=100, open_hat_prob=0.02),
    ]
    outputs: List[str] = []
    for i, vb in enumerate(vibes, start=1):
        evs, ccs = _build_breakdown_for_vibe(spec, vb, seed + 137*i)
        out_path = f"{out_prefix}_{i:02d}_{vb.name}.mid"
        write_midi_with_controls(notes=evs, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        outputs.append(out_path)
    return outputs


def _build_shaker_variant(
    spec: Spec,
    *,
    swing: float,
    fills: int,
    offbeats: bool,
    ratchet_prob: float,
    ratchet_repeat: int,
    bins_ms: list[float],
    bins_p: list[float],
    cap_ms: float,
    base_vel: int,
    dur_factor: float,
    clap_vel: int,
    add_halftime_snare: bool,
    seed: int,
) -> Tuple[List[MidiEvent], List[CCEvent]]:
    rng = random.Random(seed)
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars
    bar_ticks = ticks_per_bar(ppq, 4)
    step = bar_ticks // 16

    shaker_cfg = LayerConfig(
        steps=16,
        fills=max(1, min(16, int(fills))),
        rot=0,
        note=82,  # shaker
        velocity=base_vel,
        swing_percent=swing,
        offbeats_only=offbeats,
        ratchet_prob=ratchet_prob,
        ratchet_repeat=ratchet_repeat,
        beat_bins_ms=bins_ms,
        beat_bins_probs=bins_p,
        beat_bin_cap_ms=cap_ms,
    )
    sh = build_layer(bpm, ppq, bars, shaker_cfg, rng)
    # Post: vary velocity, extend/shorten duration
    for e in sh:
        e.vel = max(60, min(115, int(rng.gauss(base_vel, 6))))
        e.dur_tick = max(1, int(step * dur_factor * rng.uniform(0.85, 1.15)))

    evs: List[MidiEvent] = []
    evs += sh

    # Minimal clap on 4
    for b in range(bars):
        start = b * bar_ticks
        evs.append(MidiEvent(note=39, vel=clap_vel, start_abs_tick=start + 12 * step, dur_tick=step // 2, channel=9))
        if add_halftime_snare:
            evs.append(MidiEvent(note=38, vel=max(80, clap_vel - 2), start_abs_tick=start + 8 * step, dur_tick=step // 2, channel=9))

    ccs = [CCEvent(cc=91, value=48, tick=0, channel=9)]
    return evs, ccs


def render_dense_shaker_vibes(out_prefix: str, spec: Spec | None = None, seed: int = 9601) -> List[str]:
    spec = spec or Spec()
    variants = [
        {
            "name": "dense16_push",
            "swing": 0.60,
            "fills": 16,
            "offbeats": False,
            "ratchet_prob": 0.12,
            "ratchet_repeat": 3,
            "bins_ms": [-8, -5, -2, 0, 2],
            "bins_p": [0.35, 0.3, 0.2, 0.12, 0.03],
            "cap_ms": 10,
            "base_vel": 84,
            "dur_factor": 0.5,
            "clap_vel": 84,
            "add_halftime_snare": False,
        },
        {
            "name": "offbeat_double",
            "swing": 0.60,
            "fills": 16,
            "offbeats": True,
            "ratchet_prob": 0.28,
            "ratchet_repeat": 3,
            "bins_ms": [-6, -3, 0, 3],
            "bins_p": [0.4, 0.35, 0.2, 0.05],
            "cap_ms": 8,
            "base_vel": 82,
            "dur_factor": 0.55,
            "clap_vel": 82,
            "add_halftime_snare": True,
        },
        {
            "name": "shuffle_wash",
            "swing": 0.62,
            "fills": 12,
            "offbeats": False,
            "ratchet_prob": 0.10,
            "ratchet_repeat": 4,
            "bins_ms": [-10, -6, -2, 0],
            "bins_p": [0.45, 0.3, 0.2, 0.05],
            "cap_ms": 12,
            "base_vel": 86,
            "dur_factor": 0.7,
            "clap_vel": 80,
            "add_halftime_snare": False,
        },
    ]

    outs: List[str] = []
    for i, v in enumerate(variants, start=1):
        name = v["name"]
        params = {k: v[k] for k in v.keys() if k != "name"}
        evs, ccs = _build_shaker_variant(spec, seed=seed + 53 * i, **params)
        out_path = f"{out_prefix}_{i:02d}_{name}.mid"
        write_midi_with_controls(notes=evs, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        outs.append(out_path)
    return outs
