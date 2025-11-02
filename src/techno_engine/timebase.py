from __future__ import annotations

"""
Timebase utilities for converting between milliseconds and MIDI ticks.

Assumes PPQ (ticks per quarter note) and BPM are provided.
"""

def ticks_per_second(ppq: int, bpm: float) -> float:
    """Compute ticks per second for given PPQ and BPM.

    One quarter note lasts 60/BPM seconds. With PPQ ticks per quarter note,
    ticks per second = PPQ / (60/BPM) = PPQ * BPM / 60.
    """
    return (ppq * bpm) / 60.0


def ticks_per_ms(ppq: int, bpm: float) -> float:
    """Compute ticks per millisecond for given PPQ and BPM."""
    return ticks_per_second(ppq, bpm) / 1000.0


def ms_to_ticks(ms: float, ppq: int, bpm: float) -> int:
    """Convert milliseconds to integer ticks (rounded)."""
    return int(round(ms * ticks_per_ms(ppq, bpm)))


def ticks_to_ms(ticks: int, ppq: int, bpm: float) -> float:
    """Convert ticks to milliseconds (float)."""
    return float(ticks) / ticks_per_ms(ppq, bpm)


def ticks_per_beat(ppq: int) -> int:
    """Ticks per quarter note (beat)."""
    return int(ppq)


def ticks_per_bar(ppq: int, beats_per_bar: int = 4) -> int:
    """Ticks per bar given PPQ and time signature (default 4/4)."""
    return ticks_per_beat(ppq) * beats_per_bar

