#!/usr/bin/env python3
"""
Reorganize vehicle classification dataset for YOLOv8 classification format
YOLOv8 classification expects: data/train/class1/, data/train/class2/, etc.
"""

import shutil
from pathlib import Path
import yaml

# Paths
SOURCE_DIR = Path("backend/datasets/prepared/vehicle_classification")
OUTPUT_DIR = Path("backend/datasets/prepared/vehicle_classification_cls")

# Read class names from data.yaml
with open(SOURCE_DIR / "data.yaml", 'r') as f:
    data = yaml.safe_load(f)
    classes = data['names']

print("="*60)
print("🔄 Reorganizing Vehicle Classification Dataset")
print("="*60)
print(f"Classes: {classes}")

# Create output directory structure
for split in ['train', 'val', 'test']:
    for class_name in classes:
        (OUTPUT_DIR / split / class_name).mkdir(parents=True, exist_ok=True)

# Process each split
for split in ['train', 'val', 'test']:
    print(f"\n📁 Processing {split} split...")
    
    images_dir = SOURCE_DIR / split / 'images'
    labels_dir = SOURCE_DIR / split / 'labels'
    
    if not images_dir.exists():
        print(f"   ⚠️  {split} images not found, skipping")
        continue
    
    moved_count = {class_name: 0 for class_name in classes}
    
    # Process each image
    for img_file in images_dir.glob('*'):
        if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
            continue
        
        # Find corresponding label
        label_file = labels_dir / f"{img_file.stem}.txt"
        
        if not label_file.exists():
            print(f"   ⚠️  No label for {img_file.name}, skipping")
            continue
        
        # Read label (first line, first number is class ID)
        with open(label_file, 'r') as f:
            line = f.readline().strip()
            if line:
                class_id = int(line.split()[0])
                class_name = classes[class_id]
                
                # Copy image to class folder
                dest = OUTPUT_DIR / split / class_name / img_file.name
                shutil.copy2(img_file, dest)
                moved_count[class_name] += 1
    
    # Print statistics
    total = sum(moved_count.values())
    print(f"   ✅ Moved {total} images:")
    for class_name, count in moved_count.items():
        print(f"      - {class_name}: {count}")

print("\n" + "="*60)
print("✅ Dataset reorganization complete!")
print(f"   Output: {OUTPUT_DIR}")
print(f"   Structure: {OUTPUT_DIR}/train/class_name/image.jpg")
print("="*60)
