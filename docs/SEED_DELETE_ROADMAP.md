# Seed Delete Feature Roadmap (Agent Guide)

Goal: provide a **safe, predictable way to delete seeds** (and their on-disk
assets) via tools in this repo, with clear user confirmation and index
consistency. This document is for future agents implementing, extending, or
debugging delete flows.

This builds on the canonical seed layout described in
`docs/SEED_STORAGE_ROADMAP.md` and the Codex workflow in
`docs/CODEX_SEED_WORKFLOW.md`.

---

## 0. Checklist Overview

Use this as a high-level progress tracker. Mark items with `[x]` once done.

- [ ] Step 1 – Baseline verification
- [ ] Step 2 – CLI delete command (`seed_cli delete`)
- [ ] Step 3 – Shared delete helper + TUI alignment
- [ ] Step 4 – Tests (unit + integration)
- [ ] Step 5 – Docs & examples

---

## 1. Baseline: What Already Exists

**Intent:** Confirm current behaviour and assumptions before adding new delete
paths.

- [ ] Confirm canonical seed layout in `docs/SEED_STORAGE_ROADMAP.md`:
  - `seeds/<seed_id>/config.json`, `metadata.json`, `drums/`, `bass/`, `leads/`, `analysis/`.
  - `SeedMetadata.render_path == "drums/main.mid"`.
  - All `SeedAsset.path` values are relative to the seed directory.
- [ ] Confirm `rebuild_index(seeds_root=...)` behaviour:
  - Scans `seeds/` and returns `List[SeedMetadata]`.
  - Performs migration/normalisation (e.g. path canonicalisation).
- [ ] Confirm TUI (seed explorer) delete behaviour:
  - In list/detail mode, **Shift+D** sets a `pending_delete` seed id.
  - Status message: `Confirm delete <seed_id>? y/N`.
  - `y`/`Y` → `shutil.rmtree(seeds_root/<seed_id>)` + `rebuild_index(...)`.
  - Any other key cancels deletion.

**Unit-test checklist for Step 1**

These may already exist; if not, consider adding focused tests:

- [ ] Tests asserting canonical layout invariants (render_path, relative paths).
- [ ] Tests for `rebuild_index` migration behaviour.
- [ ] (Optional) A small TUI smoke test or non-interactive demo check
      (`demo_output`) confirming basic explorer behaviour.

---

## 2. CLI Delete Command: `seed_cli delete`

**Goal:** Add a non-interactive delete path to complement the TUI.

### 2.1 Behaviour Spec

- Command line interface:
  - `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_cli delete --seed-id <seed_id> [--root PATH] [--yes]`

- Arguments:
  - `--seed-id <seed_id>` (required): name of folder under `seeds_root`.
  - `--root PATH` (optional, default: `./seeds`): base directory containing
    seed folders.
  - `--yes` / `-y` (optional): skip interactive confirmation.

- Execution flow:
  1. Resolve `seeds_root = Path(args.root or "seeds")`.
  2. Compute `seed_dir = seeds_root / seed_id`.
  3. If `seed_dir` does not exist or is not a directory:
     - Print: `Seed <seed_id> not found under <seeds_root>`.
     - Exit with non-zero status code.
  4. If `--yes` is **not** provided:
     - Load `metadata.json` (if present) and print a short summary:
       - `seed_id`, `engine_mode`, `bpm`, `tags`, and main asset path.
     - Prompt on stdout:
       - `Delete seed <seed_id> under <seed_dir>? [y/N]: `
     - Read a line from stdin; only proceed if first non-whitespace char is
       `y` or `Y`. Otherwise:
       - Print `Aborted`.
       - Exit with non-zero status.
  5. On confirmed delete (via `--yes` or prompt):
     - Recursively delete `seed_dir` (see helper in Step 3).
     - Call `rebuild_index(seeds_root=seeds_root)`.
     - Exit with status code 0.

- Safety constraints:
  - Never delete anything outside `seeds_root`.
  - Do not touch `out/` or other non-seed directories.
  - Do not attempt to adjust other seeds; they are independent.

### 2.2 Implementation Notes

- Implement as a subcommand in `src/techno_engine/seed_cli.py`:
  - Extend the existing `argparse` subparsers with a `delete` command.
  - Implement a `cmd_delete(args) -> int` handler.
- Reuse the same seeds root discovery logic as other subcommands.

**Step 2 checklist**

- [ ] `seed_cli` exposes a `delete` subcommand.
- [ ] `--seed-id`, `--root`, and `--yes` are wired correctly.
- [ ] Behaviour for existing seed, missing seed, and aborted prompt matches spec.

**Unit-test checklist for Step 2**

- [ ] `delete_existing_seed_with_yes`:
  - Setup a temporary seeds root with one minimal seed.
  - Run `seed_cli delete --seed-id <id> --root <tmp>/seeds --yes`.
  - Assert `seed_dir` is gone and exit code is 0.
- [ ] `delete_missing_seed`:
  - Call delete on a non-existent id.
  - Assert non-zero exit code and no deletions.
- [ ] (Optional) `delete_existing_seed_with_prompt`:
  - Feed `y\n` to stdin and confirm delete.
  - Feed `n\n` and confirm seed remains.

---

## 3. Shared Helper & TUI Alignment

**Goal:** Ensure TUI and CLI reuse the same core deletion logic for consistency.

### 3.1 Shared helper

Introduce a helper in `src/techno_engine/seeds.py` or a small utility module:

```python
from pathlib import Path
import shutil

from .seeds import rebuild_index


def delete_seed_dir(seed_id: str, seeds_root: Path) -> None:
    seed_dir = seeds_root / seed_id
    if not seed_dir.is_dir():
        raise FileNotFoundError(f"Seed {seed_id} not found under {seeds_root}")
    shutil.rmtree(seed_dir)
    rebuild_index(seeds_root=seeds_root)
```

- CLI `cmd_delete` should call this helper after confirmation.
- TUI code (in `seed_explorer`) may be refactored to call the same helper,
  removing duplicated deletion logic.

### 3.2 Behaviour alignment

After the helper is in place:

- [ ] TUI and CLI both:
  - Delete exactly `seeds_root/<seed_id>`.
  - Call `rebuild_index(seeds_root=...)` after deletion.
  - Treat missing seeds as errors (CLI: non-zero exit; TUI: status message).

**Unit-test checklist for Step 3**

- [ ] A unit test for `delete_seed_dir` using a temporary seeds root.
- [ ] Optional: a regression test ensuring `rebuild_index` is called (e.g. by
      asserting that `rebuild_index` sees no seeds after deletion).

---

## 4. Tests (Unit & Integration)

**Goal:** Ensure deletion is safe, predictable, and doesn&apos;t affect other seeds.

### 4.1 Unit tests

- [ ] `test_delete_seed_dir_removes_only_target`:
  - Create two seeds under a temp root.
  - Delete one with `delete_seed_dir`.
  - Assert:
    - Target seed dir is gone.
    - Other seed dir remains.
- [ ] `test_delete_seed_dir_missing_raises`:
  - Call `delete_seed_dir` with a non-existent id.
  - Assert `FileNotFoundError`.

### 4.2 CLI integration tests

- [ ] `test_seed_cli_delete_yes` (see Step 2 checklist).
- [ ] `test_seed_cli_delete_missing` (see Step 2 checklist).
- [ ] (Optional) `test_seed_cli_delete_prompt_abort`.

### 4.3 Regression / safety tests

- [ ] Add or extend tests that:
  - Confirm other seeds are unaffected by deletion of one seed.
  - Confirm indexes (e.g. any seed index files or `rebuild_index` results) no
    longer include the deleted seed.

---

## 5. Documentation & Examples

**Goal:** Make seed deletion discoverable and clearly documented for users and
future agents.

### 5.1 Codex workflow docs

Update `docs/CODEX_SEED_WORKFLOW.md` with a short "Deleting seeds" section:

- TUI:
  - Describe Shift+D on the selected seed, `Confirm delete <seed_id>? y/N`.
  - `y`/`Y` deletes; other keys cancel.
- CLI:
  - Show example usage:
    - `PYTHONPATH=src .venv/bin/python -m techno_engine.seed_cli delete --seed-id <id> --root seeds --yes`
  - Note that deletion is irreversible and removes the entire `seeds/<id>/`.

### 5.2 README (optional)

- [ ] Add a brief "Seed management" section linking to `CODEX_SEED_WORKFLOW.md`.

### 5.3 Final verification

- [ ] Run `source .venv/bin/activate && pytest -q` on the feature branch.
- [ ] After merge to `master`, run tests again on `master`.
- [ ] Optionally, document the final status in this file (e.g. date, user,
      commit hash where delete feature landed).

