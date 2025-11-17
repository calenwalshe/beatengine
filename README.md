# Beatengine — Techno Rhythm & Groove-Aware Bass Engine

Beatengine is a Python techno rhythm engine that generates **drums and bass**
from configs and seeds. It started as a Berlin-style techno MIDI engine
(M0–M4) and has evolved into a **seed-aware, groove-aware** system with:

- Config-driven drum engines (m1/m2/m4).
- Self-contained *seeds* that store configs, renders, and metadata.
- A groove-aware bass generator that reacts to drum patterns.
- A terminal UI explorer for browsing and auditioning seeds.
- CLIs designed to work well both for humans and LLM agents.

---

## Features

- **Drum engines (M0–M4)**
  - High-resolution PPQ (1920) with micro-timing guardrails.
  - Configurable kick, hat, snare, clap layers with conditions and modulators.
  - m4 adds scoring/feedback, Markov modulators, and per-bar metrics.

- **Seed-aware storage**
  - Each render can be saved as a *seed* under `seeds/<seed_id>/`.
  - Seeds are self-contained projects: config, metadata, drums, bass, variants.
  - Canonical layout documented in `docs/SEED_STORAGE_ROADMAP.md`.

- **Groove-aware bass**
  - Analyzes drum MIDI and builds a 16-step “slot grid” per bar.
  - Mode-driven basslines (sub anchor, pocket groove, rolling, lead-ish, etc.).
  - Reacts to kick/snare/hat placement, swing, and tags (e.g. `warehouse`, `minimal`).
  - Design in `docs/BASS_GROOVE_ROADMAP.md`.

- **TUI Seed Explorer**
  - Curses-based terminal UI to browse seeds and assets.
  - List + detail views, drum pattern preview, MIDI summaries.
  - Shows clickable absolute `seed_dir` paths in most terminals.

- **CLIs & agent tooling**
  - `run_config`: render drums from JSON configs.
  - `paired_render_cli`: render drums + groove-aware bass in one pass.
  - `seed_cli`: list/show/render/clone/import/bass-from-seed/delete.
  - `seed_explorer`: terminal UI.
  - Agent-facing docs in `docs/AGENT_API.md`, `docs/AGENT_CHEATSHEETS/`.

---

## Quickstart (5-Minute Demo)

### 1. Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Optional: run tests
PYTHONPATH=src pytest -q
```

### 2. Render a demo seed (drums + bass)

Render an m4 warehouse groove and save it as a seed with paired drums + bass:

```bash
PYTHONPATH=src .venv/bin/python -m techno_engine.paired_render_cli \
  --config configs/m4_warehouse_sync.json \
  --prompt-text "warehouse m4 groove" \
  --tags "m4,warehouse,showcase" \
  --summary "Demo warehouse groove (drums + bass)"
```

This will:

- Render m4 drums and a groove-aware bassline.
- Save a new seed under `seeds/<seed_id>/`.
- Register both drum and bass MIDI files as assets in `metadata.json`.

### 3. Explore seeds in the TUI

```bash
PYTHONPATH=src .venv/bin/python -m techno_engine.seed_explorer
```

Keys (default explorer):

- List view: `j/k` move, `Enter` details, `r` refresh, `q` quit.
- Detail view: `j/k` change seed, `h/l` change asset, `q`/`Esc` back.
- Delete: `Shift+D` then `y`/`Y` to confirm (removes `seeds/<seed_id>/`).

On the detail page you’ll see:

- `seed_dir`, `config`, `metadata` paths.
- Assets (drums, bass, variants) with roles and descriptions.
- MIDI summaries and a 16-step drum pattern preview.
- Prompt, summary, and a link to the Codex workflow docs.

---

## Core Concepts

### Seeds & Layout

Every seed is a small project stored under `seeds/<seed_id>/`:

```text
seeds/<seed_id>/
  config.json          # canonical drum config snapshot
  metadata.json        # SeedMetadata JSON
  drums/
    main.mid           # main drum pattern for this seed
    variants/          # optional drum variants
      *.mid
  bass/
    main.mid           # primary bassline (if present)
    variants/
      *.mid            # additional basslines / leads
  leads/               # optional
  analysis/            # optional logs/metrics
```

Key rules:

- `metadata.json.render_path` is `"drums/main.mid"`.
- `SeedAsset.path` values are **relative** to the seed directory
  (e.g. `drums/main.mid`, `bass/variants/bass_leadish.mid`).
- `rebuild_index()` normalises legacy seeds into this layout and writes
  `seeds/index.json`.

See `docs/SEED_STORAGE_ROADMAP.md` and `docs/CODEX_SEED_WORKFLOW.md` for
full details.

### Groove-Aware Bass (Overview)

The groove-aware bass engine:

- Parses drum MIDI into a 16-step slot grid (per bar).
- Labels each step: `kick_here`, `near_kick_pre/post`, `snare_zone`,
  `bar_start`, `bar_end`, etc.
- Chooses a bass **mode** based on tags and drum energy:
  - Sub Anchor, Root/5th Driver, Pocket Groove, Rolling Ostinato,
    Offbeat Stabs, Lead-ish Bass.
- Builds 1–2 bar motifs using a constrained pitch pool (root, 5th,
  sub octave, occasional b7/9 for lead-ish modes).
- Applies small variations at phrase boundaries while keeping motifs
  recognisable.
- Respects swing: bass quantises to the hats’ swung grid but never swings
  more than the hats.

Design and rules: `docs/BASS_GROOVE_ROADMAP.md`.

### Explorer (Seed TUI)

- Uses Python’s `curses` to provide a terminal-first UI.
- In list mode:
  - Shows a table of seeds (id, mode, bpm, bars, tags).
  - Right pane shows seed dir/config/meta + summary.
- In detail mode:
  - Shows assets list, file paths, file stats.
  - Shows MIDI summaries and 16-step drum pattern previews.
  - Displays prompt/summary and Codex notes.
- `seed_dir:` is printed as an absolute path so terminals/editors can
  expose it as a clickable link to open the folder.

More in `docs/SHOWCASE.md` and `docs/TERMINAL_AI_ROADMAP.md`.

---

## How It Works (Algorithms & Tech)

### Drum Engine (m0–m4)

- Config-driven patterns defined in `configs/*.json`.
- M0–M1: metronome and basic 4/4 kicks with hats and backbeats.
- M2: parametric engine (Euclidean masks, swing, ratchets, choke groups).
- M3: conditions, density clamps, kick variation (ghosts, displacement).
- M4: scoring/feedback with Markov modulators and per-bar metrics
  (entropy, density, hat activity).
- Implementation entry points:
  - `src/techno_engine/run_config.py`
  - configs like `configs/m4_warehouse_sync.json`, `configs/m4_urgent.json`.

### Groove-Aware Bass Engine

- Drum analysis (in `drum_analysis`):
  - Reads drum MIDI, computes 16-step slots per bar, labels kick/snare/hat zones.
- Bass generation (in `groove_bass`):
  - Selects a mode based on tags and drum energy.
  - Generates motifs on the slot grid using a mode-specific pitch pool.
  - Enforces per-mode rules around density, register, and kick proximity.
  - Applies controlled variation across phrases and validates results.
- Writes MIDI via `midi_writer.write_midi`.

See `docs/BASS_GROOVE_ROADMAP.md` for the full design and rule set.

### Seed System & Explorer

- Seeds are managed via `src/techno_engine/seeds.py`:
  - `SeedMetadata` / `SeedAsset` dataclasses.
  - `save_seed`, `load_seed`, `rebuild_index`, `delete_seed_dir`, helpers.
- `run_config` and `paired_render_cli` call `save_seed` to snapshot
  configs and renders into `seeds/<seed_id>/`.
- `seed_cli` provides non-interactive management:
  - `list`, `show`, `render`, `clone`, `import-mid`, `bass-from-seed`, `delete`.
- `seed_explorer` is a curses UI for interactive browsing.

Architecture details: `docs/ARCHITECTURE.md`, `docs/SEED_STORAGE_ROADMAP.md`.

---

## CLI Cheatsheet

All commands assume you have `source .venv/bin/activate` and `PYTHONPATH=src`.

- Drums only:
  - `python -m techno_engine.run_config --config configs/m4_showcase.json`
- Drums + bass (paired render):
  - `python -m techno_engine.paired_render_cli --config configs/m4_warehouse_sync.json ...`
- Seed management:
  - List seeds: `python -m techno_engine.seed_cli list`
  - Show metadata: `python -m techno_engine.seed_cli show <seed_id> --json`
  - Render from seed: `python -m techno_engine.seed_cli render <seed_id> [--out path.mid]`
  - Clone seed with overrides: `python -m techno_engine.seed_cli clone <seed_id> --bars 16 ...`
  - Import an external MIDI: `python -m techno_engine.seed_cli import-mid path/to/file.mid`
  - Groove-aware bass from seed: `python -m techno_engine.seed_cli bass-from-seed <seed_id> [--bass-mode ...]`
  - Delete a seed: `python -m techno_engine.seed_cli delete <seed_id> --yes`
- TUI explorer:
  - `python -m techno_engine.seed_explorer`

See also:

- `docs/AGENT_API.md` for agent-facing tool contracts.
- `docs/AGENT_CHEATSHEETS/*` for parameter effects and planning templates.
- `docs/TECHNO-BASS.1`, `docs/TECHNO-SHOWCASE.1`, etc., for man pages.

---

## For Agents & Contributors

If you&apos;re extending the engine or wiring it into other tools:

- Read:
  - `docs/SEED_STORAGE_ROADMAP.md` – canonical seed layout & migration.
  - `docs/BASS_GROOVE_ROADMAP.md` – groove-aware bass design and rules.
  - `docs/CODEX_SEED_WORKFLOW.md` – end-to-end seed workflow and TUI usage.
  - `docs/DOCUMENTATION_ROADMAP.md` – overall docs strategy.
  - `docs/SEED_DELETE_ROADMAP.md` – seed delete semantics.
- In code:
  - Keep seed asset paths relative to the seed directory.
  - Use `save_seed` / `rebuild_index` instead of ad-hoc file management.
  - Respect bass mode rules when generating or modifying patterns.
- Tests:
  - Add or extend pytest tests under `tests/` whenever you add behaviour.
  - Use `pytest -q` as your basic verification gate.

---

## Roadmap & Status

- High-level roadmap artifacts:
  - `roadmap`, `ROADMAP_CHECKLIST.md` – original engine roadmap.
  - `docs/SEED_BEATS_PLAN.md` – seed-beat feature plans.
  - `docs/README_FRONT_PAGE_ROADMAP.md` – this README’s evolution plan.
- Recent highlights:
  - Canonical seed storage layout with migration.
  - Groove-aware bass engine and CLIs.
  - Seed explorer TUI with detail view and delete support.
  - Seed delete helper + CLI (`seed_cli delete`).
- To experiment further:
  - Explore configs in `configs/` and demos in `docs/SHOWCASE.md`.
  - Use the TUI + seeds to manage your own groove library.

