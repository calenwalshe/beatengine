# Bassline API (MVP + Scored)

This document shows how to invoke the bassline generator and validator programmatically via the tool API (`bass_tools`).

## Quick Example

```python
# SNIPPET: generate_and_validate
from techno_engine.bass_tools import bass_generate, bass_validate_lock, BassGenerateInput, BassValidateInput, API_VERSION

# Generate a 4-bar MVP bassline
gen = bass_generate(BassGenerateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, mode="mvp", root_note=45, density=0.4))
assert gen["code"] == "OK"

# Validate/lock (enforce density/monophony)
val = bass_validate_lock(BassValidateInput(version=API_VERSION, bpm=120.0, ppq=1920, bars=4, density=0.4, events=gen["events"]))
assert val["code"] == "OK"
assert isinstance(val["events"], list) and isinstance(val["summaries"], list)
```

## Styles (presets)

`style` presets modify generation defaults:

- `sparse_root` → MVP mode, density ≈ 0.30
- `offbeat_scored` → Scored mode, density ≈ 0.45
- `urgent_dense` → Scored mode, density ≈ 0.60

Use with `BassGenerateInput(style="offbeat_scored", ...)`.

## Terminal helper (one-shot)

```python
# SNIPPET: make_bass_for_config
import os
import tempfile
from techno_engine.terminal import tools

with tempfile.TemporaryDirectory() as tmp:
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = tmp
    os.environ["TECH_ENGINE_OUT_DIR"] = tmp
    cfg_path = "techno_rhythm_engine/configs/m4_95bpm.json"
    if not os.path.exists(cfg_path):
        cfg_path = "configs/m4_95bpm.json"
    result = tools.make_bass_for_config({
        "config_path": cfg_path,
        "key": "A",
        "mode": "minor",
        "density": 0.4,
    })
    print("Drums:", result["drums"])
    print("Bass:", result["bass"])
```

## Sample plan (terminal orchestrator)

```text
User: \"Need a bassline for configs/m4_95bpm.json at 0.4 density in A minor\"\nPlan:\n1. make_bass_for_config(config_path=\"configs/m4_95bpm.json\", key=\"A\", mode=\"minor\", density=0.4, save_prefix=\"user95\")\n2. Surface E/S metrics and file paths to the user\n```
