from __future__ import annotations

import argparse
import os
import random
from itertools import chain
from typing import List

from .config import load_engine_config
from .backbone import build_backbone_events
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks
from .controller import run_session
from .midi_writer import write_midi
from .seeds import save_seed


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a session from JSON config (m1/m2/m4)")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument(
        "--save-seed",
        action="store_true",
        help="If set, save a seed record (config + metadata) under seeds/",
    )
    parser.add_argument(
        "--prompt-text",
        default=None,
        help="Optional prompt text that led to this render (stored in seed metadata)",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help="Optional comma-separated tags for this seed (e.g. 'm4,warehouse,ghost_kicks')",
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

    # Determine output path: in seed workflows we avoid hard-coding into out/.
    out_path = cfg.out
    if args.save_seed:
        # Only use the basename when saving a seed; write into CWD.
        base = os.path.basename(str(cfg.out)) or "render.mid"
        out_path = os.path.join(".", base)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    mode = cfg.mode.lower()
    if mode == "m1":
        events = build_backbone_events(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars)
        write_midi(events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=out_path)
    elif mode == "m2":
        # Use provided layer configs or sensible defaults
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
        # backbeats from defaults if not overridden
        ev_sn = build_layer(cfg.bpm, cfg.ppq, cfg.bars, snare)
        ev_cl = build_layer(cfg.bpm, cfg.ppq, cfg.bars, clap)
        write_midi(list(chain(ev_k, ev_hc, ev_ho, ev_sn, ev_cl)), cfg.ppq, cfg.bpm, out_path)
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
        write_midi(all_events, cfg.ppq, cfg.bpm, out_path)
    else:
        raise SystemExit(f"Unknown mode: {mode}")

    print(f"Wrote {cfg.out} ({cfg.mode}, bpm={cfg.bpm}, ppq={cfg.ppq}, bars={cfg.bars})")

    if args.save_seed:
        tags: list[str] | None
        if args.tags:
            tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        else:
            tags = None

        meta = save_seed(
            cfg,
            config_path=args.config,
            render_path=out_path,
            prompt=args.prompt_text,
            summary=args.summary,
            tags=tags,
            log_path=getattr(cfg, "log_path", None),
            parent_seed_id=args.parent_seed_id,
        )
        print(f"Saved seed {meta.seed_id} under seeds/{meta.seed_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

