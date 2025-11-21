# Lead Modes Expansion & Tuning Roadmap

Goal: extend the existing Beatengine lead-line generator into a
**multi-mode, tuneable system** (Minimal Stab, Rolling Arp, Hypnotic,
Lyrical Call/Response, etc.) with:

- Config-driven behaviour (`configs/lead_*.json`).
- Deterministic, rhythm-aware generation using the drum slot grid.
- Unit tests at each step.
- A clear testing and logging plan so we can iterate based on actual
  listening and developer notes.

This document is an implementation path; it does **not** change code by
itself. Future agents should follow and update it as work progresses.

---

## 0. Current State & Assumptions

As of branch `feature/lead-generator`:

- Lead engine exists:
  - `src/techno_engine/leads/lead_engine.py` with `generate_lead(...)` and
    `build_lead_context(...)`.
  - Uses `DrumAnchors` (16-step drum slot grid) and `SeedMetadata`.
- Configs:
  - `configs/lead_modes.json` defines **Minimal Stab Lead** only.
  - `configs/lead_rhythm_templates.json` has a CALL template for Minimal Stab.
  - `configs/lead_contour_templates.json` has a CALL contour template.
- CLI integration:
  - `seed_cli lead-from-seed` generates a lead and writes
    `leads/variants/lead_<mode>.mid` with a `lead` asset in metadata.
- Tests currently passing:
  - `tests/test_lead_config_loading.py`
  - `tests/test_lead_modes_and_phrase.py`
  - `tests/test_lead_validation_basic.py`
  - `tests/test_generate_lead_basic.py`
  - `tests/test_lead_from_seed_cli.py`

We will **not** break existing behaviour. Minimal Stab Lead remains the
fallback mode and its tests must keep passing.

---

## 1. Define New Modes (Config Only)

**Goal:** add new, named lead personalities to `lead_modes.json` without
changing code yet.

Target modes:

- `Rolling Arp Lead` — busier, stepwise, groove-following.
- `Hypnotic Arp Lead` — repetitive, low-variation arp.
- `Lyrical Call/Response Lead` — 4-bar phrases with clear contour.

### Tasks

- [ ] Extend `configs/lead_modes.json` with entries for:
  - `Rolling Arp Lead`
  - `Hypnotic Arp Lead`
  - `Lyrical Call/Response Lead`
- [ ] For each mode, set reasonable defaults:
  - `target_notes_per_bar` (min/max density).
  - `max_consecutive_notes`.
  - `register_low` / `register_high`.
  - `preferred_slot_weights` tuned to personality (e.g. offbeats vs snare). 
  - `phrase_length_bars` (2 vs 4).
  - `call_response_style` (mild/medium/strong).

### Tests

- [ ] Extend `tests/test_lead_config_loading.py`:
  - New test: `test_lead_modes_multiple_modes_parse`
    - Load the full JSON from `configs/lead_modes.json`.
    - Assert the new mode names exist and basic fields are correct
      (e.g. density bounds, register ranges).

### How to run

- `PYTHONPATH=src pytest tests/test_lead_config_loading.py -q`

### Logging / Notes

During implementation, record in this file under a new **Dev Log**
section:

- Which ranges you chose for each mode and why.
- Any immediate issues (e.g. overlapping registers) you discovered via
  tests or quick inspection.

---

## 2. Tag → Mode Selection Refinement

**Goal:** wire the new modes into `select_lead_mode` so tags drive
reasonable defaults when `--mode` is not provided.

### Tasks

- [ ] Update `select_lead_mode(tags, modes)` in
  `src/techno_engine/leads/lead_modes.py` to:
  - Map `lyrical` → `Lyrical Call/Response Lead` (if defined).
  - Map `hypnotic` → `Hypnotic Arp Lead`.
  - Map `rolling` → `Rolling Arp Lead`.
  - Keep `minimal` → `Minimal Stab Lead`.
  - Keep existing fallback to Minimal Stab or first available mode.

### Tests

- [ ] Extend `tests/test_lead_modes_and_phrase.py`:
  - `test_select_lead_mode_handles_new_tags`:
    - With modes dict containing all four modes, assert:
      - `select_lead_mode(['lyrical'], modes).name == 'Lyrical Call/Response Lead'`.
      - `select_lead_mode(['rolling'], modes).name == 'Rolling Arp Lead'`.
      - `select_lead_mode(['hypnotic'], modes).name == 'Hypnotic Arp Lead'`.
      - `select_lead_mode(['minimal'], modes).name == 'Minimal Stab Lead'`.

### How to run

- `PYTHONPATH=src pytest tests/test_lead_modes_and_phrase.py -q`

### Logging / Notes

- If any tags feel ambiguous in real use (e.g. seeds tagged with both
  `rolling` and `lyrical`), note which mode selection you prefer and
  adjust the priority order accordingly.

---

## 3. Rhythm Templates per Mode

**Goal:** provide distinct **rhythmic skeletons** per mode.

### Tasks

- [ ] Extend `configs/lead_rhythm_templates.json`:
  - For each new mode, add at least one `CALL` template with several
    events (steps/lengths/anchor_type/accent) that match the mode’s
    personality.
  - (Optional) For Lyrical mode, add `RESP`/`CALL_VAR` templates.
- [ ] Ensure `load_rhythm_templates` remains compatible.

### Tests

- [ ] Add `tests/test_lead_rhythm_templates_modes.py`:
  - `test_rhythm_templates_present_for_new_modes`:
    - Load JSON and `load_rhythm_templates`.
    - Group by `mode_name` and assert each new mode has at least one
      template with `motif_role == 'CALL'`.

### How to run

- `PYTHONPATH=src pytest tests/test_lead_rhythm_templates_modes.py -q`

### Logging / Notes

- As you audition patterns, record which templates feel too busy or too
  sparse.
- Consider tagging certain templates as `experimental` in comments so
  they can be easily replaced.

---

## 4. Contour Templates per Mode

**Goal:** give each mode a distinct **pitch contour** behaviour.

### Tasks

- [ ] Extend `configs/lead_contour_templates.json`:
  - `Rolling Arp Lead`: ascending/stepwise arp-like intervals, e.g.
    `[0, 2, 4, 7]`.
  - `Hypnotic Arp Lead`: shorter interval loops, e.g. `[0, 2, 5]`.
  - `Lyrical Call/Response Lead`: arches and gentle up/down shapes.
- [ ] Confirm `load_contour_templates` parses them correctly.

### Tests

- [ ] Extend `tests/test_lead_config_loading.py` or a new
  `tests/test_lead_contour_templates_modes.py`:
  - Verify each new mode contributes at least one contour template.

### How to run

- `PYTHONPATH=src pytest tests/test_lead_config_loading.py -q`
  (or the dedicated contour test file).

### Logging / Notes

- While listening, note which contours feel “too random” vs “too static”
  for each mode; adjust `intervals` and `emphasis_indices` accordingly.

---

## 5. Behaviour Invariants per Mode (Unit Tests)

**Goal:** encode **soft constraints** that each mode should respect,
without over-fitting tests to exact notes.

### Tasks / Tests

Add tests to a new file `tests/test_lead_modes_behaviour.py`:

- [ ] `test_minimal_stab_lead_density`:
  - Generate a lead for a simple seed with tags `['minimal']`.
  - Assert total notes per bar fall within Minimal’s density bounds.

- [ ] `test_rolling_arp_lead_density_and_register`:
  - Use tags `['rolling']` or `--mode 'Rolling Arp Lead'`.
  - Assert:
    - At least N notes per bar (e.g. ≥ 4).
    - All pitches within the configured register.

- [ ] `test_lyrical_lead_phrase_resolution`:
  - Generate 4 bars with `--mode 'Lyrical Call/Response Lead'`.
  - Assert:
    - There are notes in bar 1 and bar 4.
    - Final note is near root/5th (within one octave of the root).

- [ ] `test_hypnotic_lead_repetition` (optional):
  - Check that bars 1 and 2 share a majority of onset positions.

### How to run

- `PYTHONPATH=src pytest tests/test_lead_modes_behaviour.py -q`

### Logging / Notes

- If a desired musical change causes tests to fail, adjust tests to use
  broader invariants rather than exact positions.

---

## 6. Logging Hooks for Tuning

**Goal:** add optional logging to help us understand what each mode is
actually doing when patterns feel off.

### Tasks

- [ ] In `generate_lead(...)`, add an optional debug flag (e.g. read from
  `os.environ.get('BEATENGINE_LEAD_DEBUG')`).
- [ ] When enabled, log (to stdout or a simple log file per run):
  - Selected mode name and tags.
  - Rhythm template IDs and contour IDs.
  - Per-bar density (notes per bar).
  - A few sample alignment scores for key events.

### Tests

- [ ] A light test in `tests/test_generate_lead_basic.py` or a dedicated
  logging test:
  - Temporarily set the env var using `monkeypatch.setenv`.
  - Call `generate_lead` and assert no exceptions are raised and some
    debug text is emitted.

### How to run

- Normal:
  - `PYTHONPATH=src pytest -q`
- Manual debug:
  - `BEATENGINE_LEAD_DEBUG=1 PYTHONPATH=src .venv/bin/python -m techno_engine.seed_cli lead-from-seed ...`

### Logging / Notes

- Use this to capture concrete examples of “why” a given mode chose certain
  slots or intervals when something sounds wrong.

---

## 7. Human Listening & Tuning Loop

**Goal:** formalise how we iterate on modes based on actual user
experience.

### Process

For each mode:

1. **Pick reference seeds**
   - One warehouse/urgent pattern.
   - One minimal pattern.
   - One rolling/hypnotic pattern.

2. **Generate leads**
   - Use `seed_cli lead-from-seed` with:
     - `--mode <Mode Name>`.
     - `--description` noting version, e.g. `"Rolling Arp Lead v3"`.

3. **Audit in TUI/DAW**
   - Open seeds in `seed_explorer` and your DAW.
   - Note what feels off:
     - Too dense? Too sparse? Wrong register? Not enough call/response?

4. **Adjust configs**
   - Tweak `target_notes_per_bar`, `preferred_slot_weights`, contour
     `intervals`, and `register_*`.

5. **Re-run tests**
   - `PYTHONPATH=src pytest tests/test_lead_*.py -q`
   - Confirm invariants still hold.

6. **Log outcome**
   - Update Dev Log (see below) with:
     - What you changed.
     - How it sounded.
     - Whether you consider the mode `experimental` or `tuned`.

---

## 8. Dev Log & Summary Template

At the bottom of this file, append entries like:

```markdown
### Dev Log — YYYY-MM-DD / branch <name>

- Modes touched: Minimal Stab Lead, Rolling Arp Lead
- Seeds auditioned:
  - 2025..._m4_warehouse: Rolling Arp Lead v2 (too busy in bars 3–4).
- Changes:
  - Reduced Rolling Arp Lead target_notes_per_bar from [6,10] → [4,8].
  - Increased penalty for slots with kicks.
- Tests run:
  - pytest tests/test_lead_config_loading.py -q
  - pytest tests/test_lead_modes_behaviour.py -q
- Failures & fixes:
  - test_rolling_arp_lead_density_respected failed (too many notes in bar 2).
  - Fix: trimmed skeleton to hi bound and adjusted template.
- Subjective result:
  - Rolling Arp Lead feels tighter around the groove; keep changes.
```

Over time, this becomes a living summary of:

- Which modes exist and how they evolved.
- Which tests guarded behaviour at each step.
- What went wrong and how it was fixed.

---

## 9. Final Success Metrics

When you consider the lead modes “v1 stable”, capture the following in
this file:

- [ ] All lead-related tests pass:
  - `tests/test_lead_config_loading.py`
  - `tests/test_lead_modes_and_phrase.py`
  - `tests/test_lead_validation_basic.py`
  - `tests/test_generate_lead_basic.py`
  - `tests/test_lead_from_seed_cli.py`
  - `tests/test_lead_rhythm_templates_modes.py`
  - `tests/test_lead_modes_behaviour.py`
- [ ] Full suite: `PYTHONPATH=src pytest -q` passes.
- [ ] For each mode, at least one real seed is tagged as “good” in its
  description (e.g. `"Rolling Arp Lead v3 (keeper)"`).
- [ ] No regressions in legacy behaviour (Minimal Stab Lead still
  behaves as expected).

