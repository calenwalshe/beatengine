# Bass V2 Web UI Backend

Flask API server for the bass_v2 generator.

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Run the server:
```bash
python3 app.py
```

The server will start on `http://localhost:5001` (CORS enabled for the web UI).

## API Endpoints

### Generate Bass
```
POST /api/generate
```

Request body:
```json
{
  "drum_pattern": "berlin_syncopated",
  "theory_context": {
    "key_scale": "D_minor",
    "tempo_bpm": 130.0
  },
  "controls": {
    "mode_and_behavior_controls": {
      "strategy": "auto_from_drums",
      "fixed_mode": null
    },
    "rhythm_controls": {
      "note_density": 0.5,
      "rhythmic_complexity": 0.65,
      "swing_amount": 0.1,
      "groove_depth": 0.4,
      "kick_interaction_mode": "avoid_kick"
    },
    "melody_controls": {
      "root_note_emphasis": 0.7,
      "interval_jump_magnitude": 0.5,
      "melodic_intensity": 0.6,
      "base_octave": 2
    },
    "articulation_controls": {
      "accent_chance": 0.35,
      "accent_pattern_mode": "offbeat_focused",
      "gate_length": 0.5,
      "tie_notes": false,
      "humanize_timing": 0.1,
      "humanize_velocity": 0.1
    }
  }
}
```

Response:
```json
{
  "success": true,
  "filename": "bass_20240123_142530_pocket_groove.mid",
  "filepath": "/path/to/file.mid",
  "metadata": {...},
  "preview": {
    "note_count": 32,
    "length_bars": 4,
    "length_seconds": 7.38,
    "pitch_range": {"min": 38, "max": 50},
    "velocity_range": {"min": 80, "max": 110},
    "modes_used": ["pocket_groove", "pocket_groove", "root_fifth_driver", "pocket_groove"]
  }
}
```

### List Presets
```
GET /api/presets
```

### Load Preset
```
GET /api/presets/<name>
```

### Save Preset
```
POST /api/presets
```

### List Drum Patterns
```
GET /api/drum-patterns
```

### Download MIDI File
```
GET /api/download/<filename>
```

### Health Check
```
GET /health
```

## Directory Structure

```
web_ui/backend/
├── app.py                      # Flask server
├── bass_generator_api.py       # Bass generator wrapper
├── drum_patterns.py            # Pre-defined drum patterns
├── presets/                    # Saved presets
│   ├── berlin_classic.json
│   ├── rolling_energy.json
│   ├── minimal_deep.json
│   └── hard_driving.json
├── requirements.txt
└── README.md
```

## Available Drum Patterns

- `berlin_syncopated` - Modern Berlin techno: syncopated kicks, driving hats
- `four_on_floor` - Classic house/techno: steady kicks, offbeat hats
- `minimal_sparse` - Minimal techno: sparse, hypnotic
- `hard_techno` - Aggressive, dense pattern
- `broken_beat` - Complex, shuffled timing
- `rolling_techno` - Continuous flowing hats
- `half_time` - Slower feel
- `industrial` - Mechanical, dark
- `acid_techno` - Groovy, syncopated
- `detroit_classic` - Classic Detroit techno
- `dub_techno` - Spacious, deep
- `breakbeat` - Funky, broken

## Available Presets

- `berlin_classic` - Classic modern Berlin techno bass
- `rolling_energy` - High-energy rolling bass line
- `minimal_deep` - Sparse, hypnotic with deep sub-focus
- `hard_driving` - Aggressive, dense with kick reinforcement

## Web UI (Standalone HTML) Payload Summary

The standalone UI (`web_ui/simple_ui.html`) sends a focused subset of controls into the API:

- `theory_context`: `key_scale`, `tempo_bpm`
- `mode_and_behavior_controls`: `strategy` (`auto_from_drums` | `fixed_mode`), `fixed_mode` (`sub_anchor`, `root_fifth_driver`, `pocket_groove`, `rolling_ostinato`, `offbeat_stabs`, `lead_ish`)
- `rhythm_controls`: `note_density`, `rhythmic_complexity`, `swing_amount`, `groove_depth`, `kick_interaction_mode`
- `melody_controls`: `root_note_emphasis`, `interval_jump_magnitude`, `melodic_intensity`, `base_octave`

These map directly to `bass_v2_pipeline` (slot selection, mode selection, timing swing/groove, and pitch mapping).
