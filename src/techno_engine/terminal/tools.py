from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict

import random
import hashlib
import re

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
    ListDocsOutput,
    ReadDocInput,
    ReadDocOutput,
    SearchDocsInput,
    SearchDocsOutput,
    SearchHit,
    DocAnswerInput,
    DocAnswerOutput,
    DocSource,
)
from techno_engine.config import engine_config_from_dict, EngineConfig
from techno_engine.parametric import LayerConfig, build_layer, collect_closed_hat_ticks
from techno_engine.controller import run_session
from techno_engine.scores import union_mask_for_bar, compute_E_S_from_mask
from techno_engine.bassline import generate_scored
from techno_engine.bass_validate import validate_bass
from techno_engine.key_mode import key_to_midi, normalize_mode
from techno_engine.bass_tools import (
    bass_generate as _bass_generate,
    bass_validate_lock as _bass_validate_lock,
    BassGenerateInput,
    BassValidateInput,
    API_VERSION as BASS_API_VERSION,
)


def render_session(inp: RenderSessionInput) -> RenderSessionOutput:
    inp.ensure_valid()
    cfg_data: Dict[str, Any]
    if inp.config_path:
        cfg_path = Path(inp.config_path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"config not found: {cfg_path}")
        cfg_data = json.loads(cfg_path.read_text())
    else:
        cfg_data = dict(inp.inline_config or {})
    engine_cfg, final_cfg = _prepare_engine_config(cfg_data)
    events = _render_events_for_config(engine_cfg)
    _, out_dir = ensure_dirs()
    out_path = safe_join(out_dir, f"{uuid.uuid4().hex}.mid")
    write_midi(events, ppq=engine_cfg.ppq, bpm=engine_cfg.bpm, out_path=str(out_path))
    return RenderSessionOutput(
        path=str(out_path), bpm=engine_cfg.bpm, bars=engine_cfg.bars,
        summary=f"{int(engine_cfg.bpm)} BPM, {engine_cfg.bars} bars; mode {engine_cfg.mode} rendered",
        config=final_cfg,
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
            "Docs & Q&A:\n"
            "  - ask about architecture/roadmap; the assistant can fetch docs.\n"
            "Local commands: :help, :quit, :about\n"
        )
    )


# Documentation tools (read-only)
_DOC_WHITELIST = [
    "README.md",
    "roadmap",
    "ROADMAP_CHECKLIST.md",
    "docs/ARCHITECTURE.md",
    "docs/TERMINAL_AI_ROADMAP.md",
    "docs/techno.1",
    "docs/BASSLINE_API.md",
]


_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "ben_klock": {
        "mode": "m4",
        "bpm": 128,
        "ppq": 1920,
        "bars": 32,
        "targets": {
            "E_target": 0.82,
            "S_low": 0.32,
            "S_high": 0.48,
            "hat_density_target": 0.78,
            "hat_density_tol": 0.08,
        },
        "guard": {"kick_immutable": False, "min_E": 0.75, "max_rot_rate": 0.12},
        "layers": {
            "kick": {
                "steps": 16,
                "fills": 6,
                "rot": 1,
                "velocity": 118,
                "ghost_pre1_prob": 0.35,
                "displace_into_2_prob": 0.22,
                "rotation_rate_per_bar": 0.05,
            },
            "hat_c": {
                "steps": 16,
                "fills": 12,
                "swing_percent": 0.56,
                "beat_bins_ms": [-12, -6, -2, 0],
                "beat_bins_probs": [0.35, 0.35, 0.2, 0.1],
                "ratchet_prob": 0.08,
            },
            "hat_o": {
                "steps": 16,
                "fills": 16,
                "offbeats_only": True,
                "ratchet_prob": 0.12,
                "choke_with_note": 42,
            },
            "snare": {
                "steps": 16,
                "fills": 2,
                "rot": 4,
                "velocity": 94,
                "ghost_pre1_prob": 0.12,
            },
            "clap": {
                "steps": 16,
                "fills": 2,
                "rot": 4,
                "velocity": 90,
            },
        },
        "modulators": [
            {
                "name": "hat_thin",
                "param_path": "hat_c.ratchet_prob",
                "mod": {
                    "mode": "random_walk",
                    "min_val": 0.05,
                    "max_val": 0.16,
                    "step_per_bar": 0.02,
                    "max_delta_per_bar": 0.02,
                },
            },
            {
                "name": "swing",
                "param_path": "hat_c.swing_percent",
                "mod": {
                    "mode": "ou",
                    "min_val": 0.54,
                    "max_val": 0.58,
                    "tau": 32.0,
                    "step_per_bar": 0.01,
                    "max_delta_per_bar": 0.01,
                },
            },
        ],
    },
    "ghost_kick": {
        "mode": "m4",
        "bpm": 130,
        "ppq": 1920,
        "bars": 32,
        "targets": {
            "E_target": 0.8,
            "S_low": 0.3,
            "S_high": 0.5,
            "hat_density_target": 0.72,
            "hat_density_tol": 0.08,
        },
        "guard": {"kick_immutable": False, "min_E": 0.72, "max_rot_rate": 0.1},
        "layers": {
            "kick": {
                "steps": 16,
                "fills": 4,
                "rot": 1,
                "velocity": 120,
                "ghost_pre1_prob": 0.6,
                "displace_into_2_prob": 0.25,
                "rotation_rate_per_bar": 0.04,
            },
            "hat_c": {
                "steps": 16,
                "fills": 14,
                "swing_percent": 0.55,
                "beat_bins_ms": [-10, -6, -2, 0],
                "beat_bins_probs": [0.3, 0.35, 0.2, 0.15],
                "ratchet_prob": 0.07,
            },
            "hat_o": {
                "steps": 16,
                "fills": 16,
                "offbeats_only": True,
                "ratchet_prob": 0.15,
                "choke_with_note": 42,
            },
        },
    },
}


def _deep_copy(data: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(data))


def _deep_update(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _expand_style(cfg_data: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _deep_copy(cfg_data)
    style = cfg.pop("style", None)
    if not style:
        return cfg
    key = str(style).strip().lower().replace(" ", "_")
    base = _STYLE_PRESETS.get(key)
    if not base:
        raise ValueError(f"unknown style '{style}'. Use list_docs to learn available styles or specify config params directly.")
    merged = _deep_copy(base)
    _deep_update(merged, cfg)
    merged["style"] = style
    return merged


def _prepare_engine_config(cfg_data: Dict[str, Any]) -> tuple[EngineConfig, Dict[str, Any]]:
    expanded = _expand_style(cfg_data)
    expanded.setdefault("mode", "m4")
    expanded.setdefault("ppq", 1920)
    expanded.setdefault("bars", 16)
    if "seed" not in expanded:
        expanded["seed"] = random.randint(1, 1_000_000)
    subset = EngineConfigSubset(
        mode=str(expanded.get("mode", "m4")),
        bpm=float(expanded.get("bpm", 132.0)),
        ppq=int(expanded.get("ppq", 1920)),
        bars=int(expanded.get("bars", 16)),
    )
    subset.validate()
    expanded["mode"] = subset.mode
    expanded["bpm"] = subset.bpm
    expanded["ppq"] = subset.ppq
    expanded["bars"] = subset.bars
    engine_cfg = engine_config_from_dict(expanded)
    return engine_cfg, expanded


def _render_events_for_config(engine_cfg: EngineConfig) -> list:
    if engine_cfg.mode == "m1":
        return build_backbone_events(bpm=engine_cfg.bpm, ppq=engine_cfg.ppq, bars=engine_cfg.bars)
    if engine_cfg.mode == "m2":
        kick = engine_cfg.kick or LayerConfig(steps=16, fills=4, note=36, velocity=110)
        hatc = engine_cfg.hat_c or LayerConfig(steps=16, fills=16, note=42, velocity=80, swing_percent=0.55,
                                               beat_bins_ms=[-10, -6, -2, 0], beat_bins_probs=[0.4, 0.35, 0.2, 0.05],
                                               beat_bin_cap_ms=12)
        hato = engine_cfg.hat_o or LayerConfig(steps=16, fills=16, note=46, velocity=80, offbeats_only=True,
                                               ratchet_prob=0.08, ratchet_repeat=3, swing_percent=0.55,
                                               beat_bins_ms=[-2, 0, 2], beat_bins_probs=[0.2, 0.6, 0.2], beat_bin_cap_ms=10,
                                               choke_with_note=42)
        snare = engine_cfg.snare or LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=96)
        clap = engine_cfg.clap or LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)
        ev_k = build_layer(engine_cfg.bpm, engine_cfg.ppq, engine_cfg.bars, kick)
        ev_hc = build_layer(engine_cfg.bpm, engine_cfg.ppq, engine_cfg.bars, hatc)
        ch_map = collect_closed_hat_ticks(ev_hc, engine_cfg.ppq, 42)
        ev_ho = build_layer(engine_cfg.bpm, engine_cfg.ppq, engine_cfg.bars, hato, closed_hat_ticks_by_bar=ch_map)
        ev_sn = build_layer(engine_cfg.bpm, engine_cfg.ppq, engine_cfg.bars, snare)
        ev_cl = build_layer(engine_cfg.bpm, engine_cfg.ppq, engine_cfg.bars, clap)
        return ev_k + ev_hc + ev_ho + ev_sn + ev_cl
    if engine_cfg.mode == "m4":
        rng = random.Random(engine_cfg.seed)
        res = run_session(
            bpm=engine_cfg.bpm,
            ppq=engine_cfg.ppq,
            bars=engine_cfg.bars,
            rng=rng,
            targets=engine_cfg.targets,
            guard=engine_cfg.guard,
            kick_layer_cfg=engine_cfg.kick,
            hat_c_cfg=engine_cfg.hat_c,
            hat_o_cfg=engine_cfg.hat_o,
            snare_cfg=engine_cfg.snare,
            clap_cfg=engine_cfg.clap,
            param_mods=engine_cfg.modulators,
            log_path=None,
        )
        events = []
        for layer_events in res.events_by_layer.values():
            events.extend(layer_events)
        return events
    raise ValueError(f"unsupported mode '{engine_cfg.mode}'")


def list_docs() -> ListDocsOutput:
    return ListDocsOutput(items=list(_DOC_WHITELIST))


def _resolve_doc_name(name: str) -> Path:
    p = Path(name)
    # enforce whitelist and normalized path
    norm = str(p.as_posix())
    if norm not in _DOC_WHITELIST:
        raise ValueError("unknown doc; use list_docs to see available items")
    return Path(norm)


def read_doc(inp: ReadDocInput) -> ReadDocOutput:
    path = _resolve_doc_name(inp.name)
    if not path.exists():
        raise FileNotFoundError(str(path))
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(1, int(inp.start_line)) if inp.start_line else 1
    max_lines = int(inp.max_lines) if inp.max_lines else 200
    start_idx = start - 1
    body = "\n".join(lines[start_idx:start_idx + max_lines])
    return ReadDocOutput(path=str(path), body=body)


def search_docs(inp: SearchDocsInput) -> SearchDocsOutput:
    q = (inp.query or "").strip()
    if not q:
        return SearchDocsOutput(results=[])
    ql = q.lower()
    results: list[SearchHit] = []
    maxr = int(inp.max_results) if inp.max_results else 10
    for item in _DOC_WHITELIST:
        p = Path(item)
        if not p.exists():
            continue
        for idx, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if ql in line.lower():
                snippet = line.strip()
                results.append(SearchHit(path=str(p), line=idx, snippet=snippet))
                if len(results) >= maxr:
                    return SearchDocsOutput(results=results)
    return SearchDocsOutput(results=results)


# Bassline tool wrappers (terminal-safe)
def bass_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    data = {**params}
    if "version" not in data:
        data["version"] = BASS_API_VERSION
    inp = BassGenerateInput(**data)
    return _bass_generate(inp)


def bass_validate(params: Dict[str, Any]) -> Dict[str, Any]:
    data = {**params}
    if "version" not in data:
        data["version"] = BASS_API_VERSION
    inp = BassValidateInput(**data)
    return _bass_validate_lock(inp)


def make_bass_for_config(params: Dict[str, Any]) -> Dict[str, Any]:
    """One-shot: render drums from config, build masks, generate+validate bass, write two files.

    Params:
      - config_path: str (required)
      - bass_out: str (optional)
      - drums_out: str (optional)
      - key: str (optional) e.g., 'A', 'D#', 'Eb'
      - mode: str (optional) 'minor'/'aeolian'/'dorian'
      - density: float (0..1)
      - root_note: int (fallback if key not provided)
    Returns: {drums: path, bass: path}
    """
    cfg_path = str(params.get("config_path", "")).strip()
    if not cfg_path:
        raise ValueError("config_path required")
    cfg = engine_config_from_dict(json.loads(Path(cfg_path).read_text()))
    # Render drums
    drum_events = _render_events_for_config(cfg)
    # Build masks per bar
    bar_ticks = cfg.ppq * 4
    def _slice(b):
        s = b * bar_ticks; e = s + bar_ticks
        return [ev for ev in drum_events if s <= ev.start_abs_tick < e]
    def _filter(evs, note):
        return [e for e in evs if e.note == note]
    kick_masks = []; hat_masks = []; clap_masks = []
    for b in range(cfg.bars):
        evs = _slice(b)
        kick_masks.append(union_mask_for_bar(_filter(evs, 36), cfg.ppq))
        hats = _filter(evs, 42) + _filter(evs, 46)
        hat_masks.append(union_mask_for_bar(hats, cfg.ppq))
        clap_masks.append(union_mask_for_bar(_filter(evs, 39), cfg.ppq))

    # Decide root note from key or fallback
    root = int(params.get("root_note", 45))
    key = params.get("key")
    try:
        if key:
            root = key_to_midi(str(key), base_octave=3)
    except Exception:
        pass
    degree = normalize_mode(params.get("mode"))
    density = float(params.get("density", 0.4))
    motif = params.get("motif")
    phrase = params.get("phrase")

    # Generate/validate bass
    bass = generate_scored(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars, root_note=root,
                           kick_masks_by_bar=kick_masks, hat_masks_by_bar=hat_masks, clap_masks_by_bar=clap_masks,
                           density_target=density, degree_mode=degree, motif=motif, phrase=phrase)
    val = validate_bass(bass, ppq=cfg.ppq, bpm=cfg.bpm, bars=cfg.bars, density_target=density)
    bass = val.events

    # Write files (optional prefix)
    _, out_dir = ensure_dirs()
    prefix = params.get("save_prefix")
    if prefix:
        base = Path(str(prefix)).stem
        drums_path = f"{base}_drums.mid"
        bass_path = f"{base}_bass.mid"
        drums_out = str(safe_join(out_dir, drums_path))
        bass_out = str(safe_join(out_dir, bass_path))
    else:
        drums_out = params.get("drums_out") or str(safe_join(out_dir, f"{uuid.uuid4().hex}_drums.mid"))
        bass_out = params.get("bass_out") or str(safe_join(out_dir, f"{uuid.uuid4().hex}_bass.mid"))
    write_midi(drum_events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=drums_out)
    write_midi(bass, ppq=cfg.ppq, bpm=cfg.bpm, out_path=bass_out)
    # Simple E/S medians for union
    es_list = []
    for b in range(cfg.bars):
        start = b * bar_ticks
        end = start + bar_ticks
        union = [e for e in drum_events if start <= e.start_abs_tick < end] + [e for e in bass if start <= e.start_abs_tick < end]
        if union:
            mask = union_mask_for_bar(union, cfg.ppq)
            es_list.append(compute_E_S_from_mask(mask))
    if es_list:
        E_med = sorted(e for e, _ in es_list)[len(es_list)//2]
        S_med = sorted(s for _, s in es_list)[len(es_list)//2]
    else:
        E_med = S_med = 0.0
    return {"drums": drums_out, "bass": bass_out, "summaries": val.summaries, "E_med": round(E_med, 3), "S_med": round(S_med, 3)}


def doc_answer(inp: DocAnswerInput) -> DocAnswerOutput:
    query = (inp.query or "").strip()
    if not query:
        return DocAnswerOutput(summary="No query provided.", sources=[])
    max_sources = max(1, int(inp.max_sources)) if inp.max_sources else 2
    context_window = max(2, int(inp.context_window)) if inp.context_window else 10
    hits = search_docs(SearchDocsInput(query=query, max_results=max_sources)).results
    if not hits:
        return DocAnswerOutput(summary=f"No documentation matches found for '{query}'.", sources=[])
    summaries: list[str] = []
    sources: list[DocSource] = []
    for hit in hits:
        start_line = max(1, hit.line - context_window)
        max_lines = context_window * 2
        body = read_doc(ReadDocInput(name=hit.path, start_line=start_line, max_lines=max_lines)).body
        excerpt = body.strip().replace("\n", " ")
        if len(excerpt) > 400:
            excerpt = excerpt[:397] + "..."
        summaries.append(f"{hit.path}:{hit.line}: {excerpt}")
        sources.append(DocSource(path=hit.path, line=hit.line))
    combined = " \n".join(summaries)
    return DocAnswerOutput(summary=combined, sources=sources)


def agent_handle(prompt: str) -> Dict[str, Any]:
    text = (prompt or "").strip()
    if not text:
        raise ValueError("prompt required")
    lowered = text.lower()

    if "save as" in lowered:
        save_match = re.search(r"save(?:\s+this)?\s+as\s+([\w\-.\/]+)", lowered)
        save_name = save_match.group(1) if save_match else None
    else:
        save_name = None

    if "ben klock" in lowered:
        style = "ben_klock"
    elif "ghost" in lowered:
        style = "ghost_kick"
    else:
        style = "ben_klock"

    cfg_data: Dict[str, Any] = {"style": style, "mode": "m4", "layers": {}}

    bpm_match = re.search(r"(\d+)\s*bpm", lowered)
    if bpm_match:
        cfg_data["bpm"] = int(bpm_match.group(1))

    bars_match = re.search(r"(\d+)\s*bars?", lowered)
    if bars_match:
        cfg_data["bars"] = int(bars_match.group(1))

    seed_match = re.search(r"seed\s*(\d+)", lowered)
    if seed_match:
        cfg_data["seed"] = int(seed_match.group(1))
    else:
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) % 1_000_000
        cfg_data["seed"] = seed

    kick_cfg = cfg_data.setdefault("layers", {}).setdefault("kick", {})
    if "ghost" in lowered:
        kick_cfg.setdefault("ghost_pre1_prob", 0.55)
        kick_cfg.setdefault("displace_into_2_prob", 0.22)
    if "more ghost" in lowered or "tons of ghost" in lowered:
        kick_cfg["ghost_pre1_prob"] = 0.7
        kick_cfg["displace_into_2_prob"] = 0.3
    if "variation" in lowered or "varied" in lowered:
        kick_cfg["rotation_rate_per_bar"] = 0.08
    if "ben klock" in lowered and "ghost" not in lowered:
        kick_cfg.setdefault("ghost_pre1_prob", 0.4)

    engine_cfg, final_cfg = _prepare_engine_config(cfg_data)
    events = _render_events_for_config(engine_cfg)

    cfg_dir, out_dir = ensure_dirs()
    midi_path = safe_join(out_dir, f"{uuid.uuid4().hex}.mid")
    write_midi(events, ppq=engine_cfg.ppq, bpm=engine_cfg.bpm, out_path=str(midi_path))

    if save_name:
        filename = Path(save_name).name
        if not filename.endswith(".json"):
            filename += ".json"
    else:
        filename = f"agent_{uuid.uuid4().hex}.json"
    config_path = safe_join(cfg_dir, filename)
    config_path.write_text(json.dumps(final_cfg, indent=2))

    summary = (
        f"{int(engine_cfg.bpm)} BPM, {engine_cfg.bars} bars; offline agent rendered style {final_cfg.get('style', style)}"
    )
    return {
        "summary": summary,
        "midi_path": str(midi_path),
        "config_path": str(config_path),
        "config": final_cfg,
    }
