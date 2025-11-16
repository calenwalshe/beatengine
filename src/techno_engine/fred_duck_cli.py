from __future__ import annotations

import argparse
import os

from .fred_spec import Spec, build_song, _ducking_cc
from .midi_writer import write_midi_with_controls, CCEvent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render heavy-ducked main groove variants")
    p.add_argument("--out_prefix", default="out/fred_big_duck", help="Output prefix for files")
    p.add_argument("--bpm", type=float, default=120.0)
    p.add_argument("--ppq", type=int, default=1920)
    p.add_argument("--bars", type=int, default=8)
    p.add_argument("--swing", type=float, default=0.60)
    p.add_argument("--count", type=int, default=3, help="How many seeds to render")
    p.add_argument("--seed_base", type=int, default=8001, help="Base seed; seeds increment by 1")
    p.add_argument("--bass_depth", type=int, default=115, help="Depth of CC11 duck on bass (0-127; higher=deeper)")
    p.add_argument("--chord_depth", type=int, default=85, help="Depth of CC11 duck on chords (0-127)")
    p.add_argument("--melody_depth", type=int, default=70, help="Optional depth of CC11 duck on melody (0-127)")
    p.add_argument("--duck_melody", action="store_true", help="Also duck the melody channel")
    args = p.parse_args(argv)

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    spec = Spec(bpm=args.bpm, ppq=args.ppq, bars=args.bars, swing_percent=args.swing)

    for i in range(args.count):
        seed = args.seed_base + i
        notes, mel_cc = build_song(spec, seed=seed)
        # Replace default ducks with heavy ones
        ccs: list[CCEvent] = []
        ccs += _ducking_cc(spec, channel=2, depth=args.chord_depth)
        ccs += _ducking_cc(spec, channel=1, depth=args.bass_depth)
        if args.duck_melody and args.melody_depth > 0:
            ccs += _ducking_cc(spec, channel=3, depth=args.melody_depth)
        # Keep melody brightness CC74 from build_song
        ccs += mel_cc
        out_path = f"{args.out_prefix}_{i+1:02d}.mid"
        write_midi_with_controls(notes=notes, ppq=spec.ppq, bpm=spec.bpm, out_path=out_path, controls=ccs)
        print(f"Wrote {out_path} (seed={seed}, big duck)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

