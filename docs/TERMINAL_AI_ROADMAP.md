# Terminal AI Front End — Deep‑Dive Roadmap

Status: Draft v0.1
Owner: you

## 0) Purpose & Outcome

Build a single‑terminal app (REPL) that:
- Accepts natural‑language requests to generate techno MIDI patterns and manage configs.
- Uses OpenAI API behind a strict, sandboxed tool layer (no arbitrary code exec).
- Can perform agentic tasks (create files, render .mid, adapt follow‑ups) only inside the project domain.
- Stays focused: refuses off‑domain tasks; returns concise summaries and file paths.

Deliverable: `techno` terminal app (or `python -m techno_engine.terminal`) + tests + docs.

---

## 1) High‑Level Architecture

- REPL (stdin/stdout) → Orchestrator → OpenAI (Chat Completions w/ function/tool calling)
- Tool Layer (sandbox):
  - render_session(config_path | inline_config) → `.mid`
  - render_phrase(style, options) → `.mid`
  - create_config/list_configs/read_config/write_config
  - list_examples
  - help/usage
- Filesystem sandbox: allowlist `configs/`, `out/` only; never navigate above CWD.
- Validation: Pydantic/JSONSchema; clamp and default out‑of‑range values.

---

## 2) Guardrails & Constraints

- The model can only act via registered tools (function calling). No shell, no HTTP, no code.
- System prompt explicitly forbids off‑domain tasks and free‑form execution.
- All tool inputs validated and clamped to musical ranges (BPM, bars, swing, thin_bias, density, ratchets, etc.).
- All writes restricted to `configs/` and `out/`.
- The terminal prints only concise summaries + paths (no model internals).

---

## 3) Tools (Allowed Actions)

Each tool defines a strict input schema and output envelope.

1) render_session
- Input: `{ config_path?: string, inline_config?: EngineConfigSubset }`
- Output: `{ path: string, bpm: number, bars: number, summary: string }`
- Notes: If both `config_path` and `inline_config` are present, prefer `config_path`. Renderer writes to `out/uuid.mid`.

2) render_phrase
- Input: `{ style: "urgent"|"polymeter"|"hard-evolving"|"breakdown", bpm?: number, bars?: number, seed?: number }`
- Output: `{ path: string, summary: string }`
- Notes: Routes to curated phrase generators (e.g., evolving_hard_64), clamped.

3) create_config
- Input: `{ name: string, params: EngineConfigSubset }`
- Output: `{ path: string }`
- Notes: Writes `configs/<safe_name>.json` (fail if traversal or exists unless `overwrite: true`).

4) read_config
- Input: `{ name: string }`
- Output: `{ path: string, body: string }`

5) write_config
- Input: `{ name: string, body: string }` (must be valid JSON)
- Output: `{ path: string }`

6) list_configs
- Input: `{}`
- Output: `{ items: string[] }` (relative paths under `configs/`)

7) list_examples
- Input: `{}`
- Output: `{ items: string[] }` (predefined examples)

8) help
- Input: `{ topic?: string }`
- Output: `{ usage: string }`

EngineConfigSubset: subset of your existing schema with safe fields only (bpm, bars, targets, thin_bias, swing_percent, ratchet_prob, offbeats_only, density, allowed modulators).

---

## 4) Prompts & Policies

System message (template):
"""
You are Techno Assistant, a terminal‑only helper for generating techno MIDI via strict tools.
- Stay in domain: groove generation, configs, rendering, and usage help.
- Use tools only. Never run code/shell or browse. If asked off‑domain, refuse politely and suggest a domain action.
- When acting, prefer the simplest tool path. When replying, keep it concise and return file paths.
"""

Developer message (tool spec): concise JSON schemas + examples (kept in code).

User message: the natural‑language prompt.

---

## 5) Milestones (Development Plan)

Progress Checklist (by milestone)
- [ ] M0 — Skeleton & Local Commands
- [ ] M1 — Tool Layer + Sandbox
- [ ] M2 — Orchestrator & Function Calling (mocked LLM)
- [ ] M3 — OpenAI Integration
- [ ] M4 — Phrase Generators & Summaries
- [ ] M5 — UX Polish & Session State
- [ ] M6 — Packaging & One‑liner
- [ ] M7 — CI & Release

M0 — Skeleton & Local Commands
- Files:
  - `src/techno_engine/terminal/app.py` (REPL: `techno> `, `:help`, `:quit`)
  - `src/techno_engine/terminal/settings.py` (loads `OPENAI_API_KEY`, model)
- Behavior: Local help/about; no LLM calls yet.
- Checklist:
  - [ ] Create REPL prompt with local `:help`, `:quit`, `:about`
  - [ ] Settings loader for `OPENAI_API_KEY` and model defaults
  - [ ] Graceful shutdown and error messages
  - [ ] Unit tests implemented (see below)
- Unit tests:
  - [ ] REPL parses `:help` and prints usage
  - [ ] `:quit` exits cleanly (status 0)
  - [ ] No LLM dependency in M0 tests

M1 — Tool Layer + Sandbox
- Files:
  - `src/techno_engine/terminal/tools.py` (implement functions)
  - `src/techno_engine/terminal/fs_sandbox.py` (safe path join; block traversal)
  - `src/techno_engine/terminal/schemas.py` (Pydantic models)
- Tools implemented: render_session, create/list/read/write config, list_examples, help.
- Clamp ranges inside validation.
- Checklist:
  - [ ] Implement `tools.py` functions with Pydantic validation
  - [ ] Implement `fs_sandbox.py` safe path join/block traversal
  - [ ] Implement `schemas.py` (EngineConfigSubset, tool inputs)
  - [ ] Unit tests implemented (see below)
- Unit tests:
  - [ ] Writes happen only under `configs/` and `out/`
  - [ ] render_session with inline config → `.mid` created
  - [ ] create_config writes file; invalid JSON rejected
  - [ ] list_configs/list_examples return expected items

M2 — Orchestrator & Function Calling (mocked LLM)
- Files:
  - `src/techno_engine/terminal/orchestrator.py` (message loop; tool registry; retries)
  - `src/techno_engine/terminal/ai_client.py` (interface; mockable)
- Behavior: Given a user input, orchestrator asks LLM; executes returned tool calls; short final reply.
- Checklist:
  - [ ] Orchestrator routes prompts → LLM → tool calls → final reply
  - [ ] AI client mock with function-calling shim
  - [ ] Retry on tool validation errors (bounded attempts)
  - [ ] Unit tests implemented (see below)
- Unit tests (mocked LLM):
  - [ ] “make an urgent 64‑bar groove” → render_phrase called; returns `.mid` path
  - [ ] Off‑domain request → polite refusal + help text
  - [ ] Invalid tool args → model retries with corrected args

M3 — OpenAI Integration
- Implement real Chat Completions with tool calling.
- Secrets: `OPENAI_API_KEY` via environment variable; no logs of secrets.
- Timeouts and backoff.
- Checklist:
  - [ ] Wire OpenAI Chat Completions with tool calling
  - [ ] Add timeouts and exponential backoff
  - [ ] Feature flag for network tests
  - [ ] Unit/integration tests implemented (see below)
- Tests:
  - [ ] Mocked tests remain green
  - [ ] Optional network smoke (skipped in CI by default)

M4 — Phrase Generators & Summaries
- Expose `render_phrase` styles (e.g., hard‑evolving, urgent) with clamped options.
- Server‑side summary (no model internals): BPM, bars, a few high‑level adjectives.
- Checklist:
  - [ ] Implement `render_phrase` styles and clamps
  - [ ] Add summary generator (bpm/bars/adjectives)
  - [ ] Unit tests implemented (see below)
- Unit tests:
  - [ ] `render_phrase` returns `.mid`
  - [ ] Phrase length matches bars; summary mentions style + bpm

M5 — UX Polish & Session State
- Add `:seed`, `:bpm`, `:bars` commands to set defaults; tools automatically inherit.
- Add `:history` (last N actions) and `:paths` (show output folder).
- Trim outputs to paths + one‑liners.
- Checklist:
  - [ ] Session defaults store & retrieval
  - [ ] `:history` and `:paths` commands
  - [ ] Consistent one‑line summaries
  - [ ] Unit tests implemented (see below)
- Unit tests:
  - [ ] Changes to defaults persist across multiple requests
  - [ ] History shows recent tool calls; paths list output dir(s)

M6 — Packaging & One‑liner
- `entry_points` console script (`techno`).
- README section with one‑liner to start the REPL.
- Checklist:
  - [ ] Add console script entry point `techno`
  - [ ] Update README with “Terminal AI” and examples
  - [ ] Unit tests implemented (see below)
- Tests:
  - [ ] Smoke: run `techno`, request an example, `.mid` created

M7 (Optional) — CI & Release
- CI job that runs unit tests and a mocked orchestrator test; optional macOS smoke job.
- Tag a release and publish instructions.
- Checklist:
  - [ ] CI runs unit tests (mocked LLM)
  - [ ] Optional macOS smoke job for REPL + tool call
  - [ ] Tag and publish release; include bootstrap instructions

---

## 6) Implementation Details

Tool I/O Schemas (examples):

render_session (input)
```json
{
  "config_path": "configs/m4_showcase.json"
}
```
render_session (output)
```json
{
  "path": "out/1b2c.mid",
  "bpm": 132,
  "bars": 64,
  "summary": "132 BPM, 64 bars; denser hats with OH ratchets"
}
```

render_phrase (input)
```json
{ "style": "hard-evolving", "bpm": 132, "bars": 64, "seed": 4242 }
```

create_config (input)
```json
{ "name": "urgent_64.json", "params": { "mode": "m4", "bpm": 132, "bars": 64 } }
```

EngineConfigSubset (suggested keys):
- mode: "m4"
- bpm [110..150], bars [8..128], ppq fixed 1920
- targets { S_low [0..1], S_high [0..1], hat_density_target [0.3..0.95], hat_density_tol [0..0.2] }
- layers (kick, hat_c, hat_o, snare, clap): steps/fills/rot, swing_percent [0.5..0.58], ratchet_prob [0..0.3], offbeats_only, beat_bins (bins + probs), density targets, allowed conditions (PROB, PRE, FILL, EVERY_N)
- modulators: param_path in { "thin_bias", "hat_c.swing_percent", "hat_o.ratchet_prob", "accent.prob" }, bounded min/max and `max_delta_per_bar`.

---

## 7) Testing Strategy

Unit tests
- `tests/terminal/test_tools.py`: filesystem sandbox, render/create/list/read/write config, clamping.
- `tests/terminal/test_repl.py`: REPL local commands (help/quit/history/state).
- `tests/terminal/test_orchestrator.py`: mock LLM → tool call → successful `.mid` and summary.
- `tests/terminal/test_guardrails.py`: off‑domain request yields refusal + usage.

Integration tests (mocked LLM)
- End‑to‑end session: “urgent 64‑bar with crash lifts” → `.mid` generated; summary includes BPM/bars.

Manual smoke
- Real OpenAI key: start REPL, request a phrase; inspect `.mid` in `out/`.

Acceptance criteria
- Tool layer never writes outside `configs/`, `out/`.
- Off‑domain requests are refused with a helpful domain alternative.
- Reasonable time to render (under ~2s for M4 session on a typical machine).
- Short responses with paths; no internal stack traces or secrets.

---

## 8) Security & Privacy

- Keep `OPENAI_API_KEY` in env only; never echo to console.
- Avoid logging prompts or responses that may contain sensitive info.
- Consider optional redacted transcript logging (opt‑in).

---

## 9) Work Plan (What to Implement First)

1. Create `src/techno_engine/terminal/` with `app.py`, `tools.py`, `schemas.py`, `fs_sandbox.py`, `orchestrator.py`, `ai_client.py`, `settings.py`.
2. Implement tools (local functions) using existing renderers (controller + phrase variants).
3. Implement REPL and local commands; write unit tests for tools + REPL.
4. Add orchestrator with mocked LLM; tests for tool calling.
5. Wire OpenAI client + function calling; smoke test with real key.
6. Add console script entry point `techno`; README update.

---

## 10) Examples (Expected UX)

```
$ techno
techno> make an urgent 64-bar pattern with crash lifts
✔ rendered out/3a9e.mid  | 132 BPM, 64 bars. Urgent hats + OH ratchets; phrase crashes.

techno> save this as configs/urgent_64.json
✔ wrote configs/urgent_64.json

techno> render configs/urgent_64.json
✔ rendered out/5b11.mid | 132 BPM, 64 bars.

techno> help
Usage:
 - “make a 64-bar groove at 132 bpm with crash lifts”
 - “save this as configs/name.json”
 - “render configs/name.json”
 - :seed 4242 | :bpm 132 | :bars 64 | :quit
```

---

## 11) Risks & Mitigations

- LLM emits non‑JSON tool call → Reject; feed error back; retry limited times.
- Prompt injection off‑domain → System prompt + strict tool set; refuse.
- Large configs → Keep subsets; default PPQ=1920; clamp ranges.
- Performance → Keep rendering pure‑Python; avoid heavy IO; show concise output only.

---

## 12) Done Criteria

- REPL operates end‑to‑end with real LLM → tool calls → `.mid` outputs.
- Domain lock verified by tests; no writes outside sandbox.
- README documents how to start and an example flow.
