from __future__ import annotations

import argparse
import os

from .fred_spec import Spec
from .fred_drums import render_vibes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render 5 drum-only candidates with humanized offbeat hats and ghost details")
    p.add_argument("--out_prefix", default="out/fred_drums", help="Output prefix; files will be suffixed with numbered vibe names")
    p.add_argument("--bpm", type=float, default=120.0, help="Tempo in BPM (default 120)")
    p.add_argument("--ppq", type=int, default=1920, help="Ticks per quarter note (PPQ)")
    p.add_argument("--bars", type=int, default=8, help="Number of bars to render (default 8)")
    p.add_argument("--seed", type=int, default=7001, help="Base random seed for variations")
    args = p.parse_args(argv)

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    spec = Spec(bpm=args.bpm, ppq=args.ppq, bars=args.bars)
    outputs = render_vibes(out_prefix=args.out_prefix, spec=spec, seed=args.seed)
    print("Generated:")
    for pth in outputs:
        print(" -", pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

