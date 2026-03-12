"""
Merge and clean COCO dataset classes
Reduces 42 classes to 10 meaningful categories
"""
import json
from pathlib import Path
from collections import defaultdict
import shutil

# Clean class taxonomy based on actual dataset
CLASS_MAPPING = {
    # Lights damage (7334 + 1964 = 9298 samples)
    'light-damage': [
        'Headlight-Damage',
        'Taillight-Damage',
        'Signlight-Damage'
    ],
    
    # Windscreen damage (3025 + 1430 + 676 + 432 = 5563 samples)
    'windscreen-damage': [
        'Front-Windscreen-Damage',
        'Rear-windscreen-Damage',
        'Cracked'  # Glass cracks
    ],
    
    # Broken/missing parts (5834 + 2527 = 8361 samples)
    'broken-part': [
        'Broken part',
        'Missing part'
    ],
    
    # Dents (1180 + 1219 + 123 + 12 + 1821 + 2883 = 7238 samples)
    'dent': [
        'Dent',
        'dent',
        'bonnet-dent',
        'doorouter-dent',
        'Major-Rear-Bumper-Dent',
        'RunningBoard-Dent'
    ],
    
    # Scratches (17 + 671 = 688 samples)
    'scratch': [
        'Scratch',
        'doorouter-scratch'
    ],
    
    # Paint/surface damage (2485 + 1807 + 12 = 4304 samples)
    'paint-damage': [
        'Corrosion',
        'Flaking',
        'Paint chip'
    ],
    
    # Major structural damage (4018 + 1551 = 5569 samples)
    'major-damage': [
        'Damage',
        'dislocation'
    ],
    
    # Mirror damage (12 samples - will be removed if <20 total)
    'mirror-damage': [
        'Sidemirror-Damage'
    ]
}

def merge_coco_dataset(input_json, output_json, class_mapping, min_samples=20):
    """
    Merge classes in COCO dataset
    
    Args:
        input_json: Path to input COCO JSON
        output_json: Path to output COCO JSON
        class_mapping: Dict mapping new class names to list of old class names
        min_samples: Minimum samples per class (classes below this are removed)
    """
    print(f"\n🔄 Processing: {input_json}")
    print("=" * 80)
    
    with open(input_json) as f:
        data = json.load(f)
    
    # Create reverse mapping (old_name -> new_name)
    old_to_new = {}
    for new_name, old_names in class_mapping.items():
        for old_name in old_names:
            old_to_new[old_name] = new_name
    
    # Get old categories
    old_categories = {cat['id']: cat['name'] for cat in data['categories']}
    
    # Count samples per new class
    new_class_counts = defaultdict(int)
    for ann in data['annotations']:
        old_name = old_categories[ann['category_id']]
        if old_name in old_to_new:
            new_name = old_to_new[old_name]
            new_class_counts[new_name] += 1
    
    # Filter out classes with too few samples
    valid_classes = {name for name, count in new_class_counts.items() if count >= min_samples}
    
    print(f"\n📊 Class Statistics:")
    print("-" * 80)
    print(f"{'New Class':<25} {'Samples':>10} {'Status':>15}")
    print("-" * 80)
    for new_name in sorted(class_mapping.keys()):
        count = new_class_counts[new_name]
        status = "✅ KEEP" if new_name in valid_classes else "❌ REMOVE"
        print(f"{new_name:<25} {count:>10} {status:>15}")
    
    # Create new categories
    new_categories = []
    new_cat_id_map = {}  # new_name -> new_id
    for idx, new_name in enumerate(sorted(valid_classes), 1):
        new_categories.append({
            'id': idx,
            'name': new_name,
            'supercategory': 'damage'
        })
        new_cat_id_map[new_name] = idx
    
    # Create mapping from old_id -> new_id
    old_id_to_new_id = {}
    for old_id, old_name in old_categories.items():
        if old_name in old_to_new:
            new_name = old_to_new[old_name]
            if new_name in valid_classes:
                old_id_to_new_id[old_id] = new_cat_id_map[new_name]
    
    # Filter and update annotations
    new_annotations = []
    removed_count = 0
    for ann in data['annotations']:
        old_cat_id = ann['category_id']
        if old_cat_id in old_id_to_new_id:
            ann['category_id'] = old_id_to_new_id[old_cat_id]
            new_annotations.append(ann)
        else:
            removed_count += 1
    
    # Update data
    data['categories'] = new_categories
    data['annotations'] = new_annotations
    
    # Save
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w') as f:
        json.dump(data, f)
    
    print(f"\n✅ Results:")
    print(f"   Original categories: {len(old_categories)}")
    print(f"   New categories: {len(new_categories)}")
    print(f"   Original annotations: {len(data['annotations']) + removed_count}")
    print(f"   New annotations: {len(new_annotations)}")
    print(f"   Removed annotations: {removed_count}")
    print(f"   Saved to: {output_json}")
    
    return {
        'old_categories': len(old_categories),
        'new_categories': len(new_categories),
        'old_annotations': len(data['annotations']) + removed_count,
        'new_annotations': len(new_annotations),
        'removed_annotations': removed_count
    }


def create_data_yaml(output_dir, categories):
    """Create data.yaml for Detectron2 training"""
    yaml_content = f"""# Merged damage segmentation dataset
# Generated automatically

# Paths
train: {output_dir}/train_coco.json
val: {output_dir}/val_coco.json

# Number of classes
nc: {len(categories)}

# Class names
names:
"""
    for cat in sorted(categories, key=lambda x: x['id']):
        yaml_content += f"  {cat['id']}: {cat['name']}\n"
    
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    
    print(f"\n✅ Created: {yaml_path}")
    return yaml_path


if __name__ == "__main__":
    # Paths
    input_dir = Path("backend/datasets/prepared/damage_segmentation_coco")
    output_dir = Path("backend/datasets/prepared/damage_segmentation_coco_merged")
    
    train_input = input_dir / "train_coco.json"
    val_input = input_dir / "val_coco.json"
    
    train_output = output_dir / "train_coco.json"
    val_output = output_dir / "val_coco.json"
    
    if not train_input.exists():
        print(f"❌ Error: {train_input} not found")
        exit(1)
    
    print("🚀 Merging COCO Dataset Classes")
    print("=" * 80)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Classes: 42 → ~7-10")
    
    # Merge train dataset
    train_stats = merge_coco_dataset(train_input, train_output, CLASS_MAPPING, min_samples=20)
    
    # Merge val dataset
    val_stats = merge_coco_dataset(val_input, val_output, CLASS_MAPPING, min_samples=20)
    
    # Load merged data to get final categories
    with open(train_output) as f:
        merged_data = json.load(f)
    
    # Create data.yaml
    create_data_yaml(output_dir, merged_data['categories'])
    
    # Copy images directory (symlink to save space)
    images_src = input_dir.parent / "damage_detection"
    images_dst = output_dir / "images"
    
    if not images_dst.exists():
        print(f"\n🔗 Creating symlink to images...")
        images_dst.symlink_to(images_src.absolute())
        print(f"   {images_dst} -> {images_src}")
    
    print("\n" + "=" * 80)
    print("✅ Dataset Merging Complete!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Train: {train_stats['old_categories']} → {train_stats['new_categories']} classes")
    print(f"   Train: {train_stats['old_annotations']} → {train_stats['new_annotations']} annotations")
    print(f"   Val: {val_stats['old_categories']} → {val_stats['new_categories']} classes")
    print(f"   Val: {val_stats['old_annotations']} → {val_stats['new_annotations']} annotations")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n🎯 Next step: Update training script to use merged dataset")
