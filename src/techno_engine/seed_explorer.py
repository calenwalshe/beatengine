from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .seeds import SeedMetadata, rebuild_index


def _format_row(meta: SeedMetadata) -> str:
    sid_disp = meta.seed_id
    tag_str = ",".join(meta.tags) if meta.tags else "-"
    return f"{sid_disp:27}  {meta.engine_mode:3}  {meta.bpm:5.1f}  {meta.bars:3d}  {tag_str}"


def demo_output(seeds_root: Path | None = None, limit: int | None = None) -> str:
    """Build a simple textual overview of seeds for non-interactive/demo use.

    This is used by tests and as a quick preview when you don't want the
    full curses UI.
    """

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


def _run_curses(seeds_root: Path) -> int:
    """Run a minimal curses-based explorer.

    Left pane: list of seeds. Right pane: details for selected seed.
    """

    import curses  # imported lazily to keep tests simple

    metas: List[SeedMetadata] = rebuild_index(seeds_root=seeds_root)

    if not metas:
        print("No seeds found under", seeds_root)
        return 0

    def _loop(stdscr: "curses._CursesWindow") -> None:  # type: ignore[name-defined]
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.keypad(True)

        selected = 0
        top = 0

        while True:
            h, w = stdscr.getmaxyx()
            stdscr.erase()

            title = "Seed Explorer (q to quit, j/k or arrows to move)"
            stdscr.addnstr(0, 0, title, w - 1)

            left_w = max(40, w // 2)
            list_height = h - 3

            # Draw header
            header = "seed_id (short)                m  bpm   bar  tags"
            stdscr.addnstr(1, 0, header[: left_w - 1], left_w - 1, curses.A_BOLD)

            # Adjust top for scrolling
            if selected < top:
                top = selected
            elif selected >= top + list_height:
                top = selected - list_height + 1

            # Draw visible rows
            for row_idx in range(list_height):
                meta_idx = top + row_idx
                if meta_idx >= len(metas):
                    break
                meta = metas[meta_idx]
                row_y = 2 + row_idx
                text = _format_row(meta)
                attr = curses.A_REVERSE if meta_idx == selected else curses.A_NORMAL
                stdscr.addnstr(row_y, 0, text[: left_w - 1], left_w - 1, attr)

            # Right pane: details for selected seed
            detail_x = left_w + 1
            if detail_x < w - 1:
                meta = metas[selected]
                detail_lines = [
                    f"seed_id: {meta.seed_id}",
                    f"created: {meta.created_at}",
                    f"mode: {meta.engine_mode}  bpm: {meta.bpm}  bars: {meta.bars}  ppq: {meta.ppq}",
                    f"tags: {', '.join(meta.tags) if meta.tags else '-'}",
                    f"render: {meta.render_path}",
                ]
                if meta.summary:
                    detail_lines.append("")
                    detail_lines.append("summary:")
                    detail_lines.append(meta.summary)
                if meta.prompt:
                    detail_lines.append("")
                    detail_lines.append("prompt:")
                    detail_lines.append(meta.prompt)

                y = 1
                for line in detail_lines:
                    if y >= h:
                        break
                    stdscr.addnstr(y, detail_x, line[: max(0, w - detail_x - 1)], max(0, w - detail_x - 1))
                    y += 1

            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q"), 27):
                break
            if ch in (curses.KEY_DOWN, ord("j")):
                if selected < len(metas) - 1:
                    selected += 1
            elif ch in (curses.KEY_UP, ord("k")):
                if selected > 0:
                    selected -= 1
            elif ch in (ord("r"), ord("R")):
                # refresh index from disk
                refreshed = rebuild_index(seeds_root=seeds_root)
                if refreshed:
                    metas[:] = refreshed
                    if selected >= len(metas):
                        selected = max(0, len(metas) - 1)

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

