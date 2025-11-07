# Techno Rhythm Engine — Architecture

Status: November 2025

This document explains how the system is designed and how the major parts work together: the core generative engine and the Terminal AI front end. It complements the detailed specs in `roadmap` and the step-by-step `docs/TERMINAL_AI_ROADMAP.md`.

## Overview

- Core Engine (M0–M4): Pure‑Python MIDI pattern generator that writes `.mid` files.
- Terminal AI Front End: A terminal REPL that uses OpenAI tool‑calling to invoke a safe, sandboxed set of local tools (render session, config CRUD, etc.).

Key properties
- High‑resolution timebase (PPQ 1920), absolute‑tick scheduling, then delta encoding.
- Aesthetics guardrails encoded as metrics and modulators; slow‑changing parameters for continuity.
- Strict filesystem sandbox for tool writes (`configs/`, `out/` only).

## Engine Architecture

Modules (core engine)
- Timebase and MIDI
  - `src/techno_engine/timebase.py`: tick math utilities.
  - `src/techno_engine/midi_writer.py`: absolute tick scheduling → sort → delta encode → `.mid` save.
- Backbones & Layers
  - `src/techno_engine/backbone.py`: deterministic M1 backbone.
  - `src/techno_engine/parametric.py`: Euclid+rotation, swing, beat‑bins, ratchets, choke.
  - `src/techno_engine/euclid.py`: Bjorklund masks + rotation.
  - `src/techno_engine/micro.py`: swing and microtiming sampling/caps.
  - `src/techno_engine/conditions.py`: PROB, PRE/NOT_PRE, FILL, EVERY_N step gating.
  - `src/techno_engine/density.py`: density clamp and void bias.
  - `src/techno_engine/accent.py`: accents post‑schedule.
- Scoring & Control (M4)
  - `src/techno_engine/scores.py`: E,S,D,H,T metrics and helpers.
  - `src/techno_engine/markov.py`: sync‑biased probability updates, sampling.
  - `src/techno_engine/modulate.py`: long‑horizon modulators with continuity caps.
  - `src/techno_engine/controller.py`: M4 session runner (feedback loop, guardrails, logging).
- Config & CLI
  - `src/techno_engine/config.py`: JSON → `EngineConfig` (m1/m2/m4) including layers, targets, guard, modulators.
  - `src/techno_engine/run_config.py`: CLI to render from config.
  - `configs/`: ready‑to‑run configs (e.g., `configs/m4_showcase.json`).

Data flow (per render)
1) Parse config (`src/techno_engine/config.py`).
2) For M1: build deterministic backbone. For M2/M4: per layer compute mask → apply conditions → schedule microtimed events; for M4 also run feedback/modulators/guard per bar (`src/techno_engine/controller.py`).
3) Collect events per layer → single list of absolute tick messages.
4) `src/techno_engine/midi_writer.py`: sort by `(time, note_off before note_on)`, delta‑encode, write `.mid`.

Algorithmic highlights
- Euclid + rotation drift: slow float accumulator rounded to int per bar.
- Swing + beat‑bins: micro offsets sampled from bins, capped per layer; swing applied on odd steps.
- Density clamp: adjust masks to meet target±tol while respecting metric weights.
- Markov sync bias: update per‑step probabilities to favor entrained positions.
- Guardrails: continuity caps on parameter deltas; rescue behavior when E dips below threshold.

Testing
- 40+ tests cover timebase, backbone, parametric features, conditions stack, kick variation, scoring/control, modulators, CLI/config, logging.
- See `tests/` (e.g., `tests/test_m2_parametric.py`, `tests/test_m4_control.py`).

## Terminal AI Front End

Modules
- REPL and settings
- `src/techno_engine/terminal/app.py`: `TerminalApp` (`:help`, `:about`, `:quit`), REPL loop. If no key is present it falls back to the offline agent workflow rather than blocking the user.
  - `src/techno_engine/terminal/settings.py`: loads `OPENAI_API_KEY` from env or `.env`.
- Orchestrator & client
  - `src/techno_engine/terminal/orchestrator.py`: message loop; tool registry; retries; tool result wiring.
  - `src/techno_engine/terminal/ai_client.py`: abstract client.
  - `src/techno_engine/terminal/ai_openai.py`: HTTP client using Chat Completions with function/tool calling.
- Tool layer & sandbox
  - `src/techno_engine/terminal/tools.py`: tool implementations (render_session, create/list/read/write config, list_examples, help_text).
  - `src/techno_engine/terminal/schemas.py`: input/output dataclasses and validation/clamping subset.
  - `src/techno_engine/terminal/fs_sandbox.py`: `safe_join` and base dirs (`TECH_ENGINE_CONFIGS_DIR`, `TECH_ENGINE_OUT_DIR`).
  - `tools.agent_handle`: heuristic agent that expands style presets, applies prompt-driven overrides (ghost probability, BPM/bars, rotation) and saves MIDI + JSON artifacts for offline use.

Tool calling protocol
- Requests: Chat Completions with `tools` (JSON Schema per function) and `OpenAI-Beta: tools=true` header (`src/techno_engine/terminal/ai_openai.py:41`).
- Tool call handling:
  - Read `message.tool_calls[0]` → extract `function.name` and JSON `arguments`.
  - Orchestrator mirrors an assistant message with `tool_calls` (id, name, arguments), then posts the tool’s JSON result as a `role: tool` message with `tool_call_id` (`src/techno_engine/terminal/orchestrator.py:103`).
  - The next assistant message (final text) summarizes and returns a short path.
  - Available tools now include `doc_answer` (documentation QA) and `agent_handle` (offline rendering) in addition to config CRUD and `render_session`.

Error handling & robustness
- TLS: uses `certifi` bundle when available (`src/techno_engine/terminal/ai_openai.py:51`).
- HTTP errors: surface status + returned JSON in text for easier debugging (`src/techno_engine/terminal/ai_openai.py:56`).
- Schema: explicit JSON Schemas per tool to reduce 400s and help the model craft valid calls (`src/techno_engine/terminal/orchestrator.py:51`).
- Sandbox: all file writes go through `ensure_dirs` + `safe_join`, preventing traversal (`src/techno_engine/terminal/fs_sandbox.py:22`).

Security & privacy
- No secrets in code. The app reads `OPENAI_API_KEY` from the environment or `.env` (if present). It never prints it.
- The tool layer restricts all writes to `configs/` and `out/` (or env‑configured base dirs).
- The REPL refuses off‑domain actions; only registered tools are available.

Usage
- With key (recommended):
  - `source .venv/bin/activate && export OPENAI_API_KEY='…' && PYTHONPATH=src python -m techno_engine.terminal.app`
  - Prompt: ask “make an 8‑bar groove at 140 bpm” → model calls `render_session` → `.mid` path.
- Without key: the offline agent interprets the prompt, renders a groove (style heuristics, ghost kick tuning, BPM/bars parsing), and returns the MIDI/config paths.

Extensibility
- Add a new tool: define input/output schema in `schemas.py`, implement in `tools.py`, register schema in orchestrator’s `_tool_specs()`.
- Add a phrase generator: implement a helper (e.g., curated M4 params), expose a `render_phrase` tool with a bounded schema, and add tests.
- Offline agent: extend `tools.agent_handle` to recognise new styles or config tweaks; register an accompanying tool schema if you want the LLM to trigger it as well.

Known limitations
- Function/tool calling details are model/version dependent; the client sets `OpenAI-Beta: tools=true` to enable the feature consistently.
- The orchestrator currently executes one tool call per turn; complex multi‑tool plans would require iterative routing.

## References

- Engine specs & milestones: `roadmap` (e.g., Section H: tests), and `ROADMAP_CHECKLIST.md`.
- Terminal AI deep dive: `docs/TERMINAL_AI_ROADMAP.md`.
- Entry points and examples:
  - Render from config: `src/techno_engine/run_config.py:1`
  - Terminal REPL: `src/techno_engine/terminal/app.py:1`
  - Orchestrator: `src/techno_engine/terminal/orchestrator.py:23`
  - OpenAI client: `src/techno_engine/terminal/ai_openai.py:18`
