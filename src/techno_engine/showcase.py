from __future__ import annotations

import argparse
import os
from typing import List, Tuple

from .combo_cli import main as combo_main, _render_drums_from_config
from .config import load_engine_config
from .scores import union_mask_for_bar, compute_E_S_from_mask
from .bassline import generate_scored, generate_mvp
from .midi_writer import MidiEvent
from .bass_validate import validate_bass
from .key_mode import key_to_midi, normalize_mode
import csv
import json
import datetime


def _scenarios(pack: str, quick: bool) -> List[Tuple[str, str, str, List[str]]]:
    """Return a list of (name, drum_cfg, drum_out, bass_out, extra_args) scenarios.

    Uses built-in configs and varies BPM/feel to showcase range.
    """
    items: List[Tuple[str, str, str, List[str]]] = []
    length_suffix = "_short" if quick else ""
    if pack == "default":
        items.extend([
            (f"syncopated_layers{length_suffix}", "configs/m4_syncopated_layers.json", "drums_sync.mid", ["--root_note", "45", "--density", "0.40"]),
            (f"low_bpm_95{length_suffix}", "configs/m4_95bpm.json", "drums_95.mid", ["--root_note", "40", "--density", "0.40", "--degree", "minor"]),
            (f"alien_bounce{length_suffix}", "configs/m4_alien_bounce.json", "drums_alien.mid", ["--root_note", "41", "--density", "0.36", "--degree", "minor"]),
            (f"ghosty_sync_hats{length_suffix}", "configs/m4_ghosty_sync_hats.json", "drums_ghosty.mid", ["--root_note", "43", "--density", "0.42", "--degree", "minor"]),
            (f"fast_kicks_140{length_suffix}", "configs/fast_kicks_140.json", "drums_fast.mid", ["--root_note", "45", "--density", "0.42"]),
        ])
    else:
        raise SystemExit(f"unknown pack: {pack}")
    return items


SCENARIO_DESCRIPTIONS = {
    "syncopated_layers": "128 BPM hypnotic rotation with scored bass.",
    "low_bpm_95": "95 BPM head-nod groove with minor colouring.",
    "alien_bounce": "126 BPM broken kick rotation with darker minor motif.",
    "ghosty_sync_hats": "128 BPM heavy ghost kicks and syncopated hats.",
    "fast_kicks_140": "140 BPM driving fast-kick showcase.",
}


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render a showcase pack of separate drum+bass MIDIs")
    p.add_argument("--pack", default="default", help="Showcase pack key (default)")
    p.add_argument("--outdir", default="out/showcase", help="Output directory root")
    p.add_argument("--quick", action="store_true", help="Render short versions (uses existing configs; bars are as-is for now)")
    p.add_argument("--key", type=str, default=None, help="Global bass key (e.g., A, D#, Eb)")
    p.add_argument("--mode", type=str, default=None, help="Global bass mode (minor/aeolian/dorian)")
    p.add_argument("--scenario", action="append", default=None, help="Limit to specific scenario name (use base name, e.g., syncopated_layers)")
    args = p.parse_args(argv)

    scenarios = _scenarios(args.pack, args.quick)
    if args.scenario:
        requested = {s.strip() for s in args.scenario if s and s.strip()}
        filtered = []
        seen = set()
        for name, cfg, drum_name, extra in scenarios:
            base = name.replace("_short", "")
            if name in requested or base in requested:
                filtered.append((name, cfg, drum_name, extra))
                seen.add(base)
        missing = requested - seen
        if missing:
            raise SystemExit(f"unknown scenario(s): {', '.join(sorted(missing))}")
        if filtered:
            scenarios = filtered
    os.makedirs(args.outdir, exist_ok=True)

    manifest_rows = []
    normalized_mode = normalize_mode(args.mode)
    for name, cfg, drum_name, extra in scenarios:
        base_name = name.replace("_short", "")
        drum_out = os.path.join(args.outdir, f"{name}_{drum_name}")
        bass_out = os.path.join(args.outdir, f"{name}_bass.mid")
        combo_args = [
            "--drum", cfg,
            "--drum_out", drum_out,
            "--bass_out", bass_out,
        ] + extra
        if args.key:
            combo_args += ["--key", args.key]
        if args.mode:
            combo_args += ["--mode", args.mode]
        # combo_cli defaults: bass_mode=scored, validate=True
        rc = combo_main(combo_args)
        if rc != 0:
            raise SystemExit(rc)
        # Compute simple union E,S medians for manifest by recomputing events
        cfg_obj = load_engine_config(cfg)
        drum_events = _render_drums_from_config(cfg_obj)
        # parse extras
        def _get_flag(flag: str, default: str | None = None) -> str | None:
            if flag in extra:
                try:
                    return extra[extra.index(flag) + 1]
                except Exception:
                    return default
            return default
        root_override = None
        if args.key:
            try:
                root_override = key_to_midi(args.key, base_octave=3)
            except Exception:
                root_override = None
        root_note = root_override if root_override is not None else int(_get_flag("--root_note", "45") or 45)
        density = float(_get_flag("--density", "0.4") or 0.4)
        degree = _get_flag("--degree", None)
        if normalized_mode:
            degree = normalized_mode
        # build masks
        bar_ticks = cfg_obj.ppq * 4
        kick_mask_by_bar = []
        hat_mask_by_bar = []
        clap_mask_by_bar = []
        for b in range(cfg_obj.bars):
            start = b * bar_ticks
            end = start + bar_ticks
            slice_evs = [e for e in drum_events if start <= e.start_abs_tick < end]
            def _filter(evs: List[MidiEvent], note: int) -> List[MidiEvent]:
                return [e for e in evs if e.note == note]
            kick_mask_by_bar.append(union_mask_for_bar(_filter(slice_evs, 36), cfg_obj.ppq))
            hats = _filter(slice_evs, 42) + _filter(slice_evs, 46)
            hat_mask_by_bar.append(union_mask_for_bar(hats, cfg_obj.ppq))
            clap_mask_by_bar.append(union_mask_for_bar(_filter(slice_evs, 39), cfg_obj.ppq))
        # generate bass similar to combo defaults (scored + validate)
        bass_events = generate_scored(bpm=cfg_obj.bpm, ppq=cfg_obj.ppq, bars=cfg_obj.bars, root_note=root_note,
                                      kick_masks_by_bar=kick_mask_by_bar, hat_masks_by_bar=hat_mask_by_bar,
                                      clap_masks_by_bar=clap_mask_by_bar, density_target=density,
                                      degree_mode=("minor" if degree == "minor" else None))
        val = validate_bass(bass_events, ppq=cfg_obj.ppq, bpm=cfg_obj.bpm, bars=cfg_obj.bars, density_target=density)
        bass_events = val.events
        # compute union per bar and median
        es_list = []
        for b in range(cfg_obj.bars):
            start = b * bar_ticks
            end = start + bar_ticks
            union = [e for e in drum_events if start <= e.start_abs_tick < end] + [e for e in bass_events if start <= e.start_abs_tick < end]
            mask = union_mask_for_bar(union, cfg_obj.ppq)
            es_list.append(compute_E_S_from_mask(mask))
        if es_list:
            E_med = sorted(e for e, _ in es_list)[len(es_list)//2]
            S_med = sorted(s for _, s in es_list)[len(es_list)//2]
        else:
            E_med = S_med = 0.0
        manifest_rows.append({
            "name": name,
            "bpm": int(cfg_obj.bpm),
            "bars": cfg_obj.bars,
            "drums": drum_out,
            "bass": bass_out,
            "E_med": round(E_med, 3),
            "S_med": round(S_med, 3),
            "key": args.key or "",
            "mode": normalized_mode or (degree or ""),
            "description": SCENARIO_DESCRIPTIONS.get(base_name, ""),
        })
    print(f"Wrote showcase to {args.outdir}")
    # write manifest CSV
    man_path = os.path.join(args.outdir, "manifest.csv")
    with open(man_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "bpm", "bars", "drums", "bass", "E_med", "S_med", "key", "mode", "description"])
        w.writeheader()
        w.writerows(manifest_rows)
    print(f"Manifest: {man_path}")
    man_json = os.path.join(args.outdir, "manifest.json")
    meta = {
        "generated_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "key": args.key,
        "mode": normalized_mode,
        "scenarios": manifest_rows,
    }
    with open(man_json, "w", encoding="utf-8") as jf:
        json.dump(meta, jf, indent=2)
    # write a simple HTML index
    idx = os.path.join(args.outdir, "index.html")
    with open(idx, "w", encoding="utf-8") as hf:
        hf.write("<html><head><meta charset='utf-8'><title>Showcase</title>")
        hf.write("<style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;padding:1.5rem;background:#fefefe;}table{border-collapse:collapse;width:100%;max-width:960px;margin-top:1rem;}th,td{border:1px solid #dcdcdc;padding:8px;text-align:left;}th{background:#f3f3f3;}tr:nth-child(even){background:#fafafa;}a{color:#0366d6;text-decoration:none;}a:hover{text-decoration:underline;}code{font-family:SFMono-Regular,Consolas,monospace;}</style>")
        hf.write("</head><body>\n")
        hf.write("<h1>Showcase Pack</h1>\n")
        if args.key or normalized_mode or args.scenario:
            hf.write("<p><strong>Filters:</strong> ")
            parts = []
            if args.key:
                parts.append(f"Key = {args.key}")
            if normalized_mode:
                parts.append(f"Mode = {normalized_mode}")
            if args.scenario:
                parts.append("Scenarios = " + ", ".join(args.scenario))
            hf.write(", ".join(parts) + "</p>\n")
        hf.write("<table>\n")
        hf.write("<tr><th>Name</th><th>Description</th><th>BPM</th><th>Bars</th><th>E_med</th><th>S_med</th><th>Key</th><th>Mode</th><th>Drums</th><th>Bass</th></tr>\n")
        for row in manifest_rows:
            hf.write(
                f"<tr><td>{row['name']}</td><td>{row.get('description','')}</td><td>{row['bpm']}</td><td>{row['bars']}</td>"
                f"<td>{row['E_med']}</td><td>{row['S_med']}</td><td>{row.get('key','')}</td><td>{row.get('mode','')}</td>"
                f"<td><a href='{os.path.basename(row['drums'])}'>{os.path.basename(row['drums'])}</a></td>"
                f"<td><a href='{os.path.basename(row['bass'])}'>{os.path.basename(row['bass'])}</a></td></tr>\n"
            )
        hf.write("</table>\n</body></html>\n")
    print(f"HTML index: {idx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
