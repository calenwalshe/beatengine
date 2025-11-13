# LLM Prompt Demo Library

This library lists ready-to-run prompts (and the shell commands behind them) that an
LLM agent or human can issue to showcase the Techno Rhythm Engine in realistic
scenarios. Each entry ships with the exact context an agent should cite, so the
assistant can answer “demo” requests without improvising new plans.

## How to Use

- During boot, agents should ingest this file and surface the available `key` names as options to the user (e.g., “try `energy_gradient` for a full tension arc”).
- When responding to a user who asks for “test prompts”, return the matching `prompt` text and execute the `run` command verbatim, adding overrides only if the user specifies them.
- Humans can also copy/paste the commands below; all paths are relative to the repo root.

## Demo Catalog

| Key | Prompt snippet | What it demonstrates | How to run |
| --- | -------------- | -------------------- | ---------- |
| `metronome_baseline` | “Render the baseline M0 metronome so I can confirm latency.” | Minimal 4-on-the-floor grid; verifies CLI wiring and PPQ timing. | `python -m techno_engine.cli --config configs/m0_metronome.json` |
| `bass_for_config` | “Make bass for configs/m4_95bpm.json in A minor with density 0.4.” | Full combo CLI path (drums+bass) plus scoring metrics. | `PYTHONPATH=src python -m techno_engine.combo_cli --drum configs/m4_95bpm.json --drum_out out/m4_95bpm_drums.mid --bass_out out/m4_95bpm_bass.mid --key A --mode minor --density 0.4` |
| `energy_gradient` | “Create an 8-file 135 BPM energy-gradient drum pack I can audition.” | Generates eight MIDI grooves that sweep up/down in energy, including the latest build-up you requested. | `PYTHONPATH=src python scripts/make_energy_gradient_pack.py --out_dir out/energy_gradient --bars 2 --bpm 135` |

## Energy Gradient Details

- Output location: defaults to `out/energy_gradient/`, including a `manifest.json` describing each variation (`energy01_intro_base` through `energy08_outro_soft`).
- Files are two bars long so the open-hat pickup on every second bar always lands on step 16; adjust `--bars` to extend phrases (must stay ≥2).
- The generator script intentionally uses only deterministic building blocks (no randomness), so repeated runs are identical—ideal for tests or demo playback.

## Extending the Library

1. Add a new row to the catalog with a unique `key` and the exact input prompt the agent should recognize.
2. Provide a deterministic command or script path so agents can execute it without extra reasoning.
3. Reference the new key in `README.md` (see “LLM Prompt Demo Library” section) so the feature remains visible to both humans and agents at startup.
