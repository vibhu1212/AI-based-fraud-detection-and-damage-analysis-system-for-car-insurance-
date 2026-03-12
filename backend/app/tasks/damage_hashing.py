"""
Damage Hashing Task (P0 Lock 4)
Generates perceptual hashes and ORB descriptors for damage regions
"""
import cv2
import numpy as np
import imagehash
from PIL import Image
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm.attributes import flag_modified
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.models.report import AIArtifact
from app.services.storage import StorageService
from typing import Dict, List, Tuple
import json

logger = get_task_logger(__name__)

# Hash generation settings
PHASH_SIZE = 8  # 8x8 = 64-bit hash
ORB_MAX_FEATURES = 100  # Max ORB keypoints per damage region


class DamageHasher:
    """Damage hashing logic using pHash and ORB"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self.orb = cv2.ORB_create(nfeatures=ORB_MAX_FEATURES)
        
    def calculate_phash(self, image_region: np.ndarray) -> str:
        """
        Calculate perceptual hash (pHash) for damage region.
        Returns 64-bit hash as hex string.
        """
        try:
            # Convert BGR to RGB for PIL
            rgb_region = cv2.cvtColor(image_region, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_region)
            
            # Calculate pHash using imagehash library
            phash = imagehash.phash(pil_image, hash_size=PHASH_SIZE)
            
            return str(phash)
        except Exception as e:
            logger.error(f"Failed to calculate pHash: {e}")
            return None
            
    def extract_orb_descriptors(self, image_region: np.ndarray) -> Dict:
        """
        Extract ORB descriptors for damage region.
        Returns dict with keypoints and descriptors.
        """
        try:
            # Convert to grayscale for ORB
            gray = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
            
            # Detect keypoints and compute descriptors
            keypoints, descriptors = self.orb.detectAndCompute(gray, None)
            
            if descriptors is None or len(keypoints) == 0:
                logger.warning("No ORB features detected in damage region")
                return {"keypoints": [], "descriptors": []}
            
            # Convert to serializable format
            kp_data = []
            for kp in keypoints:
                kp_data.append({
                    "x": float(kp.pt[0]),
                    "y": float(kp.pt[1]),
                    "size": float(kp.size),
                    "angle": float(kp.angle),
                    "response": float(kp.response)
                })
            
            # Convert descriptors to list (numpy array not JSON serializable)
            desc_data = descriptors.tolist() if descriptors is not None else []
            
            return {
                "keypoints": kp_data,
                "descriptors": desc_data,
                "count": len(keypoints)
            }
        except Exception as e:
            logger.error(f"Failed to extract ORB descriptors: {e}")
            return {"keypoints": [], "descriptors": [], "count": 0}
            
    def calculate_relative_coordinates(
        self, 
        bbox: Tuple[int, int, int, int],
        image_shape: Tuple[int, int]
    ) -> Dict:
        """
        Calculate relative coordinates anchored to panel/image.
        Normalizes bbox coordinates to [0, 1] range.
        """
        x1, y1, x2, y2 = bbox
        height, width = image_shape[:2]
        
        return {
            "x1_rel": float(x1 / width),
            "y1_rel": float(y1 / height),
            "x2_rel": float(x2 / width),
            "y2_rel": float(y2 / height),
            "center_x_rel": float((x1 + x2) / 2 / width),
            "center_y_rel": float((y1 + y2) / 2 / height),
            "width_rel": float((x2 - x1) / width),
            "height_rel": float((y2 - y1) / height)
        }
        
    def process_damage(
        self, 
        object_key: str,
        damage: DamageDetection
    ) -> Dict:
        """
        Process single damage detection to generate hashes.
        Returns dict with phash, orb, and relative coords.
        """
        # Get file path from storage
        file_path = self.storage.download_file(object_key)
        
        if not file_path or not file_path.exists():
            raise ValueError(f"Photo not found in storage: {object_key}")
            
        # Load image
        image = cv2.imread(str(file_path))
        if image is None:
            raise ValueError(f"Failed to load image: {file_path}")
            
        # Extract damage region using bounding box
        x1 = int(damage.bbox_x1) if damage.bbox_x1 else 0
        y1 = int(damage.bbox_y1) if damage.bbox_y1 else 0
        x2 = int(damage.bbox_x2) if damage.bbox_x2 else image.shape[1]
        y2 = int(damage.bbox_y2) if damage.bbox_y2 else image.shape[0]
        
        # Ensure valid bbox
        x1, y1 = max(0, x1), max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid bbox for damage {damage.id}: ({x1},{y1},{x2},{y2})")
            return None
            
        damage_region = image[y1:y2, x1:x2]
        
        if damage_region.size == 0:
            logger.warning(f"Empty damage region for damage {damage.id}")
            return None
        
        # Calculate pHash
        phash = self.calculate_phash(damage_region)
        
        # Extract ORB descriptors
        orb_data = self.extract_orb_descriptors(damage_region)
        
        # Calculate relative coordinates
        relative_coords = self.calculate_relative_coordinates(
            (x1, y1, x2, y2),
            image.shape
        )
        
        return {
            "phash": phash,
            "orb": orb_data,
            "relative_coords": relative_coords
        }


@shared_task(name="app.tasks.damage_hashing.generate_damage_hashes")
def generate_damage_hashes(claim_id: str) -> Dict:
    """
    Celery task: Generate damage hashes for all detected damages.
    Sets P0 Lock 4: damage_hash_generated
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting damage hash generation for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Check previous locks
        if not claim.p0_locks.get("damage_detected", False):
            logger.warning(f"Damage detection not complete for claim {claim_id}, skipping hashing")
            return {"status": "skipped", "reason": "Damage detection not complete"}
            
        # Get all damage detections
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        if not damages:
            logger.warning(f"No damages found for claim {claim_id}")
            # Still set the lock as complete (no damages to hash)
            claim.p0_locks["damage_hash_generated"] = True
            flag_modified(claim, "p0_locks")
            db.commit()
            return {"status": "completed", "claim_id": claim_id, "total_hashed": 0}
            
        storage = StorageService()
        hasher = DamageHasher(storage)
        
        total_hashed = 0
        failed_hashes = 0
        
        for damage in damages:
            try:
                # Get the media asset for this damage
                if not damage.media:
                    logger.warning(f"No media found for damage {damage.id}")
                    failed_hashes += 1
                    continue
                    
                # Generate hashes
                hash_data = hasher.process_damage(damage.media.object_key, damage)
                
                if hash_data:
                    # Update damage record with hash data
                    damage.damage_hash_phash = hash_data["phash"]
                    damage.damage_hash_orb = hash_data["orb"]
                    damage.relative_coords = hash_data["relative_coords"]
                    total_hashed += 1
                else:
                    failed_hashes += 1
                    
            except Exception as e:
                logger.error(f"Failed to hash damage {damage.id}: {str(e)}")
                failed_hashes += 1
                # Continue with other damages
                
        # Update claim P0 lock
        claim.p0_locks["damage_hash_generated"] = True
        flag_modified(claim, "p0_locks")
        
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="damage_hash_result",
            model_name="phash+orb",
            model_version="imagehash-4.3.1+opencv-4.x",
            artifact_json={
                "total_damages": len(damages),
                "total_hashed": total_hashed,
                "failed_hashes": failed_hashes,
                "phash_size": PHASH_SIZE,
                "orb_max_features": ORB_MAX_FEATURES
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"Damage hashing complete for claim {claim_id}. Hashed {total_hashed}/{len(damages)} damages.")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_damages": len(damages),
            "total_hashed": total_hashed,
            "failed_hashes": failed_hashes
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Damage hashing failed for claim {claim_id}: {str(e)}")
        raise
        
    finally:
        db.close()
