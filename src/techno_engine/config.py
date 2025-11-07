from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .parametric import LayerConfig
from .conditions import StepCondition, CondType
from .modulate import Modulator, ParamModSpec
from .controller import Guard, Targets


def _cond_from_dict(d: Dict[str, Any]) -> StepCondition:
    kind_str = d.get("kind", "PROB").upper()
    kind = CondType[kind_str]
    return StepCondition(
        kind=kind,
        p=float(d.get("p", 1.0)),
        n=int(d.get("n", 0)),
        offset=int(d.get("offset", 0)),
        negate=bool(d.get("negate", False)),
    )


@dataclass
class EngineConfig:
    mode: str
    bpm: float
    ppq: int
    bars: int
    seed: int = 1234
    out: str = "out/render.mid"
    # Optional per-layer params for parametric modes (m2/m3)
    kick: Optional[LayerConfig] = None
    hat_c: Optional[LayerConfig] = None
    hat_o: Optional[LayerConfig] = None
    snare: Optional[LayerConfig] = None
    clap: Optional[LayerConfig] = None
    guard: Guard = field(default_factory=Guard)
    targets: Targets = field(default_factory=Targets)
    modulators: List[ParamModSpec] = field(default_factory=list)
    log_path: Optional[str] = None


def _layer_from_dict_named(name: str, d: Optional[Dict[str, Any]]) -> Optional[LayerConfig]:
    if not d:
        return None
    # Map JSON keys directly onto LayerConfig fields; unknown keys ignored
    kw: Dict[str, Any] = {}
    for k in (
        "steps","fills","rot","note","velocity","swing_percent",
        "beat_bins_ms","beat_bins_probs","beat_bin_cap_ms","micro_ms",
        "offbeats_only","ratchet_prob","ratchet_repeat","choke_with_note",
        "rotation_rate_per_bar","ghost_pre1_prob","displace_into_2_prob",
    ):
        if k in d:
            kw[k] = d[k]
    # Sensible note defaults by layer if not provided
    if "note" not in kw:
        lname = name.lower()
        if lname == "kick":
            kw["note"] = 36
        elif lname in ("hat_c", "closed_hat", "hh_closed"):
            kw["note"] = 42
        elif lname in ("hat_o", "open_hat", "hh_open"):
            kw["note"] = 46
        elif lname == "snare":
            kw["note"] = 38
        elif lname == "clap":
            kw["note"] = 39
    if "conditions" in d and isinstance(d["conditions"], list):
        kw["conditions"] = [_cond_from_dict(c) for c in d["conditions"]]
    return LayerConfig(**kw)


def _guard_from_dict(d: Optional[Dict[str, Any]]) -> Guard:
    if not d:
        return Guard()
    return Guard(
        min_E=float(d.get("min_E", 0.78)),
        max_rot_rate=float(d.get("max_rot_rate", 0.125)),
        kick_immutable=bool(d.get("kick_immutable", True)),
    )


def _targets_from_dict(d: Optional[Dict[str, Any]]) -> Targets:
    if not d:
        return Targets()
    return Targets(
        E_target=float(d.get("E_target", 0.8)),
        S_low=float(d.get("S_low", 0.35)),
        S_high=float(d.get("S_high", 0.55)),
        T_ms_cap=float(d.get("T_ms_cap", 12.0)),
        H_low=float(d.get("H_low", 0.3)),
        H_high=float(d.get("H_high", 0.6)),
        hat_density_target=float(d.get("hat_density_target", 0.7)),
        hat_density_tol=float(d.get("hat_density_tol", 0.05)),
    )


def _modulator_from_dict(d: Dict[str, Any]) -> ParamModSpec:
    mod_cfg = d.get("mod", {})
    mod = Modulator(
        name=d.get("name", "mod"),
        mode=mod_cfg.get("mode", "random_walk"),
        min_val=float(mod_cfg.get("min_val", 0.0)),
        max_val=float(mod_cfg.get("max_val", 1.0)),
        step_per_bar=float(mod_cfg.get("step_per_bar", 0.01)),
        tau=float(mod_cfg.get("tau", 32.0)),
        max_delta_per_bar=float(mod_cfg.get("max_delta_per_bar", 0.05)),
        phase=float(mod_cfg.get("phase", 0.0)),
    )
    return ParamModSpec(
        name=d.get("name", mod.name),
        param_path=d.get("param_path", ""),
        modulator=mod,
    )


def _engine_config_from_dict(raw: Dict[str, Any]) -> EngineConfig:
    mode = str(raw.get("mode", "m1")).lower()
    cfg = EngineConfig(
        mode=mode,
        bpm=float(raw.get("bpm", 132)),
        ppq=int(raw.get("ppq", 1920)),
        bars=int(raw.get("bars", 8)),
        seed=int(raw.get("seed", 1234)),
        out=str(raw.get("out", "out/render.mid")),
        kick=_layer_from_dict_named("kick", raw.get("layers", {}).get("kick")) if raw.get("layers") else None,
        hat_c=_layer_from_dict_named("hat_c", raw.get("layers", {}).get("hat_c")) if raw.get("layers") else None,
        hat_o=_layer_from_dict_named("hat_o", raw.get("layers", {}).get("hat_o")) if raw.get("layers") else None,
        snare=_layer_from_dict_named("snare", raw.get("layers", {}).get("snare")) if raw.get("layers") else None,
        clap=_layer_from_dict_named("clap", raw.get("layers", {}).get("clap")) if raw.get("layers") else None,
        guard=_guard_from_dict(raw.get("guard")),
        targets=_targets_from_dict(raw.get("targets")),
        modulators=[_modulator_from_dict(m) for m in raw.get("modulators", [])],
        log_path=raw.get("log_path"),
    )
    return cfg


def engine_config_from_dict(raw: Dict[str, Any]) -> EngineConfig:
    return _engine_config_from_dict(raw)


def load_engine_config(path: str) -> EngineConfig:
    with open(path, "r") as f:
        raw = json.load(f)
    return _engine_config_from_dict(raw)
