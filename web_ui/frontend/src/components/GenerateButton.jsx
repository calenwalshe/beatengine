import './GenerateButton.css'

export default function GenerateButton({ onClick, isGenerating }) {
  return (
    <button
      className="generate-button"
      onClick={onClick}
      disabled={isGenerating}
    >
      {isGenerating ? (
        <>
          <span className="spinner"></span>
          Generating...
        </>
      ) : (
        <>
          ▶ Generate Bass
        </>
      )}
    </button>
  )
}
