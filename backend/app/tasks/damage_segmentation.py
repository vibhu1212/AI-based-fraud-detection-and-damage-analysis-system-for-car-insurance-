"""
Damage Segmentation Task (Optional Enhancement)
Generates pixel-level masks for damage regions using Mask R-CNN
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm.attributes import flag_modified
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.models.report import AIArtifact
from app.services.storage import StorageService
from typing import Dict, List, Optional
import io
import torch

logger = get_task_logger(__name__)

# Segmentation model settings
MASKRCNN_MODEL_PATH = "runs/maskrcnn/merged_output/model_0015999.pth"  # Production model (AP50: 45.98%)
CONFIDENCE_THRESHOLD = 0.5


class DamageSegmenter:
    """Damage segmentation logic using Mask R-CNN"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self.model = self._load_model()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    def _load_model(self):
        """Load trained Mask R-CNN model"""
        try:
            from detectron2.engine import DefaultPredictor
            from detectron2.config import get_cfg
            from detectron2 import model_zoo
            
            # Setup config
            cfg = get_cfg()
            cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
            
            # Model settings
            cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7  # 7 damage classes
            cfg.MODEL.WEIGHTS = MASKRCNN_MODEL_PATH
            cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = CONFIDENCE_THRESHOLD
            cfg.MODEL.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Create predictor
            predictor = DefaultPredictor(cfg)
            
            logger.info(f"Loaded Mask R-CNN model from: {MASKRCNN_MODEL_PATH}")
            logger.info(f"Using device: {cfg.MODEL.DEVICE}")
            return predictor
            
        except Exception as e:
            logger.error(f"Failed to load Mask R-CNN model: {e}")
            logger.warning("Falling back to simple rectangular masks")
            return None
            
    def generate_mask(
        self, 
        image_path: Path,
        bbox: tuple
    ) -> Optional[Dict]:
        """
        Generate pixel mask for damage region using Mask R-CNN.
        
        Args:
            image_path: Path to image file
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Dict with mask data or None if failed
        """
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return None
            
            # If model failed to load, use simple rectangular mask
            if self.model is None:
                x1, y1, x2, y2 = bbox
                x1, y1 = max(0, int(x1)), max(0, int(y1))
                x2 = min(image.shape[1], int(x2))
                y2 = min(image.shape[0], int(y2))
                
                if x2 <= x1 or y2 <= y1:
                    logger.warning(f"Invalid bbox: {bbox}")
                    return None
                
                mask = np.ones((y2 - y1, x2 - x1), dtype=np.uint8) * 255
                mask_area = (x2 - x1) * (y2 - y1)
                
                mask_pil = Image.fromarray(mask)
                mask_bytes = io.BytesIO()
                mask_pil.save(mask_bytes, format='PNG')
                mask_bytes.seek(0)
                
                return {
                    "mask_bytes": mask_bytes,
                    "mask_area": int(mask_area),
                    "mask_width": mask.shape[1],
                    "mask_height": mask.shape[0]
                }
            
            # Extract damage region
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2 = min(image.shape[1], int(x2))
            y2 = min(image.shape[0], int(y2))
            
            if x2 <= x1 or y2 <= y1:
                logger.warning(f"Invalid bbox: {bbox}")
                return None
            
            damage_region = image[y1:y2, x1:x2]
            
            # Run Mask R-CNN on damage region
            outputs = self.model(damage_region)
            
            # Check if any masks were generated
            if "instances" not in outputs or len(outputs["instances"]) == 0:
                logger.warning("No segmentation masks generated, using rectangular mask")
                mask = np.ones((y2 - y1, x2 - x1), dtype=np.uint8) * 255
            else:
                # Get the best mask (highest confidence)
                instances = outputs["instances"].to("cpu")
                masks = instances.pred_masks.numpy()
                
                if len(masks) > 0:
                    # Use the first (best) mask
                    mask = (masks[0] * 255).astype(np.uint8)
                else:
                    # Fallback to rectangular mask
                    mask = np.ones((y2 - y1, x2 - x1), dtype=np.uint8) * 255
            
            # Calculate mask area
            mask_area = np.sum(mask > 127)  # Count white pixels
            
            # Convert mask to PNG bytes
            mask_pil = Image.fromarray(mask)
            mask_bytes = io.BytesIO()
            mask_pil.save(mask_bytes, format='PNG')
            mask_bytes.seek(0)
            
            return {
                "mask_bytes": mask_bytes,
                "mask_area": int(mask_area),
                "mask_width": mask.shape[1],
                "mask_height": mask.shape[0]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate mask: {e}")
            return None
            
    def process_damage(
        self,
        damage: DamageDetection,
        claim_id: str
    ) -> Optional[str]:
        """
        Process single damage to generate and store mask.
        
        Args:
            damage: DamageDetection object
            claim_id: Claim ID for storage path
            
        Returns:
            Object key of stored mask or None if failed
        """
        try:
            # Get image path
            if not damage.media:
                logger.warning(f"No media found for damage {damage.id}")
                return None
            
            image_path = self.storage.download_file(damage.media.object_key)
            if not image_path or not image_path.exists():
                logger.error(f"Image not found: {damage.media.object_key}")
                return None
            
            # Get bounding box
            bbox = (
                damage.bbox_x1 or 0,
                damage.bbox_y1 or 0,
                damage.bbox_x2 or 100,
                damage.bbox_y2 or 100
            )
            
            # Generate mask
            mask_data = self.generate_mask(image_path, bbox)
            if not mask_data:
                return None
            
            # Store mask in object storage
            mask_filename = f"mask_{damage.id}.png"
            mask_object_key = self.storage.generate_object_key(
                "masks",
                claim_id,
                mask_filename
            )
            
            # Upload mask
            upload_result = self.storage.upload_file(
                file=mask_data["mask_bytes"],
                object_key=mask_object_key,
                content_type="image/png"
            )
            
            logger.info(f"Mask stored: {mask_object_key} (area: {mask_data['mask_area']} px)")
            
            return mask_object_key
            
        except Exception as e:
            logger.error(f"Failed to process damage {damage.id}: {e}")
            return None


@shared_task(name="app.tasks.damage_segmentation.segment_damages")
def segment_damages(claim_id: str) -> Dict:
    """
    Celery task: Generate segmentation masks for all detected damages.
    Optional enhancement for better damage visualization.
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting damage segmentation for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Check if damage detection is complete
        if not claim.p0_locks.get("damage_detected", False):
            logger.warning(f"Damage detection not complete for claim {claim_id}, skipping segmentation")
            return {"status": "skipped", "reason": "Damage detection not complete"}
            
        # Get all damage detections
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        if not damages:
            logger.warning(f"No damages found for claim {claim_id}")
            return {"status": "completed", "claim_id": claim_id, "total_segmented": 0}
            
        storage = StorageService()
        segmenter = DamageSegmenter(storage)
        
        total_segmented = 0
        failed_segmentations = 0
        
        for damage in damages:
            try:
                # Generate and store mask
                mask_object_key = segmenter.process_damage(damage, claim_id)
                
                if mask_object_key:
                    # Update damage record with mask URL
                    damage.mask_object_key = mask_object_key
                    total_segmented += 1
                else:
                    failed_segmentations += 1
                    
            except Exception as e:
                logger.error(f"Failed to segment damage {damage.id}: {str(e)}")
                failed_segmentations += 1
                # Continue with other damages
                
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="damage_segmentation_result",
            model_name="maskrcnn-resnet50-fpn",
            model_version="production-iter15999-ap50-46",
            artifact_json={
                "total_damages": len(damages),
                "total_segmented": total_segmented,
                "failed_segmentations": failed_segmentations
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"Damage segmentation complete for claim {claim_id}. Segmented {total_segmented}/{len(damages)} damages.")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_damages": len(damages),
            "total_segmented": total_segmented,
            "failed_segmentations": failed_segmentations
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Damage segmentation failed for claim {claim_id}: {str(e)}")
        raise
        
    finally:
        db.close()
