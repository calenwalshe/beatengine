import { useState } from 'react'

const DEFAULT_PARAMETERS = {
  drumPattern: 'berlin_syncopated',
  theoryContext: {
    key_scale: 'D_minor',
    tempo_bpm: 130,
  },
  controls: {
    mode_and_behavior_controls: {
      strategy: 'auto_from_drums',
      fixed_mode: null,
    },
    rhythm_controls: {
      rhythmic_complexity: 0.5,
      note_density: 0.5,
      onbeat_offbeat_balance: 0.0,
      kick_interaction_mode: 'avoid_kick',
      swing_amount: 0.0,
      groove_depth: 0.5,
      use_triplets: false,
      pattern_length_bars: 2,
    },
    melody_controls: {
      note_range_octaves: 1,
      base_octave: 2,
      root_note_emphasis: 0.8,
      interval_jump_magnitude: 0.4,
      melodic_intensity: 0.5,
    },
    articulation_controls: {
      velocity_normal: 80,
      velocity_accent: 110,
      accent_chance: 0.3,
      accent_pattern_mode: 'offbeat_focused',
      gate_length: 0.5,
      tie_notes: false,
      slide_chance: 0.1,
      humanize_timing: 0.1,
      humanize_velocity: 0.1,
    },
    theory_controls: {
      harmonic_strictness: 0.9,
      chord_tone_priority: 0.8,
      minorness: 0.5,
    },
    drum_interaction_controls: {
      kick_avoid_strength: 0.8,
      snare_backbeat_preference: 0.5,
      hat_sync_strength: 0.5,
    },
  },
}

export function useParameters() {
  const [parameters, setParameters] = useState(DEFAULT_PARAMETERS)

  const updateParameter = (key, value) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const loadPreset = (preset) => {
    setParameters({
      drumPattern: preset.drum_pattern || DEFAULT_PARAMETERS.drumPattern,
      theoryContext: preset.theory_context || DEFAULT_PARAMETERS.theoryContext,
      controls: preset.controls || DEFAULT_PARAMETERS.controls,
    })
  }

  const resetParameters = () => {
    setParameters(DEFAULT_PARAMETERS)
  }

  return {
    parameters,
    updateParameter,
    loadPreset,
    resetParameters,
  }
}
