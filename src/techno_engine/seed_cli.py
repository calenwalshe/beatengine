from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .run_config import main as run_config_main
from .seeds import SeedMetadata, load_seed, rebuild_index, import_mid_as_seed, delete_seed_dir
from .drum_analysis import extract_drum_anchors
from .groove_bass import generate_groove_bass
from .midi_writer import write_midi


def _get_seeds_root(root_arg: str | None) -> Path:
    return Path(root_arg) if root_arg else Path("seeds")


def _iter_seed_metadata(seeds_root: Path) -> list[SeedMetadata]:
    if not seeds_root.is_dir():
        return []
    # Delegate to seeds.rebuild_index so index.json stays up to date
    return rebuild_index(seeds_root=seeds_root)


def _cmd_list(args: argparse.Namespace) -> int:
    seeds_root = _get_seeds_root(args.root)
    metas = _iter_seed_metadata(seeds_root)

    # Apply simple filters
    if args.mode:
        metas = [m for m in metas if m.engine_mode.lower() == args.mode.lower()]
    if args.tag:
        metas = [m for m in metas if args.tag in (m.tags or [])]
    if args.bpm_min is not None:
        metas = [m for m in metas if m.bpm >= args.bpm_min]
    if args.bpm_max is not None:
        metas = [m for m in metas if m.bpm <= args.bpm_max]

    if not metas:
        if getattr(args, 'json', False):
            print("[]")
        else:
            print("No seeds found.")
        return 0

    if getattr(args, 'json', False):
        import dataclasses as _dc

        payload = [_dc.asdict(m) for m in metas]
        print(json.dumps(payload))
        return 0

    # Simple table: seed_id, mode, bpm, bars, tags
    print(f"{'seed_id':36}  {'mode':4}  {'bpm':5}  {'bars':4}  tags")
    for meta in metas:
        tag_str = ",".join(meta.tags) if meta.tags else "-"
        sid = meta.seed_id
        print(f"{sid:36}  {meta.engine_mode:4}  {meta.bpm:5.1f}  {meta.bars:4d}  {tag_str}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    seeds_root = _get_seeds_root(args.root)
    seed_id = args.seed_id
    seed_dir = seeds_root / seed_id
    meta_path = seed_dir / "metadata.json"
    if not meta_path.is_file():
        print(f"No metadata found for seed_id={seed_id} under {seeds_root}")
        return 1
    raw = json.loads(meta_path.read_text())
    if getattr(args, 'json', False):
        print(json.dumps(raw))
    else:
        print(json.dumps(raw, indent=2, sort_keys=True))
    return 0


def _build_run_config_args_from_seed(
    seed_id: str,
    seeds_root: Path,
    *,
    out_path: str | None,
    save_seed: bool,
    prompt_text: str | None,
    tags: str | None,
    summary: str | None,
    parent_seed_id: str | None,
) -> List[str]:
    seed_dir = seeds_root / seed_id
    cfg_path = seed_dir / "config.json"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Missing config.json for seed_id={seed_id} under {seeds_root}")

    run_args: List[str] = ["--config", str(cfg_path)]

    if out_path is not None:
        # Use a temporary JSON file with overridden out path.
        raw_cfg = json.loads(cfg_path.read_text())
        raw_cfg["out"] = out_path
        tmp_path = seed_dir / "_render_override.json"
        tmp_path.write_text(json.dumps(raw_cfg))
        run_args = ["--config", str(tmp_path)]

    if save_seed:
        run_args.append("--save-seed")
        if prompt_text is not None:
            run_args.extend(["--prompt-text", prompt_text])
        if tags is not None:
            run_args.extend(["--tags", tags])
        if summary is not None:
            run_args.extend(["--summary", summary])
        if parent_seed_id is not None:
            run_args.extend(["--parent-seed-id", parent_seed_id])

    return run_args


def _cmd_render(args: argparse.Namespace) -> int:
    seeds_root = _get_seeds_root(args.root)
    seed_id = args.seed_id

    # Ensure the seed can be loaded.
    load_seed(seed_id, seeds_root=seeds_root)

    run_args = _build_run_config_args_from_seed(
        seed_id=seed_id,
        seeds_root=seeds_root,
        out_path=args.out,
        save_seed=args.save_seed,
        prompt_text=args.prompt_text,
        tags=args.tags,
        summary=args.summary,
        parent_seed_id=None,
    )
    rc = run_config_main(run_args)
    return rc


def _cmd_clone(args: argparse.Namespace) -> int:
    seeds_root = _get_seeds_root(args.root)
    seed_id = args.seed_id

    cfg, meta = load_seed(seed_id, seeds_root=seeds_root)

    # Build a mutable config dict from the original JSON so that we can apply overrides.
    seed_dir = seeds_root / seed_id
    cfg_path = seed_dir / "config.json"
    raw_cfg = json.loads(cfg_path.read_text())

    if args.bpm is not None:
        raw_cfg["bpm"] = float(args.bpm)
    if args.bars is not None:
        raw_cfg["bars"] = int(args.bars)
    if args.seed is not None:
        raw_cfg["seed"] = int(args.seed)
    if args.out is not None:
        raw_cfg["out"] = args.out

    # Write a temporary config for the clone run.
    clone_cfg_path = seed_dir / "_clone_override.json"
    clone_cfg_path.write_text(json.dumps(raw_cfg))

    # For clone we always save a new seed and record the parent_seed_id.
    run_args: List[str] = ["--config", str(clone_cfg_path), "--save-seed"]
    if args.prompt_text is not None:
        run_args.extend(["--prompt-text", args.prompt_text])
    else:
        # Default to original prompt if present.
        if meta.prompt is not None:
            run_args.extend(["--prompt-text", meta.prompt])
    if args.tags is not None:
        run_args.extend(["--tags", args.tags])
    else:
        # Default to original tags if present.
        if meta.tags:
            run_args.extend(["--tags", ",".join(meta.tags)])
    if args.summary is not None:
        run_args.extend(["--summary", args.summary])
    else:
        if meta.summary is not None:
            run_args.extend(["--summary", meta.summary])
    run_args.extend(["--parent-seed-id", meta.seed_id])

    rc = run_config_main(run_args)
    return rc




def _cmd_bass_from_seed(args: argparse.Namespace) -> int:
    """Generate groove-aware bass for an existing seed and append as a bass asset.

    This uses the current seed's drum MIDI as the rhythmic source and writes
    a new bass MIDI file into the seed directory.
    """
    seeds_root = _get_seeds_root(args.root)
    seed_id = args.seed_id

    # Load metadata/config to ensure the seed exists and get tempo info.
    cfg, meta = load_seed(seed_id, seeds_root=seeds_root)
    seed_dir = seeds_root / seed_id

    # Resolve drum MIDI path: prefer meta.render_path; fall back to main asset.
    drum_path = None
    if meta.render_path:
        p = Path(meta.render_path)
        drum_path = p if p.is_absolute() else seed_dir / p

    if drum_path is None or not drum_path.is_file():
        # Try first main/midi asset.
        for asset in meta.assets or []:
            if getattr(asset, 'role', '') == 'main' and getattr(asset, 'kind', '') == 'midi':
                p = Path(asset.path)
                drum_path = p if p.is_absolute() else seed_dir / p
                if drum_path.is_file():
                    break
        else:
            print(f"Could not resolve drum MIDI for seed {seed_id}")
            return 1

    anchors = extract_drum_anchors(drum_path, ppq=int(meta.ppq))

    tags = meta.tags or []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    root_note = args.root_note if args.root_note is not None else 45

    bass_events = generate_groove_bass(
        anchors,
        bpm=float(meta.bpm),
        ppq=int(meta.ppq),
        tags=tags,
        mode=args.bass_mode,
        root_note=root_note,
        bars=int(meta.bars),
    )

    # Write bass MIDI into the canonical bass folder inside the seed directory.
    bass_dir = seed_dir / 'bass'
    bass_dir.mkdir(parents=True, exist_ok=True)
    if args.out:
        dest_name = args.out
    elif args.bass_mode:
        dest_name = f"variants/bass_{args.bass_mode}.mid"
    else:
        dest_name = "variants/bass_auto.mid"

    dest_path = bass_dir / dest_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    write_midi(bass_events, ppq=int(meta.ppq), bpm=float(meta.bpm), out_path=str(dest_path))

    # Append a bass asset entry to metadata.json and rebuild index.
    meta_path = seed_dir / 'metadata.json'
    data = json.loads(meta_path.read_text())
    assets = data.get('assets') or []
    rel_bass_path = str(dest_path.relative_to(seed_dir))
    assets.append(
        {
            'role': 'bass',
            'kind': 'midi',
            'path': rel_bass_path,
            'description': args.description or 'bass_from_seed',
        }
    )
    data['assets'] = assets
    meta_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    rebuild_index(seeds_root=seeds_root)
    print(f"Appended bass asset to seed {seed_id}: {rel_bass_path}")
    return 0

def _cmd_delete(args: argparse.Namespace) -> int:
    """Delete a seed directory and rebuild the index.

    This mirrors the TUI delete behaviour (Shift+D + confirm) but is suitable
    for scripting and automation.
    """
    seeds_root = _get_seeds_root(args.root)
    seed_id = args.seed_id
    seed_dir = seeds_root / seed_id

    if not seed_dir.is_dir():
        print(f"Seed {seed_id} not found under {seeds_root}")
        return 1

    if not args.yes:
        # Print a short summary if metadata exists.
        meta_path = seed_dir / 'metadata.json'
        if meta_path.is_file():
            try:
                raw = json.loads(meta_path.read_text())
                mode = raw.get('engine_mode')
                bpm = raw.get('bpm')
                tags = raw.get('tags') or []
                tag_str = ','.join(tags) if tags else '-'
                print(f"Seed: {seed_id} | mode={mode} bpm={bpm} tags={tag_str}")
            except Exception:
                pass
        resp = input(f"Delete seed {seed_id} under {seed_dir}? [y/N]: ").strip()
        if not resp or resp[0].lower() != 'y':
            print('Aborted')
            return 1

    try:
        delete_seed_dir(seed_id, seeds_root)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    print(f"Deleted seed {seed_id} under {seeds_root}")
    return 0


def _cmd_import_mid(args: argparse.Namespace) -> int:
    seeds_root = _get_seeds_root(args.root)
    tags: list[str] | None = None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    meta = import_mid_as_seed(
        midi_path=args.mid_path,
        mode=args.mode,
        bpm=args.bpm,
        bars=args.bars,
        ppq=args.ppq,
        prompt=args.prompt_text,
        summary=args.summary,
        tags=tags,
        seeds_root=seeds_root,
    )
    print(f"Imported {args.mid_path} as seed {meta.seed_id}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed-beat management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="List available seeds")
    p_list.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_list.add_argument("--mode", default=None, help="Filter by engine mode (m1/m2/m4)")
    p_list.add_argument("--tag", default=None, help="Filter by tag (exact match)")
    p_list.add_argument("--bpm-min", type=float, default=None, help="Filter by minimum BPM")
    p_list.add_argument("--bpm-max", type=float, default=None, help="Filter by maximum BPM")
    p_list.add_argument("--json", action="store_true", help="Emit JSON instead of table output")
    p_list.set_defaults(func=_cmd_list)

    p_show = subparsers.add_parser("show", help="Show metadata for a single seed")
    p_show.add_argument("seed_id", help="Seed identifier")
    p_show.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_show.add_argument("--json", action="store_true", help="Emit JSON (default: pretty-printed JSON)")
    p_show.set_defaults(func=_cmd_show)

    p_render = subparsers.add_parser("render", help="Render a beat from an existing seed")
    p_render.add_argument("seed_id", help="Seed identifier")
    p_render.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_render.add_argument("--out", default=None, help="Override output MIDI path")
    p_render.add_argument("--save-seed", action="store_true", help="Also save a new seed for this render")
    p_render.add_argument("--prompt-text", default=None, help="Prompt text for new seed when --save-seed is used")
    p_render.add_argument("--tags", default=None, help="Comma-separated tags for new seed when --save-seed is used")
    p_render.add_argument("--summary", default=None, help="Summary text for new seed when --save-seed is used")
    p_render.set_defaults(func=_cmd_render)

    p_clone = subparsers.add_parser("clone", help="Clone a seed with optional overrides and save a new seed")
    p_clone.add_argument("seed_id", help="Source seed identifier")
    p_clone.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_clone.add_argument("--out", default=None, help="Override output MIDI path")
    p_clone.add_argument("--bpm", type=float, default=None, help="Override BPM")
    p_clone.add_argument("--bars", type=int, default=None, help="Override number of bars")
    p_clone.add_argument("--seed", type=int, default=None, help="Override RNG seed")
    p_clone.add_argument("--prompt-text", default=None, help="Prompt text for the cloned seed")
    p_clone.add_argument("--tags", default=None, help="Comma-separated tags for the cloned seed")
    p_clone.add_argument("--summary", default=None, help="Summary text for the cloned seed")

    p_bass = subparsers.add_parser("bass-from-seed", help="Generate groove-aware bass for an existing seed")
    p_bass.add_argument("seed_id", help="Seed identifier")
    p_bass.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_bass.add_argument("--out", default=None, help="Output bass MIDI filename (relative to seed dir)")
    p_bass.add_argument("--bass-mode", default=None, help="Optional bass mode override")
    p_bass.add_argument("--root-note", type=int, default=None, help="Bass root note (MIDI number)")
    p_bass.add_argument("--tags", default=None, help="Override tags used for bass mode selection")
    p_bass.add_argument("--description", default=None, help="Description to store on the bass asset")
    p_bass.set_defaults(func=_cmd_bass_from_seed)

    p_import = subparsers.add_parser("import-mid", help="Import an existing MIDI file as a seed")
    p_import.add_argument("mid_path", help="Path to the MIDI file to import")
    p_import.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_import.add_argument("--mode", default="external", help="Engine mode label to store in metadata")
    p_import.add_argument("--bpm", type=float, default=0.0, help="Optional BPM metadata (for reference only)")
    p_import.add_argument("--bars", type=int, default=0, help="Optional bar count metadata (for reference only)")
    p_import.add_argument("--ppq", type=int, default=1920, help="PPQ to record in metadata (default 1920)")
    p_import.add_argument("--prompt-text", default=None, help="Optional prompt text to attach to the imported seed")
    p_import.add_argument("--tags", default=None, help="Comma-separated tags for the imported seed")
    p_import.add_argument("--summary", default=None, help="Summary/description of the imported MIDI")
    p_import.set_defaults(func=_cmd_import_mid)

    p_delete = subparsers.add_parser("delete", help="Delete a seed and its assets")
    p_delete.add_argument("seed_id", help="Seed identifier to delete")
    p_delete.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Delete without interactive confirmation")
    p_delete.set_defaults(func=_cmd_delete)

    p_clone.set_defaults(func=_cmd_clone)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

