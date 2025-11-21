from pathlib import Path

import mido

from techno_engine.drum_analysis import extract_drum_anchors
from techno_engine.leads.lead_engine import generate_lead, NoteEvent
from techno_engine.seeds import SeedMetadata


def _make_meta(bars: int, tags) -> SeedMetadata:
    return SeedMetadata(
        seed_id="behaviour_seed",
        created_at="2025-01-01T00:00:00Z",
        engine_mode="m4",
        bpm=130.0,
        bars=bars,
        ppq=1920,
        rng_seed=4242,
        config_path="config.json",
        render_path="drums/main.mid",
        log_path=None,
        prompt=None,
        prompt_context=None,
        summary=None,
        tags=tags,
        assets=[],
        parent_seed_id=None,
        file_version=1,
    )


def _write_simple_drums(tmp_path: Path, bars: int = 4) -> Path:
    mid = mido.MidiFile(ticks_per_beat=1920)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # Simple pattern: kick on 1, snare on 2 each bar.
    for b in range(bars):
        if b == 0:
            delta = 0
        else:
            delta = 1920 * 4
        track.append(mido.Message("note_on", note=36, velocity=100, time=delta))
        track.append(mido.Message("note_off", note=36, velocity=0, time=0))
        track.append(mido.Message("note_on", note=38, velocity=100, time=1920))
        track.append(mido.Message("note_off", note=38, velocity=0, time=0))
    path = tmp_path / "drums.mid"
    mid.save(path)
    return path


def test_minimal_stab_lead_density(tmp_path: Path):
    midi_path = _write_simple_drums(tmp_path, bars=2)
    anchors = extract_drum_anchors(midi_path, ppq=1920)
    meta = _make_meta(bars=2, tags=["minimal"])  # Minimal Stab Lead

    events = generate_lead(anchors, meta)
    assert events, "expected some events for minimal stab"

    # Ensure density roughly matches target (2-4 notes/bar).
    bar_ticks = anchors.bar_ticks
    counts = {}
    for ev in events:
        bar = ev.start_tick // bar_ticks
        counts[bar] = counts.get(bar, 0) + 1
    for bar, count in counts.items():
        assert 1 <= count <= 6  # allow a little wiggle


def test_rolling_arp_lead_density_and_register(tmp_path: Path):
    midi_path = _write_simple_drums(tmp_path, bars=4)
    anchors = extract_drum_anchors(midi_path, ppq=1920)
    meta = _make_meta(bars=4, tags=["rolling"])  # Rolling Arp Lead

    events = generate_lead(anchors, meta)
    assert events, "expected events for rolling arp"

    bar_ticks = anchors.bar_ticks
    counts = {}
    for ev in events:
        bar = ev.start_tick // bar_ticks
        counts[bar] = counts.get(bar, 0) + 1
        assert 68 <= ev.pitch <= 88

    # Rolling arp should be at least moderately busy.
    assert any(count >= 3 for count in counts.values())


def test_lyrical_lead_phrase_resolution(tmp_path: Path):
    midi_path = _write_simple_drums(tmp_path, bars=4)
    anchors = extract_drum_anchors(midi_path, ppq=1920)
    meta = _make_meta(bars=4, tags=["lyrical"])  # Lyrical Call/Response Lead

    events = generate_lead(anchors, meta)
    assert events, "expected events for lyrical lead"

    bar_ticks = anchors.bar_ticks
    bars_with_notes = {ev.start_tick // bar_ticks for ev in events}
    assert 0 in bars_with_notes and 3 in bars_with_notes

    # Final note should resolve near root within register of Lyrical mode (64..88).
    final = events[-1]
    assert 64 <= final.pitch <= 88
