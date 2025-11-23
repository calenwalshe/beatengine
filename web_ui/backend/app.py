"""Flask API server for bass_v2 generator.

Provides HTTP endpoints for:
- Generating bass MIDI files
- Managing presets
- Listing available drum patterns
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.techno_engine.bass_v2 import generate_bass_midi_from_drums, convert_to_midi_events
from src.techno_engine.bass_v2_types import TheoryContext
from src.techno_engine.simple_midi_writer import write_simple_midi
from web_ui.backend.drum_patterns import DRUM_PATTERNS
from web_ui.backend.bass_generator_api import generate_bass_with_params

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

# Paths
BASE_DIR = Path(__file__).parent
PRESETS_DIR = BASE_DIR / "presets"
OUTPUT_DIR = BASE_DIR.parent.parent / "output" / "web_ui_generated"

# Ensure directories exist
PRESETS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate bass MIDI from parameters.

    Request body:
    {
        "drum_pattern": "berlin_syncopated" | "four_on_floor" | custom object,
        "theory_context": {"key_scale": "D_minor", "tempo_bpm": 130},
        "controls": {all bass_v2 control parameters}
    }
    """
    try:
        data = request.json

        # Generate bass
        result = generate_bass_with_params(
            drum_pattern_name=data.get('drum_pattern', 'berlin_syncopated'),
            theory_params=data.get('theory_context', {}),
            control_params=data.get('controls', {}),
            output_dir=OUTPUT_DIR
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/presets', methods=['GET'])
def list_presets():
    """List all available presets."""
    try:
        presets = []
        for preset_file in PRESETS_DIR.glob("*.json"):
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
                presets.append({
                    "name": preset_file.stem,
                    "display_name": preset_data.get("display_name", preset_file.stem),
                    "description": preset_data.get("description", ""),
                })

        return jsonify({"presets": presets}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/presets/<name>', methods=['GET'])
def get_preset(name):
    """Load a specific preset."""
    try:
        preset_path = PRESETS_DIR / f"{name}.json"

        if not preset_path.exists():
            return jsonify({"error": "Preset not found"}), 404

        with open(preset_path, 'r') as f:
            preset_data = json.load(f)

        return jsonify(preset_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/presets', methods=['POST'])
def save_preset():
    """Save a new preset.

    Request body:
    {
        "name": "my_preset",
        "display_name": "My Preset",
        "description": "Description...",
        "controls": {all parameters}
    }
    """
    try:
        data = request.json
        name = data.get('name', '').strip()

        if not name:
            return jsonify({"error": "Preset name required"}), 400

        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).lower()
        preset_path = PRESETS_DIR / f"{safe_name}.json"

        preset_data = {
            "name": safe_name,
            "display_name": data.get('display_name', name),
            "description": data.get('description', ''),
            "drum_pattern": data.get('drum_pattern', 'berlin_syncopated'),
            "theory_context": data.get('theory_context', {}),
            "controls": data.get('controls', {}),
            "created_at": datetime.now().isoformat(),
        }

        with open(preset_path, 'w') as f:
            json.dump(preset_data, f, indent=2)

        return jsonify({"success": True, "name": safe_name}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/drum-patterns', methods=['GET'])
def list_drum_patterns():
    """List available drum patterns."""
    patterns = [
        {"name": name, "description": pattern.get("description", "")}
        for name, pattern in DRUM_PATTERNS.items()
    ]
    return jsonify({"patterns": patterns}), 200


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a generated MIDI file."""
    try:
        filepath = OUTPUT_DIR / filename

        if not filepath.exists():
            return jsonify({"error": "File not found"}), 404

        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename,
            mimetype='audio/midi'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "bass_v2_api"}), 200


if __name__ == '__main__':
    print("=" * 60)
    print("Bass V2 Generator API Server")
    print("=" * 60)
    print()
    print(f"Server running on: http://localhost:5001")
    print(f"Presets directory: {PRESETS_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Available endpoints:")
    print("  POST   /api/generate        - Generate bass MIDI")
    print("  GET    /api/presets         - List presets")
    print("  GET    /api/presets/<name>  - Load preset")
    print("  POST   /api/presets         - Save preset")
    print("  GET    /api/drum-patterns   - List drum patterns")
    print("  GET    /api/download/<file> - Download MIDI file")
    print("  GET    /health              - Health check")
    print()

    app.run(debug=True, host='localhost', port=5001)
