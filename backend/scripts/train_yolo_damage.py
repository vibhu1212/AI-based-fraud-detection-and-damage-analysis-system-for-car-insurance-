#!/usr/bin/env python3
"""
Damage Detection Model Training Script
Trains YOLOv8m on merged damage detection dataset with 42 damage classes
"""

import os
from pathlib import Path
from ultralytics import YOLO
import torch

# Configuration
DATA_YAML = "backend/datasets/prepared/damage_detection/data.yaml"
MODEL_SIZE = "yolov8m.pt"  # Medium model for better accuracy
EPOCHS = 100
BATCH_SIZE = 8  # Reduced for 6GB GPU (was 16)
IMG_SIZE = 640
DEVICE = 0 if torch.cuda.is_available() else 'cpu'
PROJECT = "backend/runs/damage_detection"
NAME = "yolov8m_damage_v1"

# Training hyperparameters
OPTIMIZER = "AdamW"
LR0 = 0.001
PATIENCE = 20
SAVE_PERIOD = 10

def main():
    print("="*60)
    print("🔧 Damage Detection Model Training")
    print("="*60)
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️  No GPU available, using CPU (will be VERY slow)")
    
    # Load model
    print(f"\n📦 Loading {MODEL_SIZE}...")
    model = YOLO(MODEL_SIZE)
    
    # Check data.yaml
    data_path = Path(DATA_YAML)
    if not data_path.exists():
        print(f"❌ Data file not found: {DATA_YAML}")
        return
    
    print(f"✅ Data file found: {DATA_YAML}")
    print(f"   Training on 42 damage classes")
    print(f"   21,452 total images")
    
    # Start training
    print(f"\n🚀 Starting training...")
    print(f"   Epochs: {EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Image size: {IMG_SIZE}")
    print(f"   Device: {DEVICE}")
    print(f"   Optimizer: {OPTIMIZER}")
    print(f"   Learning rate: {LR0}")
    print(f"\n⏱️  Estimated time: 6-8 hours (GPU dependent)")
    
    results = model.train(
        data=str(data_path),
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMG_SIZE,
        device=DEVICE,
        project=PROJECT,
        name=NAME,
        optimizer=OPTIMIZER,
        lr0=LR0,
        patience=PATIENCE,
        save_period=SAVE_PERIOD,
        verbose=True,
        plots=True,
        # Data augmentation
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0
    )
    
    print("\n✅ Training complete!")
    print(f"   Best model: {PROJECT}/{NAME}/weights/best.pt")
    
    # Validate
    print("\n📊 Running validation...")
    metrics = model.val()
    
    print(f"\n📈 Final Metrics:")
    print(f"   mAP50: {metrics.box.map50:.4f}")
    print(f"   mAP50-95: {metrics.box.map:.4f}")
    print(f"   Precision: {metrics.box.mp:.4f}")
    print(f"   Recall: {metrics.box.mr:.4f}")
    
    # Check if target met
    if metrics.box.map50 >= 0.75:
        print(f"\n🎯 Target achieved! mAP50 = {metrics.box.map50:.4f} (target: 0.75)")
    else:
        print(f"\n⚠️  Target not met. mAP50 = {metrics.box.map50:.4f} (target: 0.75)")
        print(f"   Consider fine-tuning or adjusting hyperparameters")
    
    # Save to models directory
    best_model_path = Path(PROJECT) / NAME / "weights" / "best.pt"
    output_path = Path("backend/models/yolov8m_damage_detection_v1.pt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if best_model_path.exists():
        import shutil
        shutil.copy2(best_model_path, output_path)
        print(f"\n✅ Model saved to: {output_path}")
    
    print("\n🎉 Damage detection training complete!")
    print(f"   Next step: Integrate model into backend/app/tasks/damage_detection.py")

if __name__ == "__main__":
    main()
