"""
PII Masker — YOLO11m for person detection, YOLO11m_plates + Haar for license plates.
Applies heavy Gaussian blur (99x99) strictly within detected bounding boxes.
"""
import cv2
import numpy as np
import base64
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

BLUR_KERNEL = (99, 99)
MODELS_DIR = Path(__file__).parent.parent.parent / "models"

# Lazy-loaded singletons
_person_model = None
_plate_model = None
_plate_cascade = None


def _get_person_model():
    global _person_model
    if _person_model is None:
        from ultralytics import YOLO
        _person_model = YOLO(str(MODELS_DIR / "yolo11m.pt"))
    return _person_model


def _get_plate_model():
    global _plate_model
    if _plate_model is None:
        from ultralytics import YOLO
        _plate_model = YOLO(str(MODELS_DIR / "yolo11m_plates.pt"))
    return _plate_model


def _get_plate_cascade():
    global _plate_cascade
    if _plate_cascade is None:
        _plate_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
        )
    return _plate_cascade


def _box_blur(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Blur a rectangular region in-place."""
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(image.shape[1], x + w), min(image.shape[0], y + h)
    if x2 <= x1 or y2 <= y1:
        return image
    roi = image[y1:y2, x1:x2]
    image[y1:y2, x1:x2] = cv2.GaussianBlur(roi, BLUR_KERNEL, 0)
    return image


def redact(image: np.ndarray) -> Tuple[np.ndarray, Dict]:
    """
    Detect persons (→ blur head region) and license plates (→ blur full box).
    Returns (redacted_image, metadata).
    """
    result = image.copy()
    h_img, w_img = image.shape[:2]

    faces_found: List[Tuple] = []
    plates_found: List[Tuple] = []

    # --- Person detection via YOLO11m (class 0 = person) ---
    try:
        pm = _get_person_model()
        res = pm(image, verbose=False, conf=0.45, classes=[0])
        for box in res[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # Blur top 35% of person bbox = head/face region
            face_h = max(30, int((y2 - y1) * 0.35))
            bx, by, bw, bh = x1, y1, x2 - x1, face_h
            faces_found.append((bx, by, bw, bh))
            result = _box_blur(result, bx, by, bw, bh)
    except Exception as e:
        logger.warning(f"Person detection failed: {e}")

    # --- Plate detection: YOLO11m_plates (conf=0.3) UNION Haar cascade ---
    try:
        plm = _get_plate_model()
        pr = plm(image, verbose=False, conf=0.3)
        for box in pr[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bx, by, bw, bh = x1, y1, x2 - x1, y2 - y1
            plates_found.append((bx, by, bw, bh))
            result = _box_blur(result, bx, by, bw, bh)
    except Exception as e:
        logger.warning(f"YOLO plate detection failed: {e}")

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cascade = _get_plate_cascade()
        haar = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(50, 20))
        if len(haar) > 0:
            for (x, y, w, h) in haar:
                plates_found.append((int(x), int(y), int(w), int(h)))
                result = _box_blur(result, int(x), int(y), int(w), int(h))
    except Exception as e:
        logger.warning(f"Haar plate detection failed: {e}")

    metadata = {
        "faces_detected": len(faces_found),
        "plates_detected": len(plates_found),
        "faces_boxes": faces_found,
        "plates_boxes": plates_found,
        "pii_found": len(faces_found) + len(plates_found) > 0,
    }
    logger.info(f"PII: {len(faces_found)} faces, {len(plates_found)} plates redacted")
    return result, metadata


def image_to_b64(image: np.ndarray) -> str:
    _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return base64.b64encode(buf.tobytes()).decode('utf-8')
