"""
Convert YOLO format dataset to COCO format for Mask R-CNN training
Handles both bounding box and segmentation polygon formats
"""
import json
import os
from pathlib import Path
import cv2
import numpy as np
from tqdm import tqdm
import yaml

def polygon_to_coco(polygon_points, img_width, img_height):
    """
    Convert YOLO polygon format to COCO segmentation format
    YOLO format: normalized coordinates [x1, y1, x2, y2, ..., xn, yn]
    COCO format: pixel coordinates [x1, y1, x2, y2, ..., xn, yn]
    """
    # Convert normalized coordinates to pixel coordinates
    segmentation = []
    for i in range(0, len(polygon_points), 2):
        x_norm = float(polygon_points[i])
        y_norm = float(polygon_points[i + 1])
        x_px = x_norm * img_width
        y_px = y_norm * img_height
        segmentation.extend([x_px, y_px])
    
    # Calculate bounding box from polygon
    x_coords = [segmentation[i] for i in range(0, len(segmentation), 2)]
    y_coords = [segmentation[i] for i in range(1, len(segmentation), 2)]
    
    x_min = min(x_coords)
    y_min = min(y_coords)
    x_max = max(x_coords)
    y_max = max(y_coords)
    
    width = x_max - x_min
    height = y_max - y_min
    
    # Calculate area using shoelace formula
    area = 0.0
    n = len(x_coords)
    for i in range(n):
        j = (i + 1) % n
        area += x_coords[i] * y_coords[j]
        area -= x_coords[j] * y_coords[i]
    area = abs(area) / 2.0
    
    # COCO bbox format: [x, y, width, height]
    coco_bbox = [float(x_min), float(y_min), float(width), float(height)]
    
    return segmentation, coco_bbox, area


def bbox_to_segmentation(bbox, img_width, img_height, expand_ratio=0.05):
    """
    Convert YOLO bounding box to segmentation polygon (fallback for bbox-only annotations)
    Expands bbox slightly and creates a polygon mask
    """
    x_center, y_center, width, height = bbox
    
    # Convert to pixel coordinates
    x_center_px = x_center * img_width
    y_center_px = y_center * img_height
    width_px = width * img_width
    height_px = height * img_height
    
    # Expand slightly for better segmentation
    width_px *= (1 + expand_ratio)
    height_px *= (1 + expand_ratio)
    
    # Calculate corners
    x1 = x_center_px - width_px / 2
    y1 = y_center_px - height_px / 2
    x2 = x_center_px + width_px / 2
    y2 = y_center_px + height_px / 2
    
    # Create polygon (rectangle with 4 points)
    # Format: [x1, y1, x2, y1, x2, y2, x1, y2]
    segmentation = [
        float(x1), float(y1),
        float(x2), float(y1),
        float(x2), float(y2),
        float(x1), float(y2)
    ]
    
    # Calculate area
    area = width_px * height_px
    
    # Calculate bbox in COCO format [x, y, width, height]
    coco_bbox = [float(x1), float(y1), float(width_px), float(height_px)]
    
    return segmentation, coco_bbox, area


def convert_yolo_to_coco(yolo_data_yaml, output_dir):
    """
    Convert YOLO dataset to COCO format
    """
    # Load YOLO data.yaml
    with open(yolo_data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)
    
    # Get paths
    dataset_root = Path(yolo_data_yaml).parent
    train_images_dir = dataset_root / data_config['train']
    val_images_dir = dataset_root / data_config['val']
    
    # Get class names
    class_names = data_config['names']
    
    print(f"📊 Dataset Info:")
    print(f"   Root: {dataset_root}")
    print(f"   Classes: {len(class_names)}")
    print(f"   Class names: {class_names}")
    print()
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert train and val splits
    for split, images_dir in [('train', train_images_dir), ('val', val_images_dir)]:
        print(f"🔄 Converting {split} split...")
        
        # Initialize COCO format
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        # Add categories
        for idx, name in enumerate(class_names):
            coco_data["categories"].append({
                "id": idx,
                "name": name,
                "supercategory": "damage"
            })
        
        # Get all images
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        
        annotation_id = 1
        
        for image_id, image_path in enumerate(tqdm(image_files, desc=f"Processing {split}")):
            # Read image to get dimensions
            img = cv2.imread(str(image_path))
            if img is None:
                continue
            
            img_height, img_width = img.shape[:2]
            
            # Add image info
            coco_data["images"].append({
                "id": image_id,
                "file_name": image_path.name,
                "width": img_width,
                "height": img_height
            })
            
            # Read corresponding label file
            # Structure: train/images/*.jpg -> train/labels/*.txt
            label_path = image_path.parent.parent / "labels" / f"{image_path.stem}.txt"
            
            if not label_path.exists():
                continue
            
            # Parse YOLO annotations
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    
                    class_id = int(parts[0])
                    
                    # Check if this is segmentation (polygon) or bbox format
                    if len(parts) > 5:
                        # Segmentation format: class x1 y1 x2 y2 ... xn yn
                        polygon_points = [float(x) for x in parts[1:]]
                        segmentation, coco_bbox, area = polygon_to_coco(
                            polygon_points, img_width, img_height
                        )
                    else:
                        # Bounding box format: class x_center y_center width height
                        bbox = [float(x) for x in parts[1:5]]
                        segmentation, coco_bbox, area = bbox_to_segmentation(
                            bbox, img_width, img_height
                        )
                    
                    # Add annotation
                    coco_data["annotations"].append({
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": class_id,
                        "segmentation": [segmentation],  # List of polygons
                        "area": area,
                        "bbox": coco_bbox,
                        "iscrowd": 0
                    })
                    
                    annotation_id += 1
        
        # Save COCO JSON
        output_file = output_dir / f"{split}_coco.json"
        with open(output_file, 'w') as f:
            json.dump(coco_data, f, indent=2)
        
        print(f"✅ {split} split converted:")
        print(f"   Images: {len(coco_data['images'])}")
        print(f"   Annotations: {len(coco_data['annotations'])}")
        print(f"   Saved to: {output_file}")
        print()
    
    print("✅ Conversion complete!")
    return output_dir


if __name__ == "__main__":
    # Convert damage detection dataset
    yolo_data_yaml = "backend/datasets/prepared/damage_detection/data.yaml"
    output_dir = "backend/datasets/prepared/damage_segmentation_coco"
    
    print("🔄 Converting YOLO dataset to COCO format for Mask R-CNN")
    print("=" * 60)
    print()
    
    convert_yolo_to_coco(yolo_data_yaml, output_dir)
    
    print()
    print("🎯 Ready for Mask R-CNN training!")
