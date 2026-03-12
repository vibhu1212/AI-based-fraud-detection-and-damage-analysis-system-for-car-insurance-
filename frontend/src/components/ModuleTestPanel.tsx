import { useState, useRef, useCallback } from 'react'

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

// Simulated module outputs for demo
function getSimulatedOutput(moduleId: string): object {
  const outputs: Record<string, object> = {
    M0: {
      quality_score: 0.92,
      blur_score: 0.15,
      exposure_score: 0.88,
      resolution: [1920, 1080],
      pii_masked: true,
      faces_detected: 2,
      plates_detected: 1,
      sanitized_image_paths: ['storage/masked_img_001.jpg'],
      processing_time_ms: 142,
    },
    M1: {
      fraud_score: 0.12,
      fraud_type: 'none',
      exif_valid: true,
      exif_anomalies: [],
      gan_fingerprint_detected: false,
      rag_similar_frauds: [],
      escalation_required: false,
      processing_time_ms: 891,
    },
    M2: {
      make: 'Maruti Suzuki',
      model: 'Baleno',
      year: 2022,
      trim: 'Zeta',
      body_type: 'hatchback',
      segment: 'premium_hatchback',
      confidence: 0.94,
      policy_match_verified: true,
      processing_time_ms: 234,
    },
    M3: {
      parts: [
        { name: 'front_bumper', bounding_box: [100, 200, 400, 350], confidence: 0.91 },
        { name: 'left_headlight', bounding_box: [120, 180, 200, 270], confidence: 0.88 },
        { name: 'hood', bounding_box: [80, 50, 500, 200], confidence: 0.95 },
        { name: 'left_fender', bounding_box: [30, 150, 120, 400], confidence: 0.87 },
      ],
      total_parts_detected: 4,
      processing_time_ms: 567,
    },
    M4: {
      damages: [
        { type: 'dent', severity: 'moderate', part: 'front_bumper', area_percentage: 12.5, confidence: 0.87, model_source: 'ensemble', sota_confidence: 0.89, scratch_confidence: 0.85 },
        { type: 'scratch', severity: 'minor', part: 'left_fender', area_percentage: 3.2, confidence: 0.92, model_source: 'sota', sota_confidence: 0.92, scratch_confidence: 0.78 },
      ],
      cross_training_metrics: { sota_map: 0.72, scratch_map: 0.68, consensus_method: 'ensemble' },
      processing_time_ms: 1243,
    },
    M5: {
      depth_map_path: 'storage/depth_maps/claim_001.png',
      max_deformation_depth_mm: 8.3,
      damage_volume_cm3: 42.7,
      reconstruction_method: 'monocular_unet',
      point_cloud_vertices: 125840,
      processing_time_ms: 3421,
    },
    M6: {
      line_items: [
        { part: 'front_bumper', damage_type: 'dent', repair_cost: 4500, replace_cost: 12000, recommended: 'repair', depreciation_pct: 15, final_cost: 3825, source_citation: 'OEM Catalog #MS-2022-FB-001' },
        { part: 'left_fender', damage_type: 'scratch', repair_cost: 1800, replace_cost: 6500, recommended: 'repair', depreciation_pct: 15, final_cost: 1530, source_citation: 'OEM Catalog #MS-2022-LF-003' },
      ],
      total_estimate: 5355,
      confidence_bounds: [4500, 6200],
      currency: 'INR',
      processing_time_ms: 89,
    },
    M7: {
      report_status: 'generated',
      report_format: ['PDF', 'JSON'],
      grad_cam_overlays: 2,
      citations_count: 8,
      all_facts_grounded: true,
      vlm_confidence: 0.91,
      audit_hash: 'sha256:a8f3c2e1...',
      processing_time_ms: 4567,
    },
  }
  return outputs[moduleId] || { error: 'Module not configured' }
}

export default function ModuleTestPanel({ module }: Props) {
  const [images, setImages] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<object | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback((files: FileList) => {
    const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'))
    setImages(prev => [...prev, ...newFiles])
    newFiles.forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        setPreviews(prev => [...prev, e.target?.result as string])
      }
      reader.readAsDataURL(file)
    })
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const processModule = useCallback(async () => {
    setIsProcessing(true)
    setResult(null)
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 2000))
    const output = getSimulatedOutput(module.id)
    setResult(output)
    setIsProcessing(false)
  }, [module.id])

  const clearAll = useCallback(() => {
    setImages([])
    setPreviews([])
    setResult(null)
  }, [])

  return (
    <div className="module-test-panel">
      <div className="page-header">
        <h2>{module.icon} {module.id}: {module.name}</h2>
        <p>{module.description} · Build: {module.buildType} · Track: {module.track}</p>
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
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInput.current?.click()}
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
              <img key={i} src={src} alt={`Upload ${i + 1}`} />
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
        >
          {isProcessing ? (
            <>
              <span className="loading-spinner" />
              Processing...
            </>
          ) : (
            <>▶ Run {module.id}</>
          )}
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {images.length} image{images.length !== 1 ? 's' : ''} selected
        </span>
      </div>

      {/* Results */}
      {result && (
        <div className="results-panel">
          <div className="results-header">
            <h4>
              <span className="status-badge ready"><span className="status-dot" /> Success</span>
              {module.id} Output
            </h4>
            <button
              className="btn btn-secondary"
              onClick={() => navigator.clipboard.writeText(JSON.stringify(result, null, 2))}
            >
              📋 Copy JSON
            </button>
          </div>

          {/* Metrics */}
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <div className="metrics-grid">
              {Object.entries(result as Record<string, unknown>)
                .filter(([, v]) => typeof v === 'number')
                .slice(0, 4)
                .map(([key, value]) => (
                  <div key={key} className="metric-card">
                    <div className="metric-value">
                      {typeof value === 'number' && value < 1 && value > 0
                        ? `${(value as number * 100).toFixed(1)}%`
                        : key.includes('time') || key.includes('ms')
                          ? `${value}ms`
                          : String(value)}
                    </div>
                    <div className="metric-label">{key.replace(/_/g, ' ')}</div>
                  </div>
                ))}
            </div>
          </div>

          {/* JSON Output */}
          <div className="results-body">
            <div className="json-viewer">
              {JSON.stringify(result, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
