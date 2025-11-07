from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .midi_writer import MidiEvent
from .bassline import generate_mvp, generate_scored
from .bass_validate import validate_bass


API_VERSION = "v1"


STYLES: Dict[str, Dict[str, Any]] = {
    "sparse_root": {"mode": "mvp", "density": 0.30},
    "offbeat_scored": {"mode": "scored", "density": 0.45},
    "urgent_dense": {"mode": "scored", "density": 0.60},
}


@dataclass
class BassGenerateInput:
    version: str = API_VERSION
    bpm: float = 128.0
    ppq: int = 1920
    bars: int = 8
    seed: int = 1234
    mode: str = "mvp"  # or "scored"
    root_note: int = 45
    density: Optional[float] = 0.4
    min_dur_steps: float = 0.5
    style: Optional[str] = None
    # Optional drum masks for scored mode (list of 16-step masks per bar)
    kick_masks_by_bar: Optional[List[List[int]]] = None
    hat_masks_by_bar: Optional[List[List[int]]] = None
    clap_masks_by_bar: Optional[List[List[int]]] = None


@dataclass
class BassValidateInput:
    version: str = API_VERSION
    bpm: float = 128.0
    ppq: int = 1920
    bars: int = 8
    density: Optional[float] = 0.4
    events: List[Dict[str, int]] = field(default_factory=list)


def _serialize_events(evs: List[MidiEvent]) -> List[Dict[str, int]]:
    return [
        {
            "note": ev.note,
            "vel": ev.vel,
            "start_abs_tick": ev.start_abs_tick,
            "dur_tick": ev.dur_tick,
            "channel": ev.channel,
        }
        for ev in evs
    ]


def _deserialize_events(items: List[Dict[str, Any]]) -> List[MidiEvent]:
    out: List[MidiEvent] = []
    for it in items:
        out.append(
            MidiEvent(
                note=int(it.get("note", 45)),
                vel=int(it.get("vel", 90)),
                start_abs_tick=int(it.get("start_abs_tick", 0)),
                dur_tick=max(1, int(it.get("dur_tick", 120))),
                channel=int(it.get("channel", 1)),
            )
        )
    return out


def bass_generate(inp: BassGenerateInput) -> Dict[str, Any]:
    if inp.version != API_VERSION:
        return {"code": "VERSION_MISMATCH", "version": API_VERSION}
    if inp.ppq <= 0 or inp.bars <= 0 or inp.bpm <= 0:
        return {"code": "BAD_CONFIG", "error": "non-positive transport parameter"}
    # Apply style overrides if provided
    if inp.style:
        key = inp.style.strip().lower().replace(" ", "_")
        preset = STYLES.get(key)
        if not preset:
            return {"code": "BAD_CONFIG", "error": "unknown style"}
        if "mode" in preset:
            inp.mode = str(preset["mode"]).lower()
        if "density" in preset:
            inp.density = float(preset["density"])
    if inp.density is not None and (inp.density < 0.0 or inp.density > 1.0):
        return {"code": "BAD_CONFIG", "error": "density out of [0,1]"}
    try:
        if inp.mode == "mvp":
            evs = generate_mvp(
                bpm=inp.bpm,
                ppq=inp.ppq,
                bars=inp.bars,
                seed=inp.seed,
                root_note=inp.root_note,
                density_target=inp.density,
                min_dur_steps=inp.min_dur_steps,
            )
        elif inp.mode == "scored":
            if not inp.kick_masks_by_bar:
                return {"code": "BAD_CONFIG", "error": "scored mode requires kick_masks_by_bar"}
            evs = generate_scored(
                bpm=inp.bpm,
                ppq=inp.ppq,
                bars=inp.bars,
                root_note=inp.root_note,
                kick_masks_by_bar=inp.kick_masks_by_bar,
                hat_masks_by_bar=inp.hat_masks_by_bar,
                clap_masks_by_bar=inp.clap_masks_by_bar,
                density_target=inp.density,
                min_dur_steps=inp.min_dur_steps,
            )
        else:
            return {"code": "BAD_CONFIG", "error": "unknown mode"}
    except Exception as e:  # pragma: no cover
        return {"code": "ERROR", "error": str(e)}
    return {"code": "OK", "version": API_VERSION, "events": _serialize_events(evs)}


def bass_validate_lock(inp: BassValidateInput) -> Dict[str, Any]:
    if inp.version != API_VERSION:
        return {"code": "VERSION_MISMATCH", "version": API_VERSION}
    if inp.ppq <= 0 or inp.bars <= 0 or inp.bpm <= 0:
        return {"code": "BAD_CONFIG", "error": "non-positive transport parameter"}
    if inp.density is not None and (inp.density < 0.0 or inp.density > 1.0):
        return {"code": "BAD_CONFIG", "error": "density out of [0,1]"}
    try:
        evs = _deserialize_events(inp.events)
        res = validate_bass(evs, ppq=inp.ppq, bpm=inp.bpm, bars=inp.bars, density_target=inp.density)
    except Exception as e:  # pragma: no cover
        return {"code": "ERROR", "error": str(e)}
    return {"code": "OK", "version": API_VERSION, "events": _serialize_events(res.events), "summaries": res.summaries}
