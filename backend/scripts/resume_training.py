#!/usr/bin/env python3
"""
Resume Training Script
Automatically resumes training from the last checkpoint after interruption
"""

from ultralytics import YOLO
from pathlib import Path
import sys

def find_latest_checkpoint():
    """Find the most recent training checkpoint"""
    
    # Check for damage detection checkpoints
    # Handle both running from project root and backend directory
    possible_paths = [
        Path("runs/detect/backend/runs/damage_detection"),  # From project root
        Path("../runs/detect/backend/runs/damage_detection"),  # From backend dir
    ]
    
    damage_runs = None
    for path in possible_paths:
        if path.exists():
            damage_runs = path
            break
    
    if not damage_runs:
        print("❌ No training runs found!")
        print(f"Searched in:")
        for path in possible_paths:
            print(f"  - {path.absolute()}")
        return None
    
    print(f"📁 Found training directory: {damage_runs.absolute()}")
    
    # Find all training runs
    runs = sorted(damage_runs.glob("yolov8m_damage_v*"), 
                  key=lambda x: x.stat().st_mtime, 
                  reverse=True)
    
    if not runs:
        print("❌ No training checkpoints found!")
        return None
    
    latest_run = runs[0]
    last_checkpoint = latest_run / "weights" / "last.pt"
    
    if last_checkpoint.exists():
        return last_checkpoint
    else:
        print(f"❌ Checkpoint not found: {last_checkpoint}")
        return None

def resume_training():
    """Resume training from the last checkpoint"""
    
    print("=" * 80)
    print("🔄 RESUME TRAINING FROM CHECKPOINT")
    print("=" * 80)
    print()
    
    # Change to project root if we're in backend directory
    import os
    current_dir = Path.cwd()
    if current_dir.name == "backend":
        os.chdir(current_dir.parent)
        print(f"📂 Changed working directory to: {Path.cwd()}")
        print()
    
    # Find checkpoint
    checkpoint = find_latest_checkpoint()
    
    if not checkpoint:
        print("Cannot resume - no checkpoint found!")
        print()
        print("If training was interrupted very early (before first epoch),")
        print("you'll need to start fresh with:")
        print("  python backend/scripts/train_yolo_damage.py")
        return False
    
    print(f"✅ Found checkpoint: {checkpoint}")
    print()
    
    # Check checkpoint info
    size_mb = checkpoint.stat().st_size / (1024 * 1024)
    print(f"📦 Checkpoint size: {size_mb:.2f} MB")
    print()
    
    # Load model from checkpoint
    print("📥 Loading model from checkpoint...")
    model = YOLO(str(checkpoint))
    
    print("✅ Model loaded successfully!")
    print()
    print("🚀 Resuming training...")
    print("=" * 80)
    print()
    
    # Resume training - YOLOv8 will automatically continue from where it left off
    # It reads the epoch number and optimizer state from the checkpoint
    results = model.train(
        resume=True  # This tells YOLO to resume from the checkpoint
    )
    
    print()
    print("=" * 80)
    print("✅ Training resumed and completed!")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        success = resume_training()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Training interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
