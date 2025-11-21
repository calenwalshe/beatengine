# Beatengine Lead Generator v2 — Product Modification Roadmap

**Document purpose:** This roadmap describes *exactly* how to evolve Beatengine’s current lead generator into a **music‑theory‑aware** system with phrase structure, call/response behavior, configurable mode personalities, and deterministic outputs. It specifies architecture, data schemas, algorithms, integration points, tests, acceptance criteria, migration steps, and operational guidance. The document is **implementation‑ready** for a coding agent.

---

## Table of Contents

1. [Context & Scope](#context--scope)  
2. [Goals, Non‑Goals, Constraints](#goals-non-goals-constraints)  
3. [Glossary](#glossary)  
4. [Current System Summary (Baseline)](#current-system-summary-baseline)  
5. [High‑Level Changes](#high-level-changes)  
6. [Milestones & Work Packages](#milestones--work-packages)  
7. [Architecture & Data Model](#architecture--data-model)  
   - [KeySpec](#keyspec)  
   - [HarmonyTrack](#harmonytrack)  
   - [LeadMode v2 Schema](#leadmode-v2-schema)  
   - [Rhythm & Contour Templates v2](#rhythm--contour-templates-v2)  
   - [Note Representation](#note-representation)  
8. [Algorithms & Pipelines](#algorithms--pipelines)  
   - [Key/Scale Derivation](#keyscale-derivation)  
   - [Phrase Planning](#phrase-planning)  
   - [Motif Construction (CALL/RESP)](#motif-construction-callresp)  
   - [Tone Category & Degree Selection](#tone-category--degree-selection)  
   - [Voice‑Leading & MIDI Mapping](#voice-leading--midi-mapping)  
   - [Slot Alignment & Scoring](#slot-alignment--scoring)  
   - [Bass Interaction](#bass-interaction)  
   - [Variation Engine](#variation-engine)  
   - [Determinism & RNG](#determinism--rng)  
9. [Integration Plan](#integration-plan)  
10. [Testing Strategy](#testing-strategy)  
11. [Configuration & Tuning](#configuration--tuning)  
12. [Migration & Compatibility](#migration--compatibility)  
13. [Operational Guidance](#operational-guidance)  
14. [Risks & Mitigations](#risks--mitigations)  
15. [Appendix A — JSON Schemas](#appendix-a--json-schemas)  
16. [Appendix B — Example Config Files](#appendix-b--example-config-files)  
17. [Appendix C — Pseudocode](#appendix-c--pseudocode)  
18. [Appendix D — Example PyTest Suite](#appendix-d--example-pytest-suite)  
19. [Appendix E — Mode Personalities Reference](#appendix-e--mode-personalities-reference)  
20. [Definition of Done Checklists](#definition-of-done-checklists)

---

## 1) Context & Scope

**Beatengine** is a Python 3 project using **mido** (MIDI I/O) and **pytest** (tests). It includes:

- A drum engine (`m4`) on a **4/4 grid with 16 steps per bar** (16th‑note resolution).  
- A **DrumAnchors**/slot grid: per bar, lists of kick/snare/hat steps; plus `slot_tags[bar][step]` with labels like `kick`, `snare_zone`, `hat`, `bar_start`, `bar_end`, `near_kick_pre`, `near_kick_post`.  
- A **seed system**: `seeds/<seed_id>/` with `config.json` (drum), `metadata.json` (SeedMetadata: bpm, bars, ppq, tags, summary, prompt, assets), and assets: `drums/main.mid`, `bass/main.mid` (optional), `leads/...` (lead experiments). `rebuild_index()` normalizes and maintains `seeds/index.json`.

There’s a **groove‑aware bass engine** that already consumes the drum grid and tags to build rhythms (modes, motifs, density, kick‑avoid rules, validation). The current **lead generator** is wired but **musically flat**.

**Scope of this roadmap:** Replace the current lead logic with a **theory‑aware, phrase‑driven** system while preserving determinism, testability, and seed/config workflows.

---

## 2) Goals, Non‑Goals, Constraints

### Goals
- Music‑theory‑aware pitch logic in a consistent **key/scale** with **chord tones**, **color tones**, and **passing tones**.  
- 2–4 bar **phrase structure** with explicit **CALL/RESP** behavior (contrast + coherence).  
- **Mode personalities** (Hypnotic Arp, Lyrical C/R, Rolling Arp) that are **data‑driven** via JSON.  
- Determinism (same seed + config ⇒ same output).  
- **Slot‑grid reuse** (drum‑aware rhythm alignment).  
- Fully configurable via new **v2 config schemas**.  
- Comprehensive tests (unit + structural “golden seed” assertions).

### Non‑Goals
- Full harmonic progression engine (we start with static tonic/minor per bar, scaffold allows extension).  
- Audio rendering/synthesis (MIDI only).  
- UI work beyond `seed_cli` integration.

### Constraints
- Python 3, mido, pytest.  
- 4/4, 16‑step grid; variable **PPQ** from seed metadata.  
- Output: list of note events `(pitch, velocity, start_tick, duration)` for `midi_writer.write_midi`.  
- Deterministic RNG seeded by CLI/seed metadata.

---

## 3) Glossary

- **Scale Degree**: Position within scale (1..7, extensions 9/11/13).  
- **Chord Tones**: 1, 3, 5, 7 in the chosen mode.  
- **Color Tones**: 2, 4, 6 (and 9/11/13) for tension.  
- **Passing Tone**: Stepwise neighbor on weak beats bridging chord tones.  
- **CALL/RESP**: Motif + answer with recognizable relation and contrast.  
- **Phrase**: 2–4 bars grouping of motifs.  
- **Beat Strength**: Strong (e.g., bar_start, snare_zone) vs weak/offbeat.

---

## 4) Current System Summary (Baseline)

- Loads a mode and *first* CALL rhythm template.  
- Aligns events to nearest good slot by `preferred_slot_weights`.  
- Applies a contour as **semitone offsets from a fixed root**, forced into register; last note resolves to root.  
- **Limitations:** no key/scale, no chord vs color tones, no phrase semantics, minimal variation, template reuse too narrow.

**Reusables:** DrumAnchors + slot grid, slot scoring (as a term in a richer score), density control, register bounds, CLI plumbing.

---

## 5) High‑Level Changes

1. Introduce **KeySpec** and **HarmonyTrack** abstractions.  
2. Replace pitch pipeline with **degree‑based, function‑aware** selection.  
3. Add **phrase planner** and **CALL/RESP** template pairing.  
4. Implement **motif variation engine** (transposition, contour inversion, rhythm edits).  
5. Upgrade **LeadMode schema** (v2) and add **templates v2** with multiple choices per role.  
6. Extend slot alignment with **role‑aware** preferences and **beat strength**.  
7. Add **bass interaction** constraints (optional per mode).  
8. Maintain determinism via **seeded RNG** and stable selection policies.  
9. Expand tests to verify **structural musical properties**.

---

## 6) Milestones & Work Packages

> ✅ = exit criteria must pass to advance.  
> Code is expected under `beatengine/lead/` unless noted.

### M0 — Scaffolding & Config Loading (1–2 days)
- Create v2 config loaders: `lead_modes_v2.json`, `lead_rhythm_templates_v2.json`, `lead_contour_templates_v2.json`.  
- Add `version` fields and coexistence with v1.  
- ✅ Parse & validate v2 JSON (jsonschema or pydantic) and expose typed objects.

### M1 — Theory Core: KeySpec & HarmonyTrack (1–2 days)
- Implement `KeySpec` (root_pc, scale_type, scale_degrees, default_root_octave).  
- Implement minimal `HarmonyTrack` (static tonic minor per bar).  
- Wire key derivation from seed tags → bass inference → default.  
- ✅ Unit tests: keys map to correct pitch classes; scale membership checkers.

### M2 — Phrase Planner & Roles (2–3 days)
- Implement phrase segmentation by bars; support lengths 2–4 (configurable).  
- Apply role sequences (e.g., `CR`, `CRCR`) and motif form patterns (`AA'B`, `ABAB`).  
- ✅ Tests: complete coverage of bars with correct role assignment; determinism.

### M3 — Motif Construction (Rhythm + Contour) (2–3 days)
- Load per‑role rhythm & contour templates; support multiple templates per role with RNG selection.  
- Fuse rhythm and contour into a **MotifPlan** (events + contour indices + tension labels).  
- ✅ Tests: motif plan length and timing match template; call/resp linkage present.

### M4 — Function‑Aware Pitch Engine (3–4 days)
- Implement tone category selection by context (role × phrase_position × beat_strength).  
- Implement degree selection per category with configurable weights; phrase‑end resolution enforcement.  
- Add passing‑tone rules on weak beats.  
- ✅ Tests: distribution of chord vs color tones; phrase ends are 1/5; all notes are in scale.

### M5 — Voice‑Leading & MIDI Mapping (2–3 days)
- Implement octave selection minimizing leaps, respecting contour emphasis and register.  
- Map degrees to MIDI via KeySpec; enforce register bounds.  
- ✅ Tests: average leap size bounds; register clipping avoided; determinism maintained.

### M6 — Slot Alignment & Scoring (1–2 days)
- Extend slot scoring with role‑aware `slot_preferences` and beat strength; jitter search ±N steps.  
- ✅ Tests: alignment respects preferences; no overlaps; density constraints applied.

### M7 — Variation Engine & Response Generation (2–3 days)
- Implement RESP from CALL: transpositions, contour inversion, rhythm edits, note substitutions.  
- ✅ Tests: structural similarity ≥ X% with ≥ Y% differences; phrase‑end resolutions preserved.

### M8 — Bass Interaction (optional per mode) (1–2 days)
- If bass MIDI present, avoid unison/close intervals at overlaps; root‑avoid on strong bass hits.  
- ✅ Tests with fixture bassline: min distance upheld; root avoidance respected.

### M9 — CLI Integration & Assets (1 day)
- `seed_cli lead-from-seed` uses v2 by default (flag to use v1).  
- Output to `leads/variants/lead_<mode_v2>.mid`; add asset entry to `metadata.json`.  
- ✅ Manual E2E run across golden seeds; files added and index updated.

### M10 — Golden Seeds, Tuning & Docs (ongoing)
- Curate a small set of seeds with expected structural metrics.  
- Document all configs and tuning parameters; provide examples.  
- ✅ CI passes unit + structural tests; README/roadmap published.

---

## 7) Architecture & Data Model

### KeySpec

```text
KeySpec:
  root_pc: int             # 0..11, C=0, C#=1, ...
  scale_type: str          # 'aeolian' | 'dorian' | 'phrygian' | 'minor_pent'
  scale_degrees: [int]     # semitone offsets 0..11 in one octave (derived)
  default_root_octave: int # e.g., 4
```

**Scale tables** (examples):  
- aeolian: `[0, 2, 3, 5, 7, 8, 10]`  
- dorian: `[0, 2, 3, 5, 7, 9, 10]`  
- phrygian: `[0, 1, 3, 5, 7, 8, 10]`  
- minor_pent: `[0, 3, 5, 7, 10]`

### HarmonyTrack

```text
HarmonyTrack:
  per_bar: [
    {
      tonic_degree: 1,
      chord_tone_degrees: [1, 3, 5, 7],
      color_tone_degrees: [2, 4, 6, 9, 11, 13]
    }, ...
  ]
```

Initial implementation: one identical entry per bar.

### LeadMode v2 Schema

Key fields (detailed JSON schema in Appendix A):

- `id`, `tags` (matching seed metadata).  
- `scale`: `{ scale_type, default_root_pc, allow_key_from_seed_tag }`.  
- `register`: `{ low, high, gravity_center }` in MIDI.  
- `density`: `{ target_notes_per_bar, max_consecutive_notes, min_rest_per_bar_steps }`.  
- `phrase`: `{ min_bars, max_bars, call_response_pattern, phrase_forms, phrase_end_resolution_degrees }`.  
- `function_profiles`: probability tables for chord/color/passing per context (role × phrase_position × beat_strength).  
- `degree_weights`: weight maps per tone category.  
- `contour`: shapes, leap limits, step bias.  
- `variation`: rhythm/pitch strengths, register drift, contour inversion probability, transposition choices.  
- `slot_preferences`: role‑aware weights over slot tags.  
- `bass_interaction`: `{ avoid_unison_with_bass, avoid_root_on_bass_hits, min_semitone_distance_from_bass }`.

### Rhythm & Contour Templates v2

**RhythmTemplate**

```text
RhythmTemplate:
  id: str
  role: 'CALL' | 'RESP'
  bars: int
  events: [
    { "step_offset": int, "length_steps": int, "accent": number, "anchor_type": "kick|snare_zone|hat|offbeat|null" }
  ]
  max_step_jitter: int
  min_inter_note_gap_steps: int
```

**ContourTemplate**

```text
ContourTemplate:
  id: str
  role: 'CALL' | 'RESP'
  degree_intervals: [int]  # in scale degrees, first element typically 0
  emphasis_indices: [int]
  shape_type: 'arch' | 'ramp_up' | 'ramp_down' | 'zigzag' | 'flat'
  tension_profile: ['low'|'medium'|'high'|'resolve', ...] # aligned to notes
```

Modes reference multiple per role; selection is by RNG + filters (bars, tags).

### Note Representation

Internal (logical) before MIDI mapping:

```text
LeadNoteLogical:
  phrase_id: int
  metric_position: { bar_index: int, step_in_bar: int }
  role: 'CALL' | 'RESP'
  phrase_position: 'start' | 'inner' | 'end'
  beat_strength: 'strong' | 'weak'
  tension_label: 'low' | 'medium' | 'high' | 'resolve'
  contour_index: int

  tone_category: 'chord_tone' | 'color' | 'passing'
  degree: int              # 1..7 + 9/11/13
  octave_offset: int       # relative to default_root_octave
```

Output event (for MIDI writer):

```text
LeadNoteEvent:
  pitch: int
  velocity: int
  start_tick: int
  duration: int
```

---

## 8) Algorithms & Pipelines

### Key/Scale Derivation

1. **From SeedMetadata.tags**: look for `key_*` and `mode_*` tags, e.g., `key_a_min`, `mode_dorian`.  
2. **From bassline** (fallback): load `bass/main.mid`, compute pitch‑class histogram; pick most frequent as `root_pc`.  
3. **Default**: `A` aeolian.  
4. Build `KeySpec` using `scale_type` → `scale_degrees` lookup table.

### Phrase Planning

- Choose phrase length `L` within `[min_bars, max_bars]` that tiles total bars `N` (prefer divisor; else last phrase shorter).  
- Assign roles by `call_response_pattern` string (e.g., `"CRCR"` → [C,R,C,R]).  
- Assign motif identities using `phrase_forms` (e.g., `AA'B` over four segments).  
- Mark **phrase_position** per note: first event = `start`, last event = `end`, others = `inner`.

### Motif Construction (CALL/RESP)

- Select **RhythmTemplate** for role & bars (if bars mismatch, repeat or truncate template evenly).  
- Select **ContourTemplate** for role & bars.  
- Fuse into **MotifPlan**:
  - Sort events by time; map each to a contour index (wrap or distribute).  
  - Carry `tension_profile` to each event.  
  - Compute `beat_strength` using slot tags: strong at `bar_start`, `snare_zone`, downbeats; else weak.

### Tone Category & Degree Selection

- For each event, build context key: `f"{role}.{phrase_position}.{beat_strength}"`.  
- Sample tone category via `function_profiles[context]` (deterministic RNG).  
- Select degree from `degree_weights[category]`:  
  - Ensure degree exists in current `scale_type` (translate 9→2, 11→4, 13→6 modulo octave).  
  - **Passing tones**: prefer ±1 diatonic step from previous degree on weak beats.  
- **Phrase end**: if `tension_label == 'resolve'` or `phrase_position == 'end'`, snap to nearest of `phrase_end_resolution_degrees` (1/5).

### Voice‑Leading & MIDI Mapping

- Choose base octave for first note near `register.gravity_center`.  
- For each next note:
  - Consider octave shifts ∈ {−1,0,+1} (clamped to `[register.low, register.high]`).  
  - Cost = `α*semitone_jump + β*register_distance + γ*violate_contour_emphasis` (weights from mode).  
  - Pick minimal cost; apply `register_drift_per_phrase` offset per phrase (bounded).  
- Convert (degree, octave) → MIDI:  
  - Map degree to semitone using `KeySpec.scale_degrees`, add `12*octave`, add `root_pc` offset.

### Slot Alignment & Scoring

- For each motif event, search slots ±`max_step_jitter`:  
  - Base start = `bar_offset + step_offset`.  
  - Score(slot) =  
    - `W_role_tag * role_slot_pref(tag)` +  
    - `W_anchor * (anchor_type match)` +  
    - `W_strength * beat_strength_value` +  
    - `W_density * local_sparsity_bonus` +  
    - `W_conflict * overlap_penalty`.  
- Pick highest score; ensure `min_inter_note_gap_steps`.  
- Duration = `length_steps * step_ticks` (shorten to avoid overlap).

### Bass Interaction

- If `bass_interaction.avoid_unison_with_bass`: for overlapping windows, if `abs(lead_pitch - bass_pitch) < min_semitone_distance_from_bass`, then:  
  - Try nearest alternative degree in same role category; else shift octave within register; else shorten note.  
- If `avoid_root_on_bass_hits`: on strong beats with bass root, avoid lead root (prefer 3/5/7).

### Variation Engine

- **Response from Call**:  
  - Transpose CALL degrees by element of `transposition_choices` (scale degrees).  
  - With `contour_inversion_prob`, invert sign of intervals.  
  - Rhythm edits proportional to `rhythm_variation_strength`: drop/merge/anticipate 1–2 weak‑beat notes.  
  - Pitch edits proportional to `pitch_variation_strength`: substitute color for chord tone at weak positions.  
- Keep phrase‑end enforcement unchanged.

### Determinism & RNG

- RNG seed = stable hash of:  
  - `seed_id`, `mode_id`, `cli_rng_seed`, `lead_version`, and **template IDs chosen**.  
- Use a small utility: `rng = Random(seed_int)` and **never** use global RNG.  
- All sampling functions take `rng` instance; sorting must be stable.

---

## 9) Integration Plan

- **Entry point:** `generate_lead_v2(anchors, seed_metadata, bass_midi_opt, mode_override, rng_seed, ...)`.  
- **CLI:** `seed_cli lead-from-seed <seed_id> --mode <mode_id> --lead-version v2 --rng-seed <int> [--use-v1]`.  
- **Asset output:** `seeds/<seed_id>/leads/variants/lead_<mode_id>_v2.mid`.  
- **Metadata:** append asset entry:  
  - `{"type": "lead", "path": "leads/variants/lead_<mode_id>_v2.mid", "mode": "<mode_id>", "version": "v2", "rng_seed": <int>, "scale": {"root_pc": X, "scale_type": "..."}}`  
- **Index:** `rebuild_index()` picks up new asset; no format change required.

---

## 10) Testing Strategy

### Unit Tests
- **KeySpec**: mapping degrees → pitch classes; scale membership.  
- **HarmonyTrack**: per‑bar structure exists and is accessible.  
- **Phrase Planner**: bar coverage, roles sequence matches config, deterministic with seed.  
- **Template Fusion**: rhythm & contour lengths; tension labels assigned.  
- **Tone Category**: context → distribution bounds (e.g., chord tones ≥ 70% on strong beats).  
- **Degree Selection**: only degrees allowed by scale; phrase‑end resolution to 1/5.  
- **Voice‑Leading**: average semitone jump within mode bounds; register respected.  
- **Slot Alignment**: min gap upheld; max jitter applied; density within bounds.  
- **Bass Interaction**: min distance from bass satisfied in overlapping windows.

### Structural / Golden Seed Tests
- For 3–5 curated seeds per mode:  
  - notes/bar within `[min,max]`,  
  - fraction of repeated positions between CALL and RESP,  
  - fraction of changed degrees in RESP,  
  - end‑of‑phrase degree ∈ {1,5}.

### Determinism
- With fixed `rng_seed`, assert identical event lists (or identical serialized MIDI) across runs.

### Performance
- End‑to‑end under 200ms per 8‑bar seed on typical dev machine (tunable).

---

## 11) Configuration & Tuning

- All behavior is in JSON files:  
  - `config/lead_modes_v2.json`  
  - `config/lead_rhythm_templates_v2.json`  
  - `config/lead_contour_templates_v2.json`  
- Hot‑swappable: generator loads at runtime; no code changes for tuning.  
- Provide **example packs** in Appendix B.

---

## 12) Migration & Compatibility

- Keep v1 code path behind `--use-v1` or `LEAD_V1_ENABLED=1` env flag.  
- Config versioning via `"version": "v2"` fields; separate file names avoid clashes.  
- Optional script: `tools/migrate_lead_modes_v1_to_v2.py` to prefill defaults.  
- Backward‑compatible CLI: default to v2, print warning when v1 is explicitly used.

---

## 13) Operational Guidance

- **Seed tags** can suggest scale:  
  - `key_a_min` → `A` + `aeolian`  
  - `mode_dorian` → dorian scale type  
  - Stylistic tags to scale mapping (fallback): `warehouse→aeolian`, `hypnotic→dorian`, `industrial→phrygian`.  
- **Debugging:**  
  - `--debug-lead` dumps: chosen templates, phrase plan, degree sequence, slot decisions, conflicts resolved.  
  - Write debug CSV at `seeds/<seed_id>/leads/debug/lead_<mode>_v2_notes.csv`.

---

## 14) Risks & Mitigations

- **Over‑complex configs** → Provide minimal defaults + JSON schema validation + examples.  
- **Non‑determinism from iteration order** → stable sorts and explicit RNG.  
- **Over‑tight constraints causing silence** → relaxation fallback (reduce passing‑tone rules first, then jitter).  
- **Bass avoidance causing awkward leaps** → prefer degree substitution before octave jumps.  
- **Template mismatch with bar count** → deterministic repeat/truncate policy.

---

## 15) Appendix A — JSON Schemas

> These are valid JSON Schema documents you can use with `jsonschema`. Comments are in prose only (no inline comments).

### A.1 `lead_modes_v2.schema.json` (excerpt)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LeadModeV2",
  "type": "object",
  "required": ["id", "scale", "register", "density", "phrase", "function_profiles", "degree_weights", "variation", "slot_preferences"],
  "properties": {
    "version": { "type": "string", "const": "v2" },
    "id": { "type": "string" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "scale": {
      "type": "object",
      "required": ["scale_type"],
      "properties": {
        "scale_type": { "type": "string", "enum": ["aeolian", "dorian", "phrygian", "minor_pent"] },
        "default_root_pc": { "type": "integer", "minimum": 0, "maximum": 11 },
        "allow_key_from_seed_tag": { "type": "boolean" }
      }
    },
    "register": {
      "type": "object",
      "required": ["low", "high", "gravity_center"],
      "properties": {
        "low": { "type": "integer" },
        "high": { "type": "integer" },
        "gravity_center": { "type": "integer" }
      }
    },
    "density": {
      "type": "object",
      "required": ["target_notes_per_bar", "max_consecutive_notes", "min_rest_per_bar_steps"],
      "properties": {
        "target_notes_per_bar": { "type": "number" },
        "max_consecutive_notes": { "type": "integer" },
        "min_rest_per_bar_steps": { "type": "integer" }
      }
    },
    "phrase": {
      "type": "object",
      "required": ["min_bars", "max_bars", "call_response_pattern", "phrase_forms", "phrase_end_resolution_degrees"],
      "properties": {
        "min_bars": { "type": "integer", "minimum": 2, "maximum": 8 },
        "max_bars": { "type": "integer", "minimum": 2, "maximum": 8 },
        "call_response_pattern": { "type": "string" },
        "phrase_forms": { "type": "array", "items": { "type": "string" } },
        "phrase_end_resolution_degrees": { "type": "array", "items": { "type": "integer" } }
      }
    },
    "function_profiles": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "chord_tone": { "type": "number" },
          "color": { "type": "number" },
          "passing": { "type": "number" }
        },
        "required": ["chord_tone", "color", "passing"]
      }
    },
    "degree_weights": {
      "type": "object",
      "properties": {
        "chord_tone": { "type": "object", "additionalProperties": { "type": "number" } },
        "color": { "type": "object", "additionalProperties": { "type": "number" } },
        "passing": { "type": "object", "additionalProperties": { "type": "number" } }
      },
      "required": ["chord_tone", "color", "passing"]
    },
    "contour": {
      "type": "object",
      "properties": {
        "primary_shapes": { "type": "array", "items": { "type": "string" } },
        "max_leap_degrees": { "type": "integer" },
        "step_bias": { "type": "number" }
      }
    },
    "variation": {
      "type": "object",
      "required": ["rhythm_variation_strength", "pitch_variation_strength", "register_drift_per_phrase", "contour_inversion_prob", "transposition_choices"],
      "properties": {
        "rhythm_variation_strength": { "type": "number" },
        "pitch_variation_strength": { "type": "number" },
        "register_drift_per_phrase": { "type": "integer" },
        "contour_inversion_prob": { "type": "number" },
        "transposition_choices": { "type": "array", "items": { "type": "integer" } }
      }
    },
    "slot_preferences": {
      "type": "object",
      "properties": {
        "CALL": { "type": "object", "additionalProperties": { "type": "number" } },
        "RESP": { "type": "object", "additionalProperties": { "type": "number" } }
      },
      "required": ["CALL", "RESP"]
    },
    "bass_interaction": {
      "type": "object",
      "properties": {
        "avoid_unison_with_bass": { "type": "boolean" },
        "avoid_root_on_bass_hits": { "type": "boolean" },
        "min_semitone_distance_from_bass": { "type": "integer" }
      }
    }
  }
}
```

### A.2 `lead_rhythm_templates_v2.schema.json` (excerpt)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LeadRhythmTemplatesV2",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "role", "bars", "events", "max_step_jitter", "min_inter_note_gap_steps"],
    "properties": {
      "id": { "type": "string" },
      "role": { "type": "string", "enum": ["CALL", "RESP"] },
      "bars": { "type": "integer", "minimum": 1, "maximum": 8 },
      "events": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["step_offset", "length_steps", "accent"],
          "properties": {
            "step_offset": { "type": "integer" },
            "length_steps": { "type": "integer" },
            "accent": { "type": "number" },
            "anchor_type": { "type": "string", "enum": ["kick", "snare_zone", "hat", "offbeat", ""] }
          }
        }
      },
      "max_step_jitter": { "type": "integer" },
      "min_inter_note_gap_steps": { "type": "integer" }
    }
  }
}
```

### A.3 `lead_contour_templates_v2.schema.json` (excerpt)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LeadContourTemplatesV2",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "role", "degree_intervals", "emphasis_indices", "shape_type", "tension_profile"],
    "properties": {
      "id": { "type": "string" },
      "role": { "type": "string", "enum": ["CALL", "RESP"] },
      "degree_intervals": {
        "type": "array",
        "items": { "type": "integer" },
        "minItems": 1
      },
      "emphasis_indices": {
        "type": "array",
        "items": { "type": "integer" }
      },
      "shape_type": { "type": "string", "enum": ["arch", "ramp_up", "ramp_down", "zigzag", "flat"] },
      "tension_profile": {
        "type": "array",
        "items": { "type": "string", "enum": ["low", "medium", "high", "resolve"] }
      }
    }
  }
}
```

---

## 16) Appendix B — Example Config Files

### B.1 Example `lead_modes_v2.json` (three modes)

```json
[
  {
    "version": "v2",
    "id": "hypnotic_arp",
    "tags": ["hypnotic", "minimal"],
    "scale": { "scale_type": "dorian", "default_root_pc": 9, "allow_key_from_seed_tag": true },
    "register": { "low": 60, "high": 76, "gravity_center": 70 },
    "density": { "target_notes_per_bar": 10, "max_consecutive_notes": 8, "min_rest_per_bar_steps": 2 },
    "phrase": {
      "min_bars": 4, "max_bars": 4,
      "call_response_pattern": "CCCC",
      "phrase_forms": ["AAAA", "AAAB"],
      "phrase_end_resolution_degrees": [1, 5]
    },
    "function_profiles": {
      "CALL.start.strong": { "chord_tone": 0.9, "color": 0.1, "passing": 0.0 },
      "CALL.inner.weak":   { "chord_tone": 0.6, "color": 0.35, "passing": 0.05 },
      "CALL.end.strong":   { "chord_tone": 0.95, "color": 0.05, "passing": 0.0 }
    },
    "degree_weights": {
      "chord_tone": { "1": 0.45, "3": 0.3, "5": 0.2, "7": 0.05 },
      "color":      { "2": 0.35, "4": 0.2, "6": 0.35, "9": 0.1 },
      "passing":    { "2": 0.5, "4": 0.25, "6": 0.25 }
    },
    "contour": { "primary_shapes": ["ramp_up", "ramp_down", "zigzag"], "max_leap_degrees": 2, "step_bias": 0.8 },
    "variation": {
      "rhythm_variation_strength": 0.1,
      "pitch_variation_strength": 0.15,
      "register_drift_per_phrase": 2,
      "contour_inversion_prob": 0.05,
      "transposition_choices": [0, 2, -2]
    },
    "slot_preferences": {
      "CALL": { "hat": 1.0, "near_kick_post": 1.4, "snare_zone": 0.8, "bar_end": 0.7 }
    },
    "bass_interaction": { "avoid_unison_with_bass": true, "avoid_root_on_bass_hits": false, "min_semitone_distance_from_bass": 3 }
  },
  {
    "version": "v2",
    "id": "lyrical_cr",
    "tags": ["lyrical"],
    "scale": { "scale_type": "aeolian", "default_root_pc": 9, "allow_key_from_seed_tag": true },
    "register": { "low": 55, "high": 72, "gravity_center": 64 },
    "density": { "target_notes_per_bar": 6, "max_consecutive_notes": 4, "min_rest_per_bar_steps": 4 },
    "phrase": {
      "min_bars": 2, "max_bars": 4,
      "call_response_pattern": "CR",
      "phrase_forms": ["AA'B"],
      "phrase_end_resolution_degrees": [1, 5]
    },
    "function_profiles": {
      "CALL.start.strong": { "chord_tone": 0.7, "color": 0.3, "passing": 0.0 },
      "CALL.inner.weak":   { "chord_tone": 0.5, "color": 0.4, "passing": 0.1 },
      "CALL.end.strong":   { "chord_tone": 0.9, "color": 0.1, "passing": 0.0 },
      "RESP.start.strong": { "chord_tone": 0.6, "color": 0.35, "passing": 0.05 },
      "RESP.inner.weak":   { "chord_tone": 0.45, "color": 0.45, "passing": 0.1 },
      "RESP.end.strong":   { "chord_tone": 0.95, "color": 0.05, "passing": 0.0 }
    },
    "degree_weights": {
      "chord_tone": { "1": 0.35, "3": 0.35, "5": 0.2, "7": 0.1 },
      "color":      { "2": 0.25, "4": 0.3, "6": 0.3, "9": 0.15 },
      "passing":    { "2": 0.5, "4": 0.25, "6": 0.25 }
    },
    "contour": { "primary_shapes": ["arch", "ramp_up", "ramp_down"], "max_leap_degrees": 5, "step_bias": 0.6 },
    "variation": {
      "rhythm_variation_strength": 0.35,
      "pitch_variation_strength": 0.5,
      "register_drift_per_phrase": 3,
      "contour_inversion_prob": 0.25,
      "transposition_choices": [0, 2, -2, 3, -3]
    },
    "slot_preferences": {
      "CALL": { "near_kick_post": 1.5, "snare_zone": 1.2, "bar_end": 1.0 },
      "RESP": { "snare_zone": 1.6, "bar_end": 1.8, "near_kick_pre": 0.7 }
    },
    "bass_interaction": { "avoid_unison_with_bass": true, "avoid_root_on_bass_hits": true, "min_semitone_distance_from_bass": 4 }
  },
  {
    "version": "v2",
    "id": "rolling_arp",
    "tags": ["rolling"],
    "scale": { "scale_type": "phrygian", "default_root_pc": 5, "allow_key_from_seed_tag": true },
    "register": { "low": 60, "high": 78, "gravity_center": 69 },
    "density": { "target_notes_per_bar": 12, "max_consecutive_notes": 12, "min_rest_per_bar_steps": 0 },
    "phrase": {
      "min_bars": 2, "max_bars": 4,
      "call_response_pattern": "CRCR",
      "phrase_forms": ["ABAB"],
      "phrase_end_resolution_degrees": [1, 5]
    },
    "function_profiles": {
      "CALL.start.strong": { "chord_tone": 0.8, "color": 0.2, "passing": 0.0 },
      "CALL.inner.weak":   { "chord_tone": 0.55, "color": 0.3, "passing": 0.15 },
      "CALL.end.strong":   { "chord_tone": 0.9,  "color": 0.1, "passing": 0.0 },
      "RESP.start.strong": { "chord_tone": 0.75, "color": 0.2, "passing": 0.05 },
      "RESP.inner.weak":   { "chord_tone": 0.5,  "color": 0.3, "passing": 0.2 },
      "RESP.end.strong":   { "chord_tone": 0.9,  "color": 0.1, "passing": 0.0 }
    },
    "degree_weights": {
      "chord_tone": { "1": 0.4, "3": 0.3, "5": 0.2, "7": 0.1 },
      "color":      { "2": 0.3, "4": 0.2, "6": 0.3, "9": 0.2 },
      "passing":    { "2": 0.5, "4": 0.25, "6": 0.25 }
    },
    "contour": { "primary_shapes": ["zigzag", "flat"], "max_leap_degrees": 2, "step_bias": 0.85 },
    "variation": {
      "rhythm_variation_strength": 0.6,
      "pitch_variation_strength": 0.25,
      "register_drift_per_phrase": 1,
      "contour_inversion_prob": 0.1,
      "transposition_choices": [0, 2, -2]
    },
    "slot_preferences": {
      "CALL": { "near_kick_post": 1.6, "hat": 1.2, "snare_zone": 1.0, "bar_end": 0.8 },
      "RESP": { "near_kick_post": 1.6, "hat": 1.2, "snare_zone": 1.0, "bar_end": 0.8 }
    },
    "bass_interaction": { "avoid_unison_with_bass": true, "avoid_root_on_bass_hits": false, "min_semitone_distance_from_bass": 3 }
  }
]
```

### B.2 Example `lead_rhythm_templates_v2.json` (excerpt)

```json
[
  {
    "id": "rh_call_arch_2b_dense",
    "role": "CALL",
    "bars": 2,
    "events": [
      { "step_offset": 0,  "length_steps": 2, "accent": 0.9, "anchor_type": "kick" },
      { "step_offset": 3,  "length_steps": 1, "accent": 0.7, "anchor_type": "hat" },
      { "step_offset": 6,  "length_steps": 2, "accent": 0.7, "anchor_type": "hat" },
      { "step_offset": 12, "length_steps": 4, "accent": 1.0, "anchor_type": "snare_zone" },
      { "step_offset": 18, "length_steps": 1, "accent": 0.6, "anchor_type": "hat" },
      { "step_offset": 28, "length_steps": 2, "accent": 0.9, "anchor_type": "snare_zone" }
    ],
    "max_step_jitter": 1,
    "min_inter_note_gap_steps": 1
  },
  {
    "id": "rh_resp_arch_2b_sparse",
    "role": "RESP",
    "bars": 2,
    "events": [
      { "step_offset": 0,  "length_steps": 3, "accent": 0.9, "anchor_type": "kick" },
      { "step_offset": 5,  "length_steps": 1, "accent": 0.7, "anchor_type": "hat" },
      { "step_offset": 12, "length_steps": 4, "accent": 1.0, "anchor_type": "snare_zone" },
      { "step_offset": 26, "length_steps": 2, "accent": 0.8, "anchor_type": "bar_end" }
    ],
    "max_step_jitter": 1,
    "min_inter_note_gap_steps": 2
  }
]
```

### B.3 Example `lead_contour_templates_v2.json` (excerpt)

```json
[
  {
    "id": "ct_call_arch",
    "role": "CALL",
    "degree_intervals": [0, 2, 1, 2, -1, -2],
    "emphasis_indices": [3],
    "shape_type": "arch",
    "tension_profile": ["low", "medium", "medium", "high", "medium", "resolve"]
  },
  {
    "id": "ct_resp_mirror_arch",
    "role": "RESP",
    "degree_intervals": [0, -2, -1, -2, 1, 2],
    "emphasis_indices": [2],
    "shape_type": "ramp_down",
    "tension_profile": ["low", "medium", "medium", "high", "medium", "resolve"]
  }
]
```

---

## 17) Appendix C — Pseudocode

### C.1 `generate_lead_v2(...)`

```python
def generate_lead_v2(anchors, seed_metadata, bass_midi=None, mode_override=None, rng_seed=0):
    rng = make_rng(seed_metadata.seed_id, mode_override or auto_mode(seed_metadata.tags), rng_seed, "v2")

    mode = select_mode_v2(seed_metadata.tags, mode_override, rng)
    key = derive_keyspec(seed_metadata.tags, bass_midi, mode.scale)

    harmony = build_harmony_track(seed_metadata.bars, key, mode)
    phrase_plan = plan_phrases(seed_metadata.bars, mode.phrase, rng)

    motifs = []
    for phrase in phrase_plan:
        for segment in phrase.segments:
            rhythm_t = pick_rhythm_template(segment.role, phrase.length, rng)
            contour_t = pick_contour_template(segment.role, phrase.length, rng)
            motif = fuse_rhythm_contour(rhythm_t, contour_t, anchors, segment, rng)
            motifs.append(motif)

    logical_notes = []
    for motif in motifs:
        logical_notes += assign_functions_and_degrees(motif, mode, key, harmony, rng)

    events = []
    last_pitch = None
    for ln in logical_notes:
        pitch = map_degree_to_midi_with_voice_leading(ln, last_pitch, mode.register, key, rng)
        slot = align_to_slots(ln, anchors, mode.slot_preferences[ln.role], rng)
        event = realize_event(slot, pitch, ln, seed_metadata.ppq)
        events.append(event)
        last_pitch = pitch

    if bass_midi and mode.bass_interaction.get("avoid_unison_with_bass", False):
        events = apply_bass_interaction(events, bass_midi, mode.bass_interaction, key, rng)

    events = enforce_density_and_finalize(events, mode.density, key, rng)
    return sorted(events, key=lambda e: e.start_tick)
```

### C.2 Slot scoring (formula)

```python
score = (
    W_role_tag * sum(slot_pref.get(tag, 0.0) for tag in slot_tags) +
    W_anchor  * anchor_match(anchor_type, slot_tags) +
    W_strength * beat_strength_value(slot_tags) +
    W_density  * local_sparsity_bonus(neighbors) -
    W_overlap  * overlap_penalty(existing_events, candidate_time)
)
```

Weights per mode or sensible defaults: `W_role_tag=1.0`, `W_anchor=0.6`, `W_strength=0.5`, `W_density=0.3`, `W_overlap=2.0`.

---

## 18) Appendix D — Example PyTest Suite

```python
# tests/test_lead_v2_theory.py

def test_keyspec_degree_to_pitch():
    key = KeySpec(root_pc=9, scale_type="aeolian", default_root_octave=4)
    assert degree_to_pc(key, 1) == (9 % 12)
    assert is_in_scale(key, midi_pitch=69)  # A4 in aeolian

def test_phrase_planner_roles_cover_bars(seed_meta_fixture, mode_fixture):
    plan = plan_phrases(seed_meta_fixture.bars, mode_fixture.phrase, rng_with_seed(123))
    assert cover_all_bars(plan, seed_meta_fixture.bars)
    assert valid_role_sequence(plan, mode_fixture.phrase.call_response_pattern)

def test_function_distribution_strong_beats(golden_seed, mode_lyrical):
    notes = generate_lead_v2(golden_seed.anchors, golden_seed.meta, mode_override="lyrical_cr", rng_seed=42)
    dist = distribution_by_context(notes, context="*.start.strong")
    assert dist["chord_tone"] >= 0.65

def test_phrase_end_resolves_to_1_or_5(golden_seed, mode_any):
    notes = generate_lead_v2(golden_seed.anchors, golden_seed.meta, rng_seed=42)
    for phrase_end in find_phrase_end_notes(notes):
        assert degree_of(phrase_end) in {1, 5}

def test_register_bounds_and_leap_size(golden_seed, mode_hypnotic):
    notes = generate_lead_v2(golden_seed.anchors, golden_seed.meta, mode_override="hypnotic_arp", rng_seed=7)
    assert all(mode_hypnotic.register.low <= n.pitch <= mode_hypnotic.register.high for n in notes)
    assert average_semitone_jump(notes) <= 5

def test_bass_interaction_distance(bass_seed, mode_rolling):
    notes = generate_lead_v2(bass_seed.anchors, bass_seed.meta, bass_midi=bass_seed.bass, mode_override="rolling_arp", rng_seed=9)
    assert min_distance_to_bass(notes, bass_seed.bass) >= mode_rolling.bass_interaction.min_semitone_distance_from_bass

def test_determinism(golden_seed, mode_lyrical):
    n1 = generate_lead_v2(golden_seed.anchors, golden_seed.meta, rng_seed=111)
    n2 = generate_lead_v2(golden_seed.anchors, golden_seed.meta, rng_seed=111)
    assert serialize(n1) == serialize(n2)
```

---

## 19) Appendix E — Mode Personalities Reference

### Hypnotic Arp Lead
- Long phrases, repetition with subtle evolution.  
- Chord‑tone heavy on strong beats; low variation; slow register drift; dorian/aeolian.  
- Density ~10 notes/bar; narrow contour amplitude.

### Lyrical Call/Response Lead
- Clear arcs; expressive leaps allowed; strong resolutions at phrase ends.  
- Medium density; rests used for contrast; `CR` or `CRCR`.  
- Color tones on inner/weak beats; call rising, response mirroring or transposed.

### Rolling Arp Lead
- Rhythmic propulsion; many short notes; minor contour shifts.  
- High density; strong coupling to kick/hat; frequent small passing tones on weak beats.  
- Phrygian flavor for darker timbre.

---

## 20) Definition of Done Checklists

### Feature DoD
- [ ] v2 configs load & validate; default modes available.  
- [ ] `generate_lead_v2` produces deterministic MIDI with fixed seed.  
- [ ] Notes are in key/scale; phrase ends resolve to 1 or 5.  
- [ ] CALL/RESP structure present and recognizable in timing & pitch.  
- [ ] Register bounds respected; average leaps within mode.  
- [ ] Density & min gaps enforced; no overlaps; durations valid.  
- [ ] Slot alignment honors role preferences and anchors.  
- [ ] (If enabled) Bass interaction constraints satisfied.

### Testing/CI DoD
- [ ] Unit tests for theory components & planners.  
- [ ] Structural/golden seed tests with thresholds.  
- [ ] Determinism tests stable across platforms.  
- [ ] Test reports in CI; flake8/black (optional).

### Ops DoD
- [ ] CLI defaults to v2 with `--use-v1` escape hatch.  
- [ ] Assets written to `leads/variants/lead_<mode>_v2.mid`; `metadata.json` updated.  
- [ ] Docs & examples accessible; debug CSV enabled with flag.


---

**End of Roadmap**  
**File version:** 1.0 (Lead Generator v2 Roadmap)  
**Owner:** Beatengine Leads Working Group

