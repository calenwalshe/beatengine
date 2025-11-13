#!/usr/bin/env python3
from __future__ import annotations

"""
Utility for generating an eight-pack of 135 BPM drum grooves that sweep up/down an
energy gradient. Each variation tweaks hat density, open-hat placements, claps,
and ghost details so agents or users can audition rising tension quickly.

Example:
    PYTHONPATH=src python scripts/make_energy_gradient_pack.py \
        --out_dir out/energy_gradient --bars 2 --bpm 135
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from techno_engine.midi_writer import MidiEvent, write_midi
from techno_engine.timebase import ticks_per_bar


STEP_COUNT = 16
KICK_STEPS = [0, 4, 8, 12]
SNARE_STEPS = [4, 12]
CHH_EIGHTHS = [0, 2, 4, 6, 8, 10, 12, 14]
GHOST_STEPS = [1, 5, 9, 13]


@dataclass(frozen=True)
class Profile:
    label: str
    description: str
    energy_hint: int
    chh_vel: float
    open_vel: float
    ghost_hats: bool = False
    sixteenth_fill: bool = False
    clap: bool = False
    crash: bool = False
    open_hat_all: Iterable[int] | None = None
    open_hat_even_bars: Iterable[int] | None = None
    snare_fill_steps: Iterable[int] | None = None
    rim_steps: Iterable[int] | None = None
    pedal_hat_steps: Iterable[int] | None = None
    ghost_vel: float = 0.5
    sixteenth_vel: float = 0.6
    snare_fill_vel: float = 0.72
    rim_vel: float = 0.6
    pedal_hat_vel: float = 0.55


def _profiles() -> List[Profile]:
    return [
        Profile(
            label="energy01_intro_base",
            description="Base groove with 8th-note closed hats and an open-hat pickup every second bar.",
            energy_hint=1,
            chh_vel=0.65,
            open_vel=0.78,
            open_hat_even_bars=[15],
        ),
        Profile(
            label="energy02_edge_warmup",
            description="Adds soft sixteenth ghost hats for a gentle lift; open hat still every other bar.",
            energy_hint=2,
            chh_vel=0.66,
            open_vel=0.78,
            ghost_hats=True,
            open_hat_even_bars=[15],
        ),
        Profile(
            label="energy03_momentum",
            description="Momentum boost: ghost hats plus open-hat pickups at the end of every bar.",
            energy_hint=3,
            chh_vel=0.70,
            open_vel=0.80,
            ghost_hats=True,
            open_hat_all=[15],
        ),
        Profile(
            label="energy04_push_forward",
            description="Forward-driving clap layer and open hats on beat 4's and, keeping the lift building.",
            energy_hint=4,
            chh_vel=0.72,
            open_vel=0.82,
            ghost_hats=True,
            clap=True,
            open_hat_all=[14, 15],
        ),
        Profile(
            label="energy05_peak_strike",
            description="Peak energy: full 16th hats, extra open-hat syncopations, rim shots, and a crash accent.",
            energy_hint=5,
            chh_vel=0.75,
            open_vel=0.85,
            sixteenth_fill=True,
            clap=True,
            snare_fill_steps=[11, 15],
            rim_steps=[2, 6, 10, 14],
            crash=True,
            open_hat_all=[11, 14, 15],
        ),
        Profile(
            label="energy06_release_glide",
            description="Energy steps down: still dense hats and claps but with fewer syncopations and a single snare pickup.",
            energy_hint=4,
            chh_vel=0.70,
            open_vel=0.82,
            sixteenth_fill=True,
            clap=True,
            snare_fill_steps=[11],
            rim_steps=[10],
            open_hat_all=[14, 15],
        ),
        Profile(
            label="energy07_afterglow",
            description="Cooling off with ghost hats, occasional rim hits, and open hats only on even bars.",
            energy_hint=3,
            chh_vel=0.67,
            open_vel=0.78,
            ghost_hats=True,
            rim_steps=[9],
            pedal_hat_steps=[6, 14],
            open_hat_even_bars=[15],
        ),
        Profile(
            label="energy08_outro_soft",
            description="Settles back near the intro vibe with a single pedal-hat accent and sparse open hats.",
            energy_hint=2,
            chh_vel=0.63,
            open_vel=0.76,
            pedal_hat_steps=[6],
            open_hat_even_bars=[15],
        ),
    ]


def _vel(value: float) -> int:
    return max(1, min(127, int(round(value * 127))))


def _add_note(
    events: List[MidiEvent],
    note: int,
    velocity: int,
    bar_idx: int,
    step_idx: int,
    step_ticks: int,
    bar_ticks: int,
    dur_steps: float = 1.0,
) -> None:
    start = bar_idx * bar_ticks + step_idx * step_ticks
    dur = max(1, int(round(dur_steps * step_ticks)))
    events.append(
        MidiEvent(note=note, vel=velocity, start_abs_tick=start, dur_tick=dur, channel=9)
    )


def _build_events(profile: Profile, bars: int, ppq: int, bpm: float) -> List[MidiEvent]:
    bar_ticks = ticks_per_bar(ppq, 4)
    step_ticks = bar_ticks // STEP_COUNT
    events: List[MidiEvent] = []
    kick_vel = _vel(0.90)
    snare_vel = _vel(0.90)
    clap_vel = _vel(0.88)

    for bar in range(bars):
        for step in KICK_STEPS:
            _add_note(events, 36, kick_vel, bar, step, step_ticks, bar_ticks)
        for step in SNARE_STEPS:
            _add_note(events, 38, snare_vel, bar, step, step_ticks, bar_ticks)
            if profile.clap:
                _add_note(events, 39, clap_vel, bar, step, step_ticks, bar_ticks)
        for step in profile.snare_fill_steps or []:
            _add_note(
                events,
                38,
                _vel(profile.snare_fill_vel),
                bar,
                step,
                step_ticks,
                bar_ticks,
                dur_steps=0.75,
            )
        for step in profile.rim_steps or []:
            _add_note(
                events,
                37,
                _vel(profile.rim_vel),
                bar,
                step,
                step_ticks,
                bar_ticks,
                dur_steps=0.5,
            )
        for step in profile.pedal_hat_steps or []:
            _add_note(
                events,
                44,
                _vel(profile.pedal_hat_vel),
                bar,
                step,
                step_ticks,
                bar_ticks,
                dur_steps=0.5,
            )

        chh_vel = _vel(profile.chh_vel)
        for step in CHH_EIGHTHS:
            _add_note(events, 42, chh_vel, bar, step, step_ticks, bar_ticks, dur_steps=0.5)

        if profile.ghost_hats:
            ghost_vel = _vel(profile.ghost_vel)
            for step in GHOST_STEPS:
                _add_note(
                    events, 42, ghost_vel, bar, step, step_ticks, bar_ticks, dur_steps=0.5
                )

        if profile.sixteenth_fill:
            sixteenth_vel = _vel(profile.sixteenth_vel)
            for step in range(STEP_COUNT):
                if step in CHH_EIGHTHS:
                    continue
                _add_note(
                    events,
                    42,
                    sixteenth_vel,
                    bar,
                    step,
                    step_ticks,
                    bar_ticks,
                    dur_steps=0.5,
                )

        open_steps = set(profile.open_hat_all or [])
        if (bar + 1) % 2 == 0:
            open_steps.update(profile.open_hat_even_bars or [])
        open_vel = _vel(profile.open_vel)
        for step in sorted(open_steps):
            _add_note(events, 46, open_vel, bar, step, step_ticks, bar_ticks, dur_steps=0.75)

    if profile.crash:
        crash_vel = _vel(0.95)
        _add_note(events, 49, crash_vel, 0, 0, step_ticks, bar_ticks, dur_steps=1.5)

    events.sort(key=lambda ev: (ev.start_abs_tick, ev.note))
    return events


def generate_pack(out_dir: Path, ppq: int, bpm: float, bars: int) -> List[Dict[str, str]]:
    manifest: List[Dict[str, str]] = []
    for profile in _profiles():
        events = _build_events(profile, bars=bars, ppq=ppq, bpm=bpm)
        out_path = out_dir / f"{profile.label}.mid"
        write_midi(events, ppq=ppq, bpm=bpm, out_path=str(out_path))
        manifest.append(
            {
                "file": str(out_path),
                "label": profile.label,
                "description": profile.description,
                "energy_hint": profile.energy_hint,
                "bpm": bpm,
                "bars": bars,
            }
        )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an energy-gradient drum groove demo pack."
    )
    parser.add_argument("--out_dir", default="out/energy_gradient", help="Where to save the pack.")
    parser.add_argument("--ppq", type=int, default=1920, help="Ticks per quarter note (default 1920).")
    parser.add_argument("--bpm", type=float, default=135.0, help="Tempo in BPM (default 135).")
    parser.add_argument(
        "--bars",
        type=int,
        default=2,
        help="Bars per groove (default 2; must be >=2 to preserve even-bar pickups).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bars < 2:
        raise SystemExit("bars must be >= 2 so that even-bar open hats are possible.")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = generate_pack(out_dir=out_dir, ppq=args.ppq, bpm=args.bpm, bars=args.bars)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(manifest)} grooves to {out_dir} (manifest: {manifest_path})")


if __name__ == "__main__":
    main()
