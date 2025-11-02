from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class Modulator:
    name: str
    mode: str = "random_walk"  # or "ou", "sine"
    min_val: float = 0.0
    max_val: float = 1.0
    step_per_bar: float = 0.01
    tau: float = 32.0
    max_delta_per_bar: float = 0.05
    phase: float = 0.0


def step_modulator(value: float, mod: Modulator, bar_idx: int) -> float:
    if mod.mode == "random_walk":
        delta = random.uniform(-mod.step_per_bar, mod.step_per_bar)
        newv = value + delta
    elif mod.mode == "ou":
        mid = 0.5 * (mod.min_val + mod.max_val)
        theta = 1.0 / max(1e-6, mod.tau)
        noise = random.gauss(0.0, mod.step_per_bar)
        newv = value + theta * (mid - value) + noise
    elif mod.mode == "sine":
        phase = (mod.phase + bar_idx / max(1e-6, mod.tau)) % 1.0
        newv = mod.min_val + 0.5 * (1 + math.sin(2 * math.pi * phase)) * (mod.max_val - mod.min_val)
    else:
        newv = value

    # reflect + clamp
    newv = max(mod.min_val, min(mod.max_val, newv))
    # clamp delta
    if abs(newv - value) > mod.max_delta_per_bar:
        newv = value + math.copysign(mod.max_delta_per_bar, newv - value)
    return newv

