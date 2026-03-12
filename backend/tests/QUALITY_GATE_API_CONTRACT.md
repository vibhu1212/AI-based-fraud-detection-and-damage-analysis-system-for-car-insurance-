# Quality Gate Validation - API Contract for Dev 1

## Overview
Quality Gate Validation (P0 Lock 1) is the first step in the AI processing pipeline. It validates photo quality before proceeding with VIN OCR and damage detection.

## Automatic Trigger
The quality gate validation task is **automatically triggered** when a customer submits a claim via:
```
POST /api/claims/{claim_id}/submit
```

## Celery Task Details

### Task Name
```
app.tasks.quality_gate.validate_claim_quality
```

### Input
```python
claim_id: str  # UUID of the claim to validate
```

### Output
```json
{
  "status": "completed",
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "all_passed": true,
  "total_photos": 5,
  "results": [
    {
      "photo_id": "660e8400-e29b-41d4-a716-446655440001",
      "capture_angle": "FRONT",
      "passed": true,
      "failure_reasons": []
    },
    {
      "photo_id": "660e8400-e29b-41d4-a716-446655440002",
      "capture_angle": "VIN",
      "passed": false,
      "failure_reasons": [
        "Image too blurry (score: 85.23, threshold: 100.0)",
        "Poor exposure (brightness: 35.12, range: 40.0-220.0)"
      ]
    }
  ]
}
```

## Quality Checks Performed

### 1. Blur Detection (Laplacian Variance)
- **Method**: Calculates variance of Laplacian operator on grayscale image
- **Threshold**: 100.0
- **Pass Criteria**: variance >= 100.0
- **Higher score = sharper image**

### 2. Exposure Detection (Mean Brightness)
- **Method**: Calculates mean pixel brightness on grayscale image
- **Range**: 40.0 - 220.0
- **Pass Criteria**: brightness within range
- **Detects under-exposed (too dark) and over-exposed (too bright) images**

### 3. Glare Detection (Bright Spot Ratio)
- **Method**: Counts pixels with brightness > 240
- **Threshold**: 5% of total pixels
- **Pass Criteria**: bright_pixel_ratio <= 0.05
- **Detects excessive glare/reflections**

### 4. Vehicle Presence Check (Mock)
- **Method**: Simple brightness check (mock for demo)
- **Threshold**: mean brightness > 30.0
- **Pass Criteria**: vehicle detected
- **Production**: Would use a trained classifier**

## Database Side Effects

### 1. QualityGateResult Records Created
For each photo validated, a record is created in `quality_gate_results` table:
```python
{
  "id": "uuid",
  "claim_id": "uuid",
  "media_id": "uuid",
  "passed": true/false,
  "blur_score": 125.45,
  "exposure_score": 145.23,
  "glare_score": 0.023,
  "vehicle_present": true,
  "failure_reasons": ["reason1", "reason2"],
  "quality_gate_version": "1.0.0",
  "created_at": "2026-01-26T10:30:00Z"
}
```

### 2. Claim P0 Lock Updated
```python
claim.p0_locks["quality_gate_passed"] = True  # or False
```

### 3. Claim Status Transition
- **If all photos pass**: `claim.status = ANALYZING`
- **If any photo fails**: `claim.status = NEEDS_RESUBMIT`

## Frontend Integration

### 1. Display Quality Gate Status
Query the claim to check P0 lock status:
```typescript
const claim = await api.get(`/api/claims/${claimId}`);
const qualityGatePassed = claim.p0_locks.quality_gate_passed;
```

### 2. Display Quality Gate Results
Query quality gate results for detailed feedback:
```sql
SELECT * FROM quality_gate_results WHERE claim_id = ?
```

### 3. Handle NEEDS_RESUBMIT Status
If quality gate fails, display failure reasons to customer:
```typescript
if (claim.status === 'NEEDS_RESUBMIT') {
  // Fetch quality gate results
  const results = await db.query('quality_gate_results', { claim_id });
  
  // Display failed photos and reasons
  results.filter(r => !r.passed).forEach(result => {
    console.log(`Photo ${result.media_id} failed:`);
    result.failure_reasons.forEach(reason => {
      console.log(`  - ${reason}`);
    });
  });
}
```

### 4. Real-Time Updates (Future)
When WebSocket is implemented, listen for quality gate completion:
```typescript
ws.on('P0_LOCK_COMPLETED', (event) => {
  if (event.lock_name === 'quality_gate_passed') {
    // Refresh claim status
    refreshClaim();
  }
});
```

## Testing

### Manual Test
```bash
# 1. Start Redis
docker-compose up redis -d

# 2. Start Celery worker
cd backend
./start_celery_worker.sh

# 3. Submit a claim via API
curl -X POST http://localhost:8000/api/claims/{claim_id}/submit \
  -H "Authorization: Bearer {token}"

# 4. Check Celery logs for task execution
# 5. Check claim status and P0 locks
```

### Automated Test
```bash
cd backend
python test_quality_gate.py
```

## Error Handling

### Task Failures
- If task fails, claim remains in SUBMITTED status
- Error logged to Celery logs
- Frontend should show "Processing..." state
- Retry mechanism: Celery will retry failed tasks automatically

### Photo Download Failures
- If photo cannot be downloaded from storage, task fails for that photo
- Entire claim validation fails
- Error message includes photo ID

### Invalid Image Files
- If image cannot be loaded by OpenCV, validation fails
- Error message: "Failed to load image: {object_key}"

## Performance

### Expected Processing Time
- **Per photo**: ~100-500ms
- **5 photos**: ~0.5-2.5 seconds
- **Depends on**: Image size, CPU speed, storage I/O

### Optimization Tips
- Use thumbnails for quality checks (future enhancement)
- Parallel processing of photos (future enhancement)
- GPU acceleration for vehicle detection (production)

## Next Steps (P0 Lock 2)
After quality gate passes, the next task in the pipeline is:
- **VIN OCR and Hashing** (Task 4.2)
- Depends on: Quality gate passed
- Extracts VIN from VIN photo
- Generates vin_hash for duplicate detection

## Questions for Dev 1?
Contact Dev 2 if you need:
- Additional quality metrics
- Different thresholds
- Custom validation rules
- Integration support
