# Bass V2 Web UI - Frontend

React-based web interface for the Bass V2 Generator.

## Project Structure

```
frontend/
├── index.html                  # Entry HTML
├── package.json                # Dependencies
├── vite.config.js              # Vite configuration
├── src/
│   ├── main.jsx                # React entry point
│   ├── App.jsx                 # Main app component
│   ├── App.css                 # Main app styles
│   ├── index.css               # Global styles
│   ├── components/
│   │   ├── PresetManager.jsx   # Preset management
│   │   ├── DrumPatternSelector.jsx
│   │   ├── TheoryControls.jsx  # Key/tempo controls
│   │   ├── ParameterPanel.jsx  # Main parameter panel
│   │   ├── ControlGroup.jsx    # Individual control groups
│   │   ├── GenerateButton.jsx  # Generate button
│   │   ├── PreviewPanel.jsx    # Result preview
│   │   └── *.css               # Component styles
│   └── hooks/
│       └── useParameters.js    # Parameter state management
└── public/
```

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The app will run on `http://localhost:3000` and proxy API requests to the Flask backend on port 5001.

## Features

### Sidebar Controls

- **Preset Manager**: Load/save presets, reset to defaults
- **Drum Pattern Selector**: Choose from 12 pre-defined patterns
- **Music Theory**: Key/scale and tempo (BPM) controls

### Main Panel

- **Parameter Groups** (collapsible):
  - Mode & Behavior: Mode selection strategy
  - Rhythm: Density, complexity, kick interaction
  - Melody: Root emphasis, interval jumps, octave range
  - Articulation: Gate length, velocity, accents
  - Music Theory: Harmonic strictness, chord tones
  - Drum Interaction: Kick avoidance, snare/hat sync

- **Generate Button**: Trigger bass generation

- **Preview Panel**: Shows generated MIDI stats:
  - Note count, duration, bars, tempo
  - Key, pitch range, velocity range
  - Modes used per bar

## API Integration

The frontend communicates with the Flask backend via:

- `GET /api/presets` - List presets
- `GET /api/presets/<name>` - Load preset
- `POST /api/presets` - Save preset
- `GET /api/drum-patterns` - List patterns
- `POST /api/generate` - Generate bass
- `GET /api/download/<filename>` - Download MIDI

## Component Hierarchy

```
App
├── PresetManager
├── DrumPatternSelector
├── TheoryControls
├── ParameterPanel
│   └── ControlGroup (6x)
│       └── Slider/Select/Toggle controls
├── GenerateButton
└── PreviewPanel
```

## State Management

State is managed through the `useParameters` hook, which provides:

- `parameters`: Current parameter values
- `updateParameter`: Update a single parameter
- `loadPreset`: Load preset data
- `resetParameters`: Reset to defaults

## Styling

- Dark theme with accent color (#00d9ff)
- Responsive grid layouts
- Smooth transitions and animations
- Custom range slider and select styling
- Collapsible sections for organization

## Build

```bash
npm run build
```

Outputs optimized production build to `dist/`.
