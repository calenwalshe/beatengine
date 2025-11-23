"""Pre-defined drum patterns for bass_v2 web UI.

Each pattern is a dictionary with:
- bars: list of bar objects
- each bar has steps: list of 16 step objects
- each step has: kick, hat, snare (bool)
- description: human-readable description
"""

from typing import Dict, Any


def create_drum_pattern(kick_positions, hat_positions, snare_positions, num_bars=4, description=""):
    """Helper to create drum pattern from position lists."""
    bars = []
    for bar_idx in range(num_bars):
        steps = []
        for step_idx in range(16):
            steps.append({
                "kick": step_idx in kick_positions,
                "hat": step_idx in hat_positions,
                "snare": step_idx in snare_positions,
            })
        bars.append({"steps": steps})

    return {
        "bars": bars,
        "description": description,
    }


# Pre-defined patterns
DRUM_PATTERNS: Dict[str, Any] = {

    # Berlin techno - syncopated, driving
    "berlin_syncopated": create_drum_pattern(
        kick_positions=[0, 6, 8, 14],
        hat_positions=[2, 4, 6, 10, 12, 14],
        snare_positions=[4, 12],
        num_bars=4,
        description="Modern Berlin techno: syncopated kicks, driving hats, classic backbeat"
    ),

    # Four on the floor - classic house/techno
    "four_on_floor": create_drum_pattern(
        kick_positions=[0, 4, 8, 12],
        hat_positions=[2, 6, 10, 14],
        snare_positions=[4, 12],
        num_bars=4,
        description="Classic four-on-the-floor: steady kicks, offbeat hats, backbeat snares"
    ),

    # Minimal techno - sparse, hypnotic
    "minimal_sparse": create_drum_pattern(
        kick_positions=[0, 8],
        hat_positions=[4, 12],
        snare_positions=[6],
        num_bars=4,
        description="Minimal techno: sparse kicks, minimal hats, occasional snare"
    ),

    # Hard techno - aggressive, dense
    "hard_techno": create_drum_pattern(
        kick_positions=[0, 3, 6, 8, 11, 14],
        hat_positions=[1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15],
        snare_positions=[4, 12],
        num_bars=4,
        description="Hard techno: aggressive kick pattern, dense hats, solid backbeat"
    ),

    # Broken beat - complex, shuffled
    "broken_beat": create_drum_pattern(
        kick_positions=[0, 5, 10, 13],
        hat_positions=[2, 4, 7, 9, 11, 14],
        snare_positions=[3, 11],
        num_bars=4,
        description="Broken beat: complex kick timing, shuffled hats, displaced snares"
    ),

    # Rolling techno - continuous, flowing
    "rolling_techno": create_drum_pattern(
        kick_positions=[0, 4, 8, 12],
        hat_positions=[1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15],
        snare_positions=[4, 12],
        num_bars=4,
        description="Rolling techno: four-on-floor kicks, continuous rolling hats, backbeat"
    ),

    # Half-time - slower feel
    "half_time": create_drum_pattern(
        kick_positions=[0, 8],
        hat_positions=[2, 6, 10, 14],
        snare_positions=[8],
        num_bars=4,
        description="Half-time: slow kick pattern, offbeat hats, single snare"
    ),

    # Industrial - mechanical, dark
    "industrial": create_drum_pattern(
        kick_positions=[0, 2, 8, 10],
        hat_positions=[4, 6, 12, 14],
        snare_positions=[5, 13],
        num_bars=4,
        description="Industrial: mechanical kick pattern, sparse hats, off-grid snares"
    ),

    # Acid techno - groovy, syncopated
    "acid_techno": create_drum_pattern(
        kick_positions=[0, 6, 8, 14],
        hat_positions=[1, 3, 5, 7, 9, 11, 13, 15],
        snare_positions=[4, 10],
        num_bars=4,
        description="Acid techno: syncopated kicks, 16th-note hats, displaced snares"
    ),

    # Detroit techno - classic, driving
    "detroit_classic": create_drum_pattern(
        kick_positions=[0, 4, 8, 12],
        hat_positions=[0, 2, 4, 6, 8, 10, 12, 14],
        snare_positions=[4, 12],
        num_bars=4,
        description="Detroit classic: four-on-floor, steady 8th-note hats, backbeat snares"
    ),

    # Dub techno - spacious, deep
    "dub_techno": create_drum_pattern(
        kick_positions=[0, 8],
        hat_positions=[2, 10],
        snare_positions=[6, 14],
        num_bars=4,
        description="Dub techno: spacious kicks, minimal hats, delayed snares"
    ),

    # Breakbeat - funky, broken
    "breakbeat": create_drum_pattern(
        kick_positions=[0, 3, 8, 13],
        hat_positions=[2, 5, 6, 10, 11, 14],
        snare_positions=[4, 9, 12],
        num_bars=4,
        description="Breakbeat: funky kick placement, complex hat pattern, multiple snares"
    ),
}


def get_pattern_names():
    """Return list of available pattern names."""
    return list(DRUM_PATTERNS.keys())


def get_pattern(name: str) -> Dict[str, Any]:
    """Get drum pattern by name."""
    return DRUM_PATTERNS.get(name, DRUM_PATTERNS["four_on_floor"])


def get_pattern_info():
    """Return pattern names and descriptions for UI display."""
    return [
        {
            "name": name,
            "description": pattern["description"]
        }
        for name, pattern in DRUM_PATTERNS.items()
    ]
