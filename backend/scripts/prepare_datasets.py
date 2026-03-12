#!/usr/bin/env python3
"""
Dataset Preparation Script for InsurAI AI Pipeline Enhancement
Handles multiple dataset formats and creates unified train/val/test splits
"""

import os
import shutil
import yaml
import random
from pathlib import Path
from collections import defaultdict
import json

# Configuration
RAW_DATASETS_DIR = Path("backend/datasets/raw")
OUTPUT_DIR = Path("backend/datasets/prepared")
RANDOM_SEED = 42

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.20
TEST_RATIO = 0.10

# Dataset configurations
DATASETS = {
    "curacel_ai": {
        "type": "damage_detection",
        "priority": "high",
        "description": "Primary damage detection dataset"
    },
    "indian_veichle": {
        "type": "vehicle_classification",
        "priority": "critical",
        "description": "Vehicle type classification"
    },
    "urfu_damage": {
        "type": "damage_detection",
        "priority": "medium",
        "description": "Supplementary damage data"
    },
    "cdd": {
        "type": "damage_detection",
        "priority": "medium",
        "description": "Supplementary damage data"
    },
    "warning_lights": {
        "type": "damage_detection",
        "priority": "low",
        "description": "Recent damage data"
    }
}


def setup_output_directories():
    """Create output directory structure"""
    print("📁 Setting up output directories...")
    
    # Damage detection directories
    for split in ['train', 'val', 'test']:
        (OUTPUT_DIR / 'damage_detection' / split / 'images').mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / 'damage_detection' / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    # Vehicle classification directories
    for split in ['train', 'val', 'test']:
        (OUTPUT_DIR / 'vehicle_classification' / split / 'images').mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / 'vehicle_classification' / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    print("✅ Output directories created")


def read_yaml_file(yaml_path):
    """Read YAML file safely"""
    try:
        with open(yaml_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Could not read {yaml_path}: {e}")
        return None


def get_dataset_structure(dataset_path):
    """Analyze dataset structure and return available splits"""
    structure = {
        'has_train': False,
        'has_val': False,
        'has_valid': False,
        'has_test': False,
        'splits': []
    }
    
    # Check for different folder names
    if (dataset_path / 'train').exists():
        structure['has_train'] = True
        structure['splits'].append('train')
    
    if (dataset_path / 'val').exists():
        structure['has_val'] = True
        structure['splits'].append('val')
    
    if (dataset_path / 'valid').exists():
        structure['has_valid'] = True
        structure['splits'].append('valid')
    
    if (dataset_path / 'test').exists():
        structure['has_test'] = True
        structure['splits'].append('test')
    
    return structure


def collect_files_from_split(split_path):
    """Collect all image and label files from a split directory"""
    files = []
    
    images_dir = split_path / 'images'
    labels_dir = split_path / 'labels'
    
    if not images_dir.exists():
        return files
    
    for img_file in images_dir.glob('*'):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            # Find corresponding label
            label_file = labels_dir / f"{img_file.stem}.txt"
            
            files.append({
                'image': img_file,
                'label': label_file if label_file.exists() else None,
                'stem': img_file.stem
            })
    
    return files


def create_unified_split(all_files, train_ratio, val_ratio, test_ratio, seed=42):
    """Create unified train/val/test split from all collected files"""
    random.seed(seed)
    random.shuffle(all_files)
    
    total = len(all_files)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    
    splits = {
        'train': all_files[:train_end],
        'val': all_files[train_end:val_end],
        'test': all_files[val_end:]
    }
    
    return splits


def copy_files_to_output(files, output_base, dataset_name, split_name):
    """Copy files to output directory with unique naming"""
    copied = 0
    
    for idx, file_info in enumerate(files):
        # Create unique filename
        unique_name = f"{dataset_name}_{split_name}_{idx:05d}"
        
        # Copy image
        img_ext = file_info['image'].suffix
        output_img = output_base / split_name / 'images' / f"{unique_name}{img_ext}"
        shutil.copy2(file_info['image'], output_img)
        
        # Copy label if exists
        if file_info['label'] and file_info['label'].exists():
            output_label = output_base / split_name / 'labels' / f"{unique_name}.txt"
            shutil.copy2(file_info['label'], output_label)
        
        copied += 1
    
    return copied


def process_dataset(dataset_name, dataset_config):
    """Process a single dataset"""
    dataset_path = RAW_DATASETS_DIR / dataset_name
    
    if not dataset_path.exists():
        print(f"⚠️  Dataset not found: {dataset_name}")
        return None
    
    print(f"\n📦 Processing {dataset_name} ({dataset_config['priority']} priority)")
    print(f"   Type: {dataset_config['type']}")
    print(f"   Description: {dataset_config['description']}")
    
    # Analyze structure
    structure = get_dataset_structure(dataset_path)
    print(f"   Available splits: {', '.join(structure['splits'])}")
    
    # Collect all files from all available splits
    all_files = []
    
    for split in structure['splits']:
        split_path = dataset_path / split
        files = collect_files_from_split(split_path)
        all_files.extend(files)
        print(f"   - {split}: {len(files)} images")
    
    if not all_files:
        print(f"   ⚠️  No files found in {dataset_name}")
        return None
    
    print(f"   Total files: {len(all_files)}")
    
    # Read data.yaml to get class information
    yaml_path = dataset_path / 'data.yaml'
    yaml_data = read_yaml_file(yaml_path)
    
    if yaml_data:
        classes = yaml_data.get('names', [])
        print(f"   Classes: {len(classes)} - {', '.join(classes[:5])}{'...' if len(classes) > 5 else ''}")
    
    return {
        'name': dataset_name,
        'type': dataset_config['type'],
        'files': all_files,
        'classes': yaml_data.get('names', []) if yaml_data else [],
        'total_files': len(all_files)
    }


def merge_and_split_datasets(processed_datasets, dataset_type):
    """Merge datasets of same type and create unified splits"""
    print(f"\n🔀 Merging {dataset_type} datasets...")
    
    # Collect all files of this type
    all_files = []
    all_classes = set()
    
    for dataset in processed_datasets:
        if dataset and dataset['type'] == dataset_type:
            all_files.extend(dataset['files'])
            all_classes.update(dataset['classes'])
            print(f"   + {dataset['name']}: {dataset['total_files']} files")
    
    if not all_files:
        print(f"   ⚠️  No files found for {dataset_type}")
        return None
    
    print(f"   Total files: {len(all_files)}")
    print(f"   Total classes: {len(all_classes)}")
    
    # Create unified splits
    splits = create_unified_split(all_files, TRAIN_RATIO, VAL_RATIO, TEST_RATIO, RANDOM_SEED)
    
    print(f"   Split distribution:")
    print(f"   - Train: {len(splits['train'])} ({len(splits['train'])/len(all_files)*100:.1f}%)")
    print(f"   - Val:   {len(splits['val'])} ({len(splits['val'])/len(all_files)*100:.1f}%)")
    print(f"   - Test:  {len(splits['test'])} ({len(splits['test'])/len(all_files)*100:.1f}%)")
    
    return {
        'splits': splits,
        'classes': sorted(list(all_classes)),
        'total_files': len(all_files)
    }


def copy_merged_dataset(merged_data, dataset_type):
    """Copy merged dataset to output directory"""
    if not merged_data:
        return
    
    print(f"\n📋 Copying {dataset_type} files to output...")
    
    output_base = OUTPUT_DIR / dataset_type.replace('_', '_')
    
    total_copied = 0
    for split_name, files in merged_data['splits'].items():
        copied = copy_files_to_output(files, output_base, dataset_type, split_name)
        print(f"   ✅ {split_name}: {copied} files copied")
        total_copied += copied
    
    print(f"   Total: {total_copied} files copied")
    
    # Create data.yaml
    create_data_yaml(output_base, merged_data['classes'], dataset_type)


def create_data_yaml(output_base, classes, dataset_type):
    """Create data.yaml file for training"""
    yaml_content = {
        'path': str(output_base.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',
        'nc': len(classes),
        'names': classes
    }
    
    yaml_path = output_base / 'data.yaml'
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
    
    print(f"   ✅ Created {yaml_path}")


def generate_statistics_report(processed_datasets):
    """Generate statistics report"""
    print("\n" + "="*60)
    print("📊 DATASET PREPARATION SUMMARY")
    print("="*60)
    
    # Overall statistics
    total_damage_files = sum(d['total_files'] for d in processed_datasets if d and d['type'] == 'damage_detection')
    total_vehicle_files = sum(d['total_files'] for d in processed_datasets if d and d['type'] == 'vehicle_classification')
    
    print(f"\n📈 Overall Statistics:")
    print(f"   Damage Detection: {total_damage_files} images")
    print(f"   Vehicle Classification: {total_vehicle_files} images")
    print(f"   Total: {total_damage_files + total_vehicle_files} images")
    
    # Per-dataset breakdown
    print(f"\n📦 Per-Dataset Breakdown:")
    for dataset in processed_datasets:
        if dataset:
            print(f"   {dataset['name']:20s} | {dataset['type']:25s} | {dataset['total_files']:5d} images | {len(dataset['classes']):3d} classes")
    
    # Output structure
    print(f"\n📁 Output Structure:")
    print(f"   {OUTPUT_DIR}/")
    print(f"   ├── damage_detection/")
    print(f"   │   ├── train/ (70%)")
    print(f"   │   ├── val/   (20%)")
    print(f"   │   ├── test/  (10%)")
    print(f"   │   └── data.yaml")
    print(f"   └── vehicle_classification/")
    print(f"       ├── train/ (70%)")
    print(f"       ├── val/   (20%)")
    print(f"       ├── test/  (10%)")
    print(f"       └── data.yaml")
    
    print("\n✅ Dataset preparation complete!")
    print(f"   Ready for training with YOLOv8")
    print(f"   Next step: python scripts/train_yolo_damage.py")


def main():
    """Main execution"""
    print("="*60)
    print("🚀 InsurAI Dataset Preparation Script")
    print("="*60)
    
    # Setup directories
    setup_output_directories()
    
    # Process each dataset
    processed_datasets = []
    for dataset_name, dataset_config in DATASETS.items():
        result = process_dataset(dataset_name, dataset_config)
        processed_datasets.append(result)
    
    # Merge and split damage detection datasets
    damage_merged = merge_and_split_datasets(processed_datasets, 'damage_detection')
    if damage_merged:
        copy_merged_dataset(damage_merged, 'damage_detection')
    
    # Merge and split vehicle classification datasets
    vehicle_merged = merge_and_split_datasets(processed_datasets, 'vehicle_classification')
    if vehicle_merged:
        copy_merged_dataset(vehicle_merged, 'vehicle_classification')
    
    # Generate report
    generate_statistics_report(processed_datasets)


if __name__ == "__main__":
    main()
