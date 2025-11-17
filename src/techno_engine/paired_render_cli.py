from __future__ import annotations

import argparse
import os
import random
from itertools import chain
from pathlib import Path
from typing import List, Optional

from .backbone import build_backbone_events
from .config import load_engine_config
from .controller import run_session
from .drum_analysis import extract_drum_anchors
from .groove_bass import generate_groove_bass
from .midi_writer import write_midi
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks
from .seeds import save_seed, rebuild_index


def _parse_tags(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    tags = [t.strip() for t in raw.split(",") if t.strip()]
    return tags or None


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render drums + groove-aware bass from JSON config (m1/m2/m4) and save as a seed",
    )
    parser.add_argument("--config", required=True, help="Path to JSON config (m1/m2/m4)")
    parser.add_argument(
        "--root-note",
        type=int,
        default=45,
        help="Bass root note (MIDI number, default: 45)",
    )
    parser.add_argument(
        "--bass-mode",
        default=None,
        help=(
            "Optional bass mode override (sub_anchor, root_fifth, pocket_groove, "
            "rolling_ostinato, offbeat_stabs, leadish)"
        ),
    )
    parser.add_argument(
        "--prompt-text",
        default=None,
        help="Optional prompt text stored in seed metadata",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help="Optional comma-separated tags for this seed (used for bass mode selection as well)",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Optional short natural-language summary of the beat",
    )
    parser.add_argument(
        "--parent-seed-id",
        default=None,
        help="Optional parent seed identifier when creating a derived seed",
    )

    args = parser.parse_args(argv)

    cfg = load_engine_config(args.config)
    random.seed(cfg.seed)

    # Render drums using the same semantics as run_config.main
    os.makedirs(os.path.dirname(cfg.out) or ".", exist_ok=True)
    mode = cfg.mode.lower()
    if mode == "m1":
        events = build_backbone_events(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars)
        write_midi(events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=cfg.out)
    elif mode == "m2":
        kick = cfg.kick or LayerConfig(steps=16, fills=4, note=36, velocity=110)
        hatc = cfg.hat_c or LayerConfig(
            steps=16,
            fills=16,
            note=42,
            velocity=80,
            swing_percent=0.55,
            beat_bins_ms=[-10, -6, -2, 0],
            beat_bins_probs=[0.4, 0.35, 0.2, 0.05],
            beat_bin_cap_ms=12,
        )
        hato = cfg.hat_o or LayerConfig(
            steps=16,
            fills=16,
            note=46,
            velocity=80,
            offbeats_only=True,
            ratchet_prob=0.08,
            ratchet_repeat=3,
            swing_percent=0.55,
            beat_bins_ms=[-2, 0, 2],
            beat_bins_probs=[0.2, 0.6, 0.2],
            beat_bin_cap_ms=10,
            choke_with_note=42,
        )
        snare = cfg.snare or LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=96)
        clap = cfg.clap or LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)

        ev_k = build_layer(cfg.bpm, cfg.ppq, cfg.bars, kick)
        ev_hc = build_layer(cfg.bpm, cfg.ppq, cfg.bars, hatc)
        ch_map = collect_closed_hat_ticks(ev_hc, cfg.ppq, 42)
        ev_ho = build_layer(cfg.bpm, cfg.ppq, cfg.bars, hato, closed_hat_ticks_by_bar=ch_map)
        ev_sn = build_layer(cfg.bpm, cfg.ppq, cfg.bars, snare)
        ev_cl = build_layer(cfg.bpm, cfg.ppq, cfg.bars, clap)
        write_midi(list(chain(ev_k, ev_hc, ev_ho, ev_sn, ev_cl)), cfg.ppq, cfg.bpm, cfg.out)
    elif mode == "m4":
        rng = random.Random(cfg.seed)
        res = run_session(
            bpm=cfg.bpm,
            ppq=cfg.ppq,
            bars=cfg.bars,
            rng=rng,
            targets=cfg.targets,
            guard=cfg.guard,
            kick_layer_cfg=cfg.kick,
            hat_c_cfg=cfg.hat_c,
            hat_o_cfg=cfg.hat_o,
            snare_cfg=cfg.snare,
            clap_cfg=cfg.clap,
            param_mods=cfg.modulators,
            log_path=cfg.log_path,
        )
        all_events = list(chain.from_iterable(res.events_by_layer.values()))
        write_midi(all_events, cfg.ppq, cfg.bpm, cfg.out)
    else:
        raise SystemExit(f"Unknown mode for paired render: {mode}")

    print(f"Wrote drums to {cfg.out} ({cfg.mode}, bpm={cfg.bpm}, ppq={cfg.ppq}, bars={cfg.bars})")

    # Generate groove-aware bass using the rendered drums.
    drum_midi_path = Path(cfg.out)
    anchors = extract_drum_anchors(drum_midi_path, ppq=cfg.ppq)

    tags_list = _parse_tags(args.tags)

    bass_events = generate_groove_bass(
        anchors,
        bpm=cfg.bpm,
        ppq=cfg.ppq,
        tags=tags_list,
        mode=args.bass_mode,
        root_note=args.root_note,
        bars=cfg.bars,
        swing_percent=0.54,
    )

    # Derive a bass output path next to the drums.
    drum_out = Path(cfg.out)
    if drum_out.suffix.lower() == ".mid":
        bass_out = drum_out.with_name(drum_out.stem + "_bass.mid")
    else:
        bass_out = drum_out.with_name(drum_out.name + "_bass.mid")

    write_midi(bass_events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=str(bass_out))
    print(f"Wrote bass to {bass_out}")

    # Save a single seed for drums + bass.
    meta = save_seed(
        cfg,
        config_path=args.config,
        render_path=cfg.out,
        prompt=args.prompt_text,
        summary=args.summary,
        tags=tags_list,
        log_path=getattr(cfg, "log_path", None),
        parent_seed_id=args.parent_seed_id,
    )
    print(f"Saved seed {meta.seed_id} under seeds/{meta.seed_id}")

    # Append bass asset into the saved metadata and refresh index.
    seed_dir = Path("seeds") / meta.seed_id
    meta_path = seed_dir / "metadata.json"
    if meta_path.is_file():
        import json

        data = json.loads(meta_path.read_text())
        assets = data.get("assets") or []
        assets.append(
            {
                "role": "bass",
                "kind": "midi",
                "path": str(bass_out),
                "description": "paired groove-aware bassline",
            }
        )
        data["assets"] = assets
        meta_path.write_text(json.dumps(data, indent=2, sort_keys=True))
        # Rebuild index to keep drum_pattern_preview / index.json consistent.
        rebuild_index()
        print(f"Registered bass asset on seed {meta.seed_id}")

    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
