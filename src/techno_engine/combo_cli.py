from __future__ import annotations

import argparse
import os
from itertools import chain
from typing import List

from .config import load_engine_config
from .backbone import build_backbone_events
from .parametric import LayerConfig, build_layer, collect_closed_hat_ticks
from .controller import run_session
from .midi_writer import write_midi, MidiEvent
from .bassline import generate_mvp, generate_scored
from .scores import union_mask_for_bar
from .bass_validate import validate_bass


def _render_drums_from_config(cfg) -> list:
    mode = cfg.mode.lower()
    if mode == "m1":
        return build_backbone_events(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars)
    elif mode == "m2":
        kick = cfg.kick or LayerConfig(steps=16, fills=4, note=36, velocity=110)
        hatc = cfg.hat_c or LayerConfig(steps=16, fills=16, note=42, velocity=80, swing_percent=0.55,
                                        beat_bins_ms=[-10,-6,-2,0], beat_bins_probs=[0.4,0.35,0.2,0.05], beat_bin_cap_ms=12)
        hato = cfg.hat_o or LayerConfig(steps=16, fills=16, note=46, velocity=80, offbeats_only=True,
                                        ratchet_prob=0.08, ratchet_repeat=3, swing_percent=0.55,
                                        beat_bins_ms=[-2,0,2], beat_bins_probs=[0.2,0.6,0.2], beat_bin_cap_ms=10,
                                        choke_with_note=42)
        snare = cfg.snare or LayerConfig(steps=16, fills=2, rot=4, note=38, velocity=96)
        clap = cfg.clap or LayerConfig(steps=16, fills=2, rot=4, note=39, velocity=92)
        ev_k = build_layer(cfg.bpm, cfg.ppq, cfg.bars, kick)
        ev_hc = build_layer(cfg.bpm, cfg.ppq, cfg.bars, hatc)
        ch_map = collect_closed_hat_ticks(ev_hc, cfg.ppq, 42)
        ev_ho = build_layer(cfg.bpm, cfg.ppq, cfg.bars, hato, closed_hat_ticks_by_bar=ch_map)
        ev_sn = build_layer(cfg.bpm, cfg.ppq, cfg.bars, snare)
        ev_cl = build_layer(cfg.bpm, cfg.ppq, cfg.bars, clap)
        return list(chain(ev_k, ev_hc, ev_ho, ev_sn, ev_cl))
    elif mode == "m4":
        res = run_session(
            bpm=cfg.bpm,
            ppq=cfg.ppq,
            bars=cfg.bars,
            targets=cfg.targets,
            guard=cfg.guard,
            kick_layer_cfg=cfg.kick,
            hat_c_cfg=cfg.hat_c,
            hat_o_cfg=cfg.hat_o,
            snare_cfg=cfg.snare,
            clap_cfg=cfg.clap,
            param_mods=cfg.modulators,
            log_path=None,
        )
        return list(chain.from_iterable(res.events_by_layer.values()))
    else:
        raise SystemExit(f"Unknown mode: {mode}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render drums from config and a separate bassline (two MIDI files)")
    parser.add_argument("--drum", required=True, help="Path to drum JSON config (m1/m2/m4)")
    parser.add_argument("--drum_out", required=False, default="out/drums_only.mid", help="Output MIDI path for drums")
    parser.add_argument("--bass_out", required=False, default="out/bass_only.mid", help="Output MIDI path for bassline")
    parser.add_argument("--root_note", type=int, default=45, help="Bass root MIDI note (default 45)")
    parser.add_argument("--key", type=str, default=None, help="Musical key (e.g., A, D#, Eb) to set root note")
    parser.add_argument("--mode", type=str, default=None, help="Mode colouring for bass (minor/aeolian/dorian)")
    parser.add_argument("--motif", type=str, default=None, help="Motif preset (root_only, root_fifth, root_b7, root_fifth_octave)")
    parser.add_argument("--phrase", type=str, default=None, help="Phrase preset (rise, bounce, fall)")
    parser.add_argument("--bass_mode", choices=["mvp", "scored"], default="scored", help="Bass generation mode (default: scored)")
    # Default validate=True; allow disabling with --no-validate
    parser.add_argument("--no-validate", dest="validate", action="store_false", help="Disable validator on bassline")
    parser.set_defaults(validate=True)
    parser.add_argument("--density", type=float, default=0.4, help="Target bass density (fraction of 16ths)")
    parser.add_argument("--min_dur_steps", type=float, default=0.5, help="Minimum duration in 16th steps for bass notes")
    parser.add_argument("--degree", choices=["minor", "none"], default="none", help="Optional degree colouring (minor adds b7 pulses)")
    args = parser.parse_args(argv)

    cfg = load_engine_config(args.drum)

    # Render drums
    drum_events = _render_drums_from_config(cfg)
    os.makedirs(os.path.dirname(args.drum_out) or ".", exist_ok=True)
    write_midi(drum_events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=args.drum_out)
    print(f"Wrote drums MIDI to {args.drum_out} (bpm={cfg.bpm}, ppq={cfg.ppq}, bars={cfg.bars})")

    # Determine root and degree
    degree = args.degree
    from .key_mode import key_to_midi, normalize_mode
    if args.key:
        try:
            args.root_note = key_to_midi(args.key, base_octave=3)
        except Exception:
            pass
    m = normalize_mode(args.mode)
    if m:
        degree = m

    # Generate bass
    if args.bass_mode == "mvp":
        bass_events = generate_mvp(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars, seed=cfg.seed, root_note=args.root_note, density_target=args.density, min_dur_steps=args.min_dur_steps, degree_mode=(degree if degree!="none" else None), motif=args.motif, phrase=args.phrase)
    else:
        # Build per-bar masks for kick/hat/clap from drum events
        def filter_note(evs: list[MidiEvent], note: int) -> list[MidiEvent]:
            return [e for e in evs if e.note == note]
        # Render drums again per layer when possible
        drum_events_for_masks = drum_events
        # Simple masks by MIDI notes (GM): kick=36, hat_c=42, hat_o=46, clap=39
        kick_mask_by_bar = []
        hat_mask_by_bar = []
        clap_mask_by_bar = []
        bar_ticks = cfg.ppq * 4
        bars = cfg.bars
        for b in range(bars):
            start = b * bar_ticks
            end = start + bar_ticks
            slice_evs = [e for e in drum_events_for_masks if start <= e.start_abs_tick < end]
            kick_mask_by_bar.append(union_mask_for_bar(filter_note(slice_evs, 36), cfg.ppq))
            # merge closed/open hat masks
            hat_evs = filter_note(slice_evs, 42) + filter_note(slice_evs, 46)
            hat_mask_by_bar.append(union_mask_for_bar(hat_evs, cfg.ppq))
            clap_mask_by_bar.append(union_mask_for_bar(filter_note(slice_evs, 39), cfg.ppq))
        bass_events = generate_scored(bpm=cfg.bpm, ppq=cfg.ppq, bars=cfg.bars, root_note=args.root_note,
                                      kick_masks_by_bar=kick_mask_by_bar, hat_masks_by_bar=hat_mask_by_bar,
                                      clap_masks_by_bar=clap_mask_by_bar, density_target=args.density,
                                      min_dur_steps=args.min_dur_steps, degree_mode=(degree if degree!="none" else None), motif=args.motif, phrase=args.phrase)

    if args.validate:
        res = validate_bass(bass_events, ppq=cfg.ppq, bpm=cfg.bpm, bars=cfg.bars, density_target=args.density)
        bass_events = res.events
        if res.summaries:
            print("Validator:")
            for s in res.summaries:
                print(" -", s)
    os.makedirs(os.path.dirname(args.bass_out) or ".", exist_ok=True)
    write_midi(bass_events, ppq=cfg.ppq, bpm=cfg.bpm, out_path=args.bass_out)
    print(f"Wrote bass MIDI to {args.bass_out} (bpm={cfg.bpm}, ppq={cfg.ppq}, bars={cfg.bars})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
