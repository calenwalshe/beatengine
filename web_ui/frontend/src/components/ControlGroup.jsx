import './ControlGroup.css'

export default function ControlGroup({ controls, values, onChange }) {
  const renderControl = (key, config) => {
    const value = values[key]

    if (config.type === 'slider') {
      return (
        <div key={key} className="control-item">
          <div className="control-header">
            <label>{config.label}</label>
            <span className="control-value">{value}</span>
          </div>
          <input
            type="range"
            min={config.min}
            max={config.max}
            step={config.step}
            value={value}
            onChange={(e) => onChange(key, Number(e.target.value))}
          />
        </div>
      )
    }

    if (config.type === 'select') {
      return (
        <div key={key} className="control-item">
          <label>{config.label}</label>
          <select
            value={value || ''}
            onChange={(e) => {
              const val = e.target.value === 'null' ? null : e.target.value
              onChange(key, val)
            }}
          >
            {config.options.map((option) => (
              <option key={String(option)} value={option === null ? 'null' : option}>
                {option === null ? 'None' : String(option).replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
      )
    }

    if (config.type === 'toggle') {
      return (
        <div key={key} className="control-item toggle-item">
          <label>{config.label}</label>
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => onChange(key, e.target.checked)}
          />
        </div>
      )
    }

    return null
  }

  return (
    <div className="control-group">
      {Object.entries(controls).map(([key, config]) => renderControl(key, config))}
    </div>
  )
}
