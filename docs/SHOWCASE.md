# Showcase Pack

Render a small set of diverse drum patterns with separate scored+validated basslines to audition engine range.

## Run

```bash
PYTHONPATH=src python -m techno_engine.showcase --pack default --outdir out/showcase \
  --key A --mode minor --scenario syncopated_layers --scenario low_bpm_95
```

Outputs a directory with paired files per scenario, e.g., `syncopated_layers_drums_sync.mid` and `syncopated_layers_bass.mid`. Open `out/showcase/index.html` for a browsable table.

Scenarios include:
- Syncopated layers (128 BPM)
- Low BPM (95 BPM)
- Alien bounce (126 BPM, minor colouring)
- Ghosty sync hats (128 BPM, heavy ghost kicks + hat syncopation)
- Fast kicks (140 BPM)

Artifacts:
- `manifest.csv` and `manifest.json` (metadata + file paths + scenario descriptions)
- `index.html` (styled table with links)
- `drums_*.mid` / `bass_*.mid` per scenario
