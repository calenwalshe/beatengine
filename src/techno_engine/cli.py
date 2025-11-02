from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any, Dict, List

from .timebase import ticks_per_bar, ticks_per_beat
from .midi_writer import MidiEvent, write_midi


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def build_metronome_events(bpm: float, ppq: int, bars: int) -> List[MidiEvent]:
    events: List[MidiEvent] = []
    tpb = ticks_per_bar(ppq, 4)
    tpb_beats = ticks_per_beat(ppq)

    # Use GM percussion notes: 76 = Hi Wood Block (downbeat), 77 = Low Wood Block
    for bar in range(bars):
        bar_start = bar * tpb
        for beat in range(4):
            start = bar_start + beat * tpb_beats
            note = 76 if beat == 0 else 77
            vel = 110 if beat == 0 else 90
            events.append(MidiEvent(note=note, vel=vel, start_abs_tick=start, dur_tick=int(0.25 * tpb_beats), channel=9))
    return events


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a 4-clicks/bar metronome to MIDI (M0)")
    parser.add_argument("--config", required=True, help="Path to JSON config with bpm, ppq, bars, seed, out")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    bpm = float(cfg.get("bpm", 132))
    ppq = int(cfg.get("ppq", 1920))
    bars = int(cfg.get("bars", 8))
    seed = int(cfg.get("seed", 1234))
    out_path = cfg.get("out", "out/metronome.mid")

    random.seed(seed)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    events = build_metronome_events(bpm=bpm, ppq=ppq, bars=bars)
    write_midi(events, ppq=ppq, bpm=bpm, out_path=out_path)
    print(f"Wrote metronome MIDI to {out_path} (bpm={bpm}, ppq={ppq}, bars={bars})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

