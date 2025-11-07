from __future__ import annotations

from pathlib import Path


def _extract_snippet(md_text: str, tag: str) -> str:
    lines = md_text.splitlines()
    inside = False
    buf: list[str] = []
    fence = "```"
    marker = f"# SNIPPET: {tag}"
    for i, ln in enumerate(lines):
        if marker in ln:
            inside = True
            continue
        if inside and ln.strip().startswith(fence):
            break
        if inside:
            buf.append(ln)
    return "\n".join(buf).strip()


def test_docs_snippets_run():
    p = Path("techno_rhythm_engine/docs/BASSLINE_API.md")
    if not p.exists():
        p = Path("docs/BASSLINE_API.md")
    body = p.read_text()
    for tag in ("generate_and_validate", "make_bass_for_config"):
        code = _extract_snippet(body, tag)
        ns: dict[str, object] = {}
        exec(code, ns, ns)
