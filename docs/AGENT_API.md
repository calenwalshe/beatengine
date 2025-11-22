# Agent API (Tools + Contracts)

Version: 1.1.0

This document defines the tool contracts used by the Terminal Orchestrator (or any agent runtime) for planning and execution. Tools are thin wrappers around the CLIs in `src/techno_engine/` with JSON inputs/outputs and controlled side effects.

## Operating Model

- Paths are workspace‑relative. Tools may read and write only under:
  - `configs/` — Engine configs.
  - `seeds/` — self‑contained seed projects.
  - `out/` — scratch/test renders.
- Agents should:
  - Prefer **seeds** for anything long‑lived (library of grooves).
  - Treat configs as templates and patch them via `create_config` or `write_config`.
  - Never modify files directly; always go through tools.
  - Keep resource usage bounded: avoid rendering more than ~10 seeds or >64 bars per request without an explicit user ask.

## Conventions

- All tools use the same envelope:

```json
{"ok": true, "result": {"midi": "out/track.mid"}}
```

```json
{"ok": false, "error": {"code": "BAD_CONFIG", "message": "missing bpm"}}
```

- On success, `ok=true` and `result` is a typed object.
- On failure, `ok=false` and `error.code` is one of the error codes below.

---

## Drum + Bass Tools

These tools are the primary way agents render audio‑ready MIDI.

### Tool: render_session

Render a drum session from an Engine config (m1/m2/m4). Wraps `run_config.py`.

Input:
- `config_path` (string) — path to JSON config under `configs/`.

Output:
- `midi` (string) — workspace‑relative drums MIDI path.
- `log_path` (string|null) — CSV metrics path (if configured on the config).
- `meta` (object) — `{bpm, ppq, bars, mode}`.

Errors: `BAD_CONFIG`, `IO_ERROR`.

Recommended use:
- One‑shot drum demos.
- First step before creating a seed if you do not need bass.

### Tool: make_bass_for_config

Render drums from a config and generate a groove‑aware bassline aligned to the drums. Wraps the behaviour of `combo_cli.py` (separate drum and bass files).

Input:
- `config_path` (string) — drum config under `configs/`.
- `key` (string, optional) — e.g. `"A"`, `"D#"`. If present, converted to a root note.
- `mode` (string, optional) — musical mode colouring, e.g. `"minor"`.
- `density` (number, optional) — target fraction of 16ths per bar (default `0.4`).
- `motif` (string, optional) — motif preset (`root_only`, `root_fifth`, etc.).
- `phrase` (string, optional) — phrase preset (`rise`, `bounce`, `fall`, etc.).
- `save_prefix` (string, optional) — naming hint for output files under `out/`.

Output:
- `drums` (string) — drums MIDI path.
- `bass` (string) — bass MIDI path.
- `metrics` (object) — median metrics over bars, e.g. `{E_med, S_med}`.

Errors: `BAD_CONFIG`, `BAD_ARGS`, `IO_ERROR`.

Recommended use:
- When the user wants drums and bass as **separate** files without touching seeds.

### Tool: bass_generate

Generate a bassline only, using either MVP or drum‑aware scoring. Wraps `bass_cli.py`/`combo_cli.py` internals.

Input:
- `mode` (string) — `"mvp"` or `"scored"`.
- Common (both modes):
  - `bpm` (number), `ppq` (integer), `bars` (integer <= 64).
  - `root_note` (integer, MIDI note).
  - `density` (number) — target fraction of 16ths per bar.
  - `min_dur_steps` (number) — minimum 16th‑note duration (e.g. `0.5`).
- Scored mode only:
  - `kick_masks_by_bar` (array) — 16‑step masks per bar.
  - `hat_masks_by_bar` (array, optional).
  - `clap_masks_by_bar` (array, optional).
- Musical colouring (optional):
  - `degree` (string) — e.g. `"minor"` or `"none"`.
  - `motif` (string) — see `MOTIFS_PHRASES.md`.
  - `phrase` (string) — see `MOTIFS_PHRASES.md`.

Output:
- `midi` (string) — bass MIDI path.
- `notes_written` (integer).

Errors: `BAD_ARGS`, `IO_ERROR`.

### Tool: bass_validate

Validate and correct a bassline: remove kick collisions, enforce monophony, and adjust density. Wraps `bass_validate.py`.

Input:
- `midi_in` (string) — existing bass MIDI.
- `bpm` (number), `ppq` (integer), `bars` (integer).
- `density_target` (number) — desired density.

Output:
- `midi_out` (string) — corrected MIDI path.
- `summaries` (string[]) — human‑readable corrections applied.

Errors: `IO_ERROR`.

Recommended use:
- After any non‑seed bass generation step before presenting to users.

---

## Config Tools

### Tool: create_config

Create a new Engine config by cloning a base and applying patches. Intended to be **high‑level only**; see `CONFIG_SCHEMA.md` for safe fields and ranges.

Input:
- `base_path` (string) — existing config JSON under `configs/`.
- `patch` (object) — shallow fields to override (e.g. `{"bpm": 126}` or nested dot‑paths).
- `save_as` (string) — new config path under `configs/`.

Output:
- `config_path` (string) — final saved config path.

Errors: `BAD_CONFIG`, `BAD_ARGS`, `IO_ERROR`, `PATH_OUT_OF_SANDBOX`.

### Tool: list_configs / read_config / write_config

- `list_configs`
  - Input: none.
  - Output: `configs` (string[]) — JSON config paths under `configs/`.
- `read_config`
  - Input: `config_path` (string).
  - Output: `config` (object) — parsed JSON.
- `write_config`
  - Input: `config_path` (string), `config` (object).
  - Output: `config_path` (string).

All three enforce that paths stay within `configs/`. `write_config` should be used sparingly; prefer `create_config` for new variants.

---

## Seed Tools

Seeds are the recommended way for agents to maintain a groove library. See `SEED_STORAGE_ROADMAP.md` for the on‑disk layout and `CODEX_SEED_WORKFLOW.md` for workflows.

### Tool: seed_list

List available seeds with simple filters. Wraps `seed_cli list`.

Input:
- `root` (string, optional) — seeds root (default `"seeds"`).
- `mode` (string, optional) — engine mode filter (`"m1"|"m2"|"m4"`).
- `tag` (string, optional) — single tag filter.
- `bpm_min` (number, optional), `bpm_max` (number, optional).

Output:
- `seeds` (array of objects) — each matching `SeedMetadata` (see `seeds.py`).

Errors: `IO_ERROR`.

### Tool: seed_show

Return full metadata for a single seed. Wraps `seed_cli show --json`.

Input:
- `seed_id` (string).
- `root` (string, optional).

Output:
- `metadata` (object) — raw `metadata.json` contents.

Errors: `NO_SUCH_SEED`, `IO_ERROR`.

### Tool: seed_render

Render audio‑ready drums (and optionally bass/lead assets) from a seed. Wraps `seed_cli render`.

Input:
- `seed_id` (string).
- `root` (string, optional).
- `out` (string, optional) — destination MIDI path; if omitted, uses the seed’s canonical render.

Output:
- `midi` (string) — rendered MIDI path.

Errors: `NO_SUCH_SEED`, `BAD_ARGS`, `IO_ERROR`.

### Tool: seed_clone

Clone a seed, optionally overriding tempo/length/seed/out and saving a new seed. Wraps `seed_cli clone`.

Input:
- `seed_id` (string).
- `root` (string, optional).
- `bpm` (number, optional).
- `bars` (integer, optional).
- `seed` (integer, optional) — RNG seed.
- `out` (string, optional) — override output file name.
- `prompt_text` (string, optional).
- `tags` (string, optional) — comma‑separated tags.
- `summary` (string, optional).

Output:
- `seed_id` (string) — new seed id.
- `metadata` (object) — metadata for the new seed.

Errors: `NO_SUCH_SEED`, `BAD_CONFIG`, `IO_ERROR`.

### Tool: seed_import_mid

Import an external MIDI file as a new seed. Wraps `seed_cli import-mid`.

Input:
- `path` (string) — external MIDI path.
- `root` (string, optional).
- `prompt_text` (string, optional).
- `tags` (string, optional).
- `summary` (string, optional).

Output:
- `seed_id` (string).
- `metadata` (object).

Errors: `IO_ERROR`, `BAD_ARGS`.

### Tool: seed_bass_from_seed

Generate groove‑aware bass for an existing seed and register it as a bass asset. Wraps `seed_cli bass-from-seed`.

Input:
- `seed_id` (string).
- `root` (string, optional).
- `bass_mode` (string, optional) — bass mode override (see `BASS_GROOVE_ROADMAP.md`).
- `root_note` (integer, optional) — MIDI note (default 45).
- `tags` (string, optional) — comma‑separated tag overrides.
- `out` (string, optional) — relative path under `bass/` (e.g. `"variants/bass_leadish.mid"`).
- `description` (string, optional) — asset description for metadata.

Output:
- `seed_id` (string).
- `bass_asset_path` (string) — path relative to the seed dir.

Errors: `NO_SUCH_SEED`, `IO_ERROR`, `BAD_ARGS`.

### Tool: seed_lead_from_seed

Generate a lead line for an existing seed and register it as a lead asset. Wraps `seed_cli lead-from-seed`.

Input:
- `seed_id` (string).
- `root` (string, optional).
- `mode` (string, optional) — lead mode override (see `LEAD_MODES_ROADMAP.md`).
- `tags` (string, optional) — comma‑separated tag overrides.
- `out` (string, optional) — relative path under `leads/`.
- `description` (string, optional) — asset description.

Output:
- `seed_id` (string).
- `lead_asset_path` (string).

Errors: `NO_SUCH_SEED`, `IO_ERROR`, `BAD_ARGS`.

### Tool: seed_delete

Delete a seed directory and rebuild the index. Wraps `seed_cli delete`.

Input:
- `seed_id` (string).
- `root` (string, optional).
- `yes` (boolean) — must be `true`; agents should only call this when a user explicitly asks to delete.

Output:
- `deleted` (boolean) — `true` if deletion succeeded.

Errors: `NO_SUCH_SEED`, `IO_ERROR`.

Guardrail:
- Agents must never call `seed_delete` without explicit user intent.

---

## Doc Tools

These tools allow the agent to self‑serve from the documentation set.

### Tool: list_docs / search_docs / read_doc / doc_answer

- `list_docs`
  - Input: none.
  - Output: `docs` (string[]) — doc paths under `docs/`.
- `search_docs`
  - Input: `query` (string).
  - Output: `matches` (string[]) — candidate doc paths.
- `read_doc`
  - Input: `path` (string).
  - Output: `text` (string) — full document body.
- `doc_answer`
  - Input: `question` (string).
  - Output: `answer` (string) — concise, sourced explanation based on the docs.

---

## Error Codes and Agent Behaviour

- `BAD_CONFIG` — missing or invalid fields in a config.  
  - Action: consult `CONFIG_SCHEMA.md`, adjust patch or choose a different base config.
- `BAD_ARGS` — input arguments are malformed or out of range.  
  - Action: clamp values into documented ranges (`PARAM_EFFECTS.md`) and retry once.
- `VERSION_MISMATCH` — client/server tool schema versions differ.  
  - Action: stop, surface the problem to the user; do not auto‑retry.
- `NO_SUCH_SEED` — referenced seed does not exist.  
  - Action: refresh with `seed_list`, ask the user which seed to use.
- `IO_ERROR` — file system errors (missing paths, permissions, etc.).  
  - Action: avoid destructive retries; report to user.
- `PATH_OUT_OF_SANDBOX` — attempted access outside `configs/`, `seeds/`, or `out/`.  
  - Action: immediately stop the current plan and ask for human guidance.

Agents should treat any unknown `error.code` as fatal for the current plan and hand control back to the user.

---

## Example: make_bass_for_config

Request:

```json
{
  "tool": "make_bass_for_config",
  "args": {
    "config_path": "configs/m4_95bpm.json",
    "key": "A",
    "mode": "minor",
    "density": 0.40,
    "motif": "root_fifth_octave",
    "phrase": "rise"
  }
}
```

Response:

```json
{
  "ok": true,
  "result": {
    "drums": "out/m4_95bpm_minor_drums.mid",
    "bass": "out/m4_95bpm_minor_bass.mid",
    "metrics": {"E_med": 0.81, "S_med": 0.51}
  }
}
```
