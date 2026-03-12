#!/usr/bin/env python3
"""
Train custom YOLOv8 model on car damage dataset
Runs in background to improve damage detection accuracy
"""
import os
import sys
from pathlib import Path

def download_and_train():
    """Download dataset and train YOLOv8 model"""
    print("=" * 80)
    print("YOLO DAMAGE DETECTION MODEL TRAINING")
    print("=" * 80)
    
    # Install kagglehub if not present
    try:
        import kagglehub
    except ImportError:
        print("\n📦 Installing kagglehub...")
        os.system("pip install kagglehub")
        import kagglehub
    
    # Download dataset
    print("\n📥 Downloading car damage dataset from Kaggle...")
    try:
        dataset_path = kagglehub.dataset_download("anujms/car-damage-detection")
        print(f"✅ Dataset downloaded to: {dataset_path}")
    except Exception as e:
        print(f"❌ Failed to download dataset: {e}")
        print("   Make sure you have Kaggle API credentials configured")
        print("   Run: kaggle datasets download -d anujms/car-damage-detection")
        return False
    
    # Check dataset structure
    dataset_dir = Path(dataset_path)
    print(f"\n📂 Dataset structure:")
    for item in dataset_dir.rglob("*"):
        if item.is_file() and len(str(item).split('/')) <= 8:  # Limit depth
            print(f"   {item.relative_to(dataset_dir)}")
    
    # Train YOLOv8
    print("\n🚀 Starting YOLOv8 training...")
    print("   Model: YOLOv8n (nano - fast training)")
    print("   Epochs: 50 (adjust based on time)")
    print("   Image size: 640x640")
    print("   This will run in background...")
    
    try:
        from ultralytics import YOLO
        
        # Initialize model
        model = YOLO('yolov8n.pt')  # Start from pretrained
        
        # Check if data.yaml exists
        data_yaml = dataset_dir / "data.yaml"
        if not data_yaml.exists():
            print(f"\n⚠️  Creating data.yaml configuration...")
            # Create basic data.yaml
            with open(data_yaml, 'w') as f:
                f.write(f"""
# Car Damage Detection Dataset
path: {dataset_dir}
train: images/train
val: images/val

# Classes
names:
  0: damage
  1: dent
  2: scratch
  3: crack
  4: broken
""")
            print(f"✅ Created {data_yaml}")
        
        # Train model
        print(f"\n🏋️  Training model (this may take 30-60 minutes)...")
        results = model.train(
            data=str(data_yaml),
            epochs=50,
            imgsz=640,
            batch=16,
            name='car_damage_detector',
            patience=10,  # Early stopping
            save=True,
            plots=True,
            verbose=True
        )
        
        # Save best model
        best_model_path = Path("runs/detect/car_damage_detector/weights/best.pt")
        if best_model_path.exists():
            # Copy to backend directory
            import shutil
            dest = Path(__file__).parent / "yolov8_damage_best.pt"
            shutil.copy(best_model_path, dest)
            print(f"\n✅ Model trained successfully!")
            print(f"   Best model saved to: {dest}")
            print(f"   Training results: runs/detect/car_damage_detector/")
            return True
        else:
            print(f"\n⚠️  Training completed but best model not found")
            return False
            
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🎯 This script will:")
    print("   1. Download car damage dataset from Kaggle")
    print("   2. Train YOLOv8n model (50 epochs)")
    print("   3. Save best model as yolov8_damage_best.pt")
    print("\n⏱️  Estimated time: 30-60 minutes")
    print("   You can continue working on other tasks while this runs\n")
    
    input("Press Enter to start training (or Ctrl+C to cancel)...")
    
    success = download_and_train()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 TRAINING COMPLETE!")
        print("=" * 80)
        print("\n📝 Next steps:")
        print("   1. Update damage_detection.py to use yolov8_damage_best.pt")
        print("   2. Test with: python test_pipeline_4.1_to_4.3.py")
        print("   3. Compare detection accuracy with generic model")
    else:
        print("\n" + "=" * 80)
        print("⚠️  TRAINING INCOMPLETE")
        print("=" * 80)
        print("\n   Continue using generic yolov8n.pt model for now")
    
    sys.exit(0 if success else 1)
