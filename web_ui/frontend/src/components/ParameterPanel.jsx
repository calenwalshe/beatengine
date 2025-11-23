import { useState } from 'react'
import ControlGroup from './ControlGroup'
import './ParameterPanel.css'

const CONTROL_GROUPS = {
  mode_and_behavior_controls: {
    title: 'Mode & Behavior',
    controls: {
      strategy: {
        type: 'select',
        label: 'Mode Strategy',
        options: ['auto_from_drums', 'fixed_mode'],
      },
      fixed_mode: {
        type: 'select',
        label: 'Fixed Mode',
        options: [null, 'sub_anchor', 'root_fifth_driver', 'pocket_groove', 'rolling_ostinato', 'offbeat_stabs', 'lead_ish'],
      },
    },
  },
  rhythm_controls: {
    title: 'Rhythm',
    controls: {
      note_density: {
        type: 'slider',
        label: 'Note Density',
        min: 0.1,
        max: 1.0,
        step: 0.05,
      },
      rhythmic_complexity: {
        type: 'slider',
        label: 'Complexity',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      onbeat_offbeat_balance: {
        type: 'slider',
        label: 'Onbeat/Offbeat',
        min: -1.0,
        max: 1.0,
        step: 0.1,
      },
      kick_interaction_mode: {
        type: 'select',
        label: 'Kick Interaction',
        options: ['avoid_kick', 'reinforce_kick', 'balanced'],
      },
      swing_amount: {
        type: 'slider',
        label: 'Swing',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      groove_depth: {
        type: 'slider',
        label: 'Groove Depth',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
    },
  },
  melody_controls: {
    title: 'Melody',
    controls: {
      root_note_emphasis: {
        type: 'slider',
        label: 'Root Emphasis',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      interval_jump_magnitude: {
        type: 'slider',
        label: 'Interval Jumps',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      melodic_intensity: {
        type: 'slider',
        label: 'Melodic Intensity',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      note_range_octaves: {
        type: 'slider',
        label: 'Octave Range',
        min: 1,
        max: 3,
        step: 1,
      },
      base_octave: {
        type: 'slider',
        label: 'Base Octave',
        min: 1,
        max: 3,
        step: 1,
      },
    },
  },
  articulation_controls: {
    title: 'Articulation',
    controls: {
      gate_length: {
        type: 'slider',
        label: 'Gate Length',
        min: 0.1,
        max: 1.0,
        step: 0.05,
      },
      velocity_normal: {
        type: 'slider',
        label: 'Normal Velocity',
        min: 30,
        max: 127,
        step: 1,
      },
      velocity_accent: {
        type: 'slider',
        label: 'Accent Velocity',
        min: 30,
        max: 127,
        step: 1,
      },
      accent_chance: {
        type: 'slider',
        label: 'Accent Chance',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      accent_pattern_mode: {
        type: 'select',
        label: 'Accent Pattern',
        options: ['random', 'offbeat_focused', 'downbeat_focused'],
      },
      slide_chance: {
        type: 'slider',
        label: 'Slide Chance',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
    },
  },
  theory_controls: {
    title: 'Music Theory',
    controls: {
      harmonic_strictness: {
        type: 'slider',
        label: 'Harmonic Strictness',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      chord_tone_priority: {
        type: 'slider',
        label: 'Chord Tone Priority',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      minorness: {
        type: 'slider',
        label: 'Minor Feel',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
    },
  },
  drum_interaction_controls: {
    title: 'Drum Interaction',
    controls: {
      kick_avoid_strength: {
        type: 'slider',
        label: 'Kick Avoidance',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      snare_backbeat_preference: {
        type: 'slider',
        label: 'Snare Preference',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      hat_sync_strength: {
        type: 'slider',
        label: 'Hat Sync',
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
    },
  },
}

export default function ParameterPanel({ parameters, onChange }) {
  const [expandedGroups, setExpandedGroups] = useState({
    mode_and_behavior_controls: true,
    rhythm_controls: true,
    melody_controls: false,
    articulation_controls: false,
    theory_controls: false,
    drum_interaction_controls: false,
  })

  const toggleGroup = (groupName) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }))
  }

  return (
    <div className="parameter-panel">
      <h2>Parameters</h2>

      {Object.entries(CONTROL_GROUPS).map(([groupName, groupConfig]) => (
        <div key={groupName} className="control-section">
          <button
            className="section-header"
            onClick={() => toggleGroup(groupName)}
          >
            <span>{groupConfig.title}</span>
            <span className="expand-icon">
              {expandedGroups[groupName] ? '▼' : '▶'}
            </span>
          </button>

          {expandedGroups[groupName] && (
            <div className="section-content">
              <ControlGroup
                controls={groupConfig.controls}
                values={parameters[groupName] || {}}
                onChange={(key, value) => onChange(groupName, key, value)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
