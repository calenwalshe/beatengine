#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
docs_dir="$root_dir/docs"

fail() { echo "[FAIL] $*" >&2; exit 1; }

# Required man pages
for f in techno.1 techno-combo.1 techno-showcase.1 techno-bass.1; do
  test -f "$docs_dir/$f" || fail "Missing $f"
  grep -q "^\\.TH" "$docs_dir/$f" || fail "$f missing .TH header"
  grep -q "^\\.SH NAME" "$docs_dir/$f" || fail "$f missing NAME"
  grep -q "^\\.SH SYNOPSIS" "$docs_dir/$f" || fail "$f missing SYNOPSIS"
done

# Agent API and cheatsheets
test -f "$docs_dir/AGENT_API.md" || fail "Missing AGENT_API.md"

for c in PARAM_EFFECTS.md PLANNING_TEMPLATES.md CONFIG_SCHEMA.md METRICS.md MOTIFS_PHRASES.md; do
  test -f "$docs_dir/AGENT_CHEATSHEETS/$c" || fail "Missing AGENT_CHEATSHEETS/$c"
done

echo "[OK] docs-test passed"

