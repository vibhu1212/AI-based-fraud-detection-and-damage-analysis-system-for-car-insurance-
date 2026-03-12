"""
Analyze dataset class distribution for Mask R-CNN training
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

def analyze_coco_dataset(json_path):
    """Analyze COCO format dataset"""
    print(f"\n📊 Analyzing: {json_path}")
    print("=" * 80)
    
    with open(json_path) as f:
        data = json.load(f)
    
    # Get categories
    categories = {cat['id']: cat['name'] for cat in data['categories']}
    print(f"\n📋 Total Categories: {len(categories)}")
    
    # Count annotations per category
    category_counts = Counter()
    for ann in data['annotations']:
        category_counts[ann['category_id']] += 1
    
    # Sort by count
    sorted_counts = sorted(
        [(categories[cat_id], count) for cat_id, count in category_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    print(f"\n📈 Class Distribution:")
    print("-" * 80)
    print(f"{'Class Name':<30} {'Count':>10} {'Percentage':>12}")
    print("-" * 80)
    
    total = sum(category_counts.values())
    for name, count in sorted_counts:
        pct = (count / total) * 100
        print(f"{name:<30} {count:>10} {pct:>11.2f}%")
    
    # Identify problematic classes
    print(f"\n⚠️  Classes with <20 samples (should remove):")
    print("-" * 80)
    rare_classes = [(name, count) for name, count in sorted_counts if count < 20]
    for name, count in rare_classes:
        print(f"  - {name}: {count} samples")
    
    print(f"\n⚡ Classes with 20-50 samples (should merge):")
    print("-" * 80)
    merge_classes = [(name, count) for name, count in sorted_counts if 20 <= count < 50]
    for name, count in merge_classes:
        print(f"  - {name}: {count} samples")
    
    print(f"\n✅ Classes with 50+ samples (keep):")
    print("-" * 80)
    good_classes = [(name, count) for name, count in sorted_counts if count >= 50]
    for name, count in good_classes:
        print(f"  - {name}: {count} samples")
    
    return {
        'total_categories': len(categories),
        'total_annotations': total,
        'rare_classes': rare_classes,
        'merge_classes': merge_classes,
        'good_classes': good_classes,
        'categories': categories,
        'category_counts': category_counts
    }


def propose_class_mapping(train_stats, val_stats):
    """Propose a clean class taxonomy"""
    print("\n" + "=" * 80)
    print("🎯 PROPOSED CLASS TAXONOMY (8-12 classes)")
    print("=" * 80)
    
    # Merge strategy based on semantic similarity
    class_mapping = {
        # Dents (all types)
        'dent': [
            'Dent', 'dent',
            'bonnet-dent', 'doorouter-dent', 'fender-dent',
            'medium-Bodypanel-Dent', 'pillar-dent', 'quaterpanel-dent',
            'rear-bumper-dent', 'roof-dent', 'Major-Rear-Bumper-Dent'
        ],
        
        # Scratches (all types)
        'scratch': [
            'Scratch', 'scratch',
            'doorouter-scratch', 'front-bumper-scratch',
            'rear-bumper-scratch'
        ],
        
        # Glass damage (all types)
        'glass-damage': [
            'glass-broken', 'glass-large-crack', 'glass-small-crack',
            'glass-spider-crack', 'Cracked'
        ],
        
        # Bumper damage (major)
        'bumper-damage': [
            'front-bumper-broken', 'rear-bumper-broken',
            'bumper-dent', 'bumper-scratch'
        ],
        
        # Broken/missing parts
        'broken-part': [
            'Broken part', 'broken part', 'Missing part',
            'Sidemirror-Damage', 'Signlight-Damage'
        ],
        
        # Paint damage
        'paint-damage': [
            'paint-chip', 'paint-trace', 'rust', 'spot',
            'discoloration'
        ],
        
        # Major structural damage
        'major-damage': [
            'Damage', 'smash', 'dislocation', 'deformation'
        ],
        
        # Tire/rubber damage
        'tire-damage': [
            'rubber-puncture', 'tire-flat'
        ]
    }
    
    print("\n📋 Proposed Mapping:")
    for new_class, old_classes in class_mapping.items():
        print(f"\n{new_class.upper()}:")
        for old_class in old_classes:
            # Count samples in train
            train_count = 0
            for cat_id, cat_name in train_stats['categories'].items():
                if cat_name == old_class:
                    train_count = train_stats['category_counts'].get(cat_id, 0)
                    break
            print(f"  - {old_class:<30} ({train_count:>4} samples)")
    
    return class_mapping


if __name__ == "__main__":
    # Analyze train and val datasets
    train_json = Path("backend/datasets/prepared/damage_segmentation_coco/train_coco.json")
    val_json = Path("backend/datasets/prepared/damage_segmentation_coco/val_coco.json")
    
    if not train_json.exists():
        print(f"❌ Error: {train_json} not found")
        exit(1)
    
    train_stats = analyze_coco_dataset(train_json)
    val_stats = analyze_coco_dataset(val_json)
    
    # Propose clean taxonomy
    class_mapping = propose_class_mapping(train_stats, val_stats)
    
    # Save mapping
    mapping_file = Path("backend/datasets/prepared/damage_segmentation_coco/class_mapping.json")
    with open(mapping_file, 'w') as f:
        json.dump(class_mapping, f, indent=2)
    
    print(f"\n✅ Class mapping saved to: {mapping_file}")
    print("\nNext step: Run merge_classes.py to apply this mapping")
