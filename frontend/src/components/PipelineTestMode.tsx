import { useState, useRef, useCallback } from 'react'

interface ModuleInfo {
  id: string
  name: string
  icon: string
  description: string
}

interface Props {
  modules: ModuleInfo[]
}

interface PipelineStep {
  moduleId: string
  status: 'pending' | 'running' | 'completed' | 'error'
  output?: object
  timeMs?: number
}

const API_BASE = 'http://localhost:8000/api'

export default function PipelineTestMode({ modules }: Props) {
  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      action()
    }
  }

  const [enabledModules, setEnabledModules] = useState<Set<string>>(
    new Set(['M0', 'M2', 'M4', 'M6', 'M7'])
  )
  const [track, setTrack] = useState<'fast' | 'full'>('fast')
  const [isRunning, setIsRunning] = useState(false)
  const [steps, setSteps] = useState<PipelineStep[]>([])
  const [image, setImage] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const toggleModule = useCallback((id: string) => {
    setEnabledModules(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const applyPreset = useCallback((preset: 'fast' | 'full') => {
    setTrack(preset)
    setEnabledModules(preset === 'fast'
      ? new Set(['M0', 'M2', 'M4', 'M6', 'M7'])
      : new Set(modules.map(m => m.id))
    )
  }, [modules])

  const runPipeline = useCallback(async () => {
    if (!image) return
    const orderedModules = modules.filter(m => enabledModules.has(m.id))
    setSteps(orderedModules.map(m => ({ moduleId: m.id, status: 'pending' as const })))
    setIsRunning(true)

    for (let i = 0; i < orderedModules.length; i++) {
      const mod = orderedModules[i]
      setSteps(prev => prev.map((s, idx) => idx === i ? { ...s, status: 'running' } : s))

      const t0 = Date.now()
      let output: object
      try {
        const fd = new FormData()
        fd.append('files', image)
        const res = await fetch(`${API_BASE}/modules/${mod.id}/process`, { method: 'POST', body: fd })
        output = await res.json()
      } catch (e: unknown) {
        output = { status: 'error', message: e instanceof Error ? e.message : 'Request failed' }
      }

      setSteps(prev => prev.map((s, idx) =>
        idx === i ? { ...s, status: 'completed', timeMs: Date.now() - t0, output } : s
      ))
    }

    setIsRunning(false)
  }, [modules, enabledModules, image])

  const totalTime = steps.reduce((sum, s) => sum + (s.timeMs || 0), 0)
  const completedSteps = steps.filter(s => s.status === 'completed').length

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>⚡ Pipeline Test Mode</h2>
        <p>Chain modules together and see data flow step-by-step through the pipeline</p>
      </div>

      {/* Image Upload */}
      <div className="card">
        <div className="card-header">
          <h3>📤 Input Image</h3>
          {image && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{image.name}</span>}
        </div>
        <div
          role="button"
          tabIndex={0}
          className="upload-zone"
          onClick={() => fileInput.current?.click()}
          onKeyDown={(e) => handleKeyDown(e, () => fileInput.current?.click())}
          style={{ padding: '20px', cursor: 'pointer' }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              fileInput.current?.click()
            }
          }}
        >
          <div className="upload-icon">📷</div>
          <h4>{image ? `✅ ${image.name}` : 'Click to upload an image for the pipeline'}</h4>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && setImage(e.target.files[0])}
          />
        </div>
      </div>

      {/* Track Selection */}
      <div className="card">
        <div className="card-header">
          <h3>🔀 Track Configuration</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`btn ${track === 'fast' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => applyPreset('fast')}
            >
              ⚡ Fast Track
            </button>
            <button
              className={`btn ${track === 'full' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => applyPreset('full')}
            >
              🔭 Full Track
            </button>
          </div>
        </div>

        {/* Module Toggle Grid */}
        <div className="pipeline-flow">
          {modules.map((mod, i) => (
            <div key={mod.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div
                role="button"
                tabIndex={0}
                className={`pipeline-node ${enabledModules.has(mod.id) ? 'enabled' : ''} ${
                  steps.find(s => s.moduleId === mod.id)?.status === 'completed' ? 'completed' :
                  steps.find(s => s.moduleId === mod.id)?.status === 'running' ? 'active' : ''
                }`}
                onClick={() => !isRunning && toggleModule(mod.id)}
                onKeyDown={(e) => !isRunning && handleKeyDown(e, () => toggleModule(mod.id))}
              >
                {mod.icon} {mod.id}
              </div>
              {i < modules.length - 1 && <span className="pipeline-arrow">→</span>}
            </div>
          ))}
        </div>

        <div style={{ padding: '0 16px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
          <button
            className="btn btn-primary"
            onClick={runPipeline}
            disabled={isRunning || enabledModules.size === 0 || !image}
            aria-busy={isRunning}
          >
            {isRunning ? (
              <>
                <span className="loading-spinner" />
                Running Pipeline...
              </>
            ) : (
              <>▶ Run Pipeline ({enabledModules.size} modules)</>
            )}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Track: {track.toUpperCase()} · {enabledModules.size} modules selected
          </span>
        </div>
      </div>

      {/* Results */}
      {steps.length > 0 && (
        <>
          {/* Summary Metrics */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value">{completedSteps}/{steps.length}</div>
              <div className="metric-label">Modules Completed</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{totalTime}ms</div>
              <div className="metric-label">Total Time</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{track.toUpperCase()}</div>
              <div className="metric-label">Track</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">
                {isRunning ? 'Running' : completedSteps === steps.length ? 'Done' : 'Idle'}
              </div>
              <div className="metric-label">Status</div>
            </div>
          </div>

          {/* Step-by-Step Results */}
          {steps.map((step, idx) => {
            const mod = modules.find(m => m.id === step.moduleId)!
            return (
              <div key={step.moduleId} className="results-panel" style={{ opacity: step.status === 'pending' ? 0.5 : 1 }}>
                <div className="results-header">
                  <h4>
                    <span className={`status-badge ${step.status === 'completed' ? 'ready' : step.status === 'running' ? 'running' : 'pending'}`}>
                      <span className="status-dot" />
                      {step.status === 'completed' ? 'Done' : step.status === 'running' ? 'Running' : 'Pending'}
                    </span>
                    Step {idx + 1}: {mod.icon} {mod.id} — {mod.name}
                  </h4>
                  {step.timeMs && (
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {step.timeMs}ms
                    </span>
                  )}
                </div>
                {step.output && (
                  <div className="results-body">
                    <div className="json-viewer" style={{ maxHeight: 200 }}>
                      {JSON.stringify(step.output, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
