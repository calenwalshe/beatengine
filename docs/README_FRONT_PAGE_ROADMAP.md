# README Front Page Roadmap (Agent Guide)

Goal: refresh the GitHub front page so humans and agents can quickly
understand **what Beatengine is, what it can do now, and how it works
under the hood**.

This roadmap is for implementing and iterating on `README.md`. Future
agents should update this file when touching the front page.

---

## Checklist Overview

- [x] Step 1 – Audit current README and capture gaps
- [ ] Step 2 – Draft new README structure (sections + ordering)
- [ ] Step 3 – Fill in content (features, quickstart, concepts, tech deep dive)
- [ ] Step 4 – Polish, cross‑link docs, and add visuals
- [ ] Step 5 – Run tests, sanity‑check commands, and land changes

---

## Step 1 – Audit Current README

**Intent:** understand the current front page and identify what’s missing
relative to the current engine (seeds, groove‑aware bass, TUI, Codex docs).

Tasks:

- [ ] Read `README.md` top to bottom.
- [ ] List which sections are still accurate (e.g. M0–M4 description,
      environment bootstrap, examples).
- [ ] Identify outdated or misleading parts, for example:
  - [ ] Heavy emphasis on `out/` as canonical storage.
  - [ ] Missing mention of `seeds/` layout and seed explorer.
  - [ ] Missing mention of groove‑aware bass engine and bass CLIs.
  - [ ] No reference to new Codex/agent docs in `docs/`.
- [ ] Summarise audit findings in this file under “Audit Notes”.

**Audit Notes (to be filled by agent):**

- Current README title/tagline:
  - "Techno Rhythm Engine — Berlin-Style Roadmap Build"
- Sections to keep (with light edits):
  - Quickstart venv/bootstrap (update commands to prefer `PYTHONPATH=src .venv/bin/python`).
  - Repository layout (needs update to mention `seeds/` and new docs, and to de-emphasise `out/` as canonical).
  - Features Implemented (M0–M4) as historical context for the drum engine.
  - LLM Prompt Demo Library (still relevant for agent usage).
- Sections to update/remove:
  - Tests/coverage badges refer to outdated numbers; either update or replace with a simpler status note.
  - Quickstart currently only renders to `out/` and doesn&apos;t mention `--save-seed` or paired drums+bass workflows.
  - Repository layout lists `out/` as a primary output location; canonical seed storage now lives under `seeds/`.
  - Running examples focus on legacy `out/*` demo packs, not seed-aware workflows.
- New sections needed:
  - Features overview (drums, seeds, TUI, groove-aware bass, CLIs).
  - 5‑minute Quickstart (with `--save-seed` or `paired_render_cli` and `seed_explorer`).
  - How It Works (Drum engine, groove-aware bass engine, seed system & TUI).
  - CLI cheatsheet + links into `docs/SEED_STORAGE_ROADMAP.md`, `docs/BASS_GROOVE_ROADMAP.md`, `docs/CODEX_SEED_WORKFLOW.md`, and `docs/DOCUMENTATION_ROADMAP.md`.

Once this section is filled and checkboxes above are marked, Step 1 is
considered complete.

---

## Step 2 – Draft New README Structure

**Intent:** design the new front page layout before filling content.

Target structure (can be refined):

1. Title + tagline
2. Hero paragraph (what it is, who it’s for)
3. Feature overview (bullets)
4. Quickstart (5‑minute demo: venv → paired render → TUI)
5. Core concepts (Seeds, Groove‑aware Bass, Explorer)
6. How It Works (Algorithms & Tech)
7. CLI cheatsheet
8. For agents / contributors
9. Roadmap & status

Tasks:

- [ ] Add a “Proposed Structure” section to this file with the headings you
      intend to use in `README.md`.
- [ ] Ensure each heading is short and scannable.
- [ ] Confirm there is a natural place to link into existing docs
      (SEED_STORAGE_ROADMAP, BASS_GROOVE_ROADMAP, DOCUMENTATION_ROADMAP,
      CODEX_SEED_WORKFLOW, etc.).

---

## Step 3 – Fill In Content

**Intent:** write the actual `README.md` content following the structure.

Content requirements:

- Features section:
  - [ ] Mention m4 drum engine, seeds, TUI, groove‑aware bass, CLIs.
- Quickstart:
  - [ ] venv bootstrap + `pip install -r requirements.txt`.
  - [ ] `pytest -q` as an optional sanity check.
  - [ ] One command that renders a seed with drums + bass.
  - [ ] One command that opens the TUI explorer.
- Core concepts:
  - [ ] Short explanation of seeds and canonical layout
        (`seeds/<seed_id>/drums/main.mid`, `bass/`, `metadata.json`).
  - [ ] Summary of groove‑aware bass (drum anchors, 16‑step grid, modes).
  - [ ] Short description of the explorer (list + detail, drum pattern preview,
        clickable `seed_dir`).
- Technical deep dive:
  - [ ] 3 sub‑sections: Drum Engine (m4), Groove‑Aware Bass Engine,
        Seed System & Explorer.
  - [ ] Each 3–6 lines max, linking to the detailed docs.

---

## Step 4 – Polish, Cross‑Link, Visuals

**Intent:** make the README pleasant to skim and connect it to the rest of
the documentation set.

Tasks:

- [ ] Add at least one ASCII seed folder layout to illustrate a project.
- [ ] Add links to:
  - `docs/SEED_STORAGE_ROADMAP.md`
  - `docs/BASS_GROOVE_ROADMAP.md`
  - `docs/CODEX_SEED_WORKFLOW.md`
  - `docs/DOCUMENTATION_ROADMAP.md`
- [ ] Optionally add a screenshot or GIF of `seed_explorer`.
- [ ] Check that all referenced commands use `PYTHONPATH=src .venv/bin/python`
      where appropriate.

---

## Step 5 – Tests & Landing

**Intent:** ensure examples are plausible and changes don&apos;t regress anything.

Tasks:

- [ ] Run `source .venv/bin/activate && pytest -q`.
- [ ] Manually sanity‑check each README command (at least once per major section)
      or clearly mark any commands as “illustrative only”.
- [ ] Commit changes on the feature branch with a clear message
      (e.g. `Improve README with seeds/bass/TUI overview`).
- [ ] Open a PR or merge into `master` following your normal workflow.

