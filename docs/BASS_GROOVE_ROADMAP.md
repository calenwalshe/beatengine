# Bass Groove Roadmap (Agent Guide)

This document captures the design, theory, and implementation plan for the
**groove‑aware, drum‑reactive bassline generator** in the `beatengine` repo.
Future agents should consult this file before touching bass/groove code.

---

## 1. Scope & Goals

- Add a **mode‑driven bass engine** that reacts to the existing m4 drum engine.
- Support two workflows:
  - **Paired render**: render m4 drums and a groove‑aware bassline in one pass,
    saving both as assets in a single seed.
  - **Bass‑from‑seed**: given an existing seed with drums, generate one or more
    bass assets that fit the groove.
- Keep everything integrated with:
  - `techno_engine.seeds` (SeedMetadata / SeedAsset / index).
  - `techno_engine.seed_explorer` (TUI explorer).
  - Existing CLIs (`run_config`, `seed_cli`, `bass_cli`).

Implementation must be **algorithmically clear, testable**, and respect the
musical rules described below.

---

## 2. Existing Architecture (Short Recap)

- **Drums (m4 engine)**
  - `techno_engine.run_config` reads JSON configs (e.g. `configs/m4_warehouse_sync.json`).
  - For mode `m4` it calls `run_session(...)` to build kick / hat / snare / clap
    events and writes a single MIDI via `midi_writer.write_midi`.

- **Seeds**
  - `techno_engine.seeds`:
    - `SeedAsset`: `role`, `kind`, `path`, `description`, `drum_pattern_preview`.
    - `SeedMetadata`: tempo info, tags, summary, prompt, `assets`, `parent_seed_id`.
    - Helpers: `save_seed`, `load_seed`, `rebuild_index`, `update_index`.
  - Each seed lives under `seeds/<seed_id>/` with:
    - `config.json` (render config snapshot).
    - `metadata.json`.
    - Assets (MIDI, etc.).
  - `rebuild_index()` also:
    - Copies main drum render into the seed folder if needed.
    - Backfills `drum_pattern_preview` for MIDI assets where missing.

- **Explorer (TUI)**
  - `techno_engine.seed_explorer`:
    - Lists seeds and shows details.
    - In detail mode:
      - Shows seed folder / config / metadata paths.
      - Lists assets with role/kind/path.
      - Shows MIDI summaries and a 16‑step drum pattern
        (kick / snare / hat) for drum assets.

- **Bass (current)**
  - `techno_engine.bass_cli` + `bassline.generate_mvp`:
    - Config: `bpm`, `ppq`, `bars`, `seed`, `root_note`, `out`.
    - Generates a basic bassline MIDI.
    - **Does not look at drum MIDI**; only tempo/length aligned.

---

## 3. Groove‑Aware Bass Design

### 3.1 Drum Anchors & Slot Grid

The bass engine must treat the drum pattern as a **slot map** at 16th‑note
resolution:

- Extract from drum MIDI:
  - Kick positions (note 36) as ticks + 16th indices.
  - Backbeat positions (snare/clap: 37/38/39/40).
  - Hat activity (42/44/46) for local density.
  - Bar boundaries.
- Label each 16th step with tags such as:
  - `kick_here`
  - `near_kick_pre` (16th before a kick)
  - `near_kick_post` (16th after a kick)
  - `snare_zone` (around 2 and 4)
  - `bar_start`, `bar_end`
  - Optional: `fill_zone`, `hat_dense`, `hat_sparse`

All bass placement decisions reference this grid.

### 3.2 Pitch / Harmony

- Each bass render chooses a `root_note` (from config or caller).
- **Foundational modes** (supporting roles) must use a tight pitch pool:
  - Root, fifth (+7), sub octave (‑12), occasional upper octave (+12).
- **Lead‑ish modes** can extend:
  - Add b7 (+10) and 9 (+14), plus passing tones adjacent to these.
- Foundational modes must stay in sub / low‑mid register; lead‑ish modes
may climb into mid but rarely above.

### 3.3 Modes (Rhythmic Personalities)

Each mode is a strict personality: density, register, kick overlap, and slot
preferences are hard constraints.

- **Sub Anchor**
  - 1–4 notes/bar.
  - Deep sub near root.
  - Avoid overlapping kicks except beat 1; quarter‑note doubling allowed in
    high‑energy tags.
  - Long sustains, minimal syncopation.

- **Root/5th Driver**
  - 2–6 notes/bar.
  - Root + fifth; sub + low‑mid.
  - Avoid collisions except strong beats; fifth often on offbeats.

- **Pocket Groove**
  - 4–10 notes/bar.
  - Low‑mid, occasional sub dips.
  - Prioritize kick gaps; heavy use of pre‑kick / post‑kick slots.
  - Syncopated 8ths/16ths; micro‑motifs.

- **Rolling Ostinato**
  - 4–8 notes/bar, structured.
  - Low‑mid, root/octave.
  - Repeating 1–2 bar cells, hypnotic.
  - In `minimal`/`dubby`: avoid overlaps with kicks.
  - In `warehouse`/`urgent`: allow some overlaps on strong kicks.

- **Offbeat Stabs**
  - 1–3 notes/bar.
  - Low‑mid/mid stabs with long decay.
  - Strict kick avoid; stabs on clean offbeats.

- **Lead‑ish Bass**
  - 6–12 notes/bar.
  - Low‑mid→mid, occasional sub on beat 1.
  - Selective overlaps with structural kicks allowed.
  - Uses passing tones + small fills.

### 3.4 Tags → Mode & Density

- Tags guide default mode and aggressiveness:
  - `minimal`, `dubby`:
    - Prefer **Sub Anchor**, **Offbeat Stabs**.
    - Restrict Pocket / Lead‑ish by default.
  - `warehouse`, `urgent`, `industrial`:
    - Prefer **Root/5th**, **Pocket Groove**, **Rolling Ostinato**.
    - Allow more kick overlap and higher density.
  - `rolling`, `groove`, `hypnotic`:
    - Prefer **Rolling Ostinato**, **Pocket Groove**.

- Drum **energy** (kick + hat density) further scales density:
  - High energy: either simpler foundational bass or more aggressive Pocket,
    depending on tags.
  - Low energy: more space (Sub / Offbeat), or a single rolling ostinato.

### 3.5 Swing & Micro‑Timing

- Bass may quantize to the same swung grid implied by hats.
- **Never swing more than the hats**; bass should follow, not exaggerate swing.
- Keep implementation conceptually on a 16‑step grid, then apply swing offsets.

### 3.6 Motifs & Variation

- Construct 1–2 bar **motifs** on the slot grid:
  - These motifs must repeat recognizably over phrases.
  - Variation occurs every 2/4/8 bars depending on drum periodicity or bars count.
- Variation operations (mode‑safe only):
  - Add/remove one note.
  - Shift a note to pre‑kick or post‑kick slot.
  - Swap root↔fifth or add an octave jump.
- **Ensure 1–2 bar motifs repeat recognizably**; variation must not completely
overwrite the motif shape.

### 3.7 Validation Philosophy

Every generated bassline must pass:

- Per‑bar density bounds for the mode.
- Register bounds appropriate to the mode.
- Kick proximity constraints (per‑mode avoid/allow windows).
- Bar‑end cleanup: ensure bass does not fight drum fills.
- Motif coherence: motif remains audible after variations.
- No runaway syncopation in modes that are meant to be foundational.

If validation fails, the engine should adjust or regenerate the pattern.

---

## 4. Implementation Roadmap (5 Steps)

Each step below should **follow and reference** the design sections above.

### Step 1 – Drum Anchor Extraction Utility

- Add `src/techno_engine/drum_analysis.py` with:
  - `extract_drum_anchors(midi_path: Path, ppq: int)` implementing §3.1.
  - Per‑bar 16‑step summaries and labeled slot grid.
- Tests (`tests/test_drum_analysis.py`):
  - Synthetic MIDIs with known kicks/snares/hats; assert anchor positions and
    slot labels match expectations.

### Step 2 – Groove‑Aware Bass Engine Core

- Add `src/techno_engine/groove_bass.py` implementing:
  - Pitch rules in §3.2.
  - Modes and constraints from §3.3.
  - Tag/energy selection from §3.4.
  - Swing handling from §3.5.
  - Motif/variation logic from §3.6.
  - Validation from §3.7.
- Tests (`tests/test_groove_bass_modes.py`):
  - For each mode, feed artificial anchors and check:
    - Density, register, and kick‑overlap constraints.
    - Slot usage (e.g. Offbeat Stabs only on offbeats).
    - Motif repetition with constrained variation.

### Step 3 – Paired Drums + Bass Render CLI

- Add `src/techno_engine/paired_render_cli.py` (or a `--paired-bass` mode):
  - Use existing m4 render path (`run_config`) to write drums.
  - Call `extract_drum_anchors` (§3.1) and `groove_bass` (§3.2–3.7).
  - Write bass MIDI alongside drums.
  - Call `save_seed` once, registering:
    - `main/midi` for drums (with drum_pattern_preview).
    - `bass/midi` for the generated bass.
- Tests (`tests/test_paired_render_cli.py`):
  - In tmp dir, run paired render; assert one seed with both drum + bass assets.

### Step 4 – Bass‑from‑Seed CLI Integration

- Extend `seed_cli` or add a new CLI (e.g. `bass_from_seed`) that:
  - Accepts `--seed-id`, mode override, root_note override.
  - Resolves seed, drum MIDI, and tags (see §§2–3.4).
  - Calls `extract_drum_anchors` + `groove_bass`.
  - Writes a new bass MIDI asset inside the seed folder and updates
    `metadata.json` / index.
- Tests (`tests/test_bass_from_seed.py`):
  - Create a seed via `run_config --save-seed`, run bass‑from‑seed, and assert
    a new bass asset appears in metadata/index.

### Step 5 – Docs & Full Test Sweep

- Update `docs/CODEX_SEED_WORKFLOW.md` to:
  - Describe paired render and bass‑from‑seed workflows.
  - Summarize bass modes and tag influences (§3.3–3.4).
  - Mention swing and motif concepts (§3.5–3.6).
- Run `pytest -q` and keep `seeds/` untracked in git.

---

## 5. Agent Guidance

- Always read this roadmap before changing `drum_analysis`, `groove_bass`,
  `bass_cli`, `run_config`, `seed_cli`, or `seed_explorer`.
- Do not alter the core drum engine semantics; bass logic must adapt to drums,
  not vice versa.
- Keep tests mode‑driven and deterministic (use fixed seeds).
- When in doubt, prioritise:
  1. Kick‑aware timing and density constraints.
  2. Clear, repeating motifs with subtle variation.
  3. Tight pitch pools for foundational modes, expanded pools only for
     lead‑ish bass.
