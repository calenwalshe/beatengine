from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .parametric import LayerConfig


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


def _layer_from_dict(d: Optional[Dict[str, Any]]) -> Optional[LayerConfig]:
    if not d:
        return None
    # Map JSON keys directly onto LayerConfig fields; unknown keys ignored
    kw = {}
    for k in (
        "steps","fills","rot","note","velocity","swing_percent",
        "beat_bins_ms","beat_bins_probs","beat_bin_cap_ms","micro_ms",
        "offbeats_only","ratchet_prob","ratchet_repeat","choke_with_note",
    ):
        if k in d:
            kw[k] = d[k]
    return LayerConfig(**kw)


def load_engine_config(path: str) -> EngineConfig:
    with open(path, "r") as f:
        raw = json.load(f)
    mode = str(raw.get("mode", "m1")).lower()
    cfg = EngineConfig(
        mode=mode,
        bpm=float(raw.get("bpm", 132)),
        ppq=int(raw.get("ppq", 1920)),
        bars=int(raw.get("bars", 8)),
        seed=int(raw.get("seed", 1234)),
        out=str(raw.get("out", "out/render.mid")),
        kick=_layer_from_dict(raw.get("layers", {}).get("kick")) if raw.get("layers") else None,
        hat_c=_layer_from_dict(raw.get("layers", {}).get("hat_c")) if raw.get("layers") else None,
        hat_o=_layer_from_dict(raw.get("layers", {}).get("hat_o")) if raw.get("layers") else None,
        snare=_layer_from_dict(raw.get("layers", {}).get("snare")) if raw.get("layers") else None,
        clap=_layer_from_dict(raw.get("layers", {}).get("clap")) if raw.get("layers") else None,
    )
    return cfg

