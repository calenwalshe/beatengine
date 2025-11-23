# Bass V2 Generator - API Documentation

## Table of Contents
- [Quick Start](#quick-start)
- [Main API Functions](#main-api-functions)
- [Data Structures](#data-structures)
- [Control Parameters](#control-parameters)
- [Bass Modes](#bass-modes)
- [Examples](#examples)

---

## Quick Start

```python
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext

# 1. Define your drum pattern
m4_drum_output = {
    "bars": [
        {
            "steps": [
                {"kick": True, "hat": False, "snare": False, "velocity": 100},
                {"kick": False, "hat": True, "snare": False, "velocity": 80},
                # ... 14 more steps (16 total per bar)
            ]
        }
        # ... more bars
    ]
}

# 2. Set musical context
theory = TheoryContext(
    key_scale="A_minor",
    tempo_bpm=128.0
)

# 3. Generate bass
clip = generate_bass_midi_from_drums(
    m4_drum_output=m4_drum_output,
    theory_context=theory,
    seed=42
)

# 4. Access results
print(f"Generated {len(clip.notes)} notes")
for note in clip.notes:
    print(f"Pitch: {note.pitch}, Beat: {note.start_beat}, Vel: {note.velocity}")
```

---

## Main API Functions

### `generate_bass_midi_from_drums()`

**Main entry point** for generating basslines from drum patterns.

```python
def generate_bass_midi_from_drums(
    m4_drum_output: Dict[str, Any],
    theory_context: Optional[TheoryContext] = None,
    global_controls: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> BassMidiClip
```

#### Parameters

**`m4_drum_output`** : `Dict[str, Any]` (required)
- Drum pattern data structure
- Format:
  ```python
  {
      "bars": [
          {
              "steps": [
                  {
                      "kick": bool,      # Kick drum hit
                      "hat": bool,       # Hi-hat hit
                      "snare": bool,     # Snare/clap hit
                      "velocity": int    # Optional, 0-127
                  },
                  # ... 16 steps total per bar
              ]
          },
          # ... N bars
      ]
  }
  ```

**`theory_context`** : `TheoryContext` (optional)
- Musical context for generation
- Default: `TheoryContext(key_scale="A_minor", tempo_bpm=128.0)`
- Fields:
  - `key_scale: str` - Musical key (e.g., "A_minor", "D_major", "G_dorian")
  - `chord_progression: List[str]` - Optional chord sequence
  - `tempo_bpm: float` - Tempo in beats per minute

**`global_controls`** : `Dict[str, Any]` (optional)
- Override default control values
- See [Control Parameters](#control-parameters) for full reference
- Example:
  ```python
  {
      "rhythm_controls": {
          "note_density": 0.7,
          "rhythmic_complexity": 0.8
      },
      "melody_controls": {
          "root_note_emphasis": 0.9
      }
  }
  ```

**`seed`** : `int` (optional)
- Random seed for deterministic generation
- Default: 42
- Same seed + same inputs = identical output

#### Returns

**`BassMidiClip`**
- Fields:
  - `notes: List[BassNote]` - Generated bass notes
  - `length_bars: int` - Number of bars
  - `metadata: Dict` - Debug info and mode assignments

---

### `convert_to_midi_events()`

Converts `BassMidiClip` to MIDI events compatible with the existing midi_writer.

```python
def convert_to_midi_events(
    clip: BassMidiClip,
    ppq: int = 480,
    channel: int = 1
) -> List[MidiEvent]
```

#### Parameters

**`clip`** : `BassMidiClip` (required)
- Bass clip from `generate_bass_midi_from_drums()`

**`ppq`** : `int` (optional, default: 480)
- Pulses per quarter note (MIDI timing resolution)

**`channel`** : `int` (optional, default: 1)
- MIDI channel (0-15)

#### Returns

**`List[MidiEvent]`**
- Compatible with `midi_writer.write_midi()`

---

## Data Structures

### TheoryContext

Musical context for generation.

```python
@dataclass
class TheoryContext:
    key_scale: str = "A_minor"           # Musical key
    chord_progression: Optional[List[str]] = None  # Chord sequence
    tempo_bpm: float = 128.0             # Tempo
```

**Supported Scales:**
- `"A_minor"`, `"C_minor"`, `"D_minor"`, etc. (natural minor)
- `"C_major"`, `"D_major"`, `"G_major"`, etc.
- `"D_dorian"`, `"E_phrygian"`, `"G_mixolydian"`

---

### BassNote

Single bass note in the generated pattern.

```python
@dataclass
class BassNote:
    pitch: int                    # MIDI note number (28-60 typical bass range)
    start_beat: float             # Start time in beats
    duration_beats: float         # Note length in beats
    velocity: int                 # MIDI velocity (1-127)
    metadata: Dict[str, Any]      # Additional info (slot_index, score, etc.)
```

---

### BassMidiClip

Complete bass pattern output.

```python
@dataclass
class BassMidiClip:
    notes: List[BassNote]         # All generated notes
    length_bars: int              # Number of bars
    metadata: Dict[str, Any]      # Debug metadata
```

**Metadata Fields:**
- `mode_per_bar: List[str]` - Bass mode used for each bar
- `scoring_debug: List[Dict]` - Per-bar scoring details
- `control_snapshot: List[Dict]` - Resolved controls per bar

---

## Control Parameters

### Complete Control Reference

Controls are organized into 9 groups. Pass them in `global_controls` dict:

```python
global_controls = {
    "theory_controls": {...},
    "rhythm_controls": {...},
    "melody_controls": {...},
    "articulation_controls": {...},
    "pattern_variation_controls": {...},
    "drum_interaction_controls": {...},
    "mode_and_behavior_controls": {...},
    "output_controls": {...},
    "advanced_overrides": {...}
}
```

---

### 1. Theory Controls

```python
"theory_controls": {
    "key_scale": "A_minor",              # str - Musical key
    "chord_progression": None,           # List[str] - Chord sequence
    "harmonic_strictness": 0.9,          # float 0-1 - How strict to key
    "chord_tone_priority": 0.8,          # float 0-1 - Prefer chord tones
    "minorness": 0.5                     # float 0-1 - Minor color bias
}
```

---

### 2. Rhythm Controls

```python
"rhythm_controls": {
    "rhythmic_complexity": 0.5,          # float 0-1 - Straight to syncopated
    "note_density": 0.5,                 # float 0-1 - Notes per bar (0.5 ≈ 8 notes)
    "onbeat_offbeat_balance": 0.0,       # float -1 to 1 - (-1=onbeat, 1=offbeat)
    "kick_interaction_mode": "avoid_kick",  # "avoid_kick" | "reinforce_kick" | "balanced"
    "swing_amount": 0.0,                 # float 0-1 - Swing feel
    "groove_depth": 0.5,                 # float 0-1 - Groove intensity
    "use_triplets": False,               # bool - Enable triplet subdivisions
    "pattern_length_bars": 2             # int - Phrase length
}
```

**Key Parameters:**
- `note_density` - **Most important** - Controls how many notes per bar
  - `0.1` = Very sparse (1-2 notes)
  - `0.5` = Medium (6-8 notes)
  - `0.9` = Dense (12-14 notes)

- `kick_interaction_mode` - How bass relates to kick
  - `"avoid_kick"` - Bass avoids kick steps (clean low-end)
  - `"reinforce_kick"` - Bass hits with kick
  - `"balanced"` - Mix of both

---

### 3. Melody Controls

```python
"melody_controls": {
    "note_range_octaves": 1,             # int - Octave range (1-3)
    "base_octave": 2,                    # int - Starting octave
    "root_note_emphasis": 0.8,           # float 0-1 - How often to use root
    "scale_degree_bias": None,           # Dict[str, float] - Degree weights
    "interval_jump_magnitude": 0.4,      # float 0-1 - Small steps to big leaps
    "melodic_intensity": 0.5             # float 0-1 - Movement amount
}
```

**Key Parameters:**
- `root_note_emphasis` - Root note frequency
  - `0.95` = Almost always root (minimal bass)
  - `0.5` = Balanced root/scale mix
  - `0.2` = Melodic, less root emphasis

- `interval_jump_magnitude` - Step size between notes
  - `0.2` = Stepwise motion (1-2 semitones)
  - `0.5` = Mixed
  - `0.9` = Large leaps (octaves, fifths)

---

### 4. Articulation Controls

```python
"articulation_controls": {
    "velocity_normal": 80,               # int 0-127 - Base velocity
    "velocity_accent": 110,              # int 0-127 - Accent velocity
    "accent_chance": 0.3,                # float 0-1 - Accent probability
    "accent_pattern_mode": "offbeat_focused",  # "random" | "offbeat_focused" | "downbeat_focused"
    "gate_length": 0.5,                  # float 0-1 - Note length (0.5 = half step)
    "tie_notes": False,                  # bool - Legato ties
    "slide_chance": 0.1,                 # float 0-1 - Portamento probability
    "humanize_timing": 0.1,              # float 0-1 - Timing variation
    "humanize_velocity": 0.1             # float 0-1 - Velocity variation
}
```

**Key Parameters:**
- `gate_length` - Note duration
  - `0.3` = Short, staccato
  - `0.5` = Standard
  - `0.9` = Long, sustained

- `accent_chance` - Accent frequency
  - `0.1` = Rare accents
  - `0.5` = Half notes accented
  - `0.9` = Mostly accented

---

### 5. Drum Interaction Controls

```python
"drum_interaction_controls": {
    "kick_avoid_strength": 0.8,          # float 0-1 - Kick avoidance strength
    "snare_backbeat_preference": 0.5,    # float 0-1 - Align with snare
    "hat_sync_strength": 0.5             # float 0-1 - Align with hats
}
```

---

### 6. Mode and Behavior Controls

```python
"mode_and_behavior_controls": {
    "strategy": "auto_from_drums",       # "auto_from_drums" | "fixed_mode" | "per_bar_explicit"
    "fixed_mode": None,                  # str - Force specific mode
    "per_bar_modes": None                # List[str] - Explicit per-bar modes
}
```

**Strategies:**
- `"auto_from_drums"` - Automatically select mode based on drum energy
- `"fixed_mode"` - Use same mode for all bars (set `fixed_mode` param)
- `"per_bar_explicit"` - Specify mode per bar (set `per_bar_modes` list)

**Example:**
```python
# Force offbeat_stabs for entire pattern
"mode_and_behavior_controls": {
    "strategy": "fixed_mode",
    "fixed_mode": "offbeat_stabs"
}

# Or specify per bar
"mode_and_behavior_controls": {
    "strategy": "per_bar_explicit",
    "per_bar_modes": ["sub_anchor", "root_fifth_driver", "pocket_groove", "sub_anchor"]
}
```

---

### 7. Output Controls

```python
"output_controls": {
    "max_notes_per_bar": 16,             # int - Maximum notes per bar
    "return_debug_metadata": False,      # bool - Include debug info
    "pattern_memory_slot": None          # int - Memory slot (future feature)
}
```

---

## Bass Modes

### Mode Reference

Each mode has distinct musical characteristics:

| Mode | Energy | Density | Character | Use Case |
|------|--------|---------|-----------|----------|
| **sub_anchor** | Low | Very Low (1-3 notes) | Minimal, root-heavy | Drops, breakdowns, minimal techno |
| **root_fifth_driver** | Medium | Medium (2-6 notes) | Classic EDM driver | House, tech house, general EDM |
| **pocket_groove** | Medium-High | Medium-High (4-10 notes) | Groovy, syncopated | Funky house, groovy techno |
| **rolling_ostinato** | High | High (4-8 notes) | Continuous rolling | Peak time, energetic sections |
| **offbeat_stabs** | Variable | Low (1-3 notes) | Sparse punchy stabs | Accents, transitions |
| **lead_ish** | High | Medium-High (6-12 notes) | Melodic, expressive | Lead bass, trance, progressive |

---

### Mode Details

#### sub_anchor
```python
Density: 1-3 notes/bar
Range: 1 octave
Root emphasis: 95%
Kick avoidance: Very strong
Ideal for: Minimal patterns, sub bass anchors
```

#### root_fifth_driver
```python
Density: 2-6 notes/bar
Range: 1 octave
Root emphasis: 80%
Kick avoidance: Medium
Ideal for: Classic house/techno driving bass
```

#### pocket_groove
```python
Density: 4-10 notes/bar
Range: 1 octave
Root emphasis: 50%
Kick avoidance: Medium-strong
Ideal for: Groovy, syncopated patterns
```

#### rolling_ostinato
```python
Density: 4-8 notes/bar
Range: 2 octaves
Root emphasis: 50%
Kick avoidance: Medium
Ideal for: Continuous rolling patterns
```

#### offbeat_stabs
```python
Density: 1-3 notes/bar
Range: 1 octave
Root emphasis: 80%
Kick avoidance: Very strong
Ideal for: Punchy offbeat accents
```

#### lead_ish
```python
Density: 6-12 notes/bar
Range: 2 octaves
Root emphasis: 40%
Kick avoidance: Medium
Ideal for: Melodic, expressive bass lines
```

---

## Examples

### Example 1: Basic House Pattern

```python
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums
from src.techno_engine.bass_v2_types import TheoryContext

# Four-on-the-floor house drum pattern
drums = {
    "bars": [
        {
            "steps": [
                {"kick": i in {0, 4, 8, 12}, "hat": i % 2 == 1, "snare": i in {4, 12}}
                for i in range(16)
            ]
        }
        for _ in range(4)
    ]
}

theory = TheoryContext(key_scale="A_minor", tempo_bpm=128.0)
clip = generate_bass_midi_from_drums(drums, theory, seed=42)

print(f"Generated {len(clip.notes)} notes using modes: {clip.metadata['mode_per_bar']}")
```

---

### Example 2: Force Specific Mode

```python
# Force groovy pocket_groove mode
controls = {
    "mode_and_behavior_controls": {
        "strategy": "fixed_mode",
        "fixed_mode": "pocket_groove"
    }
}

clip = generate_bass_midi_from_drums(drums, theory, controls, seed=42)
```

---

### Example 3: Custom Density and Articulation

```python
# Dense, aggressive bass with high accents
controls = {
    "rhythm_controls": {
        "note_density": 0.75,           # Dense pattern
        "rhythmic_complexity": 0.8,     # More syncopation
        "kick_interaction_mode": "avoid_kick"
    },
    "articulation_controls": {
        "velocity_normal": 95,
        "velocity_accent": 120,
        "accent_chance": 0.6,           # 60% notes accented
        "gate_length": 0.3,             # Short, punchy
        "slide_chance": 0.2             # Some slides
    },
    "melody_controls": {
        "root_note_emphasis": 0.6,      # More melodic
        "note_range_octaves": 2         # Wide range
    }
}

clip = generate_bass_midi_from_drums(drums, theory, controls, seed=42)
```

---

### Example 4: Minimal Sub Bass

```python
# Very minimal sub bass
controls = {
    "mode_and_behavior_controls": {
        "strategy": "fixed_mode",
        "fixed_mode": "sub_anchor"
    },
    "rhythm_controls": {
        "note_density": 0.1             # Very sparse
    },
    "melody_controls": {
        "root_note_emphasis": 0.99      # Almost all root
    }
}

clip = generate_bass_midi_from_drums(drums, theory, controls, seed=42)
# Expect 1-2 notes per bar, all root notes
```

---

### Example 5: Different Scales

```python
# Try different musical scales
scales = ["A_minor", "D_minor", "G_dorian", "C_major", "E_phrygian"]

for scale in scales:
    theory = TheoryContext(key_scale=scale, tempo_bpm=128.0)
    clip = generate_bass_midi_from_drums(drums, theory, seed=42)
    print(f"{scale}: {len(clip.notes)} notes")
```

---

### Example 6: Write to MIDI File

```python
from src.techno_engine.bass_v2 import generate_bass_midi_from_drums, convert_to_midi_events
from src.techno_engine.midi_writer import write_midi

# Generate bass
clip = generate_bass_midi_from_drums(drums, theory, seed=42)

# Convert to MIDI events
events = convert_to_midi_events(clip, ppq=480, channel=1)

# Write MIDI file
write_midi("my_bass.mid", events, tempo_bpm=128.0, ppq=480)
print("Wrote my_bass.mid")
```

---

### Example 7: Progressive Mode Changes

```python
# Different mode per bar for progression
controls = {
    "mode_and_behavior_controls": {
        "strategy": "per_bar_explicit",
        "per_bar_modes": [
            "sub_anchor",        # Bar 1: Minimal
            "root_fifth_driver", # Bar 2: Build
            "pocket_groove",     # Bar 3: Groovy
            "rolling_ostinato"   # Bar 4: Peak
        ]
    }
}

clip = generate_bass_midi_from_drums(drums, theory, controls, seed=42)
print(f"Modes used: {clip.metadata['mode_per_bar']}")
# Output: ['sub_anchor', 'root_fifth_driver', 'pocket_groove', 'rolling_ostinato']
```

---

### Example 8: Access Note Details

```python
clip = generate_bass_midi_from_drums(drums, theory, seed=42)

# Inspect each note
for i, note in enumerate(clip.notes):
    bar = int(note.start_beat / 4)
    beat = note.start_beat % 4
    print(f"Note {i}: Bar {bar}, Beat {beat:.2f}, Pitch {note.pitch}, Vel {note.velocity}")
```

---

## Performance Tips

1. **Use consistent seeds** for reproducible results during development
2. **Start with defaults** then adjust one control group at a time
3. **Use mode overrides** for predictable behavior
4. **Monitor note counts** via `len(clip.notes)` to verify density
5. **Check metadata** to understand which modes were selected

---

## Troubleshooting

### Too Many Notes
```python
# Reduce density
controls = {"rhythm_controls": {"note_density": 0.3}}
```

### Too Few Notes
```python
# Increase density
controls = {"rhythm_controls": {"note_density": 0.8}}
```

### Bass Clashing with Kick
```python
# Stronger kick avoidance
controls = {
    "rhythm_controls": {"kick_interaction_mode": "avoid_kick"},
    "drum_interaction_controls": {"kick_avoid_strength": 0.95}
}
```

### Not Enough Movement
```python
# More melodic variation
controls = {
    "melody_controls": {
        "root_note_emphasis": 0.4,      # Less root
        "interval_jump_magnitude": 0.7,  # Bigger jumps
        "note_range_octaves": 2          # Wider range
    }
}
```

---

## API Version

**Version:** 1.0.0
**Specification:** bass_v1.json
**Last Updated:** 2025-11-22
