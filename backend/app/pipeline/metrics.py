"""
Evaluation Metrics Utilities

Provides standardized metrics for pipeline evaluation:
- Intersection over Union (IoU) for segmentation and bounding boxes.
- Mean Average Precision (mAP) for object detection.
- Accuracy for classification and heuristics.
"""
from typing import List, Tuple, Dict, Optional, Any
import numpy as np # type: ignore
import collections

def compute_iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
    """Compute Intersection over Union between two bounding boxes (x1, y1, x2, y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter == 0.0:
        return 0.0
        
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter

    return float(inter / union) if union > 0 else 0.0

def compute_accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
    """Compute basic classification accuracy."""
    if not y_true or not y_pred or len(y_true) != len(y_pred):
        return 0.0
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return float(correct / len(y_true))

def compute_map(
    predictions: List[Dict[str, Any]], 
    ground_truths: List[Dict[str, Any]], 
    iou_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Compute mean Average Precision (mAP) at a specific IoU threshold.
    
    Format for predictions/ground_truths:
    [
        {
            "class": str,
            "confidence": float (only for predictions),
            "bounding_box": [x1, y1, x2, y2],
            "image_id": str (to match images)
        }, ...
    ]
    """
    # Group GTs by class and image
    gt_by_class: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for gt in ground_truths:
        cls = str(gt.get("class"))
        img_id = str(gt.get("image_id"))
        if not gt_by_class.get(cls):
            gt_by_class[cls] = {}
        if not gt_by_class[cls].get(img_id):
            gt_by_class[cls][img_id] = []
        gt_by_class[cls][img_id].append({
            "bbox": gt.get("bounding_box"),
            "matched": False
        })
        
    # Group predictions by class
    pred_by_class: Dict[str, List[Dict[str, Any]]] = {}
    for pred in predictions:
        cls = str(pred.get("class"))
        if cls not in pred_by_class:
            pred_by_class[cls] = []
        pred_by_class[cls].append(pred)
        
    aps = {}
    
    # Calculate AP for each class
    for cls, preds in pred_by_class.items():
        if not gt_by_class.get(cls): # type: ignore
            aps[cls] = 0.0
            continue
            
        # Sort predictions by confidence descending
        preds.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        
        n_gts_for_class = sum(len(bboxes) for bboxes in gt_by_class.get(cls, {}).values()) # type: ignore
        if n_gts_for_class == 0:
            continue
            
        tp = np.zeros(len(preds))
        fp = np.zeros(len(preds))
        
        for i, pred in enumerate(preds):
            img_id = str(pred.get("image_id"))
            pred_bbox = tuple(pred.get("bounding_box", [0,0,0,0]))
            
            gts = gt_by_class.get(cls, {}).get(img_id, [])
            best_iou = 0.0
            best_gt_idx = -1
            
            for j, gt in enumerate(gts):
                iou = compute_iou(pred_bbox, tuple(gt["bbox"]))
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = j
                    
            if best_iou >= iou_threshold and best_gt_idx >= 0 and not gts[best_gt_idx]["matched"]:
                tp[i] = 1
                gts[best_gt_idx]["matched"] = True
            else:
                fp[i] = 1
                
        # Compute precision and recall arrays
        tp_cumsum = np.cumsum(tp)
        fp_cumsum = np.cumsum(fp)
        
        recalls = tp_cumsum / n_gts_for_class
        precisions = tp_cumsum / np.maximum(tp_cumsum + fp_cumsum, np.finfo(float).eps)
        
        # Calculate AP (area under P-R curve) using 11-point interpolation
        ap = 0.0
        for t in np.arange(0.0, 1.1, 0.1):
            if np.sum(recalls >= t) == 0:
                p = 0.0
            else:
                p = np.max(precisions[recalls >= t])
            ap += p / 11.0
            
        aps[cls] = float(ap)
        
    # Reset matched flags
    for cls_name in gt_by_class:
        for image_id in gt_by_class.get(cls_name, {}):
            for gt_item in gt_by_class.get(cls_name, {}).get(image_id, []):
                gt_item["matched"] = False

    return {
        "mAP": float(np.mean(list(aps.values()))) if aps else 0.0,
        "class_APs": aps
    }
