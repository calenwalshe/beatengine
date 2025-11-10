# Agent API (Tools + Contracts)

Version: 1.0.0

This document defines the stable tool contracts used by the Terminal Orchestrator for planning and execution. All tools are pure functions with JSON inputs/outputs and deterministic side effects (file writes under `configs/` and `out/`).

## Conventions

- Paths are workspace-relative. Tools must not write outside `configs/` and `out/`.
- Errors return `error` with a machine-readable `code` and human `message`.
- Success returns `ok=true` and a typed `result`.

```json
{"ok": true, "result": {"midi": "out/track.mid"}}
```

```json
{"ok": false, "error": {"code": "BAD_CONFIG", "message": "missing bpm"}}
```

## Tool: render_session

Render a drum session from an Engine config and optional logging.

Input:
- `config_path` (string) — path to JSON config

Output:
- `midi` (string) — drums MIDI path
- `log_path` (string|null) — CSV metrics path (if configured)
- `meta` (object) — `{bpm, ppq, bars}`

Errors: `BAD_CONFIG`, `IO_ERROR`

## Tool: make_bass_for_config

Render drums from a config and make a scored bassline aligned to the drums.

Input:
- `config_path` (string)
- `key` (string, optional) — e.g., "A"
- `mode` (string, optional) — e.g., "minor"
- `density` (number, optional) — target fraction per bar (default 0.4)
- `save_prefix` (string, optional) — file naming hint

Output:
- `drums` (string) — drums MIDI path
- `bass` (string) — bass MIDI path
- `metrics` (object) — `{E_med, S_med}` medians over bars

Errors: `BAD_CONFIG`, `IO_ERROR`

## Tool: bass_generate

Generate a bassline only, using either MVP or drum-aware scoring.

Input:
- `mode` ("mvp"|"scored")
- Common: `bpm`, `ppq`, `bars`, `root_note`, `density`, `min_dur_steps`
- Scored: `kick_masks_by_bar`, `hat_masks_by_bar?`, `clap_masks_by_bar?`
- Musical colouring: `degree?` (e.g., minor), `motif?`, `phrase?`

Output:
- `midi` (string) — bass MIDI path
- `notes_written` (integer)

Errors: `BAD_ARGS`, `IO_ERROR`

## Tool: bass_validate

Validate and correct a bassline: remove kick collisions, enforce monophony, adjust density.

Input:
- `midi_in` (string), `bpm`, `ppq`, `bars`, `density_target`

Output:
- `midi_out` (string) — corrected path
- `summaries` (string[]) — human-readable edits summary

Errors: `IO_ERROR`

## Tool: create_config

Create a new Engine config by cloning a base and applying patches.

Input:
- `base_path` (string) — existing config JSON
- `patch` (object) — shallow fields to override (e.g., `{"bpm": 126}`)
- `save_as` (string) — new config path under `configs/`

Output:
- `config_path` (string)

Errors: `BAD_CONFIG`, `IO_ERROR`, `PATH_OUT_OF_SANDBOX`

## Tool: list_configs / read_config / write_config

- `list_configs`: returns known JSON configs under `configs/`.
- `read_config`: loads and returns parsed JSON.
- `write_config`: writes JSON to a safe path under `configs/`.

## Tool: list_docs / search_docs / read_doc / doc_answer

- `list_docs`: list available doc files under `docs/`.
- `search_docs`: simple keyword search; returns candidate paths.
- `read_doc`: returns the full text of a doc.
- `doc_answer`: higher-level helper that returns a concise answer by searching and reading.

## Error Codes

- `BAD_CONFIG` — missing or invalid fields in a config
- `BAD_ARGS` — input arguments are malformed or out of range
- `VERSION_MISMATCH` — client/server tool schema versions differ
- `IO_ERROR` — file system errors
- `PATH_OUT_OF_SANDBOX` — attempted to access outside `configs/` or `out/`

## Examples

### make_bass_for_config

Request:

```json
{
  "tool": "make_bass_for_config",
  "args": {"config_path": "configs/m4_95bpm.json", "key": "A", "mode": "minor", "density": 0.40}
}
```

Response:

```json
{
  "ok": true,
  "result": {
    "drums": "out/95/drums.mid",
    "bass": "out/95/bass.mid",
    "metrics": {"E_med": 0.81, "S_med": 0.51}
  }
}
```

