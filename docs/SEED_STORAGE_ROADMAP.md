# Seed Storage Cleanup Roadmap (Agent Guide)

Goal: standardise how each `seed_id` maps to on-disk files and metadata so that
**every seed is a self-contained project** with a predictable folder layout.
Future agents should follow this roadmap and keep this structure enforced.

---

## 1. Canonical Seed Layout

Every seed must use this layout (paths are relative to repo root):

```text
seeds/<seed_id>/
  config.json          # canonical drum config snapshot
  metadata.json        # SeedMetadata JSON
  drums/
    main.mid           # main rhythm pattern for this seed
    variants/          # optional drum variants, fills, alt patterns
      <name>.mid
  bass/
    main.mid           # primary bassline (if present)
    variants/
      <name>.mid       # additional basslines
  leads/               # (optional) melodic leads
    main.mid
    variants/
      <name>.mid
  analysis/            # (optional) logs/metrics/etc.
    *.csv
    *.json
```

Metadata rules:

- `SeedMetadata.render_path` MUST be `"drums/main.mid"` (relative path).
- `SeedAsset.path` MUST be **relative to the seed directory**, e.g.:
  - Drums: `drums/main.mid`, `drums/variants/ghost_shuffle.mid`.
  - Bass: `bass/main.mid`, `bass/variants/bass_pocket_groove.mid`.
  - Leads/analysis follow the same pattern.
- `SeedAsset.role` and `kind` reflect usage:
  - `role`: `main`, `drums_variant`, `bass`, `bass_variant`, `lead`, etc.
  - `kind`: `midi`, `audio`, `config`, `log`, etc.

`out/` (or other top-level folders) may still be used as *temporary render
locations*, but the canonical, long-lived assets must live under the seed
folder and be referenced relatively from `metadata.json`.

---

## 2. Update Generators to Write Canonical Layout

**Step 2.1 – `save_seed` (drums)**

- After copying `config.json`, ensure:
  - Drum render is stored at `drums/main.mid` under the seed directory.
  - `render_path` is set to `"drums/main.mid"`.
  - A `SeedAsset` with `role="main"`, `kind="midi"`, `path="drums/main.mid"`
    exists (description can remain as today).
- Avoid storing canonical paths pointing into `out/...`.

**Step 2.2 – Paired render (`paired_render_cli`)**

- After rendering drums to `cfg.out` (temporary), copy/move into
  `seeds/<seed_id>/drums/main.mid`.
- Write bass to `seeds/<seed_id>/bass/main.mid` for the paired bassline.
- Register assets as:
  - `main/midi` → `drums/main.mid`.
  - `bass/midi` → `bass/main.mid`.

**Step 2.3 – Bass-from-seed (`seed_cli bass-from-seed`)**

- When generating new basslines from an existing seed:
  - Write to `bass/variants/<name>.mid` inside the seed directory.
  - Asset path stored as `bass/variants/<name>.mid` (relative), with
    `role="bass"` or `"bass_variant"`, `kind="midi"`.

**Step 2.4 – Future generators (leads, imports, etc.)**

- Always write permanent assets under the seed folder into the appropriate
  subdirectory and register them with relative paths.
- Use a shared helper (to be introduced) to compute target paths, e.g.:
  `ensure_seed_asset_path(seed_dir, role="bass", variant_name=...)`.

**Tests for Step 2**

- Update/add tests to assert:
  - Newly created seeds have `drums/main.mid` and
    `render_path == "drums/main.mid"`.
  - Paired render creates `bass/main.mid` and metadata points to it.
  - Bass-from-seed creates files under `bass/variants/...` and registers
    relative paths.

---

## 3. Migration of Existing Seeds

Implement a migration pass that normalizes legacy seeds into the canonical
layout. This can be done by extending `rebuild_index()` or via a dedicated
migration helper.

**Step 3.1 – Drums**

For each `seeds/<seed_id>/`:

- If `drums/main.mid` does not exist but `metadata.render_path` points to an
  existing MIDI file:
  - Copy that MIDI to `drums/main.mid`.
  - Update `render_path` to `"drums/main.mid"`.
  - Ensure there is a primary `main/midi` asset pointing to `drums/main.mid`.

**Step 3.2 – Assets outside the seed folder**

- For each `SeedAsset` whose `path` is absolute or references `out/...` (or
  another external location):
  - Determine where it should live:
    - Drums (`role` in {`main`, `drums_variant`}): move/copy into
      `drums/main.mid` or `drums/variants/<name>.mid`.
    - Bass (`role` contains `bass`): move/copy into
      `bass/main.mid` or `bass/variants/<name>.mid`.
    - Leads/others: move/copy into `leads/...` or `analysis/...` as
      appropriate.
  - Update `asset.path` to the new **relative** path.

- Mark `needs_write` when any changes are applied, then rewrite
  `metadata.json`.

**Step 3.3 – Idempotency**

- Migration must be safe to run multiple times:
  - If assets are already in canonical locations with relative paths, the
    migration should detect that and skip changes.

**Tests for Step 3**

- Build “legacy” seed folders under `tmp_path` with:
  - `render_path` set to `out/...`.
  - Assets pointing to `out/...` or absolute paths.
- Run migration.
- Assert:
  - Files have been copied into the canonical `drums/` and `bass/` folders.
  - `render_path` and asset `path` fields are now relative and match the
    expected layout.

---

## 4. Enforce Structure for Future Writes

Once generators and migration are in place, add guardrails so future code can’t
silently regress.

- In `save_seed`:
  - After any save, normalize `render_path` and the primary `main` asset to
    `drums/main.mid` (moving/copying if necessary).
- Introduce a helper, e.g. `normalise_seed_assets(seed_dir, meta)` that:
  - Ensures all asset paths are relative and under the canonical folders.
  - Can be reused by CLIs before writing metadata.
- In `seed_explorer` and other consumers:
  - Resolve asset paths relative to the seed dir first.
  - Optionally warning-log if paths are outside the seed dir (for debugging).

**Tests for Step 4**

- Add a test that creates a seed via the public CLIs and asserts:
  - No asset has a `path` beginning with `"out/"` or an absolute path.
  - `render_path` is `"drums/main.mid"`.

---

## 5. Documentation & Agent Instructions

- Update `docs/CODEX_SEED_WORKFLOW.md` to:
  - Show the canonical seed layout.
  - Document how new drums/bass/leads are stored under `drums/`, `bass/`,
    `leads/`.
  - Mention that `render_path` is always `drums/main.mid`.

- Ensure `docs/BASS_GROOVE_ROADMAP.md` references this layout in its storage
  conventions section.

- Agent guidance (for future changes):
  - All new generators or CLIs that create assets must:
    - Store files under `seeds/<seed_id>/...`.
    - Record `SeedAsset.path` relative to the seed directory.
    - Respect the subfolder conventions.
  - When in doubt, run the migration helper in a scratch copy of the repo and
    inspect the resulting structure.
