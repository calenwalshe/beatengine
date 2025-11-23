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

The server will start on `http://localhost:5000`.

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
    "rhythm_controls": {
      "note_density": 0.5,
      "rhythmic_complexity": 0.65
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
