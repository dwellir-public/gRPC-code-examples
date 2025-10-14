import { X, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import './JsonViewerModal.css'

function JsonViewerModal({ liquidation, onClose }) {
  const [copied, setCopied] = useState(false)

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(liquidation, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-container">
        <div className="modal-header">
          <h3>Liquidation Details (JSON)</h3>
          <div className="modal-actions">
            <button
              className="modal-button copy-json-btn"
              onClick={copyJson}
              title="Copy JSON"
            >
              {copied ? <Check size={18} /> : <Copy size={18} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              className="modal-button close-btn"
              onClick={onClose}
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          <pre className="json-content">
            <code>{JSON.stringify(liquidation, null, 2)}</code>
          </pre>
        </div>
      </div>
    </div>
  )
}

export default JsonViewerModal
