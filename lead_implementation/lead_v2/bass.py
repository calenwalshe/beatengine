from __future__ import annotations

from typing import List, Any, Iterable, Tuple, Optional
from random import Random

from .theory import LeadNoteEvent, KeySpec, allowed_pitch_classes


def _normalise_bass_events(bass_midi: Any) -> List[Tuple[int, int, int]]:
    events: List[Tuple[int, int, int]] = []
    if not bass_midi:
        return events
    iterable: Iterable[Any]
    if isinstance(bass_midi, Iterable):
        iterable = bass_midi
    else:
        iterable = [bass_midi]
    for ev in iterable:
        if ev is None:
            continue
        start = getattr(ev, "start_tick", None)
        duration = getattr(ev, "duration", None)
        pitch = getattr(ev, "pitch", None)
        if start is None and isinstance(ev, dict):
            start = ev.get("start_tick")
        if duration is None and isinstance(ev, dict):
            duration = ev.get("duration")
        if pitch is None and isinstance(ev, dict):
            pitch = ev.get("pitch")
        if start is None or duration is None or pitch is None:
            continue
        start_i = int(start)
        duration_i = max(1, int(duration))
        pitch_i = int(pitch)
        events.append((start_i, start_i + duration_i, pitch_i))
    return events


def _find_alternate_pitch(
    current: int,
    overlaps: List[Tuple[int, int, int]],
    allowed_pcs: List[int],
    root_pc: int,
    register_low: int,
    register_high: int,
    min_semitone_distance: int,
    avoid_root_on_bass_hits: bool,
    rng: Random,
) -> Optional[int]:
    directions = [1, -1]
    rng.shuffle(directions)
    for direction in directions:
        candidate = current
        while register_low <= candidate <= register_high:
            candidate += direction
            if candidate < register_low or candidate > register_high:
                break
            pc = candidate % 12
            if pc not in allowed_pcs:
                continue
            if avoid_root_on_bass_hits and pc == root_pc:
                continue
            if all(abs(candidate - bass_pitch) >= min_semitone_distance for _, _, bass_pitch in overlaps):
                return candidate
    return None


def apply_bass_interaction(
    lead_events: List[LeadNoteEvent],
    bass_midi: Any,
    key: KeySpec,
    register_low: int,
    register_high: int,
    min_semitone_distance: int,
    avoid_root_on_bass_hits: bool,
    rng: Random,
) -> List[LeadNoteEvent]:
    """Adjust lead events to avoid clashing with bass."""

    bass_events = _normalise_bass_events(bass_midi)
    if not bass_events:
        return lead_events

    allowed = allowed_pitch_classes(key)

    for ev in lead_events:
        start = ev.start_tick
        end = ev.start_tick + ev.duration
        overlapping = [
            (bass_start, bass_end, bass_pitch)
            for bass_start, bass_end, bass_pitch in bass_events
            if not (bass_end <= start or bass_start >= end)
        ]
        if not overlapping:
            continue

        needs_adjustment = False
        for _, _, bass_pitch in overlapping:
            if abs(ev.pitch - bass_pitch) < min_semitone_distance:
                needs_adjustment = True
                break
            if avoid_root_on_bass_hits and ev.pitch % 12 == key.root_pc:
                needs_adjustment = True
                break

        if not needs_adjustment:
            continue

        new_pitch = _find_alternate_pitch(
            current=ev.pitch,
            overlaps=overlapping,
            allowed_pcs=allowed,
            root_pc=key.root_pc,
            register_low=register_low,
            register_high=register_high,
            min_semitone_distance=min_semitone_distance,
            avoid_root_on_bass_hits=avoid_root_on_bass_hits,
            rng=rng,
        )
        if new_pitch is not None:
            ev.pitch = new_pitch
            ev.tags["bass_adjusted"] = True
        else:
            ev.tags["bass_conflict_unresolved"] = True

    return lead_events
