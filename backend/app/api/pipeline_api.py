"""
Pipeline API — Endpoints for running the full damage analysis pipeline.

POST /api/pipeline/run      — Run full pipeline on uploaded images
GET  /api/pipeline/health    — Check all module readiness
"""
import time
import logging
import numpy as np
import cv2
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


def _sanitize(obj):
    """Recursively convert numpy types to native Python types."""
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


@router.post("/pipeline/run")
async def run_pipeline(
    files: List[UploadFile] = File(...),
    modules: Optional[str] = Query(
        None,
        description="Comma-separated list of module IDs to run (e.g., 'M0,M2,M3,M4,M6,M7'). Default: all."
    ),
):
    """
    Run the full damage analysis pipeline on uploaded image(s).

    Returns a unified result containing:
    - Quality gate assessment
    - Vehicle identification
    - Part segmentation
    - Damage detection + classification + severity
    - Cost estimation
    - Survey report

    Modules M1 (Fraud) and M5 (3D Depth) are deferred.
    """
    from app.pipeline.orchestrator import PipelineOrchestrator

    if not files:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    # Parse module list
    module_list = None
    if modules:
        module_list = [m.strip().upper() for m in modules.split(",")]

    results = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not an image")

        data = await file.read() # type: ignore
        logger.info(f"[Pipeline] Processing: {file.filename} ({len(data)} bytes)")

        try:
            img = _read_image(data)
            orchestrator = PipelineOrchestrator()
            result = orchestrator.run(img, modules=module_list)
            result["filename"] = file.filename
            results.append(_sanitize(result))
        except Exception as e:
            logger.exception(f"[Pipeline] Failed for {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e),
            })

    return results if len(results) > 1 else results[0]


@router.get("/pipeline/health")
async def pipeline_health():
    """
    Check readiness of all pipeline modules.
    Returns per-module health status and available models.
    """
    module_status = {}

    # M0 — Quality Gate (always available, no model needed)
    module_status["M0"] = {"name": "Quality Gate + PII", "available": True, "model": "YOLO11m + Haar"}

    # M1 — Fraud Detection (deferred)
    module_status["M1"] = {"name": "Fraud Detection", "available": False, "model": "deferred"}

    # M2 — Vehicle Identification
    try:
        from app.services.vehicle_classifier import VehicleClassifier
        vc = VehicleClassifier()
        module_status["M2"] = {
            "name": "Vehicle Identification",
            "available": vc.is_available(),
            "model": "YOLOv8n-cls" if vc.is_available() else "not loaded",
        }
    except Exception:
        module_status["M2"] = {"name": "Vehicle Identification", "available": False, "model": "error"}

    # M3 — Part Segmentation
    try:
        from app.services.part_segmenter import PartSegmenter
        ps = PartSegmenter()
        module_status["M3"] = {
            "name": "Part Segmentation",
            "available": True,  # Heuristic always available
            "model": "yolo_seg" if ps.is_available() else "heuristic",
        }
    except Exception:
        module_status["M3"] = {"name": "Part Segmentation", "available": False, "model": "error"}

    # M4 — Damage Analysis
    try:
        from app.services.damage_analyzer import DamageAnalyzer
        da = DamageAnalyzer()
        module_status["M4"] = {
            "name": "Damage Analysis",
            "available": True,  # Heuristic always available
            "model": da.active_model,
        }
    except Exception:
        module_status["M4"] = {"name": "Damage Analysis", "available": False, "model": "error"}

    # M5 — 3D Depth (deferred)
    module_status["M5"] = {"name": "3D Depth Estimation", "available": False, "model": "deferred"}

    # M6 — Cost Estimation (always available, rule-based)
    module_status["M6"] = {"name": "ICVE Pricing", "available": True, "model": "rule-based v2.0"}

    # M7 — Report Generator (always available, template-based)
    module_status["M7"] = {"name": "Report Generator", "available": True, "model": "template-based v1.0"}

    # Overall
    available_count = sum(1 for m in module_status.values() if m["available"])
    total_count = len(module_status)

    return {
        "status": "healthy" if available_count >= 5 else "degraded",
        "modules_available": available_count,
        "modules_total": total_count,
        "modules": module_status,
    }
