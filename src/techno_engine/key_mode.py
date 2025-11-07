from __future__ import annotations

from typing import Optional

_NOTE_TO_SEMI = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


def key_to_midi(key: str, base_octave: int = 3) -> int:
    """Return MIDI note number for key at the given base octave (default C2=36).

    Examples:
      A (oct=2) -> 45, D# -> 39, Eb -> 39
    """
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    base = raw[0].upper()
    acc = raw[1:].strip()
    # Normalize common symbols
    acc = acc.replace("♭", "b").replace("♯", "#")
    if acc.startswith("b"):
        k = base + "b"
    elif acc.startswith("#"):
        k = base + "#"
    else:
        k = base
    if k not in _NOTE_TO_SEMI:
        raise ValueError(f"unknown key '{key}'")
    semi = _NOTE_TO_SEMI[k]
    return 12 * base_octave + semi


def normalize_mode(mode: Optional[str]) -> Optional[str]:
    if not mode:
        return None
    m = mode.strip().lower()
    if m in {"minor", "aeolian"}:
        return "minor"
    if m in {"dorian"}:
        return "dorian"
    return None
