#!/usr/bin/env python3
"""
Vehicle Classification Model Training Script
Trains YOLOv8n on Indian Vehicle Dataset for 6 vehicle types
"""

import os
from pathlib import Path
from ultralytics import YOLO
import torch

# Configuration
DATA_DIR = "backend/datasets/prepared/vehicle_classification_cls"  # Directory for classification
MODEL_SIZE = "yolov8n-cls.pt"  # Nano model for classification
EPOCHS = 50
BATCH_SIZE = 32
IMG_SIZE = 224  # Standard for classification
DEVICE = 0 if torch.cuda.is_available() else 'cpu'
PROJECT = "backend/runs/vehicle_classification"
NAME = "yolov8n_vehicle_v1"

# Training hyperparameters
OPTIMIZER = "AdamW"
LR0 = 0.001
PATIENCE = 15
SAVE_PERIOD = 10

def main():
    print("="*60)
    print("🚗 Vehicle Classification Model Training")
    print("="*60)
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️  No GPU available, using CPU (will be slow)")
    
    # Load model
    print(f"\n📦 Loading {MODEL_SIZE}...")
    model = YOLO(MODEL_SIZE)
    
    # Check data directory
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        return
    
    print(f"✅ Data directory found: {DATA_DIR}")
    
    # Start training
    print(f"\n🚀 Starting training...")
    print(f"   Epochs: {EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Image size: {IMG_SIZE}")
    print(f"   Device: {DEVICE}")
    print(f"   Optimizer: {OPTIMIZER}")
    print(f"   Learning rate: {LR0}")
    
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
        plots=True
    )
    
    print("\n✅ Training complete!")
    print(f"   Best model: {PROJECT}/{NAME}/weights/best.pt")
    
    # Validate
    print("\n📊 Running validation...")
    metrics = model.val()
    
    print(f"\n📈 Final Metrics:")
    print(f"   Top-1 Accuracy: {metrics.top1:.4f}")
    print(f"   Top-5 Accuracy: {metrics.top5:.4f}")
    
    # Save to models directory
    best_model_path = Path(PROJECT) / NAME / "weights" / "best.pt"
    output_path = Path("backend/models/yolov8n_vehicle_classifier.pt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if best_model_path.exists():
        import shutil
        shutil.copy2(best_model_path, output_path)
        print(f"\n✅ Model saved to: {output_path}")
    
    print("\n🎉 Vehicle classification training complete!")
    print(f"   Next step: python scripts/train_yolo_damage.py")

if __name__ == "__main__":
    main()
