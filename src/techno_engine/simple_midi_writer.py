"""Simple MIDI writer without external dependencies.

Creates basic MIDI files from note events.
"""
import struct
from typing import List, Tuple


def write_variable_length(value: int) -> bytes:
    """Write a variable-length quantity (MIDI format)."""
    result = bytearray()
    result.append(value & 0x7F)
    value >>= 7
    while value > 0:
        result.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(result)


def write_simple_midi(notes: List[Tuple[int, int, int, int]], bpm: float, filename: str):
    """Write a simple MIDI file.

    Args:
        notes: List of (note_number, start_tick, duration_tick, velocity)
        bpm: Tempo in beats per minute
        filename: Output filename
    """
    ppq = 480  # Pulses per quarter note

    # MIDI file header
    header = b'MThd'
    header += struct.pack('>I', 6)  # Header length
    header += struct.pack('>H', 0)  # Format type 0
    header += struct.pack('>H', 1)  # Number of tracks
    header += struct.pack('>H', ppq)  # Ticks per quarter note

    # Build track events
    events = []

    # Set tempo event
    tempo = int(60_000_000 / bpm)
    tempo_bytes = struct.pack('>I', tempo)[1:]  # 3 bytes
    events.append((0, b'\xFF\x51\x03' + tempo_bytes))

    # Add note events
    for note_num, start_tick, dur_tick, velocity in notes:
        # Note on
        events.append((start_tick, bytes([0x90, note_num & 0x7F, velocity & 0x7F])))
        # Note off
        events.append((start_tick + dur_tick, bytes([0x80, note_num & 0x7F, 0x40])))

    # Sort events by time
    events.sort(key=lambda x: (x[0], x[1][0] & 0xF0))  # Time, then event type

    # Convert to delta times
    track_data = bytearray()
    last_tick = 0
    for tick, event_bytes in events:
        delta = tick - last_tick
        track_data.extend(write_variable_length(delta))
        track_data.extend(event_bytes)
        last_tick = tick

    # End of track
    track_data.extend(b'\x00\xFF\x2F\x00')

    # Track header
    track = b'MTrk'
    track += struct.pack('>I', len(track_data))
    track += track_data

    # Write file
    with open(filename, 'wb') as f:
        f.write(header)
        f.write(track)


def write_multi_channel_midi(
    tracks: List[List[Tuple[int, int, int, int, int]]],
    bpm: float,
    filename: str
):
    """Write a multi-track MIDI file.

    Args:
        tracks: List of tracks, each containing (note, start_tick, dur_tick, velocity, channel)
        bpm: Tempo
        filename: Output filename
    """
    ppq = 480

    # MIDI file header (format 1 for multiple tracks)
    header = b'MThd'
    header += struct.pack('>I', 6)
    header += struct.pack('>H', 1)  # Format type 1
    header += struct.pack('>H', len(tracks))  # Number of tracks
    header += struct.pack('>H', ppq)

    all_track_data = bytearray()

    for track_notes in tracks:
        events = []

        # First track gets tempo
        if tracks.index(track_notes) == 0:
            tempo = int(60_000_000 / bpm)
            tempo_bytes = struct.pack('>I', tempo)[1:]
            events.append((0, b'\xFF\x51\x03' + tempo_bytes))

        # Add note events for this track
        for note_num, start_tick, dur_tick, velocity, channel in track_notes:
            channel = channel & 0x0F
            events.append((start_tick, bytes([0x90 | channel, note_num & 0x7F, velocity & 0x7F])))
            events.append((start_tick + dur_tick, bytes([0x80 | channel, note_num & 0x7F, 0x40])))

        # Sort events
        events.sort(key=lambda x: (x[0], x[1][0] & 0xF0))

        # Convert to delta times
        track_data = bytearray()
        last_tick = 0
        for tick, event_bytes in events:
            delta = tick - last_tick
            track_data.extend(write_variable_length(delta))
            track_data.extend(event_bytes)
            last_tick = tick

        # End of track
        track_data.extend(b'\x00\xFF\x2F\x00')

        # Track header
        track_chunk = b'MTrk'
        track_chunk += struct.pack('>I', len(track_data))
        track_chunk += track_data
        all_track_data.extend(track_chunk)

    # Write file
    with open(filename, 'wb') as f:
        f.write(header)
        f.write(all_track_data)
