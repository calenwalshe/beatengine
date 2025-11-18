# Lead-Line Generator Roadmap (Pattern Library + Rules)

Goal: implement a **rhythm-aware, style-aware, deterministic** lead-line
generator for Beatengine, using the hybrid **Pattern Library +
Transformation + Light Rules** design.

This file turns the high-level spec into an ordered roadmap with checklists
and test ideas for each phase. Future agents should update checkboxes and
notes as work progresses.

---

## 0. Scope & Assumptions

- No ML models; all behaviour is rule-/template-based.
- Only standard library + `mido` + `pytest` (no new deps).
- Reuse existing pieces:
  - Drum slot grid + `drum_analysis` concepts (16 steps per bar, slot labels).
  - Seed system (`SeedMetadata`, `SeedAsset`, `save_seed`, `rebuild_index`).
  - Groove-aware bass concepts (modes, motifs, variation, validation).
- Lead generator will be callable from both:
  - A Python API (`generate_lead(...)`).
  - CLI workflow (`seed_cli lead-from-seed`, optional `paired_render_cli` flag).

---

## 1. Module Skeleton & Config Files

**Goal:** create the basic module structure and JSON config placeholders.

Planned structure:

```text
src/techno_engine/leads/
  __init__.py
  lead_engine.py        # public API + pipeline orchestration
  lead_modes.py         # LeadMode dataclass + mode loading/selection
  lead_templates.py     # rhythm + contour template loading
  lead_phrase.py        # phrase layout (CALL/CALL_VAR/RESP/RESP_VAR)
  lead_validation.py    # density/register/collision/motif checks

configs/
  lead_modes.json
  lead_rhythm_templates.json
  lead_contour_templates.json
```

Tasks:

- [ ] Add `src/techno_engine/leads/__init__.py`.
- [ ] Add module files with stubbed functions/classes and docstrings.
- [ ] Add minimal JSON files with at least one mode and one rhythm/contour
      template (e.g. `"Minimal Stab Lead"`).
- [ ] Wire basic config loading helpers (e.g. `load_lead_modes()`).

Tests:

- [ ] `test_lead_config_loading` — ensure JSON files parse and map into
      dataclasses without errors.

---

## 2. Core Data Types & LeadContext

**Goal:** define the core dataclasses that represent modes, templates, and
context.

From the spec, we need:

- `LeadMode` (in `lead_modes.py`):
  - `name`
  - `target_notes_per_bar: tuple[int, int]`
  - `max_consecutive_notes: int`
  - `register_low`, `register_high`: MIDI note bounds
  - `rhythmic_personality: str`
  - `preferred_slot_weights: dict[str, float]`
  - `phrase_length_bars: int`
  - `contour_profiles: list[str]`
  - `call_response_style: str`  (e.g. mild, medium, strong)

- `RhythmTemplate` (in `lead_templates.py`):
  - `id: str`
  - `mode_name: str`
  - `motif_role: str` (`"CALL"`, `"CALL_VAR"`, `"RESP"`, `"RESP_VAR"`)
  - `events: list[RhythmEvent]`, each with:
    - `step: int` (0–15)
    - `length: int` (in 16th steps)
    - `anchor_type: str` (offbeat, snare_zone, etc.)
    - `accent: bool`

- `ContourTemplate` (in `lead_templates.py`):
  - `id: str`
  - `mode_name: str`
  - `motif_role: str`
  - `intervals: list[int]` (relative scale degrees)
  - `emphasis_indices: list[int]`
  - `shape: str` (e.g. arch, stepwise, zigzag)

- `LeadContext` (in `lead_engine.py`):
  - Drum slots (16-step grid per bar with labels from analysis).
  - Optional bass notes + a simple occupancy map.
  - Seed metadata: bpm, bars, ppq, tags, root note/scale mode.
  - Derived features per slot: beat index, bar index, offbeat flags,
    hat density, fill zones, etc.
  - RNG (seeded `random.Random`).

Tasks:

- [ ] Define dataclasses / typed structures for `LeadMode`, `RhythmTemplate`,
      `ContourTemplate`, `LeadContext`.
- [ ] Implement JSON → dataclass mapping utilities.
- [ ] Implement a basic `build_lead_context(...)` that wraps drum slots,
      bass notes, seed metadata, and RNG.

Tests:

- [ ] `test_lead_mode_parsing` — config → `LeadMode` fields.
- [ ] `test_lead_context_builds_from_metadata` — ensure bars/bpm/ppq/tags make
      it into `LeadContext` correctly.

---

## 3. Mode Selection & Phrase Layout

**Goal:** convert seed tags + context into a `LeadMode` and a phrase layout
(CALL/CALL_VAR/RESP/RESP_VAR) over 2–4 bars.

Mode selection (from spec):

- Tag → mode priority (example default):
  - `lyrical` → `Lyrical Call/Response Lead`.
  - `hypnotic` → `Hypnotic Arp Lead`.
  - `rolling` → `Rolling Arp Lead`.
  - `minimal` → `Minimal Stab Lead`.
  - Else → `Minimal Stab Lead` (fallback).
- Tag modifiers (warehouse, urgent, call, response) tweak density or
  phrase_length.

Phrase layout:

- If `phrase_length_bars == 2` → `[CALL, CALL_VAR]`.
- If `phrase_length_bars == 4` → `[CALL, CALL_VAR, RESP, RESP_VAR]`.

Tasks:

- [ ] Implement `select_lead_mode(tags, available_modes)` in `lead_modes.py`.
- [ ] Implement `build_phrase_roles(lead_mode, total_bars)` in `lead_phrase.py`.

Tests:

- [ ] `test_mode_selection_from_tags` — given tags, pick the right mode.
- [ ] `test_phrase_roles_for_2_and_4_bars` — verify [CALL,...] layouts.

---

## 4. Rhythmic Skeleton & Slot Alignment

**Goal:** pick rhythm templates and align them to the drum slot grid to
create a rhythmic skeleton for the lead.

From the spec:

- Each bar/role chooses a `RhythmTemplate` matching `mode_name` and
  `motif_role`.
- For each `RhythmEvent` (step/length/anchor_type/accent):
  - Evaluate nearby slots (e.g. ±2 steps) using a score like:

  ```text
  score = sum(preferred_slot_weights for active slot labels)
          + hat_density_term
          - fill_zone_penalty
          - bass_collision_penalty
  ```

- Choose the highest-scoring slot position for each event; resolve collisions
  (e.g. no duplicate onset in same step unless desired).

Tasks:

- [ ] Implement rhythm template selection utilities in `lead_templates.py`.
- [ ] Implement scoring and alignment logic in `lead_engine.py` or
      `lead_phrase.py`.
- [ ] Build an intermediate representation: list of `(bar_index, step,
      length, accent)` for the lead skeleton.

Tests:

- [ ] `test_alignment_prefers_accented_slots` — given a toy slot grid
      (kick/snare/hat), ensure accent events gravitate toward good slots.
- [ ] `test_lead_density_respected` — skeleton stays within
      `target_notes_per_bar` per mode.

---

## 5. Pitch, Contour & Bass Avoidance

**Goal:** turn the rhythmic skeleton into pitched notes using contour
templates, scale logic, and bass avoidance.

From the spec:

- Scales: minor / Dorian / Phrygian; map degrees→semitones.
- Contour templates per mode/role:
  - `intervals` (relative scale degrees), `emphasis_indices`, `shape`.
- CALL vs RESP:
  - CALL starts on root/5th.
  - RESP may be transposed or inverted relative to CALL.
- Final bar should resolve to root/5th/octave.
- Bass avoidance:
  - If collision with bass + kick:
    1. Try transpose.
    2. Try shorten.
    3. Drop note if density is high.

Tasks:

- [ ] Implement scale helpers (degree mapping, register folding) in
      `lead_engine.py` or a small utility.
- [ ] Implement contour application: map `intervals` onto rhythm skeleton to
      produce pitch sequences.
- [ ] Implement CALL/RESP transformations (transpose/invert, etc.).
- [ ] Implement bass avoidance adjustments.

Tests:

- [ ] `test_register_respected` — all notes within mode register bounds.
- [ ] `test_phrase_resolution` — final bar tends to resolve to root/5th/octave.
- [ ] `test_bass_avoidance` — when bass occupies a slot, lead avoids direct
      conflicts according to the rules.

---

## 6. Variation Engine

**Goal:** generate CALL_VAR and RESP_VAR variants that keep motifs
recognisable while adding interest.

Variation moves (from spec):

- Drop an interior note.
- Shift a note ±1 slot.
- Lengthen final note.
- Degree ±1 (small pitch change).
- Inversion (for RESP variants).
- Transpose motifs.

Variation probability is driven by `call_response_style`.

Tasks:

- [ ] Implement a small variation engine in `lead_phrase.py` that takes a
      motif and returns a variant, constrained by mode rules.
- [ ] Ensure variations are applied after initial motif generation but before
      final validation.

Tests:

- [ ] `test_motif_similarity_for_variants` — CALL vs CALL_VAR similarity ≥ 50%.
- [ ] `test_resp_is_not_identical_to_call` — RESP motifs differ enough unless
      mode is explicitly hypnotic.

---

## 7. Validation & Repair

**Goal:** add a validation pass that enforces key invariants and repairs or
rejects bad patterns.

Checks (from spec):

1. Density per bar within `target_notes_per_bar` bounds.
2. Register compliance (within `register_low`/`register_high`).
3. Drum/bass collision safety (no excessive stacking on kicks/snare, unless
   mode allows it).
4. Motif coherence:
   - CALL vs CALL_VAR ≥ ~50% similar.
   - CALL vs RESP ≤ ~80% similar unless mode is `hypnotic`.

If a pattern fails, either:

- Apply another variation.
- Regenerate motif (bounded number of attempts).

Tasks:

- [ ] Implement validation functions in `lead_validation.py`.
- [ ] Integrate validation into the main `generate_lead` pipeline.

Tests:

- [ ] `test_lead_validation_passes_for_simple_case` — synthetic drum grid,
      simple mode, pattern passes all checks.
- [ ] `test_lead_validation_rejects_over_dense_pattern`.

---

## 8. Public API, Seeds & CLI Integration

**Goal:** expose a clean public API and wire it into seeds and CLIs.

### 8.1 Public API

Implement in `lead_engine.py`:

```python
from typing import List, Optional

class NoteEvent:  # or reuse existing note structure
    pitch: int
    velocity: int
    start_tick: int
    duration: int


def generate_lead(
    drum_slots,
    seed_metadata,
    bass_notes=None,
    rng=None,
    lead_mode_override: Optional[str] = None,
) -> List[NoteEvent]:
    """Produce deterministic lead-line MIDI note events."""
```

### 8.2 Seed integration

- [ ] Decide canonical paths:
  - `seeds/<seed_id>/leads/main.mid` or `leads/variants/*.mid`.
- [ ] When a lead is generated, write the MIDI file into the seed directory
      and register a `SeedAsset` with role `lead` / `lead_variant` and kind
      `midi`.
- [ ] Ensure paths are stored relative to the seed directory as per
      `SEED_STORAGE_ROADMAP`.

### 8.3 CLI integration

- [ ] Add `lead-from-seed` subcommand to `seed_cli`:

  ```bash
  python -m techno_engine.seed_cli lead-from-seed <seed_id> \
    [--mode NAME] [--out PATH] [--tags ...] [--description ...]
  ```

- [ ] Optionally extend `paired_render_cli` with `--with-lead` to create
      drums + bass + lead in one pass and store assets under the seed.

Tests:

- [ ] `test_lead_from_seed_cli_creates_asset` — end-to-end check that a lead
      MIDI file and metadata entry appear for a seed.
- [ ] `test_paired_render_with_lead` (optional) — smoke test for
      drums+bass+lead workflow.

---

## 9. Explorer (TUI) Enhancements (Optional/P1)

**Goal:** surface leads in the seed explorer for inspection.

Tasks:

- [ ] In `seed_explorer`, highlight assets with role `lead` / `lead_variant`.
- [ ] Optionally add a short “lead pattern summary” similar to drum pattern
      previews (e.g. pitch distribution, register, density per bar).

Tests:

- [ ] TUI demo: run `seed_explorer --demo` and verify leads are shown.

---

## 10. Logging & Debugging

**Goal:** add lightweight logging hooks for troubleshooting.

Possible debug info:

- Selected `LeadMode` and phrase layout.
- Rhythm/contour template IDs.
- Slot alignment scores for key events.
- Variation operations applied.
- Validation failures and repair attempts.

Logging should be optional (e.g. debug flag or environment variable) and must
not spam normal usage.

---

## 11. Final Verification

- [ ] Run `PYTHONPATH=src pytest -q` on the feature branch.
- [ ] Run CLI smoke tests:
  - `seed_cli lead-from-seed` on a known seed.
  - (Optional) `paired_render_cli --with-lead`.
- [ ] Document final status (date, branch, commit) at the bottom of this file
      once the feature is stable.


---

## Current Status

- Roadmap/spec drafted on branch `feature/lead-generator`.
- Remaining work: implement the lead modules, tests, and CLI/seed/TUI wiring as described in sections 1–11 above.
