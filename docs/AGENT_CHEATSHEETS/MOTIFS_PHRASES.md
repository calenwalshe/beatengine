# Motifs and Phrases

Motif presets (intervals from root):
- `root_only`: [0]
- `root_fifth`: [0, 7]
- `root_fifth_octave`: [0, 7, 12]
- `root_b7`: [0, 10]
- `pentatonic_bounce`: [0, 7, 12, 7]
- `dorian_sway`: [0, 9, 7, 14]

Phrase patterns (per bar root offsets):
- `rise`: [0, 5, 7, 12]
- `bounce`: [0, 10, 0, 7]
- `fall`: [0, -2, -4, -7]
- `surge`: [0, 12, 7, 14]
- `collapse`: [0, -5, -7, -12]

Usage in bass generators:
- MVP (`bass_cli`): anchors at step 0 (root/fifth alternating), pulses from motif along offbeats.
- Scored (`combo_cli`): same motifs/phrases but pulse steps are chosen by drum-aware scoring per bar.

