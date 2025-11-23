import './TheoryControls.css'

const KEY_SCALES = [
  'C_minor', 'D_minor', 'E_minor', 'F_minor', 'G_minor', 'A_minor', 'B_minor',
  'C_major', 'D_major', 'E_major', 'F_major', 'G_major', 'A_major', 'B_major',
  'D_dorian', 'E_phrygian', 'G_mixolydian'
]

export default function TheoryControls({ theoryContext, onChange }) {
  return (
    <div className="theory-controls">
      <h3>Music Theory</h3>

      <div className="control-group">
        <label>Key/Scale</label>
        <select
          value={theoryContext.key_scale}
          onChange={(e) => onChange({ key_scale: e.target.value })}
        >
          {KEY_SCALES.map((key) => (
            <option key={key} value={key}>
              {key.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div className="control-group">
        <label>Tempo (BPM)</label>
        <div className="tempo-control">
          <input
            type="range"
            min="100"
            max="160"
            step="1"
            value={theoryContext.tempo_bpm}
            onChange={(e) => onChange({ tempo_bpm: Number(e.target.value) })}
          />
          <span className="tempo-value">{theoryContext.tempo_bpm}</span>
        </div>
      </div>
    </div>
  )
}
