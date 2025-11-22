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

When in doubt, prefer using the **tools** defined in `AGENT_API.md` over raw CLI calls.

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

## Create and Save a New Seed (Drums + Bass)

User: "make a new warehouse groove with paired bass and save it as a seed"

Plan:
- call make_bass_for_config(config_path="configs/m4_warehouse_sync.json", key="A", mode="minor", density=0.45, save_prefix="m4_warehouse")
- call seed_import_mid(path=<drums midi from result.drums>, prompt_text="warehouse m4 groove", tags="m4,warehouse,showcase", summary="Warehouse groove (drums only)") **only if** you need a seed for drums-only workflows
- or, prefer a dedicated seed tool that wraps `paired_render_cli` if available in your toolset
- return final drums/bass paths and any created seed_id

## Bass From Existing Seed

User: "add a lead-ish bassline to seed <seed_id>"

Plan:
- call seed_show(seed_id="<seed_id>")
- call seed_bass_from_seed(seed_id="<seed_id>", bass_mode="leadish", description="leadish groove-aware bass")
- return updated metadata and bass asset path

## Lead From Existing Seed

User: "add a simple lead line to seed <seed_id>"

Plan:
- call seed_show(seed_id="<seed_id>")
- call seed_lead_from_seed(seed_id="<seed_id>", mode="lead_basic", description="simple lead line over drums+bass")
- return updated metadata and lead asset path

## Explore, Clone, and Clean Up Seeds

User: "find a minimal warehouse groove, make a longer version, and delete it if I don't like it"

Plan:
- call seed_list(tag="warehouse") and select a candidate seed_id with tags including "minimal" (or closest match)
- call seed_clone(seed_id=<chosen>, bars=32, summary="32-bar warehouse clone")
- call seed_render(seed_id=<new_seed_id>) to get MIDI for preview
- if the user explicitly says "delete that clone", call seed_delete(seed_id=<new_seed_id>, yes=true)
- never call seed_delete without explicit user confirmation
