import './DrumPatternSelector.css'

export default function DrumPatternSelector({ patterns, selected, onChange }) {
  return (
    <div className="drum-pattern-selector">
      <h3>Drum Pattern</h3>
      <select
        className="pattern-select"
        value={selected}
        onChange={(e) => onChange(e.target.value)}
      >
        {patterns.map((pattern) => (
          <option key={pattern.name} value={pattern.name}>
            {pattern.name.replace(/_/g, ' ')}
          </option>
        ))}
      </select>
      <p className="pattern-description">
        {patterns.find(p => p.name === selected)?.description || ''}
      </p>
    </div>
  )
}
