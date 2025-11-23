import { useState } from 'react'
import './PresetManager.css'

export default function PresetManager({ presets, onLoadPreset, onSavePreset, onReset }) {
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [presetName, setPresetName] = useState('')
  const [presetDisplayName, setPresetDisplayName] = useState('')
  const [presetDescription, setPresetDescription] = useState('')

  const handleSave = () => {
    if (!presetName.trim()) {
      alert('Please enter a preset name')
      return
    }

    onSavePreset({
      name: presetName.toLowerCase().replace(/[^a-z0-9_-]/g, '_'),
      display_name: presetDisplayName || presetName,
      description: presetDescription,
    })

    setShowSaveDialog(false)
    setPresetName('')
    setPresetDisplayName('')
    setPresetDescription('')
  }

  return (
    <div className="preset-manager">
      <h3>Presets</h3>

      <div className="preset-list">
        {presets.map((preset) => (
          <button
            key={preset.name}
            className="preset-button"
            onClick={() => onLoadPreset(preset.name)}
            title={preset.description}
          >
            {preset.display_name}
          </button>
        ))}
      </div>

      <div className="preset-actions">
        <button
          className="button-secondary"
          onClick={() => setShowSaveDialog(true)}
        >
          Save Preset
        </button>
        <button
          className="button-secondary"
          onClick={onReset}
        >
          Reset
        </button>
      </div>

      {showSaveDialog && (
        <div className="modal-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h4>Save Preset</h4>

            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                placeholder="my_preset"
              />
            </div>

            <div className="form-group">
              <label>Display Name</label>
              <input
                type="text"
                value={presetDisplayName}
                onChange={(e) => setPresetDisplayName(e.target.value)}
                placeholder="My Preset"
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                value={presetDescription}
                onChange={(e) => setPresetDescription(e.target.value)}
                placeholder="Describe this preset..."
                rows={3}
              />
            </div>

            <div className="modal-actions">
              <button className="button-secondary" onClick={() => setShowSaveDialog(false)}>
                Cancel
              </button>
              <button className="button-primary" onClick={handleSave}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
