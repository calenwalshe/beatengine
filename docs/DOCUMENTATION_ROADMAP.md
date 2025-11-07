# Documentation Roadmap (Human + Agent)

## Goals
- Human-readable, Unix-style man pages for each primary CLI.
- Agent-facing, tool-first spec that precisely defines contracts, planning templates, and guardrails.

## Deliverables (Two Tracks)

### A) Man Pages (Human)
- docs/techno.1 — Terminal assistant usage
- docs/techno-combo.1 — Drums + bass CLI (combo_cli)
- docs/techno-showcase.1 — Showcase CLI (scenarios, filters, artifacts)
- docs/techno-bass.1 — Bass MVP CLI (if publicly exposed)

Each page includes: NAME, SYNOPSIS, DESCRIPTION, OPTIONS, EXAMPLES, FILES, ENVIRONMENT, EXIT STATUS, SEE ALSO

### B) Agent-Facing Spec (Machine-Oriented)
- docs/AGENT_API.md — Tool list + JSON args/returns + errors (VERSION_MISMATCH, BAD_CONFIG)
- docs/AGENT_CHEATSHEETS/PARAM_EFFECTS.md — NL→param mapping + ranges/clamping
- docs/AGENT_CHEATSHEETS/PLANNING_TEMPLATES.md — one-shot and multi-step plans
- docs/AGENT_CHEATSHEETS/CONFIG_SCHEMA.md — dot-paths (kick.*, hat_c.*, targets.*)
- docs/AGENT_CHEATSHEETS/METRICS.md — E/S definitions, bands, corrections
- docs/AGENT_CHEATSHEETS/MOTIFS_PHRASES.md — preset motifs/phrases with bar-level expectations
- (Optional) docs/SCHEMAS/*.json — JSON schemas for tool inputs/outputs

## Milestones

1) Audit & Structure
- Inventory current docs (README, SHOWCASE, BASSLINE_API, techno.1)
- Draft DOCS_INDEX.md, skeleton man pages
- Tests: link existence checks; presence of NAME/SYNOPSIS in each man page

2) Man Pages v1
- Flesh out OPTIONS/EXAMPLES for combo/showcase/bass
- Tests: parse SYNOPSIS/OPTIONS presence; groff smoke build optional

3) Agent Spec v1 (Tools + Contracts)
- AGENT_API.md: `render_session`, `bass_generate`, `bass_validate`, `make_bass_for_config`
- Cheatsheets for param effects, planning templates
- Tests: docs snippet executor runs tool demos in temp dirs

4) Knowledge Capsules
- CONFIG_SCHEMA, METRICS, MOTIFS_PHRASES
- Tests: snippet presence + quick assertions (strings/ranges)

5) Showcase Docs & HTML
- Ensure SHOWCASE.md covers filters/artifacts; HTML already styled
- Tests: manifest JSON has generated_at, scenarios; HTML header checks

6) CI / Build Targets
- Makefile targets `docs-build`, `docs-test` (optional)
- CI runs snippet executor and link checks

## Current Status
- Showcase and combo CLI documented in README + SHOWCASE.md
- One-shot terminal tool documented with runnable snippets
- HTML index + JSON manifest (with metadata) implemented and tested

## Remaining (P0)
- P0: Build and publish the man pages + Agent API v1 + cheatsheets
- P1: Optional JSON Schema files + CI make targets
- P2: Extra HTML niceties (audio hooks) and screenshots for README

## Acceptance Criteria
- All man pages present and render via groff without errors
- AGENT_API.md and cheatsheets contain runnable snippets that pass tests
- docs-test target (snippet executor + link checks) passes in CI

