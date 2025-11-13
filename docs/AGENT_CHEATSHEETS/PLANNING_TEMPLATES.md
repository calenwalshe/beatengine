# Planning Templates

Templates for concise, tool-first plans used by the assistant.

## Environment Bootstrap

Before running any CLI, ensure the repo has a virtualenv with dependencies installed:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q  # optional verification (expect 98 pass / 2 skip)
```

Always reuse the same venv for subsequent commands in this session.

## Demo Prompt Shortcuts

Before proposing a plan, check `docs/LLM_PROMPT_DEMOS.md` for pre-approved demo/test prompts. Each entry ships with the exact command to run.
- `metronome_baseline`: run `python -m techno_engine.cli --config configs/m0_metronome.json` to prove the pipeline works.
- `bass_for_config`: run `PYTHONPATH=src python -m techno_engine.combo_cli ...` as documented to generate drums + bass for `configs/m4_95bpm.json`.
- `energy_gradient`: run `PYTHONPATH=src python scripts/make_energy_gradient_pack.py` to emit the eight-file energy buildup/breakdown pack; return the manifest path.

## One-shot Groove (drums only)

User: "render configs/m4_showcase.json"

Plan:
- call render_session(config_path="configs/m4_showcase.json")
- return midi path

## Make Bass For Config

User: "make bass for configs/m4_95bpm.json in A minor with density 0.4"

Plan:
- call make_bass_for_config(config_path="configs/m4_95bpm.json", key="A", mode="minor", density=0.4, save_prefix="m4_95bpm_minor")
- return drums/bass paths plus E/S metrics

## Create Variant Config

User: "copy syncopated_layers but less swing and more ghosts"

Plan:
- call create_config(base_path="configs/m4_syncopated_layers.json", patch={"layers":{"hat_c":{"swing_percent":0.54}, "kick":{"ghost_pre1_prob":0.4}}}, save_as="configs/m4_sync_lessswing_moreghosts.json")
- call render_session(config_path="configs/m4_sync_lessswing_moreghosts.json")
- return midi path
