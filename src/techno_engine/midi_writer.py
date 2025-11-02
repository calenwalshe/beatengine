from __future__ import annotations

from dataclasses import dataclass
from typing import List

try:
    from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo
except Exception:  # pragma: no cover - allows import in environments without mido
    Message = MidiFile = MidiTrack = MetaMessage = None  # type: ignore
    def bpm2tempo(bpm: float) -> int:  # type: ignore
        return int(60_000_000 / bpm)


@dataclass
class MidiEvent:
    note: int
    vel: int
    start_abs_tick: int
    dur_tick: int
    channel: int = 9  # GM percussion channel (10), zero-indexed


def _ensure_mido():
    if MidiFile is None or MidiTrack is None or Message is None or MetaMessage is None:
        raise RuntimeError(
            "mido is required to write MIDI files. Please install `mido`."
        )


def write_midi(events: List[MidiEvent], ppq: int, bpm: float, out_path: str) -> None:
    """
    Write a single-track MIDI file using absolute tick scheduling.
    Steps:
      - create track, set tempo meta
      - sort by (start_abs_tick, note_off before note_on)
      - delta-encode times
    """
    _ensure_mido()

    mid = MidiFile(type=1)  # multi-track compatible
    mid.ticks_per_beat = int(ppq)

    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(bpm), time=0))

    # Build note-on/off messages with absolute tick times
    msgs = []
    for ev in events:
        start = ev.start_abs_tick
        end = ev.start_abs_tick + max(1, ev.dur_tick)
        msgs.append((start, 0, Message("note_on", note=ev.note, velocity=ev.vel, channel=ev.channel, time=0)))
        msgs.append((end, 1, Message("note_off", note=ev.note, velocity=0, channel=ev.channel, time=0)))

    # Sort by time, and ensure note_off (1) comes before note_on (0) when same tick
    msgs.sort(key=lambda t: (t[0], t[1]))

    # Delta-encode
    last_t = 0
    for abs_t, _prio, msg in msgs:
        delta = abs_t - last_t
        msg.time = max(0, delta)
        track.append(msg)
        last_t = abs_t

    mid.save(out_path)

