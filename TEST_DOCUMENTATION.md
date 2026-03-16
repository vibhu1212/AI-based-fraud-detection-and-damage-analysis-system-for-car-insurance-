# Test Documentation & Cases Mapping

## 1. Overview
This document outlines the testing strategy, types of tests performed, and maps the critical test cases for the **AI Automated Insurance Survey Agent**. Testing ensures that all modules (M0-M7) function individually and sequentially in the hybrid pipeline.

## 2. Testing Environments
- **Local Development Environment:** `pytest` for backend API and ML models. Vite dev server for frontend dashboard.
- **CI/CD Pipeline (Planned):** GitHub Actions to run unit and integration tests on every PR.

## 3. Test Types
1. **Unit Testing:** Validates individual FastAPI endpoints and pure Python functions (e.g., pricing calculations).
2. **Module Integration Testing:** Validates the sequential JSON data flow from M0 through M7.
3. **Model Evaluation:** Benchmarks ML models (YOLO, SegFormer, UNet) against established datasets (CarDD, custom Indian vehicles dataset) using mAP, IoU, and F1 scores.

## 4. Test Cases Mapping

| Test ID | Module | Feature | Test Scenario | Expected Outcome | Status |
|---------|--------|---------|---------------|------------------|--------|
| TC-M0-01 | M0 | Quality Gate | Upload blurred image | API returns `passed: false`, `blur_score` above threshold | Implemented |
| TC-M0-02 | M0 | Quality Gate | Upload dark/overexposed image | API returns `passed: false`, `exposure_score` flagged | Implemented |
| TC-M0-03 | M0 | Quality Gate | Upload low-resolution image | API returns `passed: false`, resolution check failed | Implemented |
| TC-M0-04 | M0 | PII Masking | Upload image with visible person | `faces_detected >= 1`, head region blurred in `redacted_image_b64` | Implemented |
| TC-M0-05 | M0 | PII Masking | Upload image with visible license plate | `plates_detected >= 1`, plate region blurred in `redacted_image_b64` | Implemented |
| TC-M0-06 | M0 | PII Masking | Upload image with no PII | `pii_found: false`, `redacted_image_b64` returned unchanged | Implemented |
| TC-M0-07 | M0 | Multi-image | Upload 3 images in one request | API returns array of 3 result objects, each with own `filename` and `output` | Implemented |
| TC-M0-08 | M0 | API contract | Check response shape | Response: `{module_id, filename, processing_time_ms, output: {..., redacted_image_b64}}` | Implemented |
| TC-M1-01 | M1 | Fraud Detect | Upload known manipulated image | Fraud score > 0.85, claim flagged | Planned |
| TC-M2-01 | M2 | Vehicle ID | Upload Hyundai Creta photo | JSON output: `{"make": "Hyundai", "model": "Creta", "confidence": >0.90}` | Planned |
| TC-M4-01 | M4 | Damage Detect | Upload image of scratched bumper | JSON output includes bounding box/mask for 'scratch' on 'bumper' | Planned |
| TC-M6-01 | M6 | ICVE Pricing | Submit valid parts calculation request | Returns calculated total including correct depreciation and labor | Implemented |
| TC-M7-01 | M7 | Report Gen | Request final report for valid claim | Returns PDF URL and JSON summary with accurate citations | Planned |
| TC-E2E-01 | All | Fast Track | Submit minor damage claim | System routes to Fast Track, completes M0,M2,M4,M6,M7 in < 5s | Planned |
