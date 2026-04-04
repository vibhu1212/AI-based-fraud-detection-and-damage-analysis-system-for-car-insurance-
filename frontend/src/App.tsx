import { useState, useCallback } from 'react'
import ModuleTestPanel from './components/ModuleTestPanel'
import PipelineTestMode from './components/PipelineTestMode'
import BenchmarkView from './components/BenchmarkView'
import OverviewDashboard from './components/OverviewDashboard'

type View = 'overview' | 'module' | 'pipeline' | 'benchmark'

interface ModuleInfo {
  id: string
  name: string
  icon: string
  description: string
  buildType: string
  track: string
}

const MODULES: ModuleInfo[] = [
  { id: 'M0', name: 'Privacy & Quality Gate', icon: '🔒', description: 'Image quality assessment + PII masking', buildType: 'Custom + Fine-tuned', track: 'Both' },
  { id: 'M1', name: 'Fraud Detection', icon: '🕵️', description: 'Deepfake/tamper detection + EXIF forensics', buildType: 'From Scratch', track: 'Deep' },
  { id: 'M2', name: 'Vehicle Identification', icon: '🚗', description: 'Indian make/model/year (200+ models)', buildType: 'Fine-tuned SOTA', track: 'Both' },
  { id: 'M3', name: 'Part Segmentation', icon: '🏷️', description: 'Door/bumper/hood/fender segmentation', buildType: 'Fine-tuned SOTA', track: 'Deep' },
  { id: 'M4', name: 'Damage Analysis', icon: '🔬', description: 'Dual-model: Mask R-CNN vs Custom UNet', buildType: 'Both (Benchmarked)', track: 'Both' },
  { id: 'M5', name: '3D Depth Estimation', icon: '🌐', description: 'NeRF/3DGS multi-view or monocular depth', buildType: 'Existing + Custom', track: 'Deep' },
  { id: 'M6', name: 'ICVE Pricing', icon: '💰', description: 'Rule-based cost engine (zero AI)', buildType: 'Custom Built', track: 'Both' },
  { id: 'M7', name: 'Report Generator', icon: '📝', description: 'VLM explainable report + GRAD-CAM', buildType: 'Fine-tuned VLM', track: 'Deep' },
]

function App() {
  const [currentView, setCurrentView] = useState<View>('overview')
  const [selectedModule, setSelectedModule] = useState<string>('M0')

  const handleModuleSelect = useCallback((moduleId: string) => {
    setSelectedModule(moduleId)
    setCurrentView('module')
  }, [])

  const renderContent = () => {
    switch (currentView) {
      case 'overview':
        return <OverviewDashboard modules={MODULES} onModuleSelect={handleModuleSelect} />
      case 'module':
        return <ModuleTestPanel module={MODULES.find(m => m.id === selectedModule)!} />
      case 'pipeline':
        return <PipelineTestMode modules={MODULES} />
      case 'benchmark':
        return <BenchmarkView />
      default:
        return <OverviewDashboard modules={MODULES} onModuleSelect={handleModuleSelect} />
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">🧠</div>
          <div>
            <h1>InsurAI</h1>
            <span>Module Testing Dashboard</span>
          </div>
        </div>

        {/* Navigation */}
        <div
          role="button"
          tabIndex={0}
          className={`sidebar-item ${currentView === 'overview' ? 'active' : ''}`}
          onClick={() => setCurrentView('overview')}
          onKeyDown={(e) => handleKeyDown(e, () => setCurrentView('overview'))}
        >
          <span className="module-icon">📊</span>
          Overview
        </div>
        <div
          role="button"
          tabIndex={0}
          className={`sidebar-item ${currentView === 'pipeline' ? 'active' : ''}`}
          onClick={() => setCurrentView('pipeline')}
          onKeyDown={(e) => handleKeyDown(e, () => setCurrentView('pipeline'))}
        >
          <span className="module-icon">⚡</span>
          Pipeline Test
        </div>
        <div
          role="button"
          tabIndex={0}
          className={`sidebar-item ${currentView === 'benchmark' ? 'active' : ''}`}
          onClick={() => setCurrentView('benchmark')}
          onKeyDown={(e) => handleKeyDown(e, () => setCurrentView('benchmark'))}
        >
          <span className="module-icon">📈</span>
          Benchmark (SOTA vs Scratch)
        </div>

        {/* Module List */}
        <div className="sidebar-section">
          <h3>Pipeline Modules</h3>
        </div>
        {MODULES.map(mod => (
          <div
            key={mod.id}
            className={`sidebar-item ${currentView === 'module' && selectedModule === mod.id ? 'active' : ''}`}
            onClick={() => handleModuleSelect(mod.id)}
            onKeyDown={(e) => handleKeyDown(e, () => handleModuleSelect(mod.id))}
          >
            <span className="module-tag" style={{ background: 'rgba(124,58,237,0.15)', color: '#a78bfa' }}>
              {mod.id}
            </span>
            <span className="module-icon">{mod.icon}</span>
            {mod.name}
          </div>
        ))}
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  )
}

export default App
