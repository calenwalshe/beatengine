# AI Bassline Module: 10-Step Roadmap & Unit Test Plan

## Overview
This roadmap defines the implementation plan for a deterministic, stateless AI bassline generator integrated into the existing Python rhythm engine. It prioritizes an early MVP for listening tests (Step 3) and builds toward full validation, scoring, and schema stability by Step 7.

---

## Step 1 — Seed Discipline, Canonicalization, and PRNG
**Goal:** Ensure determinism across OS/Python versions.

**Milestones**
- Implement `pcg32` PRNG.
- Add `canonicalize_json()` for ordered key normalization.
- Compute `audit_hash()` (SHA-256).
- Define stable `master_seed()` derivation.

**Unit Tests**
- `test_prng_repeatability_same_seed()` → identical sequences.
- `test_canonicalization_order_independent()` → stable hash.
- `test_master_seed_stability()` → consistent cross-platform.

---

## Step 2 — Transport, Swung Micro-Grid, and Masks
**Goal:** Build timing grid and constraint masks.

**Milestones**
- Create `build_swung_grid()` and `build_masks()`.
- Generate kick forbid, pre-kick ghost, and clap/hat boost masks.

**Unit Tests**
- `test_grid_quantization_16th_32nd_ticks()` → tick integrity.
- `test_kick_forbid_exact_matches()` → all kicks forbidden.
- `test_prekick_ghost_exact_offset()` → -1/32 pre-kick alignment.

---

## Step 3 — MVP: Bar Anchor + Offbeat Pulse Generator
**Goal:** Produce audible deterministic basslines for early sanity checks.

**Milestones**
- Implement `bassline.generate()`.
- One anchor (root/5th) per bar; offbeat pulses avoiding kicks.
- Clamp pitches [34,52]; deterministic hash and CLI output.

**Unit Tests**
- `test_mvp_emits_events()` → ≥1 event/bar.
- `test_mvp_no_note_on_kick()` → zero collisions.
- `test_mvp_register_bounds()` → all pitches within [34,52].
- `test_mvp_roundtrip_hash_stable()` → consistent output.

🎧 **Listening checkpoint:** Render 4 bars @120 BPM for subjective evaluation.

---

## Step 4 — Density Targeting & Sustain Accounting
**Goal:** Hit density target ρ ∈ [0.25, 0.60] within tolerance.

**Milestones**
- Implement density tracking model.
- Realizer fills bars to target note count.

**Unit Tests**
- `test_density_within_loose_tolerance()` → ±0.05.
- `test_density_scales_with_config()` → monotonic increase with ρ.
- `test_min_duration_respected()` → ≥ configured min duration.

---

## Step 5 — Validator: Kick, Density, Register, Monophony
**Goal:** Apply one correction pass with clear summaries.

**Milestones**
- Correction order: kick → register → density → monophony.
- Limit edits; summaries ≤3 sentences each.

**Unit Tests**
- `test_validator_removes_kick_collisions()` → 0 collisions post-validate.
- `test_validator_density_tight()` → ±0.03 tolerance.
- `test_validator_single_pass_only()` → ≤1 pass.
- `test_validator_summaries_are_short()` → summary length check.

---

## Step 6 — Drum-Aware Scoring and Pre-Kick Ghosts
**Goal:** Add musical coherence and anticipations.

**Milestones**
- Implement scoring `S(t,p)` with weighted drum sync features.
- Support pre-kick ghosts (end before kick).

**Unit Tests**
- `test_ghosts_end_before_kick()` → all ghosts end < kick tick.
- `test_clap_response_rate_minimum()` → ≥20% response rate.
- `test_hat_sync_bonus_effect()` → measurable hat sync influence.

---

## Step 7 — Tool API Surface & Error Handling
**Goal:** Finalize schemas and validation responses.

**Milestones**
- Implement tool functions `generate()` and `validate_lock()`.
- Add unified error codes.

**Unit Tests**
- `test_generate_schema_contract()` and `test_validate_lock_schema_contract()`.
- `test_error_on_infeasible_density()` → BAD_CONFIG triggered.
- `test_version_mismatch_rejected()` → VERSION_MISMATCH enforced.

---

## Step 8 — Performance, Statelessness, and Concurrency
**Goal:** Optimize latency and guarantee stateless operation.

**Milestones**
- O(#notes) runtime; preallocate arrays.
- No mutable globals or shared PRNG state.

**Unit Tests**
- `test_latency_budget_4bars()` → p95 <3 ms.
- `test_stateless_reentrancy()` → no cross-seed leakage.
- `test_no_global_mutation()` → globals unchanged.

---

## Step 9 — Integration & Golden Tests
**Goal:** Validate reproducibility and listening quality.

**Milestones**
- Bridge to rhythm engine transport.
- Golden fixtures + audit hashes.

**Unit Tests**
- `test_e2e_golden_simple()` → byte-identical replay.
- `test_seed_replay()` → identical output across OS.
- `test_latency_consistent()` → stable under varied loads.

🎧 **Listening checkpoint:** Commit golden 4–8 example MIDIs for regression listening.

---

## Step 10 — Packaging, CLI, and Docs
**Goal:** Ship stable release.

**Milestones**
- Add CLI tool: `python -m ai_bass.generate --cfg config.json --out bass.mid`.
- Include schema docs and examples.

**Unit Tests**
- `test_cli_smoke()` → valid MIDI output.
- `test_docs_snippets_run()` → doctest validation.
- `test_style_table_swap_deterministic()` → deterministic variant output.

---

## Acceptance Gates
| Gate | Criteria |
|------|-----------|
| **A** | MVP audible; deterministic hash stable. |
| **B** | Tight validator; ≤3-sentence summaries. |
| **C** | API schema stable; errors standardized. |
| **D** | Golden tests & latency budgets pass. |

---

### Summary
This roadmap ensures early auditory feedback by Step 3 while guaranteeing deterministic, stateless, and schema-stable evolution. By Step 7, all unit tests confirm reproducibility, density control, and API correctness, enabling confident integration into the existing rhythm engine.

