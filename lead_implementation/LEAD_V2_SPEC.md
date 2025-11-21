# Lead Generator v2 – Implementation & Test Spec

This document distills the scaffolding that already exists inside `lead_implementation/lead_v2` and turns it into an actionable plan for bringing the theory-aware lead generator online. Each section links back to the relevant code/config stubs so the required work is grounded in the current repo state.

## 1. Current Status Snapshot

- `generate_lead_v2` wires the intended stages (key → phrases → motifs → slots → bass) but almost every stage is placeholder logic that needs real rules (`lead_implementation/lead_v2/generate.py#L56-L161`).
- Supporting modules define data classes and skeletal helpers—`phrases.py` plans evenly tiled CALL/RESP bars (`lead_implementation/lead_v2/phrases.py#L7-L70`), `motifs.py` fuses rhythm & contour templates without tension- or anchor-awareness (`lead_implementation/lead_v2/motifs.py#L10-L93`), `theory.py` exposes minimal theory helpers (`lead_implementation/lead_v2/theory.py#L7-L123`), `slots.py` simply echoes the requested metric slot (`lead_implementation/lead_v2/slots.py#L10-L64`), and `bass.py` is a stub pass-through (`lead_implementation/lead_v2/bass.py#L9-L25`).
- Example configs already capture mode, rhythm, and contour data structures that the runtime must ingest (`lead_implementation/config/lead_modes_v2.example.json`, `lead_implementation/config/lead_rhythm_templates_v2.example.json`, `lead_implementation/config/lead_contour_templates_v2.example.json`).
- Tests only cover two trivial invariants (in-scale check and phrase coverage) (`lead_implementation/tests/test_lead_v2_scaffold.py#L1-L24`).

## 2. Data Contracts

1. **Mode Config → `LeadModeConfig`**
   - Parse JSON at load time into `LeadModeConfig` (see `lead_implementation/lead_v2/generate.py#L20-L36`).
   - Nested sections map as follows:
     - `scale.scale_type`, `scale.default_root_pc`, `scale.allow_key_from_seed_tag`
     - `register.low/high/gravity_center`
     - `phrase` → `PhraseConfig`
     - `density`, `slot_preferences`, `bass_interaction`
     - Additional sections such as `function_profiles` and `degree_weights` should be plumbed through to new helper structs in `theory.py`.

2. **Templates**
   - Rhythm templates (`lead_implementation/config/lead_rhythm_templates_v2.example.json`) populate `RhythmTemplate` and `RhythmEvent` instances (`lead_implementation/lead_v2/motifs.py#L10-L33`).
   - Contour templates (`lead_implementation/config/lead_contour_templates_v2.example.json`) populate `ContourTemplate` (`lead_implementation/lead_v2/motifs.py#L28-L36`).

3. **Anchors & Seed Metadata**
   - `anchors` must expose timing grid info such as `step_ticks`, downbeat tags, and per-step drum hits so slot scoring can evaluate anchor types (referenced but not implemented in `generate_lead_v2` at `lead_implementation/lead_v2/generate.py#L100-L145`).
   - `seed_metadata` should provide `seed_id`, `tags`, `bars`, and any phrase-level descriptors needed by the planner (`lead_implementation/lead_v2/generate.py#L84-L99`).

4. **Outputs**
   - `generate_lead_v2` returns a sorted list of `LeadNoteEvent` items with populated metadata (`lead_implementation/lead_v2/theory.py#L63-L75`) suitable for Beatengine’s MIDI writer.

## 3. Pipeline Specification

### Stage 1 – Key & Harmony
1. Extend `derive_keyspec` to read `seed_metadata.tags` for patterns like `key_a_min`; fall back to mode defaults when absent. Optionally analyze `bass_midi` root distribution for confirmation (`lead_implementation/lead_v2/generate.py#L45-L54`).
2. Expand `build_scale_degrees` to cover all mode scale types referenced by configs and support extensions (add blues, melodic minor, etc.) (`lead_implementation/lead_v2/theory.py#L81-L123`).
3. Upgrade `build_harmony_track` to support per-bar harmonic functions (tonic / predominant / dominant), using either a deterministic pattern per mode or hints from `seed_metadata` sections.

### Stage 2 – Phrase Planning
1. Replace the even-tiling stub in `plan_phrases` with a planner that:
   - Samples phrase lengths from `[min_bars, max_bars]` while ensuring total bars == `seed_metadata.bars`.
   - Applies `call_response_pattern` cyclically within each phrase; allows weighting by `mode_cfg.density` and future `seed_metadata` cues.
   - Assigns `form_label` from `phrase_forms` (support e.g. `["A", "A'", "B"]`) and ensures phrase IDs map to contiguous bar ranges.
   - Marks final bars with `phrase_end_resolution_degrees` so later stages know which tones should resolve (`lead_implementation/lead_v2/phrases.py#L29-L70`).

### Stage 3 – Motif Fusion & Template Selection
1. Implement template loaders that filter rhythm/contour templates by role, bar length, and optional tags (density, syncopation) from mode config.
2. In `generate_lead_v2`, select templates per phrase segment:
   - Support weighted cycling and controlled variation (reuse vs mutate) using `rng`.
   - Ensure `steps_per_bar` derives from anchors (beats * steps) rather than the temporary constant (`lead_implementation/lead_v2/generate.py#L99-L128`).
3. Enhance `fuse_rhythm_contour` to:
   - Map contour degree intervals cumulatively so each logical note has a relative degree target.
   - Annotate `beat_strength` from anchor metadata (`RhythmEvent.anchor_type`) rather than assuming `"weak"` (`lead_implementation/lead_v2/motifs.py#L46-L93`).
   - Track per-note `accent`, reference to template IDs, and phrase position (`start/inner/end`).

### Stage 4 – Theory Mapping & Pitch Assignment
1. Introduce tone selection helpers in `theory.py` that leverage `mode_cfg.function_profiles` and `degree_weights`:
   - Determine `tone_category` (chord / color / passing) for each logical note based on `(role, phrase_position, beat_strength, tension_label)`.
   - Sample degrees respecting contour instructions while enforcing `mode_cfg.contour.max_leap_degrees` and `step_bias`.
2. Map degrees to MIDI:
   - Convert degree → pitch class with `degree_to_pitch_class`, then choose octave within `[register_low, register_high]` while gravitating toward `register_gravity_center` (`lead_implementation/lead_v2/theory.py#L7-L61`).
   - Apply contour transpositions and per-phrase register drift from `mode_cfg.variation`.

### Stage 5 – Slot Alignment & Timing
1. Implement slot extraction from anchors:
   - Collect candidate slots near each logical note’s metric target, annotated with tags such as `near_kick_pre`, `snare_zone`, `offbeat`, `sustain_room`.
2. Replace `align_to_slots` stub with a search routine:
   - Evaluate ±`max_step_jitter` steps plus extra offsets from rhythm template’s `max_step_jitter` (`lead_implementation/lead_v2/slots.py#L29-L64`).
   - Score using `role_slot_prefs`, anchor alignment, local density (e.g., penalize placing notes too close per `rhythm.min_inter_note_gap_steps`), and overlap with existing `LeadNoteEvent`s.
   - Adjust durations based on `RhythmEvent.length_steps` × `step_ticks`, with truncation to avoid collisions.
   - Populate debug tags: slot tags, anchor hits matched, jitter applied, and resolved tone category.

### Stage 6 – Bass Interaction
1. Implement `apply_bass_interaction` to enforce `min_semitone_distance` and `avoid_root_on_bass_hits` when bass and lead overlap (`lead_implementation/lead_v2/bass.py#L9-L25`).
2. Provide strategies (e.g., nudge up/down by a step, resample tone category, shorten note) and deterministic tie-breaking using `rng`.

### Stage 7 – Output Normalization
1. Ensure events are sorted by `start_tick` and deduplicated if jitter collapses onto same slot.
2. Provide metadata summary (phrase_id, template IDs, function labels) for downstream debugging/logging.

## 4. Integration Notes

- Add a thin adapter inside the main Beatengine package that:
  1. Resolves the requested lead mode to a `LeadModeConfig` instance.
  2. Loads matching rhythm/contour templates once per session (cache).
  3. Calls `generate_lead_v2` with real `DrumAnchors`, `SeedMetadata`, and optional bass MIDI.
  4. Converts returned `LeadNoteEvent`s into the existing track/event representation.
- Keep deterministic RNG seeding across pipeline stages using `make_rng` (`lead_implementation/lead_v2/generate.py#L39-L43`) plus per-stage offsets (e.g., `"...|phrase|motif"` seeds) to allow reproducible tests.

## 5. Testing Strategy

1. **Unit Tests**
   - Phrase planner: verify bar coverage, role counts, and deterministic output for fixed seeds; extend `test_phrase_planner_covers_bars` (`lead_implementation/tests/test_lead_v2_scaffold.py#L12-L24`).
   - Theory helpers: confirm `degree_to_pitch_class` and register mapping stay in key/register bounds.
   - Slot alignment: simulate anchors to ensure jitter search honors `min_inter_note_gap_steps` and preference weights.
   - Bass interaction: craft overlapping bass clips to ensure notes are retuned or muted according to config flags.

2. **Snapshot / Golden Tests**
   - For at least one mode (e.g., `hypnotic_arp` from `lead_implementation/config/lead_modes_v2.example.json`), freeze a deterministic seed and assert the resulting `LeadNoteEvent` list (pitch, start_tick, role tags). Store as JSON to avoid binary diffs.

3. **Statistical/Property Tests**
   - Density: check average notes per bar matches `mode_cfg.density.target_notes_per_bar`.
   - Register: confirm min/max event pitches obey `[register_low, register_high]`.
   - Scale compliance: reuse `is_in_scale` to validate every pitch is diatonic to the derived key (patterned after `test_keyspec_in_scale_basic` at `lead_implementation/tests/test_lead_v2_scaffold.py#L7-L10`).

4. **Integration Smoke**
   - Run the full pipeline with sample anchors & bass, export to MIDI, and ensure events play without overlaps or silent bars. Automate via a pytest that renders to memory (no file I/O) and inspects timing.

## 6. Execution Roadmap

1. **Bootstrap configs and loaders** – parse JSON into strong dataclasses, implement template registries.
2. **Phrase & motif logic** – finalize planner and template fusion so `MotifPlan` instances carry all required metadata (degree targets, accents, rhythm lengths).
3. **Theory/pitch assignment** – implement tone selection, degree mapping, and register handling.
4. **Slot alignment & anchors** – integrate with DrumAnchors, finalize timing/velocity rules.
5. **Bass interaction + variation controls** – enforce spacing constraints and apply per-phrase variation.
6. **Testing & validation harness** – expand the pytest suite + optional golden snapshots.

Following this staged plan keeps the work aligned with the scaffolding already present in `lead_implementation/lead_v2` while ensuring every new feature comes with explicit tests and determinism hooks.
