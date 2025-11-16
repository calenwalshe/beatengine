from __future__ import annotations

import argparse
import os

from .fred_spec import Spec, render_to_file


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render an 8-bar Fred-again style groove with swing, ducking, and velocity-shaping")
    p.add_argument("--out", default="out/fred_again_groove.mid", help="Output MIDI path")
    p.add_argument("--bpm", type=float, default=120.0, help="Tempo in BPM (default 120)")
    p.add_argument("--ppq", type=int, default=1920, help="Ticks per quarter note (PPQ)")
    p.add_argument("--bars", type=int, default=8, help="Number of bars to render (default 8)")
    p.add_argument("--swing", type=float, default=0.60, help="Swing percent (0.5=straight, 0.60=60% swing)")
    p.add_argument("--seed", type=int, default=6061, help="Random seed for small variations")
    p.add_argument("--variant16", action="store_true", help="Also write a 16-bar variant with passing notes only in bars 9-16")
    args = p.parse_args(argv)

    spec = Spec(bpm=args.bpm, ppq=args.ppq, bars=args.bars, swing_percent=args.swing)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    render_to_file(out_path=args.out, spec=spec, seed=args.seed)
    print(f"Wrote MIDI to {args.out} (bpm={args.bpm}, ppq={args.ppq}, bars={args.bars}, swing={args.swing:.2f})")

    if args.variant16:
        # Write an extended variant where passing notes appear only in the second 8 bars
        spec16 = Spec(bpm=args.bpm, ppq=args.ppq, bars=16, swing_percent=args.swing)
        base, ext = os.path.splitext(args.out)
        out16 = f"{base}_16bar_variant{ext or '.mid'}"
        render_to_file(out_path=out16, spec=spec16, seed=args.seed, variant_every_other=True)
        print(f"Wrote variant to {out16} (16 bars; passing notes in bars 9-16)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
