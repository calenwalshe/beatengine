from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict

from techno_engine.backbone import build_backbone_events
from techno_engine.midi_writer import write_midi
from techno_engine.terminal.fs_sandbox import ensure_dirs, safe_join, get_base_dirs
from techno_engine.terminal.schemas import (
    EngineConfigSubset,
    RenderSessionInput,
    RenderSessionOutput,
    CreateConfigInput,
    ReadConfigInput,
    WriteConfigInput,
    ListOutput,
    HelpInput,
    HelpOutput,
)


def render_session(inp: RenderSessionInput) -> RenderSessionOutput:
    inp.ensure_valid()
    cfg: Dict[str, Any]
    if inp.config_path:
        cfg_path = Path(inp.config_path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"config not found: {cfg_path}")
        cfg = json.loads(cfg_path.read_text())
    else:
        cfg = dict(inp.inline_config or {})

    subset = EngineConfigSubset(
        mode=str(cfg.get("mode", "m1")),
        bpm=float(cfg.get("bpm", 132.0)),
        ppq=int(cfg.get("ppq", 1920)),
        bars=int(cfg.get("bars", 8)),
    )
    subset.validate()

    # M1: render a deterministic backbone to keep the tool simple and predictable
    events = build_backbone_events(bpm=subset.bpm, ppq=subset.ppq, bars=subset.bars)
    _, out_dir = ensure_dirs()
    out_path = safe_join(out_dir, f"{uuid.uuid4().hex}.mid")
    write_midi(events, ppq=subset.ppq, bpm=subset.bpm, out_path=str(out_path))
    return RenderSessionOutput(
        path=str(out_path), bpm=subset.bpm, bars=subset.bars,
        summary=f"{int(subset.bpm)} BPM, {subset.bars} bars; deterministic backbone rendered",
    )


def create_config(inp: CreateConfigInput) -> Dict[str, str]:
    cfg_dir, _ = ensure_dirs()
    name = Path(inp.name).name  # prevent traversal
    path = safe_join(cfg_dir, name)
    if path.exists():
        raise FileExistsError(f"config already exists: {path}")
    body = json.dumps(inp.params, indent=2)
    path.write_text(body)
    return {"path": str(path)}


def list_configs() -> ListOutput:
    cfg_dir, _ = ensure_dirs()
    items = sorted([p.name for p in cfg_dir.glob("*.json")])
    return ListOutput(items=items)


def list_examples() -> ListOutput:
    # For now, same as list_configs (user examples live in configs/)
    return list_configs()


def read_config(inp: ReadConfigInput) -> Dict[str, str]:
    cfg_dir, _ = ensure_dirs()
    path = safe_join(cfg_dir, Path(inp.name).name)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return {"path": str(path), "body": path.read_text()}


def write_config(inp: WriteConfigInput) -> Dict[str, str]:
    # Validate JSON body
    try:
        parsed = json.loads(inp.body)
    except json.JSONDecodeError as e:
        raise ValueError("invalid JSON body") from e
    cfg_dir, _ = ensure_dirs()
    path = safe_join(cfg_dir, Path(inp.name).name)
    path.write_text(json.dumps(parsed, indent=2))
    return {"path": str(path)}


def help_text(inp: HelpInput | None = None) -> HelpOutput:
    return HelpOutput(
        usage=(
            "Examples:\n"
            "  - 'make a 64-bar groove at 132 bpm with crash lifts'\n"
            "  - 'save this as configs/name.json'\n"
            "  - 'render configs/name.json'\n"
            "Local commands: :help, :quit, :about\n"
        )
    )

