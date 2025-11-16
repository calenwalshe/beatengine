# Seed Beats Feature Plan

Tracking plan, progress, and demos for the seed-beats feature and future TUI explorer.

## Overview

Goal: every time we generate a beat, treat it as a "seed beat" with:
- Exact config for perfect regeneration
- Stored metadata (prompt, tags, summary, engine settings, paths)
- APIs/CLIs to list, inspect, and re-render seeds
- JSON/index output to power a future terminal-based explorer

Branch: `feature/seed-beats`

---

## Step 1 – Branch & Scaffolding

**Objective:** Create the working branch and a minimal seeds module that imports cleanly.

- Implementation
  - Create branch: `git checkout -b feature/seed-beats`
  - Add `src/techno_engine/seeds.py` with a minimal placeholder (e.g., module docstring and a no-op function or `SeedMetadata` stub).
- Demo
  - `git branch` shows `* feature/seed-beats`
  - `python -c "import techno_engine.seeds"` runs without error
- Unit Test
  - `tests/test_seeds_smoke.py::test_seeds_module_imports` asserts that `import techno_engine.seeds` succeeds.

---

## Step 2 – SeedMetadata Model & Save/Load

**Objective:** Define the core data model and filesystem layout for seeds.

- Implementation
  - In `src/techno_engine/seeds.py`:
    - Add a `SeedMetadata` dataclass with fields like:
      - `seed_id`, `created_at`, `engine_mode`, `bpm`, `bars`, `rng_seed`
      - `config_path`, `render_path`, `log_path`
      - `prompt`, `prompt_context`, `summary`, `tags`
      - `parent_seed_id`, `file_version`
    - Implement:
      - `save_seed(config: EngineConfig, config_path: str, render_path: str, *, prompt: str | None = None, summary: str | None = None, tags: list[str] | None = None, log_path: str | None = None) -> SeedMetadata`
      - `load_seed(seed_id: str) -> tuple[EngineConfig, SeedMetadata]`
    - Filesystem layout:
      - `seeds/<seed_id>/config.json`
      - `seeds/<seed_id>/metadata.json`
      - `seeds/<seed_id>/render.mid` (or symlink/reference)
- Demo
  - Run a small demo script (or REPL snippet) that:
    - Constructs a tiny `EngineConfig`
    - Calls `save_seed(...)`
    - Calls `load_seed(seed_id)` and prints `seed_id`, `bpm`, `render_path`
- Unit Test
  - `tests/test_seeds_basic.py::test_seed_save_and_load_roundtrip`:
    - Creates a small config and temp render path
    - Saves a seed
    - Loads it back and asserts key fields round-trip correctly.

---

## Step 3 – Integrate Seeds into run_config Flow

**Objective:** Automatically save seeds when beats are generated from JSON configs.

- Implementation
  - In `src/techno_engine/run_config.py`:
    - Add CLI flags:
      - `--save-seed` (bool)
      - `--prompt-text` (str, optional)
      - `--tags` (comma-separated, optional)
      - `--summary` (str, optional)
    - After a successful render:
      - If `--save-seed` is set, call `save_seed(...)` with:
        - `cfg` (EngineConfig)
        - the `--config` path
        - the MIDI output path
        - prompt / tags / summary if provided
      - Print the `seed_id` so callers can capture it.
- Demo
  - Run:
    - `python -m techno_engine.run_config --config configs/m4_warehouse_sync.json --save-seed --prompt-text "warehouse m4 groove" --tags "m4,warehouse" --summary "Driving warehouse m4 pattern"`
  - Confirm:
    - New folder appears under `seeds/`
    - It contains `config.json`, `metadata.json`, and a `render.mid`
    - CLI prints the `seed_id`
- Unit Test
  - `tests/test_run_config_seeds.py::test_run_config_saves_seed`:
    - Uses a small test config and temp output directory
    - Invokes `main()` with `--save-seed`
    - Asserts that a seed folder is created and metadata matches the config (mode, bpm, bars, seed, out path).

---

## Step 4 – Seed CLI (list/show/render/clone)

**Objective:** Provide user-friendly commands to explore and reuse seeds.

- Implementation
  - Add a `seed` subcommand to the CLI (e.g. in `src/techno_engine/cli.py` or a `seed_cli.py`):
    - `seed list [--tag=...] [--mode=...] [--bpm-min ... --bpm-max ...]`
    - `seed show <seed_id>`
    - `seed render <seed_id> [--out new.mid]`
    - `seed clone <seed_id> [--out new.mid] [--bpm ...] [--bars ...] [--tags +new-tag]`
  - Internally:
    - Use `list_seeds()`, `load_seed()`, and existing render logic.
    - For clone, create a new `EngineConfig` with overrides and save a new seed with `parent_seed_id`.
- Demo
  - `python -m techno_engine.cli seed list` → prints a table of seeds
  - `python -m techno_engine.cli seed show <seed_id>` → prints detailed metadata
  - `python -m techno_engine.cli seed render <seed_id> --out out/clone.mid` → regenerates the beat
- Unit Test
  - `tests/test_seed_cli.py::test_seed_list_and_show`:
    - Seeds the `seeds/` directory with a known metadata file
    - Runs the CLI via a helper
    - Asserts that `seed_id` and `bpm` are visible in the output.

---

## Step 5 – JSON/Index Output for Future TUI

**Objective:** Make seed data easy to consume for a terminal-based explorer.

- Implementation
  - In `src/techno_engine/seeds.py`:
    - Add optional index file support:
      - `seeds/index.json` (array of lightweight entries)
    - Implement:
      - `rebuild_index() -> list[SeedMetadata]`
      - `update_index(meta: SeedMetadata) -> None`
  - Extend CLI with JSON output:
    - `seed list --json` → prints JSON array of seed summaries (ideally from the index)
    - `seed show <seed_id> --json` → prints JSON object with full metadata
  - Design this so a future TUI can:
    - Call the CLI with `--json`, or
    - Import `seeds.py` directly to query seeds.
- Demo
  - `python -m techno_engine.cli seed list --json` → JSON array suitable for TUI consumption
  - `python -m techno_engine.cli seed show <seed_id> --json` → JSON object with metadata
- Unit Test
  - `tests/test_seeds_index.py::test_index_and_json_output`:
    - Creates a couple of seed folders
    - Calls `rebuild_index()`
    - Runs CLI with `--json`
    - `json.loads` the output and asserts that entries match the underlying metadata.

---

## Progress Tracking

As we implement each step, we can:
- Mark the step as **[DONE]** / **[IN PROGRESS]** / **[TODO]**
- Add notes under each step with:
  - Commit hashes
  - Demo commands used
  - Any deviations from the original plan

