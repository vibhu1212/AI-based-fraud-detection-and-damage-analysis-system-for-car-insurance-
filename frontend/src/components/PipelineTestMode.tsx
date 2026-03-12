import { useState, useCallback } from 'react'

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
  status: 'pending' | 'running' | 'completed' | 'skipped'
  output?: object
  timeMs?: number
}

export default function PipelineTestMode({ modules }: Props) {
  const [enabledModules, setEnabledModules] = useState<Set<string>>(
    new Set(['M0', 'M2', 'M4', 'M6', 'M7'])
  )
  const [track, setTrack] = useState<'fast' | 'full'>('fast')
  const [isRunning, setIsRunning] = useState(false)
  const [steps, setSteps] = useState<PipelineStep[]>([])

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
    if (preset === 'fast') {
      setEnabledModules(new Set(['M0', 'M2', 'M4', 'M6', 'M7']))
    } else {
      setEnabledModules(new Set(modules.map(m => m.id)))
    }
  }, [modules])

  const runPipeline = useCallback(async () => {
    const orderedModules = modules.filter(m => enabledModules.has(m.id))
    const initialSteps: PipelineStep[] = orderedModules.map(m => ({
      moduleId: m.id,
      status: 'pending' as const,
    }))
    setSteps(initialSteps)
    setIsRunning(true)

    for (let i = 0; i < orderedModules.length; i++) {
      setSteps(prev => prev.map((s, idx) =>
        idx === i ? { ...s, status: 'running' } : s
      ))

      const delay = 800 + Math.random() * 1500
      await new Promise(resolve => setTimeout(resolve, delay))

      setSteps(prev => prev.map((s, idx) =>
        idx === i ? {
          ...s,
          status: 'completed',
          timeMs: Math.round(delay),
          output: {
            module: orderedModules[i].id,
            status: 'success',
            confidence: +(0.8 + Math.random() * 0.19).toFixed(2),
            items_detected: Math.floor(Math.random() * 5) + 1,
          }
        } : s
      ))
    }

    setIsRunning(false)
  }, [modules, enabledModules])

  const totalTime = steps.reduce((sum, s) => sum + (s.timeMs || 0), 0)
  const completedSteps = steps.filter(s => s.status === 'completed').length

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>⚡ Pipeline Test Mode</h2>
        <p>Chain modules together and see data flow step-by-step through the pipeline</p>
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
                className={`pipeline-node ${enabledModules.has(mod.id) ? 'enabled' : ''} ${
                  steps.find(s => s.moduleId === mod.id)?.status === 'completed' ? 'completed' :
                  steps.find(s => s.moduleId === mod.id)?.status === 'running' ? 'active' : ''
                }`}
                onClick={() => !isRunning && toggleModule(mod.id)}
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
            disabled={isRunning || enabledModules.size === 0}
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
