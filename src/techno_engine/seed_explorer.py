from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .seeds import SeedMetadata, rebuild_index


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _format_note(num: int) -> str:
    name = _NOTE_NAMES[num % 12]
    octave = (num // 12) - 1
    return f"{name}{octave}"


def _format_row(meta: SeedMetadata) -> str:
    sid_disp = meta.seed_id
    tag_str = ",".join(meta.tags) if meta.tags else "-"
    return f"{sid_disp:27}  {meta.engine_mode:3}  {meta.bpm:5.1f}  {meta.bars:3d}  {tag_str}"


def demo_output(seeds_root: Path | None = None, limit: int | None = None) -> str:
    """Build a simple textual overview of seeds for non-interactive/demo use."""

    root = seeds_root or Path("seeds")
    metas = rebuild_index(seeds_root=root)
    if not metas:
        return "Seed Explorer Demo\n(no seeds found under ./seeds)\n"

    lines: List[str] = []
    lines.append("Seed Explorer Demo")
    lines.append("seed_id (short)                mode   bpm  bar  tags")
    lines.append("-" * 72)

    for idx, meta in enumerate(metas):
        if limit is not None and idx >= limit:
            break
        lines.append(_format_row(meta))

    # Show details for the first seed as a preview
    first = metas[0]
    lines.append("")
    lines.append("First seed details:")
    lines.append(f"  seed_id: {first.seed_id}")
    lines.append(f"  created_at: {first.created_at}")
    lines.append(f"  mode: {first.engine_mode}  bpm: {first.bpm}  bars: {first.bars}  ppq: {first.ppq}")
    if first.tags:
        lines.append(f"  tags: {', '.join(first.tags)}")
    if first.summary:
        lines.append(f"  summary: {first.summary}")

    return "\n".join(lines) + "\n"


def _summarise_midi(midi_path: Path, ppq: int) -> Optional[str]:
    """Summarise MIDI notes with counts and beat timings."""

    try:
        import mido
    except ImportError:
        return None

    path = Path(midi_path)
    if not path.exists():
        return None

    try:
        mid = mido.MidiFile(path)
    except Exception:
        return None

    ticks_per_beat = mid.ticks_per_beat or ppq or 480

    notes: Dict[int, int] = {}
    hits = 0
    first_tick: Optional[int] = None
    last_tick: Optional[int] = None

    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += int(getattr(msg, "time", 0))
            if getattr(msg, "type", None) != "note_on":
                continue
            if getattr(msg, "velocity", 0) <= 0:
                continue
            note = int(getattr(msg, "note", -1))
            hits += 1
            notes[note] = notes.get(note, 0) + 1
            first_tick = tick if first_tick is None else min(first_tick, tick)
            last_tick = tick if last_tick is None else max(last_tick, tick)

    if hits == 0:
        return None

    note_list = ",".join(_format_note(n) for n in sorted(notes))
    first_beats = (first_tick or 0) / ticks_per_beat
    last_beats = (last_tick or 0) / ticks_per_beat
    length_beats = last_beats

    return (
        f"notes: {note_list} | hits: {hits} | "
        f"length: {length_beats:.2f} beats | first: {first_beats:.2f} | last: {last_beats:.2f}"
    )


def _extract_drum_pattern(midi_path: Path, ppq: int) -> Optional[str]:
    """Extract a simple 16-step drum pattern string from a MIDI file."""

    try:
        import mido
    except ImportError:
        return None

    path = Path(midi_path)
    if not path.exists():
        return None

    try:
        mid = mido.MidiFile(path)
    except Exception:
        return None

    ticks_per_beat = mid.ticks_per_beat or ppq or 480
    ticks_per_step = max(1, int(round(ticks_per_beat / 4)))  # 16th notes
    steps = 16

    note_roles = {
        "kick": {36},
        "snare": {37, 38, 39, 40},
        "hat": {42, 44, 46},
    }
    hits: Dict[str, List[bool]] = {role: [False] * steps for role in note_roles}

    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += int(getattr(msg, "time", 0))
            if getattr(msg, "type", None) != "note_on":
                continue
            if getattr(msg, "velocity", 0) <= 0:
                continue

            step = int(tick // ticks_per_step)
            if 0 <= step < steps:
                for role, notes in note_roles.items():
                    if getattr(msg, "note", -1) in notes:
                        hits[role][step] = True

    if not any(any(v) for v in hits.values()):
        return None

    def _line(role: str) -> str:
        patt = "".join("x" if hit else "." for hit in hits[role])
        return f"{role:<5}: {patt}"

    return "\n".join([_line("kick"), _line("snare"), _line("hat")])


def _run_curses(seeds_root: Path) -> int:
    """Run a curses-based explorer with modes and basic actions menu."""

    import curses  # imported lazily to keep tests simple

    metas: List[SeedMetadata] = rebuild_index(seeds_root=seeds_root)

    if not metas:
        print("No seeds found under", seeds_root)
        return 0

    # Cache drum-pattern extraction per seed_id to avoid repeating work.
    pattern_cache: Dict[str, str] = {}
    midi_summary_cache: Dict[str, str] = {}
    asset_idx_by_seed: Dict[str, int] = {}

    def _loop(stdscr: "curses._CursesWindow") -> None:  # type: ignore[name-defined]
        # Basic curses setup
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.keypad(True)

        # Colour setup (best-effort; falls back to attributes if colours unsupported)
        selected_attr = curses.A_REVERSE
        header_attr = curses.A_BOLD
        title_attr = curses.A_BOLD
        status_attr = curses.A_REVERSE
        border_attr = curses.A_NORMAL
        section_header_attr = curses.A_BOLD
        asset_label_attr = curses.A_BOLD
        try:
            if curses.has_colors():
                curses.start_color()
                try:
                    curses.use_default_colors()
                except curses.error:
                    pass
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # selected row
                curses.init_pair(2, curses.COLOR_YELLOW, -1)                 # headers/title
                curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)  # status bar
                curses.init_pair(4, curses.COLOR_CYAN, -1)                   # borders/dividers
                curses.init_pair(5, curses.COLOR_GREEN, -1)                  # section headers
                curses.init_pair(6, curses.COLOR_MAGENTA, -1)                # asset labels
                selected_attr = curses.color_pair(1) | curses.A_BOLD
                header_attr = curses.color_pair(2) | curses.A_BOLD
                title_attr = curses.color_pair(2) | curses.A_BOLD
                status_attr = curses.color_pair(3)
                border_attr = curses.color_pair(4)
                section_header_attr = curses.color_pair(5) | curses.A_BOLD
                asset_label_attr = curses.color_pair(6) | curses.A_BOLD
        except curses.error:
            # Keep defaults if colour init fails
            pass

        mode = "list"  # or "detail"
        selected = 0
        top = 0
        last_message = ""

        while True:
            h, w = stdscr.getmaxyx()
            stdscr.erase()

            left_w = max(40, w // 2)
            list_height = max(1, h - 5)

            if mode == "list":
                title = " Seed Explorer — q: quit | Enter: details | j/k: move | r: refresh "
            else:
                meta = metas[selected]
                title = f" Seed Detail — {meta.seed_id} (q/Esc: back | j/k: seed | h/l: asset ) "
            stdscr.addnstr(0, 0, title.ljust(w - 1), w - 1, title_attr)

            try:
                stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            except curses.error:
                pass

            if mode == "list":
                header = "seed_id                             m   bpm  bar  tags"
                stdscr.addnstr(2, 0, header[: left_w - 1], left_w - 1, header_attr)

                divider_x = left_w
                for y in range(1, h - 1):
                    try:
                        stdscr.addch(y, divider_x, curses.ACS_VLINE, border_attr)
                    except curses.error:
                        stdscr.addnstr(y, divider_x, "|", 1, border_attr)

                if selected < top:
                    top = selected
                elif selected >= top + list_height:
                    top = selected - list_height + 1

                for row_idx in range(list_height):
                    meta_idx = top + row_idx
                    if meta_idx >= len(metas):
                        break
                    meta = metas[meta_idx]
                    row_y = 3 + row_idx
                    if row_y >= h - 1:
                        break
                    text = _format_row(meta)
                    attr = selected_attr if meta_idx == selected else curses.A_NORMAL
                    stdscr.addnstr(row_y, 0, text[: left_w - 1], left_w - 1, attr)

                detail_x = left_w + 1
                if detail_x < w - 1 and metas:
                    meta = metas[selected]
                    seed_dir = seeds_root / meta.seed_id
                    cfg_path = seed_dir / meta.config_path
                    meta_path = seed_dir / "metadata.json"
                    detail_lines = [
                        f"seed_dir: {seed_dir}",
                        f"config : {cfg_path}",
                        f"meta   : {meta_path}",
                        "",
                        f"mode: {meta.engine_mode}  bpm: {meta.bpm}  bars: {meta.bars}  ppq: {meta.ppq}",
                        f"tags: {', '.join(meta.tags) if meta.tags else '-'}",
                        f"render: {meta.render_path}",
                    ]
                    y = 2
                    for line in detail_lines:
                        if y >= h - 2:
                            break
                        attr = header_attr if line.startswith(("seed_dir:", "config ", "meta   ", "mode:", "tags:", "render:")) else curses.A_NORMAL
                        stdscr.addnstr(
                            y,
                            detail_x,
                            line[: max(0, w - detail_x - 1)],
                            max(0, w - detail_x - 1),
                            attr,
                        )
                        y += 1

                status = " j/k: move  Enter: details  r: refresh  q: quit "
            else:
                meta = metas[selected]
                seed_dir = seeds_root / meta.seed_id
                cfg_path = seed_dir / meta.config_path
                meta_path = seed_dir / "metadata.json"

                def _resolve_path(raw_path: str) -> Optional[Path]:
                    p = Path(raw_path)
                    cands = [p]
                    if not p.is_absolute():
                        cands.append(seed_dir / p.name)
                        cands.append(seed_dir / p)
                        cands.append(seeds_root / p)
                    for cand in cands:
                        if cand.exists():
                            return cand
                    return None

                def _asset_list() -> List[Dict[str, object]]:
                    assets = list(getattr(meta, "assets", []) or [])
                    if not assets and meta.render_path:
                        assets = [
                            type("_A", (), {"role": "main", "kind": "midi", "path": meta.render_path, "description": "primary render"})()
                        ]
                    return assets

                assets = _asset_list()
                asset_idx = asset_idx_by_seed.get(meta.seed_id, 0)
                if assets:
                    asset_idx = max(0, min(asset_idx, len(assets) - 1))
                    asset_idx_by_seed[meta.seed_id] = asset_idx
                    selected_asset = assets[asset_idx]
                else:
                    selected_asset = None

                def _resolve_midi_for_asset(asset_obj) -> Optional[Path]:
                    if asset_obj is None:
                        return None
                    return _resolve_path(str(getattr(asset_obj, "path", "")))

                midi_path = _resolve_midi_for_asset(selected_asset)

                pattern_text: Optional[str] = None
                if selected_asset is not None:
                    pattern_text = getattr(selected_asset, "drum_pattern_preview", None)

                cache_key = f"{meta.seed_id}:{getattr(selected_asset, 'path', '') if selected_asset else ''}"
                preferred = midi_path
                if preferred is None:
                    preferred = _resolve_path(meta.render_path) if meta.render_path else None

                if pattern_text is None:
                    if cache_key in pattern_cache:
                        pattern_text = pattern_cache[cache_key] or None
                    else:
                        extracted = _extract_drum_pattern(preferred, meta.ppq) if preferred else None
                        pattern_cache[cache_key] = extracted or ""
                        pattern_text = extracted

                midi_summary_text: Optional[str] = None
                midi_summary_text: Optional[str] = None
                if midi_path:
                    cache_key = str(midi_path)
                    if cache_key in midi_summary_cache:
                        midi_summary_text = midi_summary_cache[cache_key] or None
                    else:
                        midi_summary_text = _summarise_midi(midi_path, meta.ppq)
                        midi_summary_cache[cache_key] = midi_summary_text or ""

                detail_lines = [
                    f"seed_id : {meta.seed_id}",
                    f"engine  : {meta.engine_mode}",
                    f"created : {meta.created_at}",
                    f"seed_dir: {seed_dir}",
                    f"config  : {cfg_path}",
                    f"meta    : {meta_path}",
                    f"render  : {meta.render_path}",
                    "",
                    f"bpm: {meta.bpm}  bars: {meta.bars}  ppq: {meta.ppq}",
                    f"tags: {', '.join(meta.tags) if meta.tags else '-'}",
                ]

                if getattr(meta, "assets", None):
                    detail_lines.append("")
                    detail_lines.append("assets (h/l to change):")
                    for idx, asset in enumerate(assets):
                        prefix = "→" if idx == asset_idx_by_seed.get(meta.seed_id, 0) else " "
                        line = f" {prefix} [{idx+1}/{len(assets)}] {asset.role}/{asset.kind}: {asset.path}"
                        detail_lines.append(line)
                        if getattr(asset, "description", None):
                            detail_lines.append(f"     desc: {asset.description}")

                if selected_asset:
                    detail_lines.append("")
                    detail_lines.append("selected asset detail:")
                    resolved = midi_path if midi_path else _resolve_path(str(getattr(selected_asset, "path", "")))
                    if resolved:
                        detail_lines.append(f"     file: {resolved}")
                        try:
                            stat = resolved.stat()
                            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                            detail_lines.append(f"     mtime: {mtime}  size: {stat.st_size} bytes")
                        except OSError:
                            pass
                    if midi_summary_text:
                        detail_lines.append(f"     midi: {midi_summary_text}")

                if pattern_text:
                    detail_lines.append("")
                    detail_lines.append("drum pattern (1 bar, 16 steps):")
                    detail_lines.extend(pattern_text.splitlines())

                if meta.summary:
                    detail_lines.append("")
                    detail_lines.append("summary:")
                    detail_lines.append(meta.summary)
                if meta.prompt:
                    detail_lines.append("")
                    detail_lines.append("prompt:")
                    detail_lines.append(meta.prompt)

                detail_lines.append("")
                detail_lines.append("codex notes: docs/CODEX_SEED_WORKFLOW.md")

                y = 2
                for line in detail_lines:
                    if y >= h - 2:
                        break
                    # Highlight section headers and asset labels for readability.
                    if line in {"assets (h/l to change):", "selected asset detail:", "summary:", "prompt:", "drum pattern (1 bar, 16 steps):"}:
                        attr = section_header_attr
                    elif line.startswith(" ") and "[" in line and "/" in line and ":" in line:
                        # asset listing line
                        attr = asset_label_attr
                    else:
                        attr = curses.A_NORMAL
                    stdscr.addnstr(y, 0, line[: w - 1], w - 1, attr)
                    y += 1

                status = " DETAIL: j/k seed  h/l asset  q/Esc: back "

            if last_message:
                msg = f" | {last_message}"
                status = (status + msg)[: w - 1]
            stdscr.addnstr(h - 1, 0, status.ljust(w - 1), w - 1, status_attr)

            stdscr.refresh()

            ch = stdscr.getch()

            # Global quit / back
            if ch in (ord("q"), ord("Q"), 27):  # Esc
                if mode == "list":
                    break
                else:
                    mode = "list"
                    last_message = ""
                    continue

            if mode == "list":
                if ch in (curses.KEY_DOWN, ord("j")):
                    if selected < len(metas) - 1:
                        selected += 1
                elif ch in (curses.KEY_UP, ord("k")):
                    if selected > 0:
                        selected -= 1
                elif ch in (ord("r"), ord("R")):
                    refreshed = rebuild_index(seeds_root=seeds_root)
                    if refreshed:
                        metas[:] = refreshed
                        if selected >= len(metas):
                            selected = max(0, len(metas) - 1)
                    last_message = "Refreshed seed index"
                elif ch in (curses.KEY_ENTER, 10, 13, ord("\n"), ord("\r")):
                    # Enter detail mode for current seed
                    mode = "detail"
                    last_message = ""
            else:  # DETAIL mode
                # In detail mode, allow moving selection but stay in detail view
                if ch in (curses.KEY_DOWN, ord("j")):
                    if selected < len(metas) - 1:
                        selected += 1
                        last_message = ""
                elif ch in (curses.KEY_UP, ord("k")):
                    if selected > 0:
                        selected -= 1
                        last_message = ""
                elif ch in (curses.KEY_RIGHT, ord("l"), ord("]")):
                    cur = asset_idx_by_seed.get(meta.seed_id, 0)
                    if getattr(meta, "assets", None):
                        if cur < len(getattr(meta, "assets", [])) - 1:
                            asset_idx_by_seed[meta.seed_id] = cur + 1
                    else:
                        asset_idx_by_seed[meta.seed_id] = 0
                elif ch in (curses.KEY_LEFT, ord("h"), ord("[")):
                    cur = asset_idx_by_seed.get(meta.seed_id, 0)
                    if cur > 0:
                        asset_idx_by_seed[meta.seed_id] = cur - 1

    curses.wrapper(_loop)
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed-beat terminal explorer")
    parser.add_argument("--root", default=None, help="Seeds root directory (default: ./seeds)")
    parser.add_argument("--demo", action="store_true", help="Print a non-interactive demo view and exit")
    args = parser.parse_args(argv)

    seeds_root = Path(args.root) if args.root else Path("seeds")

    if args.demo:
        print(demo_output(seeds_root=seeds_root))
        return 0

    return _run_curses(seeds_root)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
