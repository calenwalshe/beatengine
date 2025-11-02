from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Optional, Tuple

from .midi_writer import MidiEvent
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks
from .scores import compute_E_S_from_mask, micro_offsets_ms_for_layer, rms, union_mask_for_bar
from .timebase import ticks_per_bar
from .conditions import mask_from_steps, thin_probs_near_kick
from .density import enforce_density
from .modulate import Modulator, step_modulator
from .accent import AccentProfile, apply_accent


@dataclass
class Targets:
    E_target: float = 0.8
    S_low: float = 0.35
    S_high: float = 0.55
    T_ms_cap: float = 12.0


@dataclass
class Guard:
    min_E: float = 0.78
    max_rot_rate: float = 0.125


@dataclass
class RunResult:
    events_by_layer: Dict[str, List[MidiEvent]]
    E_by_bar: List[float]
    S_by_bar: List[float]
    swing_series: List[float]
    thin_bias_series: List[float]
    rot_rate_series: List[float]
    rescues: int


def run_session(
    bpm: float,
    ppq: int,
    bars: int,
    rng: Optional[random.Random] = None,
    targets: Optional[Targets] = None,
    guard: Optional[Guard] = None,
    inject_low_E_bars: Optional[Tuple[int, int]] = None,
    accent_profile: Optional[AccentProfile] = None,
) -> RunResult:
    rng = rng or random.Random(1234)
    targets = targets or Targets()
    guard = guard or Guard()

    # Modulators
    swing_mod = Modulator(name="swing", mode="ou", min_val=0.51, max_val=0.58, tau=48.0, step_per_bar=0.005, max_delta_per_bar=0.01)
    thin_mod = Modulator(name="thin_bias", mode="ou", min_val=-0.8, max_val=0.0, tau=32.0, step_per_bar=0.02, max_delta_per_bar=0.03)
    rot_rate_mod = Modulator(name="rot_rate", mode="random_walk", min_val=0.0, max_val=0.125, step_per_bar=0.01, max_delta_per_bar=0.02)

    swing = 0.545
    thin_bias = -0.2
    rot_rate = 0.0
    rot_f = 0.0

    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // 16

    events_kick: List[MidiEvent] = []
    events_hatc: List[MidiEvent] = []
    events_hato: List[MidiEvent] = []
    events_snare: List[MidiEvent] = []
    events_clap: List[MidiEvent] = []

    E_series: List[float] = []
    S_series: List[float] = []
    swing_series: List[float] = []
    thin_series: List[float] = []
    rot_rate_series: List[float] = []
    rescues = 0
    rescue_next_bar_full = False

    for bar in range(bars):
        # Update modulators
        prev_swing = swing
        prev_thin = thin_bias
        prev_rot_rate = rot_rate

        swing = step_modulator(swing, swing_mod, bar)
        thin_bias = step_modulator(thin_bias, thin_mod, bar)
        rot_rate = step_modulator(rot_rate, rot_rate_mod, bar)
        rot_rate = min(guard.max_rot_rate, max(0.0, rot_rate))
        rot_f = (rot_f + rot_rate) % 16
        rot = int(round(rot_f)) % 16

        # Post-feedback parameter log happens after E/S calculation and feedback clamps

        # Build base layers for 1 bar
        kick_cfg = LayerConfig(steps=16, fills=4, rot=0, note=36, velocity=110)
        hatc_cfg = LayerConfig(
            steps=16, fills=12, rot=rot, note=42, velocity=80,
            swing_percent=swing,
            beat_bins_ms=[-10,-6,-2,0], beat_bins_probs=[0.4,0.35,0.2,0.05], beat_bin_cap_ms=12,
        )
        hato_cfg = LayerConfig(
            steps=16, fills=16, rot=rot, note=46, velocity=80,
            offbeats_only=True, ratchet_prob=0.06, ratchet_repeat=3,
            swing_percent=swing,
            beat_bins_ms=[-2,0,2], beat_bins_probs=[0.2,0.6,0.2], beat_bin_cap_ms=10,
            choke_with_note=42,
        )
        sn_cfg = LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=96)
        cl_cfg = LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)

        k = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=kick_cfg, rng=rng)
        hc = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=hatc_cfg, rng=rng)
        ch_map = collect_closed_hat_ticks(hc, ppq=ppq, closed_hat_note=42)
        ho = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=hato_cfg, rng=rng, closed_hat_ticks_by_bar=ch_map)
        sn = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=sn_cfg, rng=rng)
        cl = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=cl_cfg, rng=rng)

        # Optional test hook to force low E
        if inject_low_E_bars and inject_low_E_bars[0] <= bar <= inject_low_E_bars[1]:
            hc.clear(); ho.clear(); sn.clear(); cl.clear()

        # Apply hat thinning via per-step probability mask near kicks
        # Build masks
        def bar_step(ev: MidiEvent) -> int:
            within = ev.start_abs_tick % bar_ticks
            return int(within // step_ticks)

        hat_mask = [0] * 16
        for ev in hc:
            hat_mask[bar_step(ev)] = 1
        kick_mask = [0] * 16
        for ev in k:
            kick_mask[bar_step(ev)] = 1
        probs = thin_probs_near_kick(base_prob=1.0, steps=16, kick_mask=kick_mask, window=1, bias=thin_bias)
        for i in range(16):
            if hat_mask[i] == 1 and rng.random() >= probs[i]:
                hat_mask[i] = 0
        # density clamp ~ 0.7 ± 0.05 with metric preference away from kicks
        metric_w = [1.0] * 16
        for i in range(16):
            if i in {0,4,8,12}:
                metric_w[i] = 0.6
        hat_mask = enforce_density(hat_mask, target_ratio=0.7, tol=0.05, metric_w=metric_w)
        # rebuild hihat events using original timing of earliest event per step
        by_step: Dict[int, List[MidiEvent]] = {}
        for ev in hc:
            by_step.setdefault(bar_step(ev), []).append(ev)
        hc = []
        for i, keep in enumerate(hat_mask):
            if keep and i in by_step:
                ev = sorted(by_step[i], key=lambda e: e.start_abs_tick)[0]
                hc.append(ev)

        # Compute E,S for this bar on union
        union = k + hc + ho + sn + cl
        mask = union_mask_for_bar(union, ppq)
        E, S = compute_E_S_from_mask(mask)

        # Guard: if E below minimum, trigger rescue
        if E < guard.min_E:
            rescues += 1
            # rescue actions: straighten swing, reset rotations, lighten thinning
            swing = 0.5
            rot_f = 0.0
            thin_bias = -0.2
            rescue_next_bar_full = True

        # Feedback: nudge thin_bias toward S target and small swing adjustment
        S_mid = 0.5 * (targets.S_low + targets.S_high)
        sync_error = S_mid - S
        thin_bias += 0.1 * sync_error  # increase bias (less negative) when S too low, decrease when high
        # clamp continuity for thin_bias and swing relative to previous values
        if thin_bias - prev_thin > thin_mod.max_delta_per_bar:
            thin_bias = prev_thin + thin_mod.max_delta_per_bar
        if thin_bias - prev_thin < -thin_mod.max_delta_per_bar:
            thin_bias = prev_thin - thin_mod.max_delta_per_bar
        thin_bias = max(thin_mod.min_val, min(thin_mod.max_val, thin_bias))
        # small swing dampening
        swing += 0.02 * (0.545 - swing)
        if swing - prev_swing > swing_mod.max_delta_per_bar:
            swing = prev_swing + swing_mod.max_delta_per_bar
        if swing - prev_swing < -swing_mod.max_delta_per_bar:
            swing = prev_swing - swing_mod.max_delta_per_bar
        swing = max(swing_mod.min_val, min(swing_mod.max_val, swing))

        # Apply global accent if provided (pre-offset), then offset events into timeline
        if accent_profile is not None:
            union = apply_accent(union, ppq=ppq, profile=accent_profile, rng=rng)
            # split back by note
            def pick(note):
                return [ev for ev in union if ev.note == note]
            k, hc, ho, sn, cl = pick(36), pick(42), pick(46), pick(38), pick(39)

        # Offset events into timeline and accumulate
        offset = bar * bar_ticks
        # If a rescue was triggered in previous bar, force a full 16-step hat layer this bar for recovery
        if rescue_next_bar_full:
            rescue_next_bar_full = False
            hc = build_layer(
                bpm=bpm, ppq=ppq, bars=1,
                cfg=LayerConfig(steps=16, fills=16, rot=0, note=42, velocity=80, swing_percent=swing,
                                beat_bins_ms=[-10,-6,-2,0], beat_bins_probs=[0.4,0.35,0.2,0.05], beat_bin_cap_ms=12),
                rng=rng
            )

        for ev in k + hc + ho + sn + cl:
            ev.start_abs_tick += offset
        events_kick.extend(k)
        events_hatc.extend(hc)
        events_hato.extend(ho)
        events_snare.extend(sn)
        events_clap.extend(cl)

        E_series.append(E)
        S_series.append(S)
        swing_series.append(swing)
        thin_series.append(thin_bias)
        rot_rate_series.append(rot_rate)

    return RunResult(
        events_by_layer={
            "kick": events_kick,
            "hat_c": events_hatc,
            "hat_o": events_hato,
            "snare": events_snare,
            "clap": events_clap,
        },
        E_by_bar=E_series,
        S_by_bar=S_series,
        swing_series=swing_series,
        thin_bias_series=thin_series,
        rot_rate_series=rot_rate_series,
        rescues=rescues,
    )
