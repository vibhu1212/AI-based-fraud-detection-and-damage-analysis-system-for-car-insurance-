"""
Pipeline Orchestrator — Chains modules sequentially with error handling.

Execution order: M0 → M2 → M3 → M4 → M6 → M7
(M1 Fraud and M5 3D Depth are deferred to later phases)
"""
import cv2
import numpy as np
import logging
import time
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the full damage analysis pipeline.
    Each module runs sequentially; output from one feeds into the next.
    Gracefully handles module failures — pipeline continues with available data.
    """

    PIPELINE_VERSION = "1.0.0"

    # Default execution order (M1, M5 deferred)
    DEFAULT_MODULES = ["M0", "M2", "M3", "M4", "M6", "M7"]

    def __init__(self):
        # Lazy-load module dependencies to avoid circular imports
        self._m0_quality = None
        self._m0_pii = None
        self._m2_classifier = None
        self._m3_segmenter = None
        self._m4_analyzer = None
        self._m6_estimator = None
        self._m7_reporter = None

    def run(
        self,
        image: np.ndarray,
        modules: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline on a single image.

        Args:
            image: BGR image (numpy array)
            modules: Optional list of module IDs to run (default: all)
            config: Optional configuration overrides

        Returns:
            Unified pipeline result dict
        """
        start_time = time.time()
        modules = modules or self.DEFAULT_MODULES
        config = config or {}

        result = {
            "pipeline_version": self.PIPELINE_VERSION,
            "modules_executed": [],
            "modules_skipped": [],
            "modules_failed": [],
            "errors": [],
        }

        # Module outputs accumulate here
        context: Dict[str, Any] = {}

        # ============================================================
        # M0 — Quality Gate + PII Masking
        # ============================================================
        if "M0" in modules:
            try:
                logger.info("[Pipeline] Running M0: Quality Gate + PII Masking")
                m0_start = time.time()

                from app.services.quality_gate_enhanced import EnhancedQualityGateValidator
                from app.services.pii_masker import redact, image_to_b64

                validator = EnhancedQualityGateValidator()
                quality = validator.validate_photo(image)

                redacted_img, pii_meta = redact(image)

                context["m0"] = {
                    **quality,
                    **pii_meta,
                    "status": "passed" if quality.get("passed") else "failed",
                    "redacted_image_b64": image_to_b64(redacted_img),
                    "inference_time_ms": round((time.time() - m0_start) * 1000),
                }

                # Use redacted image for subsequent modules
                processed_image = redacted_img

                result["quality_gate"] = context["m0"]
                result["modules_executed"].append("M0")
                logger.info(f"[Pipeline] M0 complete: passed={quality.get('passed')}")

            except Exception as e:
                logger.error(f"[Pipeline] M0 failed: {e}")
                result["modules_failed"].append("M0")
                result["errors"].append(f"M0: {str(e)}")
                processed_image = image
        else:
            result["modules_skipped"].append("M0")
            processed_image = image

        # ============================================================
        # M2 — Vehicle Identification
        # ============================================================
        if "M2" in modules:
            try:
                logger.info("[Pipeline] Running M2: Vehicle Identification")
                m2_start = time.time()

                from app.services.vehicle_classifier import VehicleClassifier

                # Write to temp file — YOLO needs file path
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    cv2.imwrite(tmp.name, processed_image)
                    tmp_path = tmp.name

                try:
                    classifier = VehicleClassifier()
                    veh_result = classifier.classify(tmp_path)
                    if veh_result is None:
                        veh_result = {
                            "vehicle_type": "CAR",
                            "confidence": 0.0,
                            "raw_class": "unknown",
                            "display_name": "Unknown Vehicle",
                            "status": "model_not_available",
                        }
                    else:
                        veh_result["status"] = "success"
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

                veh_result["inference_time_ms"] = round((time.time() - m2_start) * 1000)
                context["m2"] = veh_result
                result["vehicle_id"] = veh_result
                result["modules_executed"].append("M2")
                logger.info(f"[Pipeline] M2 complete: {veh_result.get('vehicle_type')}")

            except Exception as e:
                logger.error(f"[Pipeline] M2 failed: {e}")
                result["modules_failed"].append("M2")
                result["errors"].append(f"M2: {str(e)}")
                context["m2"] = {"vehicle_type": "CAR", "confidence": 0.0, "status": "error"}
                result["vehicle_id"] = context["m2"]
        else:
            result["modules_skipped"].append("M2")
            context["m2"] = {"vehicle_type": "CAR", "confidence": 0.0}

        # ============================================================
        # M3 — Part Segmentation
        # ============================================================
        if "M3" in modules:
            try:
                logger.info("[Pipeline] Running M3: Part Segmentation")
                m3_start = time.time()

                from app.services.part_segmenter import PartSegmenter

                segmenter = PartSegmenter()
                m3_result = segmenter.segment(processed_image)

                context["m3"] = m3_result
                result["parts"] = m3_result.get("parts", [])
                result["modules_executed"].append("M3")
                logger.info(f"[Pipeline] M3 complete: {m3_result.get('total_parts_detected')} parts")

            except Exception as e:
                logger.error(f"[Pipeline] M3 failed: {e}")
                result["modules_failed"].append("M3")
                result["errors"].append(f"M3: {str(e)}")
                context["m3"] = {"parts": []}
                result["parts"] = []
        else:
            result["modules_skipped"].append("M3")
            context["m3"] = {"parts": []}

        # ============================================================
        # M4 — Damage Detection + Classification + Severity
        # ============================================================
        if "M4" in modules:
            try:
                logger.info("[Pipeline] Running M4: Damage Analysis")
                m4_start = time.time()

                from app.services.damage_analyzer import DamageAnalyzer

                analyzer = DamageAnalyzer()
                m4_result = analyzer.analyze(
                    processed_image,
                    parts=context.get("m3", {}).get("parts", [])
                )

                context["m4"] = m4_result
                result["damages"] = m4_result.get("damages", [])
                result["severity"] = m4_result.get("severity", {})
                result["modules_executed"].append("M4")
                logger.info(f"[Pipeline] M4 complete: {m4_result.get('total_damages')} damages, "
                            f"severity={m4_result.get('severity', {}).get('severity_level')}")

            except Exception as e:
                logger.error(f"[Pipeline] M4 failed: {e}")
                result["modules_failed"].append("M4")
                result["errors"].append(f"M4: {str(e)}")
                context["m4"] = {"damages": [], "severity": {}}
                result["damages"] = []
                result["severity"] = {}
        else:
            result["modules_skipped"].append("M4")
            context["m4"] = {"damages": [], "severity": {}}

        # ============================================================
        # M6 — Cost Estimation (ICVE)
        # ============================================================
        if "M6" in modules:
            try:
                logger.info("[Pipeline] Running M6: Cost Estimation")
                m6_start = time.time()

                from app.services.cost_estimator_v2 import EnhancedCostEstimatorV2, VehicleInfo

                estimator = EnhancedCostEstimatorV2()

                # Build vehicle info from M2 output
                vehicle_type = context.get("m2", {}).get("vehicle_type", "CAR")
                vehicle_info = VehicleInfo(
                    brand="Unknown",
                    model="Unknown",
                    segment="hatchback",
                    age_years=3.0,
                    vehicle_type=vehicle_type.lower() if vehicle_type else "car",
                )

                # Estimate cost for each damage
                damages = context.get("m4", {}).get("damages", [])
                line_items = []
                total_cost = 0

                for dmg in damages:
                    damage_type_key = self._map_damage_to_cost_key(
                        dmg.get("damage_type", "dent"),
                        dmg.get("part", "unknown")
                    )
                    severity = dmg.get("severity", "moderate")

                    try:
                        estimate = estimator.estimate_damage_cost(
                            damage_type=damage_type_key,
                            severity=severity,
                            vehicle_info=vehicle_info,
                        )
                        cost = estimate.breakdown.claim_settlement_estimate
                        total_cost += cost

                        line_items.append({
                            "part": dmg.get("part", "unknown"),
                            "damage_type": dmg.get("damage_type", "unknown"),
                            "severity": severity,
                            "repair_cost": estimate.breakdown.adjusted_repair_cost,
                            "replace_cost": estimate.breakdown.adjusted_replace_cost,
                            "final_cost": cost,
                            "depreciation_pct": estimate.breakdown.depreciation_percent,
                        })
                    except Exception as cost_err:
                        logger.warning(f"Cost estimation failed for {damage_type_key}: {cost_err}")
                        # Fallback cost based on severity
                        fallback = {"minor": 3000, "moderate": 8000, "severe": 15000, "totalled": 30000}
                        cost = fallback.get(severity, 5000)
                        total_cost += cost
                        line_items.append({
                            "part": dmg.get("part", "unknown"),
                            "damage_type": dmg.get("damage_type", "unknown"),
                            "severity": severity,
                            "final_cost": cost,
                            "source": "fallback",
                        })

                cost_result = {
                    "status": "success",
                    "total_estimate": total_cost,
                    "currency": "INR",
                    "line_items": line_items,
                    "vehicle_info": {
                        "type": vehicle_type,
                        "segment": vehicle_info.segment,
                    },
                    "inference_time_ms": round((time.time() - m6_start) * 1000),
                }

                context["m6"] = cost_result
                result["cost"] = cost_result
                result["modules_executed"].append("M6")
                logger.info(f"[Pipeline] M6 complete: ₹{total_cost:,}")

            except Exception as e:
                logger.error(f"[Pipeline] M6 failed: {e}")
                result["modules_failed"].append("M6")
                result["errors"].append(f"M6: {str(e)}")
                context["m6"] = {"total_estimate": 0, "line_items": []}
                result["cost"] = context["m6"]
        else:
            result["modules_skipped"].append("M6")
            context["m6"] = {"total_estimate": 0, "line_items": []}

        # ============================================================
        # M7 — Report Generation
        # ============================================================
        if "M7" in modules:
            try:
                logger.info("[Pipeline] Running M7: Report Generation")

                from app.services.report_generator import ReportGenerator

                reporter = ReportGenerator()
                m7_result = reporter.generate(
                    image=processed_image,
                    quality_gate=context.get("m0", {}),
                    vehicle_id=context.get("m2", {}),
                    parts=context.get("m3", {}).get("parts", []),
                    damages=context.get("m4", {}).get("damages", []),
                    severity=context.get("m4", {}).get("severity", {}),
                    cost_estimate=context.get("m6", {}),
                )

                context["m7"] = m7_result
                result["report"] = m7_result
                result["modules_executed"].append("M7")
                logger.info("[Pipeline] M7 complete: report generated")

            except Exception as e:
                logger.error(f"[Pipeline] M7 failed: {e}")
                result["modules_failed"].append("M7")
                result["errors"].append(f"M7: {str(e)}")
                result["report"] = {}
        else:
            result["modules_skipped"].append("M7")

        # ============================================================
        # Finalize
        # ============================================================
        result["total_time_ms"] = round((time.time() - start_time) * 1000)
        result["status"] = "success" if not result["modules_failed"] else "partial"

        logger.info(f"[Pipeline] Complete in {result['total_time_ms']}ms — "
                     f"executed: {result['modules_executed']}, "
                     f"failed: {result['modules_failed']}")

        return result

    @staticmethod
    def _map_damage_to_cost_key(damage_type: str, part: str) -> str:
        """
        Map damage_type + part to a cost database key.
        Format: 'part-damage_type' (e.g., 'front-bumper-dent')
        """
        # Map part names to cost DB format
        part_mappings = {
            "front_bumper": "front-bumper",
            "rear_bumper": "rear-bumper",
            "hood": "bonnet",
            "trunk": "boot",
            "front_left_door": "doorouter",
            "front_right_door": "doorouter",
            "rear_left_door": "doorouter",
            "rear_right_door": "doorouter",
            "front_left_fender": "fender",
            "front_right_fender": "fender",
            "rear_left_fender": "quarter-panel",
            "rear_right_fender": "quarter-panel",
            "windshield": "windscreen",
            "rear_window": "rear-windscreen",
            "front_left_headlight": "Headlight",
            "front_right_headlight": "Headlight",
            "rear_left_taillight": "tail-light",
            "rear_right_taillight": "tail-light",
            "roof": "roof",
            "grille": "grille",
            "vehicle_body": "front-bumper",  # fallback
        }

        part_key = part_mappings.get(part, "front-bumper")

        # Map damage type
        damage_mappings = {
            "dent": "dent",
            "scratch": "scratch",
            "crack": "crack",
            "shatter": "crack",
            "deformation": "dent",
            "paint_damage": "scratch",
            "glass_damage": "crack",
        }

        damage_key = damage_mappings.get(damage_type, "dent")

        return f"{part_key}-{damage_key}"
