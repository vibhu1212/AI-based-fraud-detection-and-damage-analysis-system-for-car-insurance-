import { useState, useCallback } from 'react'

interface BenchmarkResult {
  metric: string
  sota: number
  scratch: number
  unit: string
}

const INITIAL_RESULTS: BenchmarkResult[] = [
  { metric: 'mAP@50', sota: 0.72, scratch: 0.68, unit: '%' },
  { metric: 'mAP@50-95', sota: 0.45, scratch: 0.39, unit: '%' },
  { metric: 'IoU (Avg)', sota: 0.71, scratch: 0.64, unit: '%' },
  { metric: 'F1 Score', sota: 0.78, scratch: 0.73, unit: '%' },
  { metric: 'Precision', sota: 0.82, scratch: 0.76, unit: '%' },
  { metric: 'Recall', sota: 0.74, scratch: 0.70, unit: '%' },
  { metric: 'Inference Time', sota: 89, scratch: 42, unit: 'ms' },
  { metric: 'Model Size', sota: 178, scratch: 23, unit: 'MB' },
  { metric: 'Parameters', sota: 44.2, scratch: 5.8, unit: 'M' },
]

const DAMAGE_CLASSES = ['Dent', 'Scratch', 'Crack', 'Shatter', 'Deformation', 'Paint Damage', 'Glass Damage']

export default function BenchmarkView() {
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<BenchmarkResult[]>(INITIAL_RESULTS)
  const [perClassResults, setPerClassResults] = useState<{ cls: string; sota: number; scratch: number }[]>([])
  const [consensusMethod, setConsensusMethod] = useState('ensemble')

  const runBenchmark = useCallback(async () => {
    setIsRunning(true)
    await new Promise(resolve => setTimeout(resolve, 2500))

    // Randomize slightly for demo
    setResults(INITIAL_RESULTS.map(r => ({
      ...r,
      sota: r.unit === 'ms' || r.unit === 'MB' || r.unit === 'M' ? r.sota : +(r.sota + (Math.random() * 0.06 - 0.03)).toFixed(2),
      scratch: r.unit === 'ms' || r.unit === 'MB' || r.unit === 'M' ? r.scratch : +(r.scratch + (Math.random() * 0.06 - 0.03)).toFixed(2),
    })))

    setPerClassResults(DAMAGE_CLASSES.map(cls => ({
      cls,
      sota: +(0.6 + Math.random() * 0.3).toFixed(2),
      scratch: +(0.5 + Math.random() * 0.35).toFixed(2),
    })))

    setIsRunning(false)
  }, [])

  const formatValue = (val: number, unit: string) => {
    if (unit === '%') return `${(val * 100).toFixed(1)}%`
    if (unit === 'ms') return `${val}ms`
    if (unit === 'MB') return `${val}MB`
    if (unit === 'M') return `${val}M`
    return String(val)
  }

  const getWinner = (r: BenchmarkResult) => {
    if (r.metric === 'Inference Time' || r.metric === 'Model Size' || r.metric === 'Parameters') {
      return r.sota < r.scratch ? 'sota' : 'scratch'
    }
    return r.sota > r.scratch ? 'sota' : 'scratch'
  }

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>📈 SOTA vs Scratch Benchmark</h2>
        <p>Head-to-head comparison: Mask R-CNN (fine-tuned SOTA) vs Custom UNet + Attention (from scratch)</p>
      </div>

      <div className="card" style={{ borderColor: '#f59e0b', background: 'rgba(245,158,11,0.05)' }}>
        <div style={{ padding: '12px 16px', color: '#f59e0b', fontSize: 13 }}>
          ⚠️ <strong>Simulated data</strong> — Real model comparison will be available after M4 training is complete (Phase 2). Numbers below are placeholders.
        </div>
      </div>

      {/* Controls */}
      <div className="card">
        <div className="card-header">
          <h3>⚙️ Benchmark Configuration</h3>
          <button className="btn btn-primary" onClick={runBenchmark} disabled={isRunning}>
            {isRunning ? (
              <><span className="loading-spinner" /> Running Benchmark...</>
            ) : (
              <>▶ Run Benchmark</>
            )}
          </button>
        </div>
        <div className="config-panel">
          <div className="config-group">
            <label htmlFor="dataset">Dataset</label>
            <select id="dataset" defaultValue="cardd">
              <option value="cardd">CarDD + Custom (7 classes)</option>
              <option value="coco">COCO-Vehicles</option>
              <option value="custom">Custom Indian Only</option>
            </select>
          </div>
          <div className="config-group">
            <label htmlFor="consensus-method">Consensus Method</label>
            <select id="consensus-method" value={consensusMethod} onChange={e => setConsensusMethod(e.target.value)}>
              <option value="ensemble">Ensemble (Weighted Avg)</option>
              <option value="sota_priority">SOTA Priority</option>
              <option value="scratch_priority">Scratch Priority</option>
              <option value="best_confidence">Best Confidence</option>
            </select>
          </div>
          <div className="config-group">
            <label htmlFor="test-split">Test Split Size</label>
            <input id="test-split" type="number" defaultValue={500} min={50} max={5000} />
          </div>
          <div className="config-group">
            <label htmlFor="distillation-temp">Distillation Temperature</label>
            <input id="distillation-temp" type="number" defaultValue={3.0} step={0.5} min={1} max={10} />
          </div>
        </div>
      </div>

      {/* Side-by-Side Comparison */}
      <div className="benchmark-comparison">
        <div className="benchmark-column sota">
          <h4>🏆 SOTA Path — Mask R-CNN</h4>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Fine-tuned on CarDD + Custom annotated dataset
          </p>
          {results.map(r => (
            <div key={r.metric} className="benchmark-metric">
              <span className="label">{r.metric}</span>
              <span className="value" style={{ color: getWinner(r) === 'sota' ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                {formatValue(r.sota, r.unit)} {getWinner(r) === 'sota' ? '✓' : ''}
              </span>
            </div>
          ))}
        </div>

        <div className="benchmark-column scratch">
          <h4>🔨 Research Path — Custom UNet</h4>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Built from scratch with attention mechanism
          </p>
          {results.map(r => (
            <div key={r.metric} className="benchmark-metric">
              <span className="label">{r.metric}</span>
              <span className="value" style={{ color: getWinner(r) === 'scratch' ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                {formatValue(r.scratch, r.unit)} {getWinner(r) === 'scratch' ? '✓' : ''}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-Class Results */}
      {perClassResults.length > 0 && (
        <div className="results-panel">
          <div className="results-header">
            <h4>📊 Per-Class mAP Comparison</h4>
            <span className="status-badge ready"><span className="status-dot" /> Complete</span>
          </div>
          <div className="results-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {perClassResults.map(r => {
                const sotaWidth = r.sota * 100
                const scratchWidth = r.scratch * 100
                const sotaWins = r.sota > r.scratch
                return (
                  <div key={r.cls}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{r.cls}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        SOTA: {(r.sota * 100).toFixed(1)}% · Scratch: {(r.scratch * 100).toFixed(1)}%
                        {sotaWins ? ' · SOTA ✓' : ' · Scratch ✓'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 4, height: 8 }}>
                      <div style={{
                        width: `${sotaWidth}%`,
                        background: sotaWins ? 'var(--accent-cyan)' : 'rgba(6,182,212,0.3)',
                        borderRadius: 4,
                        transition: 'width 0.5s ease',
                      }} />
                      <div style={{
                        width: `${scratchWidth}%`,
                        background: !sotaWins ? 'var(--accent-pink)' : 'rgba(236,72,153,0.3)',
                        borderRadius: 4,
                        transition: 'width 0.5s ease',
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Cross-Training Status */}
      <div className="card">
        <div className="card-header">
          <h3>🔄 Cross-Training Flywheel Status</h3>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-value">{consensusMethod.replace('_', ' ')}</div>
            <div className="metric-label">Consensus Method</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">0</div>
            <div className="metric-label">Distillation Rounds</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">0</div>
            <div className="metric-label">Blind Spots Found</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">0</div>
            <div className="metric-label">Active Learning Samples</div>
          </div>
        </div>
      </div>
    </div>
  )
}
