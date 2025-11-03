# Techno Rhythm Engine — Berlin-Style Roadmap Build

This repository is an implementation of the "Berlin-Style Techno MIDI Engine" roadmap. It generates hypnotic Berlin/Berghain-style techno loops with high-resolution PPQ, microtiming guardrails, long-horizon feedback, and configurable probabilities.

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt  # if applicable
pytest -q                         # run unit tests (32 currently)

# Render from a JSON config
python -m techno_engine.run_config --config configs/m4_showcase.json

# Direct CLI for metronome (M0 baseline)
python -m techno_engine.cli --config configs/m0_metronome.json
```

The engine writes `.mid` files to the configured `out` path and, for M4 configs, can optionally emit a CSV log with per-bar metrics (`E`, `S`, hat density, entropy).

## Repository Layout

| Path                         | Purpose |
|-----------------------------|---------|
| `src/techno_engine/`        | Core engine modules |
| `tests/`                    | 32 unit tests (conditions, Markov sync, kick variation, config loading, modulators, logging) |
| `configs/`                  | Ready-to-run JSON configs (M0–M4, Markov/kick/condition showcases) |
| `out/`                      | Generated MIDI examples (not tracked) |
| `roadmap`, `ROADMAP_CHECKLIST.md` | Roadmap artifact and progress log |

## Features Implemented

1. **Skeleton & Backbone (M0–M1)**
   - Deterministic 4/4 kick, straight 16th hats, backbeat snare/clap.
   - MIDI writer with PPQ 1920 and microtiming conversions.

2. **Parametric Engine (M2)**
   - Euclidean mask + slow rotation, swing + beat-bin micro, ratchets, choke groups, open-hat offbeats.
   - Dispersion metrics and unit tests for swing delay, micro-bin sampling, and choke behaviour.

3. **Conditions, Density & Kick Variation (M3)**
   - Condition stack: PROB, PRE/NOT_PRE, FILL, EVERY_N.
   - Density clamp with void bias and hat thinning near kicks.
   - Kick ghosts, displacement into the 2, slow rotation, optional guard allowing kick variation.

4. **Scoring, Feedback, Markov Modulators (M4)**
   - Sync-biased Markov probabilities, long-horizon modulators (random walk, OU, sine).
   - Per-bar entropy and density corrections; guard/rescue path with logging.
   - CSV logging of per-bar E/S hat density/entropy.

5. **Config & CLI Integration**
   - Full JSON loader for layer configs, conditions, guard/target settings, modulators, logging path.
   - `run_config` CLI renders M1/M2/M4 sessions with optional logging and metadata.

## Running Examples

We’ve rendered several demo packs; rerun them to audition styles:

```bash
# Markov variety
ls out/markov_variety

# Kick variations
ls out/kick_variation_showcase

# Condition-driven grooves
ls out/condition_showcase

# Param modulator showcase
ls out/modulator_showcase
```

Each `.mid` corresponds to a config or script change in the repo, making it easier to reproduce the sound.

## Configuration Guide

### EngineConfig (JSON snippet)

```json
{
  "mode": "m4",
  "bpm": 132,
  "ppq": 1920,
  "bars": 64,
  "seed": 42,
  "out": "out/m4_render.mid",
  "log_path": "out/m4_render.csv",
  "guard": {"min_E": 0.7, "max_rot_rate": 0.12, "kick_immutable": false},
  "targets": {"S_low": 0.35, "S_high": 0.55, "H_low": 0.35, "H_high": 0.6,
               "hat_density_target": 0.7, "hat_density_tol": 0.05},
  "layers": {
    "kick": {"rotation_rate_per_bar": 0.05, "ghost_pre1_prob": 0.25},
    "hat_c": {
      "steps": 16,
      "fills": 12,
      "swing_percent": 0.55,
      "conditions": [{"kind": "EVERY_N", "n": 4, "offset": 2}]
    }
  },
  "modulators": [
    {
      "name": "hat_swing",
      "param_path": "hat_c.swing_percent",
      "mod": {"mode": "ou", "min_val": 0.52, "max_val": 0.58,
               "step_per_bar": 0.008, "tau": 24, "max_delta_per_bar": 0.01}
    }
  ]
}
```

Parameters:

- `layers.<name>.conditions`: Array of condition objects with `kind` [`PROB`, `PRE`, `NOT_PRE`, `FILL`, `EVERY_N`], optional `p`, `n`, `offset`, `negate`.
- `modulators`: `param_path` uses dot notation into `thin_bias`, `hat_c`, `hat_o`, `snare`, `clap`, or `accent`.
- `guard`: `kick_immutable=false` permits kick variation; otherwise the kick stays 4/4.
- `targets`: optional bands for S, H, and hat density.
- `log_path`: optional CSV output with per-bar metrics.

### Supported Param Paths

| Param Path              | Description |
|------------------------|-------------|
| `thin_bias`            | Hat thinning bias (affects hats near kicks) |
| `hat_c.swing_percent`  | Closed-hat swing percent |
| `hat_o.ratchet_prob`   | Open-hat ratchet probability |
| `hat_o.s,...`          | Any LayerConfig float (e.g. `hat_o.swing_percent`) |
| `accent.prob`          | Global accent probability |

## Unit Tests

We ship 32 tests covering the entire pipeline. Key suites:

- `tests/test_m0_metronome.py`: timebase sanity.
- `tests/test_m2_parametric.py`: swing/beat-bin/choke behaviour.
- `tests/test_m4_control.py`: sync targeting, continuity, rescue behaviour.
- `tests/test_conditions_stack.py`: PROB/PRE/FILL/EVERY_N gating.
- `tests/test_kick_variation.py`: ghosts, displacement, rotation.
- `tests/test_param_modulators.py`: param-path modulators and bounds.
- `tests/test_config_modulators.py`: JSON parsing and integration.
- `tests/test_logging_metrics.py`: CSV logging.

Run `pytest -q` to ensure all pass; the pipeline is currently green.

## Roadmap Status Highlights

- Markov sync bias, condition stacks, kick variation, entropy/density feedback, and logging integrated.
- Config loader/CLI now mirror roadmap Section F/J.
- Example packs generated and checked into `out/` for quick auditioning.
- Remaining tasks: documentation polish (this README), additional configs (as needed), and optional YAML support if required.

## License & Credits

- Engine inspired by the Berlin-Style Techno MIDI Engine roadmap (see `roadmap`).
- Example outputs are for demonstration—the engine itself is MIDI-only and can drive any sound source.

Enjoy exploring the groove!
