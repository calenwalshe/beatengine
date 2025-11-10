# Planning Templates

Templates for concise, tool-first plans used by the assistant.

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

