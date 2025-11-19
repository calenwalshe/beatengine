from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RhythmEvent:
    step: int
    length: int
    anchor_type: str
    accent: bool = False


@dataclass
class RhythmTemplate:
    id: str
    mode_name: str
    motif_role: str  # CALL, CALL_VAR, RESP, RESP_VAR
    events: List[RhythmEvent]


@dataclass
class ContourTemplate:
    id: str
    mode_name: str
    motif_role: str
    intervals: List[int]
    emphasis_indices: List[int]
    shape: str


def load_rhythm_templates(raw: Dict[str, Dict]) -> List[RhythmTemplate]:
    """Parse rhythm templates from JSON-loaded dict.

    JSON structure is expected to be of the form:

    {
      "Mode Name": {
        "CALL": [ {"id": ..., "events": [...]}, ... ],
        "RESP": [ ... ]
      },
      ...
    }
    """

    templates: List[RhythmTemplate] = []
    for mode_name, by_role in (raw or {}).items():
        for role, templ_list in (by_role or {}).items():
            for entry in templ_list or []:
                events = [
                    RhythmEvent(
                        step=int(e.get("step", 0)),
                        length=int(e.get("length", 1)),
                        anchor_type=str(e.get("anchor_type", "")),
                        accent=bool(e.get("accent", False)),
                    )
                    for e in entry.get("events", [])
                ]
                templates.append(
                    RhythmTemplate(
                        id=str(entry.get("id", f"{mode_name}_{role}")),
                        mode_name=mode_name,
                        motif_role=role,
                        events=events,
                    )
                )
    return templates


def load_contour_templates(raw: Dict[str, Dict]) -> List[ContourTemplate]:
    """Parse contour templates from JSON-loaded dict.

    JSON structure mirrors `load_rhythm_templates` but uses contour fields.
    """

    templates: List[ContourTemplate] = []
    for mode_name, by_role in (raw or {}).items():
        for role, templ_list in (by_role or {}).items():
            for entry in templ_list or []:
                templates.append(
                    ContourTemplate(
                        id=str(entry.get("id", f"{mode_name}_{role}")),
                        mode_name=mode_name,
                        motif_role=role,
                        intervals=[int(i) for i in entry.get("intervals", [])],
                        emphasis_indices=[int(i) for i in entry.get("emphasis_indices", [])],
                        shape=str(entry.get("shape", "arch")),
                    )
                )
    return templates
