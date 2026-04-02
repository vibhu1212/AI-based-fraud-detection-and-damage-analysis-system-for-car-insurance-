import { useState, useRef, useCallback, useEffect } from 'react'

interface ModuleInfo {
  id: string
  name: string
  icon: string
  description: string
  buildType: string
  track: string
}

interface Props {
  module: ModuleInfo
}

const API_BASE = 'http://localhost:8000/api'

export default function ModuleTestPanel({ module }: Props) {
  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      action()
    }
  }

  const [images, setImages] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [results, setResults] = useState<object[]>([])
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [online, setOnline] = useState<boolean | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  // Check backend connectivity
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => setOnline(r.ok))
      .catch(() => setOnline(false))
  }, [])

  const handleFiles = useCallback((files: FileList) => {
    const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'))
    setImages(prev => [...prev, ...newFiles])
    newFiles.forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => setPreviews(prev => [...prev, e.target?.result as string])
      reader.readAsDataURL(file)
    })
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const processModule = useCallback(async () => {
    if (images.length === 0) return
    setIsProcessing(true)
    setResults([])
    setError(null)

    const formData = new FormData()
    images.forEach(img => formData.append('files', img))

    try {
      const res = await fetch(`${API_BASE}/modules/${module.id}/process`, {
        method: 'POST',
        body: formData,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`)
      setResults(Array.isArray(json) ? json : [json])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setIsProcessing(false)
    }
  }, [images, module.id])

  const clearAll = useCallback(() => {
    setImages([])
    setPreviews([])
    setResults([])
    setError(null)
  }, [])

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>{module.icon} {module.id}: {module.name}</h2>
        <p>
          {module.description} · Build: {module.buildType} · Track: {module.track}
          &nbsp;&nbsp;
          {online === null ? '⏳ Checking backend...' : online ? '🟢 Backend Live' : '🔴 Backend Offline'}
        </p>
      </div>

      {/* Upload Zone */}
      <div className="card">
        <div className="card-header">
          <h3>📤 Input Images</h3>
          {images.length > 0 && (
            <button className="btn btn-danger" onClick={clearAll}>Clear All</button>
          )}
        </div>
        <div
          role="button"
          tabIndex={0}
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInput.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInput.current?.click();
            }
          }}
        >
          <div className="upload-icon">📷</div>
          <h4>Drop images here or click to upload</h4>
          <p>Supports JPEG, PNG · Upload vehicle damage photos for analysis</p>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
        </div>

        {previews.length > 0 && (
          <div className="image-preview-grid">
            {previews.map((src, i) => (
              <div key={i} style={{ position: 'relative', display: 'inline-block' }}>
                <img src={src} alt={`Upload ${i + 1}`} />
                <button
                  aria-label="Remove image"
                  onClick={(e) => {
                    e.stopPropagation()
                    setImages(prev => prev.filter((_, idx) => idx !== i))
                    setPreviews(prev => prev.filter((_, idx) => idx !== i))
                    setResults(prev => prev.filter((_, idx) => idx !== i))
                  }}
                  style={{
                    position: 'absolute', top: 4, right: 4,
                    background: 'rgba(0,0,0,0.65)', color: '#fff',
                    border: 'none', borderRadius: '50%',
                    width: 22, height: 22, cursor: 'pointer',
                    fontSize: 13, lineHeight: '22px', textAlign: 'center', padding: 0,
                  }}
                  title="Remove image"
                >✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Process Button */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button
          className="btn btn-primary"
          onClick={processModule}
          disabled={images.length === 0 || isProcessing}
          aria-busy={isProcessing}
        >
          {isProcessing ? (
            <><span className="loading-spinner" />Processing...</>
          ) : (
            <>▶ Run {module.id}</>
          )}
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {images.length} image{images.length !== 1 ? 's' : ''} selected
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="results-panel" style={{ borderColor: '#ef4444' }}>
          <div className="results-header">
            <h4>❌ Error</h4>
          </div>
          <div className="results-body">
            <div className="json-viewer" style={{ color: '#ef4444' }}>{error}</div>
          </div>
        </div>
      )}

      {/* Results — one card per image */}
      {results.map((result, idx) => {
        const r = result as Record<string, unknown>
        const out = r.output as Record<string, unknown> | undefined
        const cleanResult = out
          ? { ...r, output: Object.fromEntries(Object.entries(out).filter(([k]) => k !== 'redacted_image_b64')) }
          : r

        return (
          <div key={idx} className="results-panel">
            <div className="results-header">
              <h4>
                <span className="status-badge ready"><span className="status-dot" /> Success</span>
                {module.id} · {String(r.filename)} ({String(r.processing_time_ms)}ms)
              </h4>
              <button
                className="btn btn-secondary"
                onClick={() => navigator.clipboard.writeText(JSON.stringify(cleanResult, null, 2))}
              >
                📋 Copy JSON
              </button>
            </div>

            {/* PII comparison (M0 only) */}
            {Boolean(out?.redacted_image_b64) && (
              <div style={{ padding: '20px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>🔒 PII Masking Result</span>
                  {out?.pii_found ? (
                    <span style={{ background: '#fef3c7', color: '#92400e', fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
                      ⚠️ {String(out?.faces_detected ?? 0)} face(s) · {String(out?.plates_detected ?? 0)} plate(s) masked
                    </span>
                  ) : (
                    <span style={{ background: '#d1fae5', color: '#065f46', fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
                      ✅ No PII detected
                    </span>
                  )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Original</p>
                    {previews[idx] && <img src={previews[idx]} alt="Original" style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border)' }} />}
                  </div>
                  <div>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Redacted (Gaussian Blur 99×99)</p>
                    {typeof out?.redacted_image_b64 === 'string' && (
                      <img
                        src={`data:image/jpeg;base64,${out?.redacted_image_b64}`}
                        alt="Redacted"
                        style={{ width: '100%', borderRadius: 8, border: '2px solid #7c3aed' }}
                      />
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Metrics */}
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <div className="metrics-grid">
                {Object.entries(out ?? r)
                  .filter(([, v]) => typeof v === 'number')
                  .slice(0, 4)
                  .map(([key, value]) => (
                    <div key={key} className="metric-card">
                      <div className="metric-value">
                        {typeof value === 'number' && value < 1 && value > 0
                          ? `${(value * 100).toFixed(1)}%`
                          : key.includes('time') || key.includes('ms') ? `${String(value)}ms` : String(value)}
                      </div>
                      <div className="metric-label">{key.replace(/_/g, ' ')}</div>
                    </div>
                  ))}
              </div>
            </div>

            {/* JSON */}
            <div className="results-body">
              <div className="json-viewer">{JSON.stringify(cleanResult, null, 2)}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
