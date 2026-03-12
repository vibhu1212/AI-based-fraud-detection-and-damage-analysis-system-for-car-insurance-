"""
Damage Detection Task (P0 Lock 3) - Enhanced with Senior's YOLO Approach
Detects vehicle damage using YOLOv8 with 8-class damage classification
Includes cost estimation and part-specific classification
Enhanced with lighting normalization for harsh conditions
Based on: https://github.com/ShivangSharma3/car_Damage_Final_Yolo
"""
import cv2
import numpy as np
import os
import torch
import yaml
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.damage import DamageDetection
from app.models.report import AIArtifact
from app.models.enums import ClaimStatus, DamageType
from app.services.storage import StorageService
from app.services.quality_gate_enhanced import EnhancedQualityGateValidator
from app.config import settings
from ultralytics import YOLO

# Import senior's utilities
from app.utils_yolo.price_estimator import DamagePriceEstimator
from app.utils_yolo.part_classifier import CarPartClassifier

# Set torch to allow loading YOLOv8 weights
torch.serialization.add_safe_globals([torch.nn.modules.container.Sequential])

logger = get_task_logger(__name__)

# YOLOv8 model settings
# Using trained damage detection model (epoch 30 checkpoint)
# Will be updated to best.pt when training completes
TRAINED_MODEL_PATH = "runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/epoch30.pt"
BEST_MODEL_PATH = "runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/best.pt"
FALLBACK_MODEL = "yolov8n.pt"  # Fallback if trained model not found
CONFIDENCE_THRESHOLD = 0.25  # Lowered for better detection

# Feature flag for preprocessing
USE_LIGHTING_NORMALIZATION = True  # Enable CLAHE preprocessing

# Class mapping from senior's model (8 damage classes)
DAMAGE_CLASS_MAPPING = {
    "bumper_dent": DamageType.DENT,
    "bumper_scratch": DamageType.SCRATCH,
    "door_dent": DamageType.DENT,
    "door_scratch": DamageType.SCRATCH,
    "glass_shatter": DamageType.GLASS_SHATTER,
    "head_lamp": DamageType.LAMP_BROKEN,
    "tail_lamp": DamageType.LAMP_BROKEN,
    "unknown": DamageType.OTHER,
    "grille": DamageType.MISSING_PART,
    "trunk": DamageType.DENT
}


class DamageDetector:
    """
    Damage detection using senior's enhanced YOLO approach
    Supports 8-class damage detection with price estimation and part classification
    Enhanced with lighting normalization for harsh conditions
    """
    
    def __init__(self, storage_service: StorageService, config_path: str = "backend/yolo_config.yaml"):
        self.storage = storage_service
        self.model = self._load_model()
        
        # Initialize preprocessing (for harsh lighting handling)
        if USE_LIGHTING_NORMALIZATION:
            self.preprocessor = EnhancedQualityGateValidator()
            logger.info("✓ Lighting normalization enabled (CLAHE preprocessing)")
        else:
            self.preprocessor = None
            logger.info("Lighting normalization disabled")
        
        # Load configuration
        config_full_path = Path(config_path)
        if not config_full_path.exists():
            # Fallback to relative path
            config_full_path = Path("yolo_config.yaml")
        
        if config_full_path.exists():
            with open(config_full_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Initialize price estimator and part classifier
            self.price_estimator = DamagePriceEstimator(str(config_full_path))
            self.part_classifier = CarPartClassifier(str(config_full_path))
            logger.info("✓ Loaded YOLO config and utilities")
        else:
            logger.warning("YOLO config not found, using defaults")
            self.config = None
            self.price_estimator = None
            self.part_classifier = None
        
    def _load_model(self):
        """Load YOLOv8 model (will use trained model when available)"""
        try:
            # Patch torch.load for YOLOv8 compatibility
            import torch
            original_load = torch.load
            
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            
            torch.load = patched_load
            
            # Check for trained model first - use absolute path from backend directory
            trained_model_path = Path("backend/yolov8_car_damage.pt")
            if not trained_model_path.exists():
                # Try relative path (if running from backend directory)
                trained_model_path = Path("yolov8_car_damage.pt")
            
            if trained_model_path.exists():
                logger.info(f"Loading trained model: {trained_model_path}")
                model = YOLO(str(trained_model_path))
            else:
                logger.info(f"Trained model not found at {trained_model_path}, using base model: yolov8n.pt")
                model = YOLO("yolov8n.pt")
            
            # Restore original torch.load
            torch.load = original_load
            
            return model
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def _map_class_to_damage_type(self, class_name: str) -> DamageType:
        """Map detected class name to our DamageType enum"""
        return DAMAGE_CLASS_MAPPING.get(class_name, DamageType.OTHER)
    
    def _extract_part_name(self, class_name: str) -> str:
        """Extract part name from class (e.g., 'bumper_dent' -> 'bumper')"""
        # For senior's 8-class model, the class name already contains the part
        if '_' in class_name:
            return class_name.split('_')[0]  # 'bumper_dent' -> 'bumper'
        return class_name
    
    def process_photo(self, object_key: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process photo for damage detection using enhanced YOLO model.
        Applies lighting normalization for harsh conditions.
        Returns (detections, price_analysis)
        """
        # Get file path from storage
        file_path = self.storage.download_file(object_key)
        
        if not file_path or not file_path.exists():
            raise ValueError(f"Photo not found in storage: {object_key}")
        
        # Read image for dimensions
        image = cv2.imread(str(file_path))
        if image is None:
            raise ValueError(f"Could not read image: {file_path}")
        
        img_height, img_width = image.shape[:2]
        
        # Apply preprocessing if enabled
        if self.preprocessor and USE_LIGHTING_NORMALIZATION:
            logger.info(f"Applying lighting normalization to {object_key}")
            try:
                # Use the preprocessing method from EnhancedQualityGateValidator
                processed_image = self.preprocessor.preprocess_for_damage_detection(image)
                logger.info("✓ Lighting normalization applied successfully")
                
                # Save processed image temporarily for YOLO inference
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                    cv2.imwrite(temp_path, processed_image)
                    inference_path = temp_path
            except Exception as e:
                logger.warning(f"Preprocessing failed, using original image: {e}")
                inference_path = str(file_path)
        else:
            inference_path = str(file_path)
        
        try:
            # Run inference
            results = self.model(inference_path, conf=CONFIDENCE_THRESHOLD)
            
            detections = []
            price_detections = []  # For price estimation
            
            # Parse results
            for r in results:
                boxes = r.boxes
                
                for box in boxes:
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Get confidence
                    conf = float(box.conf[0])
                    
                    # Get class
                    cls_id = int(box.cls[0])
                    class_name = self.model.names[cls_id] if hasattr(self.model, 'names') else f"class_{cls_id}"
                    
                    # Map to our damage type
                    damage_type = self._map_class_to_damage_type(class_name)
                    
                    # Extract part name for price estimation
                    part_name = self._extract_part_name(class_name)
                    
                    detection = {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf,
                        "class_id": cls_id,
                        "class_name": class_name,
                        "damage_type": damage_type,
                        "part_name": part_name
                    }
                    detections.append(detection)
                    
                    # Prepare for price estimation
                    if self.price_estimator:
                        price_detections.append({
                            'part': class_name,  # Use full class name for pricing
                            'detailed_part': class_name,
                            'confidence': conf,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)]
                        })
            
            # Calculate price estimate
            price_analysis = {}
            if self.price_estimator and price_detections:
                try:
                    price_analysis = self.price_estimator.calculate_total_estimate(price_detections)
                except Exception as e:
                    logger.warning(f"Price estimation failed: {e}")
                    price_analysis = {'total_cost': 0, 'damages': []}
            
            return detections, price_analysis
            
        finally:
            # Clean up temporary file if created
            if self.preprocessor and USE_LIGHTING_NORMALIZATION and inference_path != str(file_path):
                try:
                    os.unlink(inference_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
        return [], {}


@shared_task(name="app.tasks.damage_detection.detect_damages")
def detect_damages(claim_id: str) -> Dict[str, Any]:
    """
    Celery task: Detect damages using enhanced YOLO approach with cost estimation.
    Sets P0 Lock 3: damage_detected
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting enhanced damage detection for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        
        # Check previous locks
        if not claim.p0_locks.get("quality_gate_passed", False):
            logger.warning(f"Quality gate not passed for claim {claim_id}, skipping damage detection")
            return {"status": "skipped", "reason": "Quality gate not passed"}
        
        # Get all photos
        photos = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim_id
        ).all()
        
        if not photos:
            logger.warning(f"No photos found for claim {claim_id}")
            return {"status": "error", "error": "No photos found"}
        
        storage = StorageService()
        detector = DamageDetector(storage)
        
        total_damages: int = 0
        total_estimated_cost: float = 0.0
        photo_results: List[Dict[str, Any]] = []
        all_damages_info = []
        
        for photo in photos:
            try:
                detections, price_analysis = detector.process_photo(photo.object_key)
                
                # Save detections to DB
                for d in detections:
                    # Try to get severity from model first, fallback to intelligent calculation
                    severity = d.get("severity", None)
                    if severity is None:
                        # Calculate intelligent severity based on bbox size and confidence
                        bbox_width = d["bbox"][2] - d["bbox"][0]
                        bbox_height = d["bbox"][3] - d["bbox"][1]
                        bbox_area = bbox_width * bbox_height
                        confidence = d["confidence"]
                        
                        # Get image dimensions for relative sizing
                        img_area = photo.width * photo.height if photo.width and photo.height else 640 * 640
                        relative_area = bbox_area / img_area if img_area > 0 else 0
                        
                        # Determine severity based on relative damage size and confidence
                        # SEVERE: Large damage (>20% of image) with high confidence
                        # MODERATE: Medium damage (5-20% of image) or large with lower confidence
                        # MINOR: Small damage (<5% of image)
                        
                        if relative_area > 0.20 and confidence > 0.75:
                            severity = "SEVERE"
                        elif relative_area > 0.15 and confidence > 0.70:
                            severity = "MODERATE"
                        elif relative_area > 0.05:
                            severity = "MODERATE"
                        else:
                            severity = "MINOR"
                        
                        # Special cases: glass shatter and missing parts are always at least moderate
                        damage_type_str = str(d["damage_type"])
                        if "GLASS_SHATTER" in damage_type_str or "MISSING_PART" in damage_type_str:
                            if severity == "MINOR":
                                severity = "MODERATE"
                    
                    # Try to get vehicle part from model first, fallback to intelligent extraction
                    vehicle_part = d.get("part_name", None)
                    if vehicle_part is None:
                        # Extract vehicle part from detection metadata or use intelligent mapping
                        damage_class = d.get("class_name", "").lower()
                        
                        # Map damage class to vehicle part
                        if "bumper" in damage_class:
                            vehicle_part = "FRONT_BUMPER" if "front" in damage_class else "REAR_BUMPER"
                        elif "door" in damage_class:
                            vehicle_part = "DOOR_FL"  # Default to front left, can be refined
                        elif "head_lamp" in damage_class or "headlight" in damage_class:
                            vehicle_part = "HEADLIGHT_L"
                        elif "tail_lamp" in damage_class or "taillight" in damage_class:
                            vehicle_part = "TAILLIGHT_L"
                        elif "windshield" in damage_class or "glass" in damage_class:
                            vehicle_part = "WINDSHIELD"
                        elif "hood" in damage_class:
                            vehicle_part = "HOOD"
                        elif "fender" in damage_class:
                            vehicle_part = "FENDER_L"
                        else:
                            vehicle_part = "OTHER"
                    
                    damage = DamageDetection(
                        claim_id=claim_id,
                        media_id=photo.id,
                        damage_type=d["damage_type"],
                        confidence=d["confidence"],
                        bbox_x1=int(d["bbox"][0]),
                        bbox_y1=int(d["bbox"][1]),
                        bbox_x2=int(d["bbox"][2]),
                        bbox_y2=int(d["bbox"][3]),
                        severity=severity,
                        vehicle_part=vehicle_part,
                        metadata={
                            "class_name": d.get("class_name", "unknown"),
                            "part_name": d.get("part_name", "unknown"),
                            "bbox_area": (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]),
                            "severity_source": "model" if d.get("severity") else "calculated",
                            "part_source": "model" if d.get("part_name") else "extracted"
                        }
                    )
                    db.add(damage)
                    total_damages += 1
                
                # Accumulate price estimates
                if price_analysis and 'total_cost' in price_analysis:
                    total_estimated_cost += float(price_analysis['total_cost'])
                    if 'damages' in price_analysis:
                        all_damages_info.extend(price_analysis['damages'])
                
                photo_results.append({
                    "photo_id": str(photo.id),
                    "detections": len(detections),
                    "estimated_cost": price_analysis.get('total_cost', 0) if price_analysis else 0
                })
                
                logger.info(f"Processed photo {photo.id}: {len(detections)} damages detected")
                
            except Exception as e:
                logger.error(f"Failed to process photo {photo.id}: {str(e)}")
                # Continue with other photos
        
        # Update claim P0 lock
        claim.p0_locks["damage_detected"] = True
        flag_modified(claim, "p0_locks")
        
        # Store estimated cost in claim extra_data
        if not claim.extra_data:
            claim.extra_data = {}
        claim.extra_data["estimated_repair_cost"] = total_estimated_cost
        claim.extra_data["damage_breakdown"] = all_damages_info
        flag_modified(claim, "extra_data")
        
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="damage_detection_result",
            model_name="yolov8_enhanced",
            model_version="senior_approach_v1",
            artifact_json={
                "total_damages": total_damages,
                "estimated_cost_inr": total_estimated_cost,
                "photo_results": photo_results,
                "damage_classes_detected": list(set([d.get('part', 'unknown') for d in all_damages_info]))
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"Enhanced damage detection complete for claim {claim_id}. "
                   f"Found {total_damages} damages. Estimated cost: ₹{total_estimated_cost:,}")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_damages": total_damages,
            "estimated_cost_inr": total_estimated_cost,
            "photo_results": photo_results
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Enhanced damage detection failed for claim {claim_id}: {str(e)}")
        raise
    
    finally:
        db.close()
        
    return {"status": "error", "error": "Unexpected completion path"}

