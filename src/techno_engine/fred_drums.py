from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random

from .midi_writer import MidiEvent, CCEvent, write_midi_with_controls
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks, apply_choke
from .timebase import ticks_per_bar
from .fred_spec import Spec, _postprocess_hats


@dataclass
class Vibe:
    name: str
    swing: float
    hat_vel: int
    hat_bins: Tuple[list[float], list[float], float]  # (ms, probs, cap)
    open_prob: float
    ratchet_prob: float
    ghost_intensity: float  # 0..1
    clap_vel: int
    snare_vel: int


def _build_drums_for_vibe(spec: Spec, vibe: Vibe, seed: int) -> Tuple[List[MidiEvent], List[CCEvent]]:
    rng = random.Random(seed)
    bpm, ppq, bars = spec.bpm, spec.ppq, spec.bars

    # Kick: 4-on-the-floor
    kick = LayerConfig(steps=16, fills=4, rot=0, note=36, velocity=116)

    bins_ms, bins_p, cap = vibe.hat_bins
    # Closed hats offbeats with swing and micro bins
    hatc = LayerConfig(
        steps=16, fills=16, offbeats_only=True, note=42, velocity=vibe.hat_vel,
        swing_percent=vibe.swing, beat_bins_ms=bins_ms, beat_bins_probs=bins_p, beat_bin_cap_ms=cap
    )
    # Open hats choked, offbeats, small ratchets
    hato = LayerConfig(
        steps=16, fills=16, offbeats_only=True, note=46, velocity=max(70, vibe.hat_vel - 2),
        ratchet_prob=vibe.ratchet_prob, ratchet_repeat=3, swing_percent=vibe.swing,
        beat_bins_ms=[-2, 0, 2], beat_bins_probs=[0.3, 0.5, 0.2], beat_bin_cap_ms=min(10, cap), choke_with_note=42
    )
    # Snare/clap backbeats with slight micro on response (micro_ms small)
    snare = LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=vibe.snare_vel, swing_percent=vibe.swing, micro_ms=-2.0)
    clap = LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=vibe.clap_vel, swing_percent=vibe.swing, micro_ms=1.5)

    ev_k = build_layer(bpm, ppq, bars, kick, rng)
    ev_hc = build_layer(bpm, ppq, bars, hatc, rng)
    ch_map = collect_closed_hat_ticks(ev_hc, ppq, 42)
    ev_ho = build_layer(bpm, ppq, bars, hato, rng, closed_hat_ticks_by_bar=ch_map)
    ev_sn = build_layer(bpm, ppq, bars, snare, rng)
    ev_cl = build_layer(bpm, ppq, bars, clap, rng)

    # Post-process hats for per-hit variation and occasional open hat promotion
    drums = ev_k + _postprocess_hats(ev_hc, ppq, spec.bpm, rng) + ev_ho + ev_sn + ev_cl

    # Ghost details scaled by intensity
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16
    ghosts: List[MidiEvent] = []
    for b in range(bars):
        bar_start = b * bar_ticks
        for step in (1, 5, 9, 13):
            if rng.random() < (0.25 + 0.5 * vibe.ghost_intensity):
                t = bar_start + step * step_ticks + int(round(rng.uniform(-0.12, 0.08) * step_ticks))
                ghosts.append(MidiEvent(note=37, vel=60 + int(10*vibe.ghost_intensity), start_abs_tick=t, dur_tick=max(1, step_ticks // 3), channel=9))
        for s in (7, 11, 15):
            if rng.random() < (0.15 + 0.35 * vibe.ghost_intensity):
                t = bar_start + s * step_ticks + int(round(rng.uniform(-0.08, 0.05) * step_ticks))
                ghosts.append(MidiEvent(note=36, vel=66 + int(12*vibe.ghost_intensity), start_abs_tick=t, dur_tick=max(1, step_ticks // 4), channel=9))

    drums += ghosts

    # Subtle short reverb via CC91
    ccs = [CCEvent(cc=91, value=24, tick=0, channel=9)]
    return drums, ccs


def render_vibes(out_prefix: str, spec: Spec | None = None, seed: int = 7001) -> List[str]:
    spec = spec or Spec()
    # Define five distinct vibes within the brief
    vibes = [
        Vibe("vinyl_warm", swing=0.60, hat_vel=84, hat_bins=([-10,-6,-2,0],[0.4,0.35,0.2,0.05],12), open_prob=0.02, ratchet_prob=0.08, ghost_intensity=0.6, clap_vel=92, snare_vel=96),
        Vibe("warehouse_tight", swing=0.58, hat_vel=82, hat_bins=([-6,-3,0],[0.5,0.35,0.15],8), open_prob=0.01, ratchet_prob=0.04, ghost_intensity=0.2, clap_vel=94, snare_vel=98),
        Vibe("ghosty_shuffle", swing=0.62, hat_vel=86, hat_bins=([-12,-8,-4,0],[0.45,0.3,0.2,0.05],14), open_prob=0.03, ratchet_prob=0.16, ghost_intensity=0.8, clap_vel=90, snare_vel=94),
        Vibe("punchy_crunch", swing=0.59, hat_vel=88, hat_bins=([-8,-4,0],[0.5,0.45,0.05],10), open_prob=0.02, ratchet_prob=0.10, ghost_intensity=0.35, clap_vel=98, snare_vel=100),
        Vibe("loose_human", swing=0.61, hat_vel=80, hat_bins=([-9,-5,-1,1],[0.38,0.36,0.2,0.06],11), open_prob=0.03, ratchet_prob=0.12, ghost_intensity=0.7, clap_vel=90, snare_vel=95),
    ]

    outputs: List[str] = []
    for i, vb in enumerate(vibes, start=1):
        drums, ccs = _build_drums_for_vibe(spec, vb, seed + i * 101)
        out_path = f"{out_prefix}_{i:02d}_{vb.name}.mid"
        write_midi_with_controls(notes=drums, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        outputs.append(out_path)
    return outputs

