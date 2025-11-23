import './PreviewPanel.css'

export default function PreviewPanel({ result, onDownload }) {
  if (!result) return null

  const { preview, metadata, theory_context } = result

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <h3>Generated Bass</h3>
        <button className="download-button" onClick={onDownload}>
          ⬇ Download MIDI
        </button>
      </div>

      <div className="preview-grid">
        <div className="preview-stat">
          <div className="stat-label">Notes</div>
          <div className="stat-value">{preview.note_count}</div>
        </div>

        <div className="preview-stat">
          <div className="stat-label">Duration</div>
          <div className="stat-value">{preview.length_seconds}s</div>
        </div>

        <div className="preview-stat">
          <div className="stat-label">Bars</div>
          <div className="stat-value">{preview.length_bars}</div>
        </div>

        <div className="preview-stat">
          <div className="stat-label">Tempo</div>
          <div className="stat-value">{theory_context.tempo_bpm} BPM</div>
        </div>
      </div>

      <div className="preview-details">
        <div className="detail-item">
          <span className="detail-label">Key:</span>
          <span className="detail-value">{theory_context.key_scale.replace(/_/g, ' ')}</span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Pitch Range:</span>
          <span className="detail-value">
            {preview.pitch_range.min} - {preview.pitch_range.max}
          </span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Velocity Range:</span>
          <span className="detail-value">
            {preview.velocity_range.min} - {preview.velocity_range.max}
          </span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Modes Used:</span>
          <div className="modes-list">
            {preview.modes_used.map((mode, idx) => (
              <span key={idx} className="mode-badge">
                {mode.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
