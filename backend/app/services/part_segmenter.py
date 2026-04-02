"""
M3 — Part Segmentation Service
Detects and segments vehicle parts (bumper, door, hood, fender, etc).

Primary: YOLOv8-seg model inference (when weights available)
Fallback: Heuristic region-based segmentation using the full image as a single part
"""
import cv2 # type: ignore
import numpy as np # type: ignore
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Standard car parts for detection
CAR_PARTS = [
    "front_bumper", "rear_bumper", "hood", "trunk",
    "front_left_door", "front_right_door", "rear_left_door", "rear_right_door",
    "front_left_fender", "front_right_fender", "rear_left_fender", "rear_right_fender",
    "windshield", "rear_window", "front_left_headlight", "front_right_headlight",
    "rear_left_taillight", "rear_right_taillight", "roof",
    "left_side_mirror", "right_side_mirror", "grille",
    "front_left_wheel", "front_right_wheel", "rear_left_wheel", "rear_right_wheel",
]

# Part criticality for severity scoring (used by M4)
PART_CRITICALITY = {
    "windshield": "critical",
    "rear_window": "critical",
    "hood": "high",
    "front_bumper": "medium",
    "rear_bumper": "medium",
    "front_left_door": "high",
    "front_right_door": "high",
    "rear_left_door": "high",
    "rear_right_door": "high",
    "front_left_fender": "medium",
    "front_right_fender": "medium",
    "rear_left_fender": "medium",
    "rear_right_fender": "medium",
    "trunk": "medium",
    "roof": "high",
    "grille": "low",
    "left_side_mirror": "low",
    "right_side_mirror": "low",
    "front_left_headlight": "medium",
    "front_right_headlight": "medium",
    "rear_left_taillight": "medium",
    "rear_right_taillight": "medium",
    "front_left_wheel": "high",
    "front_right_wheel": "high",
    "rear_left_wheel": "high",
    "rear_right_wheel": "high",
}

MODELS_DIR = Path(__file__).parent.parent.parent / "models"

# Lazy-loaded singleton
_segmenter_model = None


class PartSegmenter:
    """
    Vehicle part segmentation service.
    Uses YOLOv8-seg when weights are available, otherwise falls back to
    heuristic grid-based part estimation.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_type = "none"

        # Try to load YOLO segmentation model
        if model_path:
            self._try_load_model(Path(model_path))
        else:
            # Check default locations
            candidates = [
                MODELS_DIR / "yolov8m_parts_seg.pt",
                MODELS_DIR / "yolov8n_parts_seg.pt",
                MODELS_DIR / "best_parts.pt",
            ]
            for candidate in candidates:
                if candidate.exists():
                    self._try_load_model(candidate)
                    break

        if self.model is None:
            logger.warning("No part segmentation model found — using heuristic fallback")
            self.model_type = "heuristic"
        else:
            logger.info(f"Part segmenter loaded: {self.model_type}")

    def _try_load_model(self, path: Path) -> None:
        """Attempt to load a YOLO segmentation model."""
        try:
            import torch # type: ignore
            from ultralytics import YOLO # type: ignore

            # Patch torch.load for compatibility
            original_load = torch.load
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            torch.load = patched_load

            self.model = YOLO(str(path))
            self.model_type = "yolo_seg"
            logger.info(f"Loaded YOLO segmentation model: {path}")

            torch.load = original_load
        except Exception as e:
            logger.warning(f"Failed to load model {path}: {e}")
            self.model = None

    def segment(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Segment vehicle parts in the image.

        Args:
            image: BGR image (numpy array)

        Returns:
            Dict with keys:
                parts: list of detected parts
                model_used: which model/method was used
                inference_time_ms: processing time
        """
        start = time.time()

        if self.model_type == "yolo_seg" and self.model is not None:
            parts = self._segment_with_yolo(image)
            method = "yolo_seg"
        else:
            parts = self._segment_heuristic(image)
            method = "heuristic"

        elapsed = round((time.time() - start) * 1000)

        return {
            "parts": parts,
            "model_used": method,
            "total_parts_detected": len(parts),
            "inference_time_ms": elapsed,
        }

    def _segment_with_yolo(self, image: np.ndarray) -> List[Dict]:
        """Segment parts using YOLO-seg model."""
        model = self.model
        assert model is not None
        try:
            results = model(image, verbose=False, conf=0.3)

            parts = []
            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])

                        # Get class name
                        if hasattr(model, 'names') and cls_id in model.names:
                            name = model.names[cls_id]
                        else:
                            name = f"part_{cls_id}"

                        parts.append({
                            "name": name,
                            "bounding_box": [x1, y1, x2, y2],
                            "confidence": float(f"{conf:.4f}"),
                            "mask_path": None,
                        })

            return parts
        except Exception as e:
            logger.error(f"YOLO segmentation failed: {e}")
            return self._segment_heuristic(image)

    def _segment_heuristic(self, image: np.ndarray) -> List[Dict]:
        """
        Heuristic part detection using edge analysis + spatial reasoning.
        Divides the image into zones and assigns likely part names based on
        position and edge density.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Define spatial zones that roughly correspond to car parts
        # These are approximate regions assuming a ~45 degree angle view
        zones = {
            "front_bumper":    (0.0, 0.65, 1.0, 1.0),    # bottom center
            "hood":            (0.1, 0.35, 0.9, 0.65),    # middle
            "windshield":      (0.15, 0.10, 0.85, 0.35),  # upper middle
            "grille":          (0.25, 0.60, 0.75, 0.70),   # lower middle
            "front_left_headlight":  (0.0, 0.50, 0.25, 0.70),
            "front_right_headlight": (0.75, 0.50, 1.0, 0.70),
        }

        parts = []
        for part_name, (rx1, ry1, rx2, ry2) in zones.items():
            x1, y1 = int(rx1 * w), int(ry1 * h)
            x2, y2 = int(rx2 * w), int(ry2 * h)

            # Check edge density in this zone
            zone_edges = edges[y1:y2, x1:x2]
            if zone_edges.size == 0:
                continue
            edge_density = np.sum(zone_edges > 0) / zone_edges.size

            # Only report zones with some edge content (indicates structure)
            if edge_density > 0.02:
                conf_heuristic = float(min(edge_density * 5, 0.85))
                parts.append({
                    "name": part_name,
                    "bounding_box": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": float(f"{conf_heuristic:.4f}"),
                    "mask_path": None,
                })

        # Always include a whole-vehicle bounding box
        parts.append({
            "name": "vehicle_body",
            "bounding_box": [0.0, 0.0, float(w), float(h)],
            "confidence": 0.95,
            "mask_path": None,
        })

        return parts

    def is_available(self) -> bool:
        """Check if segmenter has real model loaded."""
        return self.model is not None

    def get_part_criticality(self, part_name: str) -> str:
        """Get criticality level for a part name."""
        return PART_CRITICALITY.get(part_name, "medium")
