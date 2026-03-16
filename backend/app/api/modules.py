"""
Module Testing API — routes image uploads to real backend services.
Endpoint: POST /api/modules/{module_id}/process
"""
import time
import tempfile
import logging
import numpy as np
import cv2
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()

NOT_AVAILABLE = {"status": "not_available", "message": "Module not yet implemented — coming in Phase 2"}

VALID_MODULES = {"M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"}


def _sanitize(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _read_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


@router.post("/modules/{module_id}/process")
async def process_module(module_id: str, files: List[UploadFile] = File(...)):
    module_id = module_id.upper()
    if module_id not in VALID_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_id}")

    results = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="All files must be images")

        data = await file.read()
        logger.info(f"[{module_id}] Processing: {file.filename} ({len(data)} bytes)")
        start = time.time()

        try:
            output = await _dispatch(module_id, data)
        except Exception as e:
            logger.exception(f"[{module_id}] Failed: {e}")
            output = {"status": "error", "message": str(e)}

        elapsed_ms = round((time.time() - start) * 1000)
        results.append({
            "module_id": module_id,
            "filename": file.filename,
            "processing_time_ms": elapsed_ms,
            "output": _sanitize(output),
        })

    return results if len(results) > 1 else results[0]


async def _dispatch(module_id: str, data: bytes) -> dict:
    if module_id == "M0":
        return _run_m0(data)
    elif module_id == "M2":
        return _run_m2(data)
    elif module_id == "M6":
        return _run_m6()
    else:
        return NOT_AVAILABLE


def _run_m0(data: bytes) -> dict:
    from app.services.quality_gate_enhanced import EnhancedQualityGateValidator
    from app.services.pii_masker import redact, image_to_b64

    img = _read_image(data)
    validator = EnhancedQualityGateValidator()
    quality = validator.validate_photo(img)
    quality["status"] = "passed" if quality.get("passed") else "failed"

    redacted_img, pii_meta = redact(img)

    return {
        **quality,
        **pii_meta,
        "redacted_image_b64": image_to_b64(redacted_img),
    }


def _run_m2(data: bytes) -> dict:
    from app.services.vehicle_classifier import VehicleClassifier
    # Write to temp file — YOLO needs a file path
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        classifier = VehicleClassifier()
        result = classifier.classify(tmp_path)
        if result is None:
            return {"status": "model_not_found", "message": "Vehicle classifier model weights not loaded. Train or download the model first."}
        result["status"] = "success"
        return result
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _run_m6() -> dict:
    """M6 is rule-based — returns a sample estimate with default inputs."""
    from app.services.cost_estimator_v2 import EnhancedCostEstimatorV2, VehicleInfo
    estimator = EnhancedCostEstimatorV2()
    vehicle = VehicleInfo(brand="Maruti Suzuki", model="Swift", segment="hatchback", age_years=3.0)
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=vehicle,
    )
    return {"status": "success", **estimate.__dict__}
