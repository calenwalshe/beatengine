from __future__ import annotations

import argparse
import os

from .fred_spec import Spec
from .acid303 import render_303_over_drums, AcidParams


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render TB-303 style patterns over drums")
    p.add_argument("--out_prefix", default="out/fred_acid303", help="Output prefix for files")
    p.add_argument("--bpm", type=float, default=120.0)
    p.add_argument("--ppq", type=int, default=1920)
    p.add_argument("--bars", type=int, default=8)
    p.add_argument("--swing", type=float, default=0.60)
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--seed_base", type=int, default=1203)
    p.add_argument("--bend_semi", type=int, default=2, help="Assumed synth bend range in semitones for glides")
    args = p.parse_args(argv)

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    spec = Spec(bpm=args.bpm, ppq=args.ppq, bars=args.bars, swing_percent=args.swing)
    params = AcidParams(bend_semitones=args.bend_semi)
    for i in range(args.count):
        seed = args.seed_base + i
        out = f"{args.out_prefix}_{i+1:02d}.mid"
        render_303_over_drums(out_path=out, spec=spec, seed=seed, params=params)
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

