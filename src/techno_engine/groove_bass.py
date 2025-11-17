from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .bass_score import SyncWeights, score_steps, select_steps_by_score
from .bassline import build_swung_grid
from .drum_analysis import DrumAnchors
from .midi_writer import MidiEvent


@dataclass
class BassModeConfig:
    name: str
    density_min: int
    density_max: int
    register_lo: int
    register_hi: int
    strict_kick_avoid: bool
    offbeat_only: bool


def _compute_energy(anchors: DrumAnchors) -> float:
    """Rough drum energy score based on kicks + hats per bar."""

    total_kicks = sum(len(steps) for steps in anchors.bar_kick_steps)
    total_hats = sum(len(steps) for steps in anchors.bar_hat_steps)
    bars = max(1, anchors.bar_count)
    return (total_kicks + 0.5 * total_hats) / bars


def _normalise_tags(tags: Optional[Sequence[str]]) -> List[str]:
    if not tags:
        return []
    return [t.strip().lower() for t in tags if t.strip()]


def choose_mode(tags: Optional[Sequence[str]], energy: float) -> BassModeConfig:
    """Pick a bass mode from tags + energy (see docs/BASS_GROOVE_ROADMAP.md)."""

    norm = set(_normalise_tags(tags))

    # Defaults – root/5th style driver.
    mode_name = "root_fifth"
    density_min, density_max = 2, 6
    register_lo, register_hi = 34, 52
    strict_kick_avoid = True
    offbeat_only = False

    if {"minimal", "dubby"} & norm:
        mode_name = "sub_anchor"
        density_min, density_max = 1, 3
        register_lo, register_hi = 32, 48
        strict_kick_avoid = True
        offbeat_only = False
    elif {"rolling", "groove", "hypnotic"} & norm:
        mode_name = "rolling_ostinato"
        density_min, density_max = 4, 8
        register_lo, register_hi = 36, 52
        strict_kick_avoid = True
        offbeat_only = False
    elif {"warehouse", "urgent", "industrial"} & norm:
        mode_name = "pocket_groove"
        density_min, density_max = 4, 10
        register_lo, register_hi = 34, 54
        strict_kick_avoid = False
        offbeat_only = False

    # Very low energy → bias toward sparse sub.
    if energy < 4 and mode_name in {"root_fifth", "pocket_groove"}:
        mode_name = "sub_anchor"
        density_min, density_max = 1, 3
        register_lo, register_hi = 32, 48
        strict_kick_avoid = True

    return BassModeConfig(
        name=mode_name,
        density_min=density_min,
        density_max=density_max,
        register_lo=register_lo,
        register_hi=register_hi,
        strict_kick_avoid=strict_kick_avoid,
        offbeat_only=offbeat_only,
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def generate_groove_bass(
    anchors: DrumAnchors,
    bpm: float,
    ppq: int,
    *,
    tags: Optional[Sequence[str]] = None,
    mode: Optional[str] = None,
    root_note: int = 45,
    bars: Optional[int] = None,
    swing_percent: float = 0.54,
) -> List[MidiEvent]:
    """Generate a simple groove-aware bassline using drum anchors.

    This first-pass implementation:
    - Chooses a mode based on tags + energy (or explicit override).
    - Places an anchor on step 0 for non-offbeat modes.
    - Uses drum-aware scoring to pick additional steps within per-mode
      density and kick-avoid rules.
    """

    grid = build_swung_grid(bpm, ppq)
    bar_ticks = grid.bar_ticks
    step_ticks = grid.step_ticks

    total_bars = bars if bars is not None else anchors.bar_count
    total_bars = max(1, min(total_bars, anchors.bar_count))

    energy = _compute_energy(anchors)
    mode_cfg = choose_mode(tags, energy)
    if mode:
        # Allow explicit override of mode name for tests / tooling.
        mode_lower = mode.strip().lower()
        if mode_lower == "sub_anchor":
            mode_cfg = BassModeConfig("sub_anchor", 1, 3, 32, 48, True, False)
        elif mode_lower in {"root_fifth", "root/5th"}:
            mode_cfg = BassModeConfig("root_fifth", 2, 6, 34, 52, True, False)
        elif mode_lower == "pocket_groove":
            mode_cfg = BassModeConfig("pocket_groove", 4, 10, 34, 54, False, False)
        elif mode_lower == "rolling_ostinato":
            mode_cfg = BassModeConfig("rolling_ostinato", 4, 8, 36, 52, True, False)
        elif mode_lower == "offbeat_stabs":
            mode_cfg = BassModeConfig("offbeat_stabs", 1, 3, 36, 55, True, True)
        elif mode_lower == "leadish":
            mode_cfg = BassModeConfig("leadish", 6, 12, 38, 62, False, False)

    events: List[MidiEvent] = []
    weights = SyncWeights()

    # Global root clamped to mode register.
    base_root = _clamp(root_note, mode_cfg.register_lo, mode_cfg.register_hi)

    for bar in range(total_bars):
        # Per-bar density target (midpoint within mode range with light energy mod).
        density_mid = (mode_cfg.density_min + mode_cfg.density_max) / 2.0
        if energy > 8:
            density_mid = min(mode_cfg.density_max, density_mid + 1)
        elif energy < 3:
            density_mid = max(mode_cfg.density_min, density_mid - 1)

        target_notes = int(round(density_mid))
        target_notes = max(mode_cfg.density_min, min(mode_cfg.density_max, target_notes))

        steps = 16
        bar_kicks = anchors.bar_kick_steps[bar] if bar < anchors.bar_count else []
        bar_snares = anchors.bar_snare_steps[bar] if bar < anchors.bar_count else []
        bar_hats = anchors.bar_hat_steps[bar] if bar < anchors.bar_count else []

        kick_mask = [0] * steps
        hat_mask = [0] * steps
        clap_mask = [0] * steps
        for s in bar_kicks:
            if 0 <= s < steps:
                kick_mask[s] = 1
        for s in bar_hats:
            if 0 <= s < steps:
                hat_mask[s] = 1
        for s in bar_snares:
            if 0 <= s < steps:
                clap_mask[s] = 1

        scores = score_steps(steps, kick_mask, hat_mask, clap_mask, weights)

        bar_root = base_root
        bar_fifth = _clamp(bar_root + 7, mode_cfg.register_lo, mode_cfg.register_hi)
        bar_start = bar * bar_ticks

        remaining = target_notes
        # Place an anchor at step 0 for non-offbeat modes.
        if not mode_cfg.offbeat_only:
            if mode_cfg.name == "sub_anchor":
                anchor_note = bar_root
            elif mode_cfg.name == "root_fifth":
                anchor_note = bar_root if bar % 2 == 0 else bar_fifth
            else:
                anchor_note = bar_root

            anchor_start = bar_start
            anchor_dur = max(1, int(round(1.0 * step_ticks)))
            events.append(
                MidiEvent(
                    note=anchor_note,
                    vel=100,
                    start_abs_tick=anchor_start,
                    dur_tick=anchor_dur,
                    channel=1,
                )
            )
            remaining = max(0, remaining - 1)

        if remaining == 0:
            continue

        forbidden: set[int] = set()
        if not mode_cfg.offbeat_only:
            forbidden.add(0)

        if mode_cfg.strict_kick_avoid:
            forbidden.update(s for s, v in enumerate(kick_mask) if v)

        if mode_cfg.offbeat_only:
            # Only allow 8th-note offbeats: steps 2,6,10,14.
            allowed_offbeats = {2, 6, 10, 14}
            forbidden.update(i for i in range(steps) if i not in allowed_offbeats)

        chosen = select_steps_by_score(scores, forbidden, remaining)

        for s in chosen:
            note = bar_root
            if mode_cfg.name in {"root_fifth", "pocket_groove", "rolling_ostinato"}:
                # Alternate root/fifth pattern for a bit of movement.
                note = bar_root if (s % 4) in (0, 1) else bar_fifth
            elif mode_cfg.name == "leadish":
                # Simple lead-ish: allow octave occasionally.
                note = (
                    bar_root
                    if s % 4 != 3
                    else _clamp(bar_root + 12, mode_cfg.register_lo, mode_cfg.register_hi)
                )

            start = bar_start + s * step_ticks
            dur = max(1, int(round(0.5 * step_ticks)))
            events.append(
                MidiEvent(
                    note=note,
                    vel=90,
                    start_abs_tick=start,
                    dur_tick=dur,
                    channel=1,
                )
            )

    return events
