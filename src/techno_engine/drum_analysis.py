from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple


@dataclass
class DrumAnchors:
    """Lightweight summary of drum anchors and a 16-step grid per bar.

    All indices are 0-based. Bars are assumed to be 4/4 with 16 steps per bar.
    """

    ppq: int
    bar_count: int
    bar_ticks: int
    step_ticks: int

    # Per-event listings
    kick_steps: List[Tuple[int, int]]       # (bar, step)
    backbeat_steps: List[Tuple[int, int]]   # (bar, step)

    # Per-bar summaries
    bar_kick_steps: List[List[int]]         # steps 0-15
    bar_snare_steps: List[List[int]]
    bar_hat_steps: List[List[int]]

    # Slot tags per bar/step, e.g. {"kick", "near_kick_pre", "snare_zone"}
    slot_tags: List[List[Set[str]]]


def _iter_note_events(midi_path: Path) -> Tuple[int, List[Tuple[int, int]]]:
    """Return ticks_per_beat and a list of (tick, note) note_on events."""

    try:
        import mido
    except ImportError:  # pragma: no cover - guarded by requirements
        raise RuntimeError("mido is required for drum analysis")

    mf = mido.MidiFile(midi_path)
    ticks_per_beat = mf.ticks_per_beat

    events: List[Tuple[int, int]] = []
    for track in mf.tracks:
        tick = 0
        for msg in track:
            tick += int(getattr(msg, "time", 0))
            if getattr(msg, "type", None) != "note_on":
                continue
            if getattr(msg, "velocity", 0) <= 0:
                continue
            note = int(getattr(msg, "note", 0))
            events.append((tick, note))

    return ticks_per_beat, events


def extract_drum_anchors(midi_path: Path, ppq: int) -> DrumAnchors:
    """Extract kick/backbeat anchors and a 16-step summary from a drum MIDI.

    Assumes 4/4 bars with 16 logical steps per bar.
    """

    ticks_per_beat, events = _iter_note_events(midi_path)

    # Prefer the provided ppq, but sanity check against the file.
    ticks_per_beat = int(ppq or ticks_per_beat)

    bar_ticks = ticks_per_beat * 4
    step_ticks = max(1, bar_ticks // 16)

    if not events:
        # No events: return an empty single-bar structure.
        slot_tags = [[set() for _ in range(16)]]
        slot_tags[0][0].add("bar_start")
        slot_tags[0][15].add("bar_end")
        return DrumAnchors(
            ppq=ticks_per_beat,
            bar_count=1,
            bar_ticks=bar_ticks,
            step_ticks=step_ticks,
            kick_steps=[],
            backbeat_steps=[],
            bar_kick_steps=[[]],
            bar_snare_steps=[[]],
            bar_hat_steps=[[]],
            slot_tags=slot_tags,
        )

    max_tick = max(t for t, _ in events)
    bar_count = max(1, 1 + max_tick // bar_ticks)

    bar_kicks: List[List[int]] = [[] for _ in range(bar_count)]
    bar_snares: List[List[int]] = [[] for _ in range(bar_count)]
    bar_hats: List[List[int]] = [[] for _ in range(bar_count)]

    slot_tags: List[List[Set[str]]] = [
        [set() for _ in range(16)] for _ in range(bar_count)
    ]

    kick_steps: List[Tuple[int, int]] = []
    backbeat_steps: List[Tuple[int, int]] = []

    # Basic classification by MIDI note number.
    kick_notes = {36}
    snare_notes = {37, 38, 39, 40}
    hat_notes = {42, 44, 46}

    def _quantise_step(tick_in_bar: int) -> int:
        # Round to nearest 16th.
        step = int(round(tick_in_bar / step_ticks))
        if step < 0:
            return 0
        if step > 15:
            return 15
        return step

    for tick, note in events:
        bar = tick // bar_ticks
        if bar >= bar_count:
            bar = bar_count - 1
        tick_in_bar = tick - bar * bar_ticks
        step = _quantise_step(tick_in_bar)

        if note in kick_notes:
            bar_kicks[bar].append(step)
            kick_steps.append((bar, step))
            slot_tags[bar][step].add("kick")
        if note in snare_notes:
            bar_snares[bar].append(step)
            backbeat_steps.append((bar, step))
            slot_tags[bar][step].add("snare")
        if note in hat_notes:
            bar_hats[bar].append(step)
            slot_tags[bar][step].add("hat")

    # Tag bar_start / bar_end and near-kick / snare_zone markers.
    for bar in range(bar_count):
        slot_tags[bar][0].add("bar_start")
        slot_tags[bar][15].add("bar_end")

        # Near-kick tags.
        for step in bar_kicks[bar]:
            if step - 1 >= 0:
                slot_tags[bar][step - 1].add("near_kick_pre")
            if step + 1 <= 15:
                slot_tags[bar][step + 1].add("near_kick_post")

        # Snare zone: mark the snare step and its immediate neighbours.
        for step in bar_snares[bar]:
            slot_tags[bar][step].add("snare_zone")
            if step - 1 >= 0:
                slot_tags[bar][step - 1].add("snare_zone")
            if step + 1 <= 15:
                slot_tags[bar][step + 1].add("snare_zone")

    return DrumAnchors(
        ppq=ticks_per_beat,
        bar_count=bar_count,
        bar_ticks=bar_ticks,
        step_ticks=step_ticks,
        kick_steps=kick_steps,
        backbeat_steps=backbeat_steps,
        bar_kick_steps=bar_kicks,
        bar_snare_steps=bar_snares,
        bar_hat_steps=bar_hats,
        slot_tags=slot_tags,
    )
