# Codex Seed Workflow

Quick reference for generating seeds and nested variations so the TUI shows everything in one place (Enter → detail, h/l to flip assets).

## Seed layout
- Each seed lives under `seeds/<seed_id>/` with:
  - `config.json` — canonical drum config snapshot.
  - `metadata.json` — SeedMetadata JSON.
  - `drums/main.mid` — main rhythm pattern for this seed.
  - Optional subfolders: `drums/variants/`, `bass/`, `bass/variants/`, `leads/`, `analysis/`.
- `metadata.json` (key fields): `seed_id`, `engine_mode`, `bpm`, `bars`, `ppq`, `rng_seed`, `config_path`, `render_path`, `tags`, `summary`, `prompt`, `parent_seed_id`, `assets` (list of `{role, kind, path, description}`).
- `render_path` is always `"drums/main.mid"` and all `assets[].path` entries are
  relative to the seed directory (e.g. `drums/main.mid`, `bass/main.mid`,
  `bass/variants/…`).
- `rebuild_index()` normalizes legacy seeds into this layout and rewrites
  `metadata.json` and `index.json` accordingly.

## Baseline render (new seed)
1) Start from a config (e.g., `configs/m4_warehouse_sync.json`).
2) Render and save:  
   `PYTHONPATH=src .venv/bin/python -m techno_engine.run_config --config <cfg> --save-seed --prompt-text "<prompt>" --tags "<tags>" --summary "<summary>"`
3) A new seed folder appears under `seeds/<seed_id>/` with config + metadata.

## Nested variations under an existing seed
Purpose: keep child patterns visible inside the parent seed’s detail view.
1) Use the parent seed’s config as base: `seeds/<parent_seed_id>/config.json`.
2) Set outputs **inside the parent seed folder**, e.g. `seeds/<parent_seed_id>/variants/<name>.mid` (and logs alongside).
3) Render with parent linkage:  
   `PYTHONPATH=src .venv/bin/python -m techno_engine.run_config --config /tmp/<name>.json --save-seed --parent-seed-id <parent_seed_id> --prompt-text "<prompt>" --tags "m4,variation,<label>" --summary "<summary>"`
4) Register the new file in the parent `metadata.json` (so the TUI shows it):  
   ```json
   { "role": "variant", "kind": "midi", "path": "seeds/<parent_seed_id>/variants/<name>.mid", "description": "<what changed>" }
   ```
   Keep the original main render asset intact.
5) Optional: note the child seed_id; lineage is already recorded via `parent_seed_id`.
6) Refresh: run `rebuild_index()` or just open the TUI; it rewrites `index.json`.

## Paired drums + bass render
- Render drums + groove-aware bass and save a seed in one go:
  `PYTHONPATH=src .venv/bin/python -m techno_engine.paired_render_cli --config <cfg> --prompt-text "<prompt>" --tags "<tags>" --summary "<summary>"`
- Seed will contain main drum MIDI (role `main`) and a `bass` asset pointing to the paired bassline.

## Bass-from-seed
- Given an existing seed, append a groove-aware bass asset:
  `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_cli bass-from-seed <seed_id> [--bass-mode ... --root-note ... --tags ... --description ...]`
- The CLI resolves the seed's drum MIDI, analyzes it, generates a bassline, writes it inside the seed folder, and appends a `bass/midi` asset.

## Explorer usage
- Launch: `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_explorer`
- List: j/k move, Enter details, r refresh, q quit.
- Detail: j/k move seeds, h/l cycle assets, q/Esc back. Shows seed dir/config/meta paths, assets, MIDI summary, drum pattern preview (16 steps), prompt/summary, and these codex notes.

## Best practices
- Prefer storing new renders inside the parent seed folder for nested visibility.
- Always append a SeedAsset entry after generating a new file.
- Keep BPM/PPQ/Bars consistent unless intentionally changing them.
- Use descriptive prompts/summaries/tags for future automation and UI clarity.

## Deleting seeds

You can delete seeds (including all assets under `seeds/<seed_id>/`) via:

- TUI:
  - Open the explorer:
    `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_explorer`
  - In list or detail mode:
    - Press **Shift+D** on the selected seed to mark it for deletion.
    - Confirm with `y`/`Y` when prompted (`Confirm delete <seed_id>? y/N`).
    - Any other key cancels the delete.
  - On confirm, the entire seed folder is removed and the index is rebuilt.

- CLI:
  - `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_cli delete --seed-id <seed_id> [--root seeds] [--yes]`
  - Without `--yes`, the CLI prints a short summary and prompts:
    `Delete seed <seed_id> under <path>? [y/N]:`
  - With `--yes`, it deletes without prompting.
  - On success it removes `seeds/<seed_id>` and runs `rebuild_index`.
  - On missing seed or failures it exits with a non-zero status.

Deletion must never touch anything outside the configured seeds root.
