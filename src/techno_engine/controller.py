from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Optional, Tuple

from .midi_writer import MidiEvent
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks, schedule_bar_from_mask, apply_choke
from .scores import compute_E_S_from_mask, micro_offsets_ms_for_layer, rms, union_mask_for_bar
from .timebase import ticks_per_bar
from .conditions import mask_from_steps, thin_probs_near_kick, apply_step_conditions
from .density import enforce_density
from .modulate import Modulator, step_modulator
from .accent import AccentProfile, apply_accent
from .markov import DEFAULT_METRIC_WEIGHTS, update_probabilities, sample_markov_mask
from .euclid import bjorklund, rotate


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
    kick_immutable: bool = True


@dataclass
class RunResult:
    events_by_layer: Dict[str, List[MidiEvent]]
    E_by_bar: List[float]
    S_by_bar: List[float]
    swing_series: List[float]
    thin_bias_series: List[float]
    rot_rate_series: List[float]
    hatc_prob_series: List[List[float]]
    hato_prob_series: List[List[float]]
    rescue_bars: List[int]
    rescues: int


def _apply_kick_variations(mask: List[int], ghost_prob: float, displace_prob: float, rng: random.Random) -> None:
    positions = [0, 4, 8, 12]
    length = len(mask)
    # Displacements first
    for base in positions:
        if mask[base] == 1 and rng.random() < displace_prob:
            target = (base + 2) % length
            mask[base] = 0
            mask[target] = 1
    # Ghost hits (pre-step)
    for base in positions:
        if mask[base] == 1 and rng.random() < ghost_prob:
            ghost = (base - 1) % length
            mask[ghost] = 1
    # Ensure each quarter retains at least one strike nearby
    for base in positions:
        quarter = [(base + offset) % length for offset in (0, 1, -1)]
        if not any(mask[idx] for idx in quarter):
            mask[base] = 1


def run_session(
    bpm: float,
    ppq: int,
    bars: int,
    rng: Optional[random.Random] = None,
    targets: Optional[Targets] = None,
    guard: Optional[Guard] = None,
    inject_low_E_bars: Optional[Tuple[int, int]] = None,
    accent_profile: Optional[AccentProfile] = None,
    kick_layer_cfg: Optional[LayerConfig] = None,
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
    hatc_prob_series: List[List[float]] = []
    hato_prob_series: List[List[float]] = []
    rescues = 0
    rescue_bar_indices: List[int] = []
    rescue_next_bar_full = False

    metric_weights = DEFAULT_METRIC_WEIGHTS
    hatc_settings = {"gain": 0.12, "delta": 0.03, "floor": 0.25, "ceil": 0.95, "stick": 0.4}
    hato_settings = {"gain": 0.10, "delta": 0.03, "floor": 0.05, "ceil": 0.75, "stick": 0.5}

    kick_cfg = kick_layer_cfg or LayerConfig(
        steps=16,
        fills=4,
        rot=1,
        note=36,
        velocity=110,
        rotation_rate_per_bar=0.0,
        ghost_pre1_prob=0.0,
        displace_into_2_prob=0.0,
    )
    kick_rot_f = float(kick_cfg.rot)

    hatc_probs = [0.75] * 16
    hato_probs = [0.1] * 16
    for idx in range(16):
        if idx % 4 == 2:
            hato_probs[idx] = 0.4
    hatc_prev_state = 0
    hato_prev_state = 0
    sync_error_prev = 0.0

    for bar in range(bars):
        prev_swing = swing
        prev_thin = thin_bias
        prev_rot_rate = rot_rate

        swing = step_modulator(swing, swing_mod, bar)
        thin_bias = step_modulator(thin_bias, thin_mod, bar)
        rot_rate = step_modulator(rot_rate, rot_rate_mod, bar)
        rot_rate = min(guard.max_rot_rate, max(0.0, rot_rate))
        rot_f = (rot_f + rot_rate) % 16
        rot = int(round(rot_f)) % 16

        base_mask = bjorklund(kick_cfg.steps, kick_cfg.fills)
        base_rot = kick_cfg.rot % kick_cfg.steps
        if guard.kick_immutable:
            kick_mask = rotate(base_mask, base_rot)
        else:
            kick_rot_f = (kick_rot_f + kick_cfg.rotation_rate_per_bar) % kick_cfg.steps
            rot_int = int(round(kick_rot_f)) % kick_cfg.steps
            kick_mask = rotate(base_mask, rot_int)
            _apply_kick_variations(kick_mask, kick_cfg.ghost_pre1_prob, kick_cfg.displace_into_2_prob, rng)
        kick_events = schedule_bar_from_mask(
            bpm=bpm,
            ppq=ppq,
            bar_idx=0,
            cfg=kick_cfg,
            mask=kick_mask,
            rng=rng,
        )
        k = kick_events

        def bar_step(ev: MidiEvent) -> int:
            within = ev.start_abs_tick % bar_ticks
            return int(within // step_ticks)

        kick_mask = [0] * 16
        for ev in k:
            kick_mask[bar_step(ev)] = 1

        if rescue_next_bar_full:
            hatc_mask = [1] * 16
            hatc_probs = [hatc_settings["ceil"]] * 16
            hatc_prev_state = 0
            rescue_next_bar_full = False
        else:
            hatc_probs = update_probabilities(
                hatc_probs,
                sync_error_prev,
                metric_weights,
                hatc_settings["gain"],
                hatc_settings["delta"],
                hatc_settings["floor"],
                hatc_settings["ceil"],
            )
            hatc_mask, hatc_prev_state = sample_markov_mask(
                hatc_probs,
                rng,
                hatc_prev_state,
                offbeats_only=False,
                stickiness=hatc_settings["stick"],
                p_floor=hatc_settings["floor"],
                p_ceil=hatc_settings["ceil"],
            )
        hatc_prob_series.append(hatc_probs.copy())

        hat_mask = hatc_mask[:]
        hat_mask = apply_step_conditions(hat_mask, bar, [], rng)
        probs_thin = thin_probs_near_kick(base_prob=1.0, steps=16, kick_mask=kick_mask, window=1, bias=thin_bias)
        for i in range(16):
            if hat_mask[i] == 1 and rng.random() >= probs_thin[i]:
                hat_mask[i] = 0
        metric_w_density = [1.0] * 16
        for i in {0, 4, 8, 12}:
            metric_w_density[i] = 0.6
        hat_mask = enforce_density(hat_mask, target_ratio=0.7, tol=0.05, metric_w=metric_w_density)
        hatc_cfg = LayerConfig(
            steps=16,
            fills=12,
            rot=rot,
            note=42,
            velocity=80,
            swing_percent=swing,
            beat_bins_ms=[-10, -6, -2, 0],
            beat_bins_probs=[0.4, 0.35, 0.2, 0.05],
            beat_bin_cap_ms=12,
        )
        hc = schedule_bar_from_mask(bpm=bpm, ppq=ppq, bar_idx=0, cfg=hatc_cfg, mask=hat_mask, rng=rng)

        hato_probs = update_probabilities(
            hato_probs,
            sync_error_prev,
            metric_weights,
            hato_settings["gain"],
            hato_settings["delta"],
            hato_settings["floor"],
            hato_settings["ceil"],
        )
        hato_mask, hato_prev_state = sample_markov_mask(
            hato_probs,
            rng,
            hato_prev_state,
            offbeats_only=True,
            stickiness=hato_settings["stick"],
            p_floor=hato_settings["floor"],
            p_ceil=hato_settings["ceil"],
        )
        hato_prob_series.append(hato_probs.copy())
        ho_mask = hato_mask[:]
        ho_mask = apply_step_conditions(ho_mask, bar, [], rng)
        probs_open = thin_probs_near_kick(base_prob=1.0, steps=16, kick_mask=kick_mask, window=1, bias=thin_bias * 0.3)
        for i in range(16):
            if ho_mask[i] == 1 and rng.random() >= probs_open[i]:
                ho_mask[i] = 0
        metric_void = [1.0 if idx % 4 == 2 else 0.0 for idx in range(16)]
        ho_mask = enforce_density(ho_mask, target_ratio=0.25, tol=0.1, metric_w=metric_void)
        for idx in range(16):
            if idx % 4 != 2:
                ho_mask[idx] = 0
        hato_cfg = LayerConfig(
            steps=16,
            fills=16,
            rot=rot,
            note=46,
            velocity=80,
            offbeats_only=True,
            ratchet_prob=0.06,
            ratchet_repeat=3,
            swing_percent=swing,
            beat_bins_ms=[-2, 0, 2],
            beat_bins_probs=[0.2, 0.6, 0.2],
            beat_bin_cap_ms=10,
            choke_with_note=42,
        )
        ho = schedule_bar_from_mask(bpm=bpm, ppq=ppq, bar_idx=0, cfg=hato_cfg, mask=ho_mask, rng=rng)

        sn_cfg = LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=96)
        cl_cfg = LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)
        sn = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=sn_cfg, rng=rng)
        cl = build_layer(bpm=bpm, ppq=ppq, bars=1, cfg=cl_cfg, rng=rng)

        if inject_low_E_bars and inject_low_E_bars[0] <= bar <= inject_low_E_bars[1]:
            k.clear(); hc.clear(); ho.clear(); sn.clear(); cl.clear()

        union = k + hc + ho + sn + cl
        mask = union_mask_for_bar(union, ppq)
        E, S = compute_E_S_from_mask(mask)

        S_mid = 0.5 * (targets.S_low + targets.S_high)
        sync_error = S_mid - S

        if E < guard.min_E:
            rescues += 1
            swing = 0.5
            rot_f = 0.0
            thin_bias = -0.2
            rescue_next_bar_full = True
            sync_error = 0.0
            rescue_bar_indices.append(bar)

        thin_bias += 0.1 * sync_error
        if thin_bias - prev_thin > thin_mod.max_delta_per_bar:
            thin_bias = prev_thin + thin_mod.max_delta_per_bar
        if thin_bias - prev_thin < -thin_mod.max_delta_per_bar:
            thin_bias = prev_thin - thin_mod.max_delta_per_bar
        thin_bias = max(thin_mod.min_val, min(thin_mod.max_val, thin_bias))

        swing += 0.02 * (0.545 - swing)
        if swing - prev_swing > swing_mod.max_delta_per_bar:
            swing = prev_swing + swing_mod.max_delta_per_bar
        if swing - prev_swing < -swing_mod.max_delta_per_bar:
            swing = prev_swing - swing_mod.max_delta_per_bar
        swing = max(swing_mod.min_val, min(swing_mod.max_val, swing))

        if accent_profile is not None:
            union = apply_accent(union, ppq=ppq, profile=accent_profile, rng=rng)

            def pick(note: int) -> List[MidiEvent]:
                return [ev for ev in union if ev.note == note]

            k, hc, ho, sn, cl = pick(36), pick(42), pick(46), pick(38), pick(39)

        offset = bar * bar_ticks
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
        sync_error_prev = sync_error

    closed_hat_map = collect_closed_hat_ticks(events_hatc, ppq=ppq, closed_hat_note=42)
    events_hato = apply_choke(events_hato, ppq=ppq, closed_hat_ticks_by_bar=closed_hat_map)

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
        hatc_prob_series=hatc_prob_series,
        hato_prob_series=hato_prob_series,
        rescue_bars=rescue_bar_indices,
        rescues=rescues,
    )
