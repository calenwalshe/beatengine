from __future__ import annotations

import argparse
import os

from .fred_spec import Spec
from .fred_kick_variants import build_kick_variants


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render 3 main-groove variants with subtle kick variation")
    p.add_argument("--out_prefix", default="out/fred_sync_kick", help="Output prefix")
    p.add_argument("--bpm", type=float, default=120.0)
    p.add_argument("--ppq", type=int, default=1920)
    p.add_argument("--bars", type=int, default=8)
    p.add_argument("--swing", type=float, default=0.60)
    p.add_argument("--seed_base", type=int, default=9701)
    p.add_argument("--heavy_duck", action="store_true", help="Use heavier ducking envelopes")
    args = p.parse_args(argv)

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    spec = Spec(bpm=args.bpm, ppq=args.ppq, bars=args.bars, swing_percent=args.swing)
    outs = build_kick_variants(out_prefix=args.out_prefix, spec=spec, seed_base=args.seed_base, heavy_duck=args.heavy_duck)
    print("Generated:")
    for pth in outs:
        print(" -", pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

