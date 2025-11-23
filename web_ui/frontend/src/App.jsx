import { useState, useEffect } from 'react'
import './App.css'
import PresetManager from './components/PresetManager'
import DrumPatternSelector from './components/DrumPatternSelector'
import TheoryControls from './components/TheoryControls'
import ParameterPanel from './components/ParameterPanel'
import GenerateButton from './components/GenerateButton'
import PreviewPanel from './components/PreviewPanel'
import { useParameters } from './hooks/useParameters'

function App() {
  const {
    parameters,
    updateParameter,
    loadPreset,
    resetParameters,
  } = useParameters()

  const [drumPatterns, setDrumPatterns] = useState([])
  const [presets, setPresets] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationResult, setGenerationResult] = useState(null)
  const [error, setError] = useState(null)

  // Load drum patterns and presets on mount
  useEffect(() => {
    fetchDrumPatterns()
    fetchPresets()
  }, [])

  const fetchDrumPatterns = async () => {
    try {
      const response = await fetch('/api/drum-patterns')
      const data = await response.json()
      setDrumPatterns(data.patterns || [])
    } catch (err) {
      console.error('Failed to load drum patterns:', err)
    }
  }

  const fetchPresets = async () => {
    try {
      const response = await fetch('/api/presets')
      const data = await response.json()
      setPresets(data.presets || [])
    } catch (err) {
      console.error('Failed to load presets:', err)
    }
  }

  const handleGenerate = async () => {
    setIsGenerating(true)
    setError(null)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          drum_pattern: parameters.drumPattern,
          theory_context: parameters.theoryContext,
          controls: parameters.controls,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setGenerationResult(data)
      } else {
        setError(data.error || 'Generation failed')
      }
    } catch (err) {
      setError(err.message || 'Network error')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleLoadPreset = async (presetName) => {
    try {
      const response = await fetch(`/api/presets/${presetName}`)
      const preset = await response.json()
      loadPreset(preset)
    } catch (err) {
      console.error('Failed to load preset:', err)
      setError('Failed to load preset')
    }
  }

  const handleSavePreset = async (presetData) => {
    try {
      const response = await fetch('/api/presets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...presetData,
          drum_pattern: parameters.drumPattern,
          theory_context: parameters.theoryContext,
          controls: parameters.controls,
        }),
      })

      const data = await response.json()

      if (data.success) {
        fetchPresets() // Reload presets
      } else {
        setError(data.error || 'Failed to save preset')
      }
    } catch (err) {
      setError(err.message || 'Network error')
    }
  }

  const handleDownload = () => {
    if (generationResult && generationResult.filename) {
      window.location.href = `/api/download/${generationResult.filename}`
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Bass V2 Generator</h1>
        <p>Techno Bass Line Generator</p>
      </header>

      <div className="app-container">
        <div className="sidebar">
          <PresetManager
            presets={presets}
            onLoadPreset={handleLoadPreset}
            onSavePreset={handleSavePreset}
            onReset={resetParameters}
          />

          <DrumPatternSelector
            patterns={drumPatterns}
            selected={parameters.drumPattern}
            onChange={(pattern) => updateParameter('drumPattern', pattern)}
          />

          <TheoryControls
            theoryContext={parameters.theoryContext}
            onChange={(updates) => updateParameter('theoryContext', {
              ...parameters.theoryContext,
              ...updates
            })}
          />
        </div>

        <div className="main-content">
          <ParameterPanel
            parameters={parameters.controls}
            onChange={(controlGroup, key, value) => {
              updateParameter('controls', {
                ...parameters.controls,
                [controlGroup]: {
                  ...parameters.controls[controlGroup],
                  [key]: value
                }
              })
            }}
          />

          <GenerateButton
            onClick={handleGenerate}
            isGenerating={isGenerating}
          />

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {generationResult && (
            <PreviewPanel
              result={generationResult}
              onDownload={handleDownload}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
