interface ModuleInfo {
  id: string
  name: string
  icon: string
  description: string
  buildType: string
  track: string
}

interface Props {
  modules: ModuleInfo[]
  onModuleSelect: (id: string) => void
}

export default function OverviewDashboard({ modules, onModuleSelect }: Props) {
  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      action()
    }
  }

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>📊 Pipeline Overview</h2>
        <p>AI Automated Insurance Survey Agent — Hybrid Pipeline Module Dashboard</p>
      </div>

      {/* System Status */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-value">8</div>
          <div className="metric-label">Pipeline Modules</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">2</div>
          <div className="metric-label">Processing Tracks</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">5</div>
          <div className="metric-label">RAG Collections</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">v0.1</div>
          <div className="metric-label">Pipeline Version</div>
        </div>
      </div>

      {/* Pipeline Flow Visualization */}
      <div className="card">
        <div className="card-header">
          <h3>🔀 Pipeline Flow</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="status-badge pending"><span className="status-dot" /> Fast Track</span>
            <span className="status-badge ready"><span className="status-dot" /> Full Track</span>
          </div>
        </div>
        <div className="pipeline-flow">
          <div className="pipeline-node" style={{ background: 'rgba(245,158,11,0.1)', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' }}>
            📱 Input
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node" style={{ background: 'rgba(245,158,11,0.1)', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' }}>
            🔀 Triage
          </div>
          <span className="pipeline-arrow">→</span>
          {modules.map((mod, i) => (
            <div key={mod.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div
                role="button"
                tabIndex={0}
                className="pipeline-node enabled"
                onClick={() => onModuleSelect(mod.id)}
                onKeyDown={(e) => handleKeyDown(e, () => onModuleSelect(mod.id))}
                style={{ cursor: 'pointer' }}
              >
                {mod.icon} {mod.id}
              </div>
              {i < modules.length - 1 && <span className="pipeline-arrow">→</span>}
            </div>
          ))}
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node" style={{ background: 'rgba(16,185,129,0.1)', borderColor: 'var(--accent-green)', color: 'var(--accent-green)' }}>
            ✅ Decision
          </div>
        </div>
      </div>

      {/* Module Cards */}
      <div className="overview-grid">
        {modules.map(mod => (
          <div
            role="button"
            tabIndex={0}
            key={mod.id}
            className="module-overview-card"
            onClick={() => onModuleSelect(mod.id)}
            onKeyDown={(e) => handleKeyDown(e, () => onModuleSelect(mod.id))}
          >
            <div className="module-id">{mod.id}</div>
            <h4>{mod.icon} {mod.name}</h4>
            <p>{mod.description}</p>
            <div className="card-footer">
              <span className="status-badge pending">
                <span className="status-dot" />
                Not started
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{mod.buildType}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Architecture Summary */}
      <div className="card">
        <div className="card-header">
          <h3>🏗️ Hybrid Architecture</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: 'var(--accent-cyan)' }}>
              ⚡ Fast Track (&lt;5 sec)
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              M0 → M2 (Nano) → M4 (lightweight) → M6 (simplified) → M7 (template)<br />
              Handles ~80% of simple, low-value claims with lightweight models.
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: 'var(--accent-purple-light)' }}>
              🔭 Full Track (30-120 sec)
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              M0 → M1 → M2 → M3 → M4 (dual) → M5 → M6 (RAG) → M7 (VLM)<br />
              Complex damage, fraud flags, high-value claims with full analysis.
            </p>
          </div>
        </div>
      </div>

      {/* Cross-Cutting Components */}
      <div className="card">
        <div className="card-header">
          <h3>🧩 Cross-Cutting Components</h3>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-value">📚</div>
            <div className="metric-label">RAG Knowledge Layer</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">🔄</div>
            <div className="metric-label">Cross-Training Engine</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">🎯</div>
            <div className="metric-label">Active Learning</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">📉</div>
            <div className="metric-label">Drift Monitor</div>
          </div>
        </div>
      </div>
    </div>
  )
}
