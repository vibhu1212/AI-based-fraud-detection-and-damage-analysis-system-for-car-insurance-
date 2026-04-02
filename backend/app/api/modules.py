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

DEFERRED = {"status": "deferred", "message": "Module deferred to later phase (Fraud Detection / 3D Depth)"}

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
            output = await _dispatch(module_id, data) # type: ignore
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
    elif module_id == "M3":
        return _run_m3(data)
    elif module_id == "M4":
        return _run_m4(data)
    elif module_id == "M6":
        return _run_m6()
    elif module_id == "M7":
        return _run_m7(data)
    elif module_id in ("M1", "M5"):
        return DEFERRED
    else:
        return DEFERRED


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
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _run_m3(data: bytes) -> dict:
    """M3 — Part Segmentation."""
    from app.services.part_segmenter import PartSegmenter

    img = _read_image(data)
    segmenter = PartSegmenter()
    result = segmenter.segment(img)
    result["status"] = "success"
    return result


def _run_m4(data: bytes) -> dict:
    """M4 — Damage Detection + Classification + Severity."""
    from app.services.damage_analyzer import DamageAnalyzer
    from app.services.part_segmenter import PartSegmenter

    img = _read_image(data)

    # Run M3 first to get parts (for damage-to-part assignment)
    segmenter = PartSegmenter()
    parts_result = segmenter.segment(img)

    # Run damage analysis
    analyzer = DamageAnalyzer()
    result = analyzer.analyze(img, parts=parts_result.get("parts", []))
    result["status"] = "success"
    return result


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


def _run_m7(data: bytes) -> dict:
    """M7 — Report Generation (runs M0→M2→M3→M4→M6 internally for single-image test)."""
    from app.pipeline.orchestrator import PipelineOrchestrator

    img = _read_image(data)
    orchestrator = PipelineOrchestrator()
    result = orchestrator.run(img)

    # Return the report section plus a summary
    return {
        "status": result.get("status", "success"),
        "report": result.get("report", {}),
        "damages_found": len(result.get("damages", [])),
        "severity": result.get("severity", {}),
        "cost": result.get("cost", {}),
        "total_time_ms": result.get("total_time_ms", 0),
        "modules_executed": result.get("modules_executed", []),
        "modules_failed": result.get("modules_failed", []),
    }

