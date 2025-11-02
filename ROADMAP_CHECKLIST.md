# Roadmap Checklist & Change Tracking

Purpose: Track progress against the roadmap and record any changes made to the roadmap content itself. Use alongside `roadmap`.

Status fields use GitHub-style checkboxes. Update incrementally as work proceeds and whenever editing the roadmap.

---

## Progress by Milestone

### M0 — Skeleton & I/O
- [x] Spec captured in roadmap (M0)
- [x] Tests specified (PPQ, tempo, ms→ticks, metronome)
- [x] Implementation scaffolding in repo
- [x] MIDI writer (abs→sorted→delta) passes checks
- [ ] Docs updated (usage + assumptions)

### M1 — Deterministic Backbone
- [ ] Spec captured in roadmap (M1)
- [ ] Tests specified (kick 4/4, hat-c 16ths, snare backbeat, E/S bounds)
- [ ] Backbone implemented
- [ ] Tests implemented and passing
- [ ] Docs updated

### M2 — Parametric Engine + Micro + Choke + Polymeter
- [ ] Spec captured in roadmap (M2)
- [ ] Tests specified (swing ticks, beat-bins bins/caps, choke, dispersion)
- [ ] Features implemented (euclid+rotation, ratchets, choke, micro)
- [ ] Tests implemented and passing
- [ ] Docs updated

### M3 — Conditions, Constraints & Density
- [ ] Spec captured in roadmap (M3)
- [ ] Tests specified (EVERY_N, mute-near-kick, density clamp, thinning)
- [ ] Features implemented
- [ ] Tests implemented and passing
- [ ] Docs updated

### M4 — Scoring, Feedback, Modulators & Guardrails
- [ ] Spec captured in roadmap (M4)
- [ ] Tests specified (S band, E target, T_ms caps, continuity, rescue)
- [ ] Features implemented (metrics, feedback, modulators, guards)
- [ ] Tests implemented and passing
- [ ] Docs updated

---

## Section-Level Review Checklist (Roadmap A–L)

For each section below, mark Reviewed when verified, and log changes in the Change Log.

- [ ] A. Aesthetic Principles → Engineering Encodings (A.1–A.5)
- [ ] B. System Architecture (data flow)
- [ ] C. Data Model (dataclasses)
- [ ] D. Core Algorithms (D.1–D.9)
- [ ] E. Scoring & Controller
- [ ] F. Config Schema
- [ ] G. MIDI Backend & Mapping
- [ ] H. Milestones & Tests
- [ ] I. Pseudocode Stubs & Signatures
- [ ] J. Example Config
- [ ] K. Development Checklist
- [ ] L. Implementation Tips

---

## Roadmap Change Log

Record every substantive roadmap change here. Use IDs like `RM-YYYYMMDD-##`.

| Change ID | Date (YYYY-MM-DD) | Author | Section(s) | Summary | Impact | Link (PR/Commit) |
|---|---|---|---|---|---|---|
| RM- |  |  |  |  |  |  |

Guidance:
- Section(s): e.g., `C`, `D.2`, `H (M2 tests)`
- Impact: doc-only, tests-updated, API-change, algorithm-change, targets-adjusted

---

## Version & Metadata

- Current roadmap version: v0.1.0
- Source file: `roadmap`
- Last reviewed by: __________
- Next review due: __________

Versioning rules:
- Bump patch for doc-only clarifications without changing tests/spec.
- Bump minor when specs/tests change but API remains stable.
- Bump major on breaking API or aesthetic guardrail changes.

---

## Review Cadence & Owners

- Weekly: Section H (milestones/tests) and active milestone section.
- Biweekly: Sections C, D, E (schemas/algorithms/metrics) for drift.
- Owners:
  - Roadmap steward: __________
  - Test lead: __________
  - MIDI/backend: __________
  - Aesthetics/UX: __________

---

## Open Questions (to resolve before M1)

- [ ] Finalize PPQ default (1920 vs configurable in config files) and tolerance for ms→ticks.
- [ ] Decide single vs multi-track MIDI layout for metronome and voices.
- [ ] Confirm target ranges (S, H) and enforcement horizon (bars window).
