# Berlin Techno Bass Grid - Quick Reference

## Grid Exploration Results Summary

Successfully explored **24 parameter combinations** for modern Berlin techno bass:

```
✅ 24 variations generated
✅ Analysis complete
✅ Results saved to: output/berlin_bass_grid/analysis.json
```

---

## Key Findings

### 📊 Density Impact

| Level | Notes/Bar | Total Notes (4 bars) | Character |
|-------|-----------|---------------------|-----------|
| **Medium** (0.50) | 8 notes | 32 notes | Moderate driving |
| **High** (0.65) | 10 notes | 40 notes | Rolling patterns |
| **Very High** (0.80) | 11.5 notes | 46 notes | Dense ostinato |

### 🎹 Articulation Comparison

| Style | Avg Velocity | Accent Ratio | Character |
|-------|--------------|--------------|-----------|
| **Punchy** (gate 0.35, 70% accents) | 110-112 | 0.69 | Aggressive, industrial |
| **Driving** (gate 0.55, 50% accents) | 104-106 | 0.44 | Smooth, classic |

### 🔥 Most Aggressive Combinations

Top 5 by velocity (all using "punchy" articulation):
1. **very_high/medium/pocket_groove_punchy** - 112 avg vel, 46 notes
2. **very_high/medium/rolling_ostinato_punchy** - 112 avg vel, 46 notes
3. **very_high/high/pocket_groove_punchy** - 112 avg vel, 46 notes
4. **very_high/high/rolling_ostinato_punchy** - 112 avg vel, 46 notes
5. **high/medium/pocket_groove_punchy** - 111 avg vel, 40 notes

---

## Parameter Quick Reference

### What Each Dimension Controls

**Density** (`note_density`):
- `medium` (0.50) → ~8 notes/bar → Spacious, minimal
- `high` (0.65) → ~10 notes/bar → Rolling, energetic
- `very_high` (0.80) → ~12 notes/bar → Dense, hypnotic

**Syncopation** (`rhythmic_complexity`):
- `medium` (0.65) → Groovy syncopation, some straight beats
- `high` (0.85) → Heavily syncopated, offbeat-heavy

**Mode**:
- `pocket_groove` → Drum-reactive, hat-synced, groovy
- `rolling_ostinato` → Continuous rolling, less drum-dependent

**Articulation**:
- `punchy` → Short notes (0.35 gate), high accents (70%)
- `driving` → Medium notes (0.55 gate), moderate accents (50%)

---

## Recommended Combinations for Different Use Cases

### 🎯 Classic Berlin Driving Techno
```
Density: high
Syncopation: medium
Mode: pocket_groove
Articulation: driving
```
**Result:** 40 notes, 105 avg velocity, smooth groove

### 🔥 Peak Time Energy
```
Density: very_high
Syncopation: high
Mode: rolling_ostinato
Articulation: punchy
```
**Result:** 46 notes, 112 avg velocity, relentless drive

### 🌙 Warm-Up/Breakdown
```
Density: medium
Syncopation: medium
Mode: pocket_groove
Articulation: driving
```
**Result:** 32 notes, 104 avg velocity, spacious groove

### ⚙️ Industrial/Hard Techno
```
Density: very_high
Syncopation: high
Mode: pocket_groove
Articulation: punchy
```
**Result:** 46 notes, 112 avg velocity, aggressive

---

## How to Generate Specific Variations

### Method 1: Quick Generation (Python)

```python
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext

# Use the Berlin drum pattern from the grid explorer
from scripts.berlin_bass_grid_explorer import create_berlin_drum_pattern

# Example: Peak time energy
drums = create_berlin_drum_pattern()
theory = TheoryContext(key_scale="D_minor", tempo_bpm=130.0)

controls = {
    "rhythm_controls": {
        "note_density": 0.80,  # very_high
        "rhythmic_complexity": 0.85,  # high
        "kick_interaction_mode": "avoid_kick"
    },
    "articulation_controls": {
        "gate_length": 0.35,  # punchy
        "accent_chance": 0.7,
        "velocity_normal": 95,
        "velocity_accent": 118
    },
    "mode_and_behavior_controls": {
        "strategy": "fixed_mode",
        "fixed_mode": "rolling_ostinato"
    },
    "melody_controls": {
        "root_note_emphasis": 0.6,
        "note_range_octaves": 1
    }
}

clip = generate_bass_midi_from_drums(drums, theory, controls, seed=42)
print(f"Generated {len(clip.notes)} notes")
```

### Method 2: Export to MIDI (requires mido)

```python
from src.techno_engine.bass_v2 import convert_to_midi_events
from src.techno_engine.midi_writer import write_midi

# After generating clip (see Method 1):
events = convert_to_midi_events(clip, ppq=480, channel=1)
write_midi(events, 480, 130.0, "my_berlin_bass.mid")
```

---

## Grid Explorer Files

### Generated Files

```
output/berlin_bass_grid/
└── analysis.json              # Complete parameter space analysis
```

### Scripts

```
scripts/
├── berlin_bass_grid_explorer.py    # Run parameter exploration (no MIDI)
└── berlin_bass_grid_generator.py   # Full MIDI export (requires mido)
```

---

## Full Grid Results (All 24 Variations)

| ID | Density | Syncopation | Mode | Articulation | Notes | Avg Vel |
|----|---------|-------------|------|--------------|-------|---------|
| 1 | medium | medium | pocket_groove | punchy | 32 | 110 |
| 2 | medium | medium | pocket_groove | driving | 32 | 104 |
| 3 | medium | medium | rolling_ostinato | punchy | 32 | 110 |
| 4 | medium | medium | rolling_ostinato | driving | 32 | 104 |
| 5 | medium | high | pocket_groove | punchy | 32 | 110 |
| 6 | medium | high | pocket_groove | driving | 32 | 104 |
| 7 | medium | high | rolling_ostinato | punchy | 32 | 110 |
| 8 | medium | high | rolling_ostinato | driving | 32 | 104 |
| 9 | high | medium | pocket_groove | punchy | 40 | 111 |
| 10 | high | medium | pocket_groove | driving | 40 | 105 |
| 11 | high | medium | rolling_ostinato | punchy | 40 | 111 |
| 12 | high | medium | rolling_ostinato | driving | 40 | 105 |
| 13 | high | high | pocket_groove | punchy | 40 | 111 |
| 14 | high | high | pocket_groove | driving | 40 | 105 |
| 15 | high | high | rolling_ostinato | punchy | 40 | 111 |
| 16 | high | high | rolling_ostinato | driving | 40 | 105 |
| 17 | very_high | medium | pocket_groove | punchy | 46 | 112 |
| 18 | very_high | medium | pocket_groove | driving | 46 | 106 |
| 19 | very_high | medium | rolling_ostinato | punchy | 46 | 112 |
| 20 | very_high | medium | rolling_ostinato | driving | 46 | 106 |
| 21 | very_high | high | pocket_groove | punchy | 46 | 112 |
| 22 | very_high | high | pocket_groove | driving | 46 | 106 |
| 23 | very_high | high | rolling_ostinato | punchy | 46 | 112 |
| 24 | very_high | high | rolling_ostinato | driving | 46 | 106 |

---

## Next Steps

1. **Review the analysis** above and identify combinations that match your sound
2. **Customize parameters** - Use the findings as a starting point and tweak
3. **Export favorites** - Use the code examples to generate MIDI files
4. **Blend variations** - Try switching modes between sections for progression

---

## Drum Pattern Used

**Syncopated Berlin Groove** (130 BPM, 4 bars):

- Bar 1: Syncopated kick (steps 0, 4, 7, 12), offbeat hats, backbeat clap
- Bar 2: Ghost kick added (step 3)
- Bar 3: More syncopation, double clap
- Bar 4: Four-on-floor return

This pattern provides the rhythmic foundation for all variations.

---

**Generated:** 2025-11-22
**Total Exploration Time:** ~1 second (24 variations)
**Framework:** bass_v2 generator
