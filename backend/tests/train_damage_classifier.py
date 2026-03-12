#!/usr/bin/env python3
"""
Train YOLOv8 classification model on car damage dataset
This will improve damage detection by training on actual car damage images
"""
import os
import sys
from pathlib import Path
import shutil

# Dataset path
DATASET_PATH = "/home/kartikay/.cache/kagglehub/datasets/anujms/car-damage-detection/versions/1/data1a"

def prepare_yolo_classification_dataset():
    """Prepare dataset in YOLO classification format"""
    print("=" * 80)
    print("PREPARING YOLO CLASSIFICATION DATASET")
    print("=" * 80)
    
    # Create dataset directory
    yolo_dataset = Path("./yolo_damage_dataset")
    yolo_dataset.mkdir(exist_ok=True)
    
    # YOLO classification format: dataset/train/class_name/images
    train_dir = yolo_dataset / "train"
    val_dir = yolo_dataset / "val"
    
    train_dir.mkdir(exist_ok=True)
    val_dir.mkdir(exist_ok=True)
    
    # Copy training data
    print("\n📂 Copying training images...")
    src_train_damage = Path(DATASET_PATH) / "training" / "00-damage"
    src_train_whole = Path(DATASET_PATH) / "training" / "01-whole"
    
    dst_train_damage = train_dir / "damage"
    dst_train_whole = train_dir / "whole"
    
    if dst_train_damage.exists():
        shutil.rmtree(dst_train_damage)
    if dst_train_whole.exists():
        shutil.rmtree(dst_train_whole)
    
    shutil.copytree(src_train_damage, dst_train_damage)
    shutil.copytree(src_train_whole, dst_train_whole)
    
    train_damage_count = len(list(dst_train_damage.glob("*.JPEG")))
    train_whole_count = len(list(dst_train_whole.glob("*.JPEG")))
    
    print(f"   ✅ Training damage images: {train_damage_count}")
    print(f"   ✅ Training whole images: {train_whole_count}")
    
    # Copy validation data
    print("\n📂 Copying validation images...")
    src_val_damage = Path(DATASET_PATH) / "validation" / "00-damage"
    src_val_whole = Path(DATASET_PATH) / "validation" / "01-whole"
    
    dst_val_damage = val_dir / "damage"
    dst_val_whole = val_dir / "whole"
    
    if dst_val_damage.exists():
        shutil.rmtree(dst_val_damage)
    if dst_val_whole.exists():
        shutil.rmtree(dst_val_whole)
    
    shutil.copytree(src_val_damage, dst_val_damage)
    shutil.copytree(src_val_whole, dst_val_whole)
    
    val_damage_count = len(list(dst_val_damage.glob("*.JPEG")))
    val_whole_count = len(list(dst_val_whole.glob("*.JPEG")))
    
    print(f"   ✅ Validation damage images: {val_damage_count}")
    print(f"   ✅ Validation whole images: {val_whole_count}")
    
    print(f"\n✅ Dataset prepared at: {yolo_dataset}")
    print(f"   Total training images: {train_damage_count + train_whole_count}")
    print(f"   Total validation images: {val_damage_count + val_whole_count}")
    
    return yolo_dataset


def train_yolo_classifier():
    """Train YOLOv8 classification model"""
    print("\n" + "=" * 80)
    print("TRAINING YOLO CLASSIFICATION MODEL")
    print("=" * 80)
    
    try:
        from ultralytics import YOLO
        
        # Prepare dataset
        dataset_path = prepare_yolo_classification_dataset()
        
        # Initialize model
        print("\n🤖 Initializing YOLOv8n-cls model...")
        model = YOLO('yolov8n-cls.pt')  # Classification model
        
        # Train
        print("\n🏋️  Starting training...")
        print("   Model: YOLOv8n-cls (nano classification)")
        print("   Epochs: 30")
        print("   Image size: 224x224")
        print("   Batch size: 32")
        print("\n   ⏱️  This will take approximately 15-20 minutes...")
        print("   You can continue working on other tasks!\n")
        
        results = model.train(
            data=str(dataset_path),
            epochs=30,
            imgsz=224,
            batch=32,
            name='damage_classifier',
            patience=5,  # Early stopping
            save=True,
            plots=True,
            verbose=True,
            device='cpu'  # Use CPU (change to 0 for GPU if available)
        )
        
        # Validate
        print("\n📊 Validating model...")
        metrics = model.val()
        
        print(f"\n✅ Validation Results:")
        print(f"   Top-1 Accuracy: {metrics.top1:.2%}")
        print(f"   Top-5 Accuracy: {metrics.top5:.2%}")
        
        # Save best model
        best_model_path = Path("runs/classify/damage_classifier/weights/best.pt")
        if best_model_path.exists():
            dest = Path(__file__).parent / "yolov8_damage_classifier.pt"
            shutil.copy(best_model_path, dest)
            print(f"\n✅ Model saved to: {dest}")
            return True, dest
        else:
            print(f"\n⚠️  Best model not found at expected location")
            return False, None
            
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    print("\n🎯 Car Damage Classification Model Training")
    print("\n📊 Dataset Info:")
    print(f"   Source: Kaggle - anujms/car-damage-detection")
    print(f"   Classes: damage, whole")
    print(f"   Images: ~1241 total")
    print("\n⏱️  Estimated training time: 15-20 minutes")
    print("   (You can work on other tasks while this runs)\n")
    
    response = input("Start training? (y/n): ")
    if response.lower() != 'y':
        print("Training cancelled.")
        return
    
    success, model_path = train_yolo_classifier()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 TRAINING COMPLETE!")
        print("=" * 80)
        print(f"\n✅ Model saved: {model_path}")
        print("\n📝 Next steps:")
        print("   1. This classifier can identify if a car has damage")
        print("   2. For detection (bounding boxes), we still use yolov8n.pt")
        print("   3. In production, combine both models:")
        print("      - Classifier: Does car have damage? (yes/no)")
        print("      - Detector: Where is the damage? (bounding boxes)")
        print("\n💡 To use in damage_detection.py:")
        print("   - Load classifier first to filter images")
        print("   - Only run detector on images classified as 'damage'")
        print("   - This improves accuracy and reduces false positives")
    else:
        print("\n" + "=" * 80)
        print("⚠️  TRAINING FAILED OR INCOMPLETE")
        print("=" * 80)
        print("\n   Continue using generic yolov8n.pt for now")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
