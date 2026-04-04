import os
import shutil
from pathlib import Path

# Try to import YOLO, fail gracefully if not installed yet
try:
    from ultralytics import YOLO
except ImportError:
    print("Ultralytics not installed yet. Skipping model downloads.")
    exit(0)

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def setup_models():
    print("Downloading and setting up YOLO models...")
    
    # 1. Base YOLO11m for PII Masker (Persons)
    print("Downloading yolo11m.pt...")
    YOLO("yolo11m.pt")
    if os.path.exists("yolo11m.pt"):
        shutil.copy("yolo11m.pt", MODELS_DIR / "yolo11m.pt")
        # Placeholder for custom plates model (use base model to avoid file not found errors)
        shutil.copy("yolo11m.pt", MODELS_DIR / "yolo11m_plates.pt")

    # 2. Base YOLOv8m for Damage Detection fallback
    print("Downloading yolov8m.pt...")
    YOLO("yolov8m.pt")
    if os.path.exists("yolov8m.pt"):
        shutil.copy("yolov8m.pt", MODELS_DIR / "yolov8m_damage_detection_v1.pt")

    # 3. Base YOLOv8n-cls for Vehicle Classifier fallback
    print("Downloading yolov8n-cls.pt...")
    YOLO("yolov8n-cls.pt")
    if os.path.exists("yolov8n-cls.pt"):
        shutil.copy("yolov8n-cls.pt", MODELS_DIR / "yolov8n_vehicle_classifier.pt")
    
    # 4. YOLOv8m-seg for Part Segmentation fallback
    print("Downloading yolov8m-seg.pt...")
    YOLO("yolov8m-seg.pt")
    if os.path.exists("yolov8m-seg.pt"):
        shutil.copy("yolov8m-seg.pt", MODELS_DIR / "yolov8m_parts_seg.pt")

    print(f"Models successfully set up in {MODELS_DIR}")

if __name__ == "__main__":
    setup_models()
