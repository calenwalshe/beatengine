#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_URL="${ARCHIVE_URL:-https://codeload.github.com/mltechno/techno_rhythm_engine/tar.gz/refs/heads/main}"
DEMO_CONFIG="${DEMO_CONFIG:-configs/m4_showcase.json}"

log() { printf '>>> %s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

if ! command -v python3 >/dev/null 2>&1; then
  fail "Python 3 not found. Install from https://www.python.org/downloads/macos/ and re-run."
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

log "Downloading engine archive"
curl -fsSL "$ARCHIVE_URL" -o repo.tar.gz || fail "Unable to download $ARCHIVE_URL"

log "Extracting archive"
tar xzf repo.tar.gz
ROOT_DIR="$(tar tzf repo.tar.gz | head -1 | cut -d/ -f1)"
cd "$ROOT_DIR"

log "Creating virtual environment"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python3 -m pip install --upgrade pip >/dev/null

if [[ -f requirements.txt ]]; then
  python3 -m pip install -r requirements.txt >/dev/null
else
  python3 -m pip install mido >/dev/null
fi

if [[ ! -f "$DEMO_CONFIG" ]]; then
  fail "Demo config '$DEMO_CONFIG' not found in archive"
fi

log "Rendering demo using $DEMO_CONFIG"
python3 -m techno_engine.run_config --config "$DEMO_CONFIG"

log "Demo complete. MIDI written under out/."
log "Activate the environment with 'source $PWD/.venv/bin/activate' to run other configs."
