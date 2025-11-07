from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from .midi_writer import write_midi
from .bassline import generate_mvp


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate MVP bassline and write MIDI (Step 3)")
    parser.add_argument("--config", required=True, help="Path to JSON config with bpm, ppq, bars, seed, out, root_note?")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    bpm = float(cfg.get("bpm", 128))
    ppq = int(cfg.get("ppq", 1920))
    bars = int(cfg.get("bars", 4))
    seed = int(cfg.get("seed", 1234))
    out_path = str(cfg.get("out", "out/bass_mvp.mid"))
    root_note = int(cfg.get("root_note", 45))

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    events = generate_mvp(bpm=bpm, ppq=ppq, bars=bars, seed=seed, root_note=root_note)
    write_midi(events, ppq=ppq, bpm=bpm, out_path=out_path)
    print(f"Wrote bassline MIDI to {out_path} (bpm={bpm}, ppq={ppq}, bars={bars})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

