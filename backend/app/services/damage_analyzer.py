"""
M4 — Damage Analysis Service
Detects, classifies, and scores damage severity.

Supports two detection paths:
1. YOLOv8m — fast bounding-box detection (from train_yolo_damage.py)
2. Mask R-CNN — instance segmentation (from train_maskrcnn_merged.py)
Falls back gracefully to basic CV analysis when no model weights are available.
"""
import cv2 # type: ignore
import numpy as np # type: ignore
import logging
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# 7 damage classes (matches training scripts)
DAMAGE_CLASSES = [
    "dent", "scratch", "crack", "shatter",
    "deformation", "paint_damage", "glass_damage",
]

# Severity weights per damage type (higher = more severe inherently)
DAMAGE_TYPE_SEVERITY_WEIGHT = {
    "dent": 0.5,
    "scratch": 0.3,
    "crack": 0.7,
    "shatter": 0.9,
    "deformation": 0.8,
    "paint_damage": 0.2,
    "glass_damage": 0.85,
}

# Severity thresholds
SEVERITY_THRESHOLDS = {
    "minor": (0.0, 0.30),
    "moderate": (0.30, 0.60),
    "severe": (0.60, 0.85),
    "totalled": (0.85, 1.0),
}

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
RUNS_DIR = Path(__file__).parent.parent.parent / "runs"


class DamageAnalyzer:
    """
    Damage detection, classification, and severity scoring.

    Loads best available model:
    1. YOLOv8m damage weights (fastest, bbox + class)
    2. Mask R-CNN via Detectron2 (slower, instance segmentation masks)
    3. Heuristic fallback (basic CV edge/color analysis)
    """

    def __init__(self):
        self.yolo_model = None
        self.maskrcnn_predictor = None
        self.maskrcnn_cfg = None
        self.active_model = "none"

        # Try loading models in priority order
        self._try_load_yolo()
        if self.yolo_model is None:
            self._try_load_maskrcnn()

        if self.active_model == "none":
            logger.warning("No damage detection model found — using heuristic fallback")
            self.active_model = "heuristic"
        else:
            logger.info(f"Damage analyzer loaded: {self.active_model}")

    def _try_load_yolo(self):
        """Try to load YOLOv8 damage detection model."""
        candidates = [
            MODELS_DIR / "yolov8m_damage_detection_v1.pt",
            RUNS_DIR / "damage_detection" / "yolov8m_damage_v1" / "weights" / "best.pt",
            MODELS_DIR / "best_damage.pt",
        ]
        for path in candidates:
            if path.exists():
                try:
                    import torch # type: ignore
                    from ultralytics import YOLO # type: ignore

                    original_load = torch.load
                    def patched_load(*args, **kwargs):
                        kwargs['weights_only'] = False
                        return original_load(*args, **kwargs)
                    torch.load = patched_load

                    self.yolo_model = YOLO(str(path))
                    self.active_model = "yolo"
                    logger.info(f"Loaded YOLO damage model: {path}")

                    torch.load = original_load
                    return
                except Exception as e:
                    logger.warning(f"Failed to load YOLO model {path}: {e}")

    def _try_load_maskrcnn(self):
        """Try to load Mask R-CNN via Detectron2."""
        candidates = [
            RUNS_DIR / "maskrcnn" / "merged_output" / "model_final.pth",
            MODELS_DIR / "maskrcnn_damage_v1.pth",
        ]
        for path in candidates:
            if path.exists():
                try:
                    from detectron2.engine import DefaultPredictor # type: ignore
                    from detectron2.config import get_cfg # type: ignore
                    from detectron2 import model_zoo # type: ignore

                    cfg = get_cfg()
                    cfg.merge_from_file(model_zoo.get_config_file(
                        "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
                    ))
                    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7
                    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
                    cfg.MODEL.WEIGHTS = str(path)

                    # Use CPU if no GPU
                    import torch # type: ignore
                    if not torch.cuda.is_available():
                        cfg.MODEL.DEVICE = "cpu"

                    self.maskrcnn_predictor = DefaultPredictor(cfg)
                    self.maskrcnn_cfg = cfg
                    self.active_model = "maskrcnn"
                    logger.info(f"Loaded Mask R-CNN model: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load Mask R-CNN {path}: {e}")

    def analyze(self, image: np.ndarray, parts: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Run damage detection, classification, and severity scoring.

        Args:
            image: BGR image (numpy array)
            parts: Optional list of detected parts from M3

        Returns:
            Dict with:
                damages: list of damage detections
                severity: overall severity assessment
                model_used: which model was used
                inference_time_ms: processing time
        """
        start = time.time()

        if self.active_model == "yolo" and self.yolo_model is not None:
            damages = self._detect_yolo(image)
            method = "yolo"
        elif self.active_model == "maskrcnn" and self.maskrcnn_predictor is not None:
            damages = self._detect_maskrcnn(image)
            method = "maskrcnn"
        else:
            damages = self._detect_heuristic(image)
            method = "heuristic"

        # Assign parts to damages (spatial overlap)
        if parts:
            damages = self._assign_parts_to_damages(damages, parts)

        # Compute severity for each damage
        for dmg in damages:
            dmg["severity"], dmg["severity_score"] = self._compute_severity(dmg, image)

        # Compute overall severity
        severity = self._compute_overall_severity(damages, image)

        elapsed = round((time.time() - start) * 1000)

        return {
            "damages": damages,
            "severity": severity,
            "model_used": method,
            "total_damages": len(damages),
            "inference_time_ms": elapsed,
        }

    # ========================================================================
    # YOLO Detection Path
    # ========================================================================

    def _detect_yolo(self, image: np.ndarray) -> List[Dict]:
        """Detect damages using YOLOv8."""
        model = self.yolo_model
        assert model is not None
        try:
            results = model(image, verbose=False, conf=0.25)
            damages = []

            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    h, w = image.shape[:2]
                    image_area = h * w

                    for box in result.boxes:
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])

                        # Get damage type name
                        if hasattr(model, 'names') and cls_id in model.names:
                            damage_type = model.names[cls_id]
                        elif cls_id < len(DAMAGE_CLASSES):
                            damage_type = DAMAGE_CLASSES[cls_id]
                        else:
                            damage_type = f"damage_{cls_id}"

                        # Normalize damage type
                        damage_type = self._normalize_damage_type(damage_type)

                        # Compute area percentage
                        bbox_area = float((x2 - x1) * (y2 - y1))
                        area_pct = float(f"{(bbox_area / image_area) * 100:.2f}") if image_area > 0 else 0.0

                        damages.append({
                            "damage_type": damage_type,
                            "bounding_box": [float(f"{x1:.1f}"), float(f"{y1:.1f}"), float(f"{x2:.1f}"), float(f"{y2:.1f}")],
                            "confidence": float(f"{conf:.4f}"),
                            "area_percentage": area_pct,
                            "part": "unknown",
                            "mask_path": None,
                            "model_source": "yolo",
                            "severity": "moderate",
                            "severity_score": 0.5,
                        })

            return damages
        except Exception as e:
            logger.error(f"YOLO detection failed: {e}")
            return self._detect_heuristic(image)

    # ========================================================================
    # Mask R-CNN Detection Path
    # ========================================================================

    def _detect_maskrcnn(self, image: np.ndarray) -> List[Dict]:
        """Detect damages using Mask R-CNN (Detectron2)."""
        predictor = self.maskrcnn_predictor
        assert predictor is not None
        try:
            outputs = predictor(image)
            from typing import cast
            instances_any = cast(Any, outputs["instances"])
            instances = outputs["instances"]

            damages = []
            h, w = image.shape[:2]
            image_area = h * w

            if len(instances) > 0:
                boxes = instances_any.pred_boxes.tensor.cpu().numpy()
                scores = instances_any.scores.cpu().numpy()
                classes = instances_any.pred_classes.cpu().numpy()

                # Get masks if available
                has_masks = instances_any.has("pred_masks")
                if has_masks:
                    masks = instances_any.pred_masks.cpu().numpy()

                for i in range(len(instances)):
                    x1, y1, x2, y2 = boxes[i]
                    conf = float(scores[i])
                    cls_id = int(classes[i])

                    if cls_id < len(DAMAGE_CLASSES):
                        damage_type = DAMAGE_CLASSES[cls_id]
                    else:
                        damage_type = f"damage_{cls_id}"

                    # Compute area from mask if available, else from bbox
                    if has_masks:
                        mask_area = float(np.sum(masks[i]))
                        area_pct = float(f"{(mask_area / image_area) * 100:.2f}")
                    else:
                        bbox_area = float((x2 - x1) * (y2 - y1))
                        area_pct = float(f"{(bbox_area / image_area) * 100:.2f}")

                    damages.append({
                        "damage_type": damage_type,
                        "bounding_box": [float(f"{x1:.1f}"), float(f"{y1:.1f}"),
                                         float(f"{x2:.1f}"), float(f"{y2:.1f}")],
                        "confidence": float(f"{conf:.4f}"),
                        "area_percentage": area_pct,
                        "part": "unknown",
                        "mask_path": None,
                        "model_source": "maskrcnn",
                        "severity": "moderate",
                        "severity_score": 0.5,
                    })

            return damages
        except Exception as e:
            logger.error(f"Mask R-CNN detection failed: {e}")
            return self._detect_heuristic(image)

    # ========================================================================
    # Heuristic Fallback
    # ========================================================================

    def _detect_heuristic(self, image: np.ndarray) -> List[Dict]:
        """
        Heuristic damage detection using color + edge anomalies.
        This is a rough approximation — real detection needs trained models.
        """
        h, w = image.shape[:2]
        image_area = h * w
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        damages = []

        # 1. Detect scratches via edge analysis (long thin edge clusters)
        edges = cv2.Canny(gray, 80, 200)
        kernel = np.ones((1, 15), np.uint8)  # Horizontal kernel for scratch-like edges
        scratch_regions = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(scratch_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < 500:
                continue
            x, y, cw, ch = [int(v) for v in cv2.boundingRect(cnt)]
            aspect_ratio = cw / max(ch, 1)

            # Long thin regions are likely scratches
            if aspect_ratio > 3.0 or aspect_ratio < 0.33:
                area_pct = float(f"{(area / image_area) * 100:.2f}")
                damages.append({
                    "damage_type": "scratch",
                    "bounding_box": [float(x), float(y), float(x + cw), float(y + ch)],
                    "confidence": 0.35,
                    "area_percentage": area_pct,
                    "part": "unknown",
                    "mask_path": None,
                    "model_source": "heuristic",
                    "severity": "minor",
                    "severity_score": 0.2,
                })

        # 2. Detect dents via shadow/highlight gradient anomalies
        blurred = cv2.GaussianBlur(gray, (15, 15), 0)
        diff = cv2.absdiff(gray, blurred)
        _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)

        kernel_dent = np.ones((7, 7), np.uint8)
        dent_mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_dent)
        dent_mask = cv2.morphologyEx(dent_mask, cv2.MORPH_OPEN, kernel_dent)

        contours_dent, _ = cv2.findContours(dent_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_dent:
            area = float(cv2.contourArea(cnt))
            if area < 1000:
                continue
            x, y, cw, ch = [int(v) for v in cv2.boundingRect(cnt)]
            area_pct = float(f"{(area / image_area) * 100:.2f}")

            damages.append({
                "damage_type": "dent",
                "bounding_box": [float(x), float(y), float(x + cw), float(y + ch)],
                "confidence": 0.30,
                "area_percentage": area_pct,
                "part": "unknown",
                "mask_path": None,
                "model_source": "heuristic",
                "severity": "moderate",
                "severity_score": 0.4,
            })

        # 3. Detect cracks/shatter via very high edge density regions
        edge_density_map = cv2.dilate(edges, np.ones((5, 5), np.uint8))
        _, high_edge = cv2.threshold(edge_density_map, 200, 255, cv2.THRESH_BINARY)

        contours_crack, _ = cv2.findContours(high_edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_crack:
            area = float(cv2.contourArea(cnt))
            if area < 2000:
                continue
            x, y, cw, ch = [int(v) for v in cv2.boundingRect(cnt)]
            area_pct = float(f"{(area / image_area) * 100:.2f}")

            damages.append({
                "damage_type": "crack",
                "bounding_box": [float(x), float(y), float(x + cw), float(y + ch)],
                "confidence": 0.25,
                "area_percentage": area_pct,
                "part": "unknown",
                "mask_path": None,
                "model_source": "heuristic",
                "severity": "moderate",
                "severity_score": 0.5,
            })

        # Deduplicate overlapping detections
        damages = self._nms_simple(damages, iou_threshold=0.5)

        # Limit to top-N by confidence
        damages.sort(key=lambda d: d["confidence"], reverse=True)
        damages = damages[:15] # type: ignore
        
        return damages

    # ========================================================================
    # Severity Computation
    # ========================================================================

    def _compute_severity(self, damage: Dict, image: np.ndarray) -> Tuple[str, float]:
        """
        Compute severity for a single damage.
        Combines: damage type weight + area percentage + part criticality.
        """
        # Type weight (0.0 - 1.0)
        type_weight = DAMAGE_TYPE_SEVERITY_WEIGHT.get(damage["damage_type"], 0.5)

        # Area contribution (larger area = more severe)
        area_pct = damage.get("area_percentage", 0.0)
        area_score = min(area_pct / 30.0, 1.0)  # 30% area = max severity from area

        # Part criticality
        part = damage.get("part", "unknown")
        part_weights = {"critical": 1.0, "high": 0.7, "medium": 0.5, "low": 0.3}
        from app.services.part_segmenter import PART_CRITICALITY # type: ignore
        criticality = PART_CRITICALITY.get(part, "medium")
        part_score = part_weights.get(criticality, 0.5)

        # Combined severity score
        severity_score = float((type_weight * 0.5) + (area_score * 0.3) + (part_score * 0.2))
        severity_score = float(f"{min(max(severity_score, 0.0), 1.0):.4f}")

        # Map to severity level
        for level, (lo, hi) in SEVERITY_THRESHOLDS.items():
            if lo <= severity_score < hi:
                return level, severity_score

        return "moderate", severity_score

    def _compute_overall_severity(self, damages: List[Dict], image: np.ndarray) -> Dict:
        """Compute overall claim severity from all damages."""
        if not damages:
            return {
                "severity_score": 0.0,
                "severity_level": "none",
                "damage_count": 0,
                "total_area_percentage": 0.0,
                "critical_parts_affected": [],
            }

        scores = [d.get("severity_score", 0.5) for d in damages]
        total_area = sum(d.get("area_percentage", 0.0) for d in damages)

        # Overall score: weighted max + count bonus
        max_score = float(max(scores))
        avg_score = float(sum(scores) / len(scores))
        count_bonus = float(min(len(damages) * 0.05, 0.2))  # More damages = slightly higher severity
        overall = min(max_score * 0.6 + avg_score * 0.3 + count_bonus, 1.0)
        overall = float(f"{overall:.4f}")

        # Critical parts
        critical_parts = []
        from app.services.part_segmenter import PART_CRITICALITY # type: ignore
        for d in damages:
            part = d.get("part", "unknown")
            if PART_CRITICALITY.get(part, "medium") in ("critical", "high"):
                if part not in critical_parts:
                    critical_parts.append(part)

        # Map to level
        level = "low"
        for lev, (lo, hi) in SEVERITY_THRESHOLDS.items():
            if lo <= overall < hi:
                level = lev
                break

        return {
            "severity_score": overall,
            "severity_level": level,
            "damage_count": len(damages),
            "total_area_percentage": float(f"{total_area:.2f}"),
            "critical_parts_affected": critical_parts,
        }

    # ========================================================================
    # Utilities
    # ========================================================================

    def _assign_parts_to_damages(self, damages: List[Dict], parts: List[Dict]) -> List[Dict]:
        """Assign the best-matching part to each damage based on bbox overlap."""
        for dmg in damages:
            dx1, dy1, dx2, dy2 = dmg["bounding_box"]
            best_part = "unknown"
            best_iou = 0.0

            for part in parts:
                px1, py1, px2, py2 = part["bounding_box"]
                iou = self._compute_iou(
                    (dx1, dy1, dx2, dy2),
                    (px1, py1, px2, py2)
                )
                if iou > best_iou:
                    best_iou = iou
                    best_part = part["name"]

            if best_iou > 0.1:
                dmg["part"] = best_part

        return damages

    @staticmethod
    def _compute_iou(box1: Tuple, box2: Tuple) -> float:
        """Compute Intersection over Union between two bboxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0.0

    @staticmethod
    def _nms_simple(damages: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
        """Simple non-maximum suppression to remove overlapping detections."""
        if not damages:
            return damages

        # Sort by confidence descending
        damages.sort(key=lambda d: d["confidence"], reverse=True)

        keep = []
        for dmg in damages:
            should_keep = True
            for kept in keep:
                iou = DamageAnalyzer._compute_iou(
                    tuple(dmg["bounding_box"]),
                    tuple(kept["bounding_box"])
                )
                if iou > iou_threshold:
                    should_keep = False
                    break
            if should_keep:
                keep.append(dmg)

        return keep

    def _normalize_damage_type(self, raw_type: str) -> str:
        """Normalize damage type names from various model outputs."""
        raw_lower = raw_type.lower().strip().replace(" ", "_").replace("-", "_")

        # Common mappings
        mappings = {
            "dent": "dent",
            "scratch": "scratch",
            "crack": "crack",
            "broken": "shatter",
            "shatter": "shatter",
            "shattered": "shatter",
            "deformation": "deformation",
            "deformed": "deformation",
            "paint": "paint_damage",
            "paint_damage": "paint_damage",
            "paint_scratch": "paint_damage",
            "glass": "glass_damage",
            "glass_damage": "glass_damage",
            "glass_shatter": "glass_damage",
            "breakage": "shatter",
        }

        for key, value in mappings.items():
            if key in raw_lower:
                return value

        return raw_lower if raw_lower in DAMAGE_CLASSES else "dent"

    def is_available(self) -> bool:
        """Check if analyzer has a real model loaded."""
        return self.active_model != "heuristic"
