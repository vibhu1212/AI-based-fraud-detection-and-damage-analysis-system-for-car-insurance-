"""
PII Redaction Task (Task 7.3)
Detects and blurs faces and license plates for privacy compliance
"""
import cv2
import numpy as np
from pathlib import Path
from celery import shared_task
from celery.utils.log import get_task_logger
from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.report import AIArtifact
from app.services.storage import StorageService
from typing import Dict, List, Tuple, Optional
import io
from PIL import Image

logger = get_task_logger(__name__)

# Redaction settings
FACE_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
BLUR_KERNEL_SIZE = (51, 51)  # Gaussian blur kernel size
MIN_FACE_SIZE = (30, 30)  # Minimum face size to detect


class PIIRedactor:
    """PII redaction logic using OpenCV"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self.face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in image using Haar Cascade.
        Returns list of (x, y, w, h) tuples.
        """
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=MIN_FACE_SIZE
            )
            
            return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []
            
    def detect_license_plates(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect license plates using simple heuristics.
        Returns list of (x, y, w, h) tuples.
        
        Note: This is a simplified implementation for demo.
        Production would use specialized license plate detection models.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            plates = []
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # License plate heuristics:
                # - Aspect ratio between 2:1 and 5:1
                # - Minimum size
                aspect_ratio = w / h if h > 0 else 0
                if 2.0 <= aspect_ratio <= 5.0 and w > 50 and h > 15:
                    plates.append((x, y, w, h))
            
            return plates
            
        except Exception as e:
            logger.error(f"License plate detection failed: {e}")
            return []
            
    def blur_region(
        self, 
        image: np.ndarray, 
        x: int, 
        y: int, 
        w: int, 
        h: int
    ) -> np.ndarray:
        """
        Blur a specific region of the image.
        Returns modified image.
        """
        # Extract region
        region = image[y:y+h, x:x+w]
        
        # Apply Gaussian blur
        blurred_region = cv2.GaussianBlur(region, BLUR_KERNEL_SIZE, 0)
        
        # Replace region in image
        image[y:y+h, x:x+w] = blurred_region
        
        return image
        
    def redact_image(self, image_path: Path) -> Optional[Tuple[np.ndarray, Dict]]:
        """
        Redact PII from image (faces and license plates).
        Returns (redacted_image, metadata) or None if failed.
        """
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return None
            
            # Make a copy for redaction
            redacted = image.copy()
            
            # Detect and blur faces
            faces = self.detect_faces(image)
            for x, y, w, h in faces:
                redacted = self.blur_region(redacted, x, y, w, h)
            
            # Detect and blur license plates
            plates = self.detect_license_plates(image)
            for x, y, w, h in plates:
                redacted = self.blur_region(redacted, x, y, w, h)
            
            metadata = {
                "faces_detected": len(faces),
                "plates_detected": len(plates),
                "total_redactions": len(faces) + len(plates)
            }
            
            return redacted, metadata
            
        except Exception as e:
            logger.error(f"Image redaction failed: {e}")
            return None
            
    def process_photo(
        self,
        media: MediaAsset,
        claim_id: str
    ) -> Optional[str]:
        """
        Process single photo to create redacted version.
        Returns object key of redacted photo or None if failed.
        """
        try:
            # Get original image path
            image_path = self.storage.download_file(media.object_key)
            if not image_path or not image_path.exists():
                logger.error(f"Image not found: {media.object_key}")
                return None
            
            # Redact image
            result = self.redact_image(image_path)
            if not result:
                return None
            
            redacted_image, metadata = result
            
            # Convert to bytes
            is_success, buffer = cv2.imencode('.jpg', redacted_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not is_success:
                logger.error("Failed to encode redacted image")
                return None
            
            redacted_bytes = io.BytesIO(buffer.tobytes())
            
            # Generate redacted filename
            original_filename = Path(media.object_key).name
            redacted_filename = f"redacted_{original_filename}"
            
            # Store redacted version (correct parameter order: claim_id, filename, folder)
            redacted_object_key = self.storage.generate_object_key(
                claim_id,
                redacted_filename,
                "redacted"
            )
            
            # Upload redacted image
            upload_result = self.storage.upload_file(
                file=redacted_bytes,
                object_key=redacted_object_key,
                content_type="image/jpeg"
            )
            
            logger.info(f"Redacted image stored: {redacted_object_key} ({metadata['total_redactions']} redactions)")
            
            return redacted_object_key
            
        except Exception as e:
            logger.error(f"Failed to process photo {media.id}: {e}")
            return None


@shared_task(name="app.tasks.pii_redaction.redact_claim_photos")
def redact_claim_photos(claim_id: str) -> Dict:
    """
    Celery task: Redact PII from all claim photos.
    Creates redacted versions with faces and license plates blurred.
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting PII redaction for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Get all photos
        photos = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim_id
        ).all()
        
        if not photos:
            logger.warning(f"No photos found for claim {claim_id}")
            return {"status": "completed", "claim_id": claim_id, "total_redacted": 0}
            
        storage = StorageService()
        redactor = PIIRedactor(storage)
        
        total_redacted = 0
        failed_redactions = 0
        total_faces = 0
        total_plates = 0
        
        for photo in photos:
            try:
                # Get original image for detection stats
                image_path = storage.download_file(photo.object_key)
                if image_path and image_path.exists():
                    image = cv2.imread(str(image_path))
                    if image is not None:
                        faces = redactor.detect_faces(image)
                        plates = redactor.detect_license_plates(image)
                        total_faces += len(faces)
                        total_plates += len(plates)
                
                # Create redacted version
                redacted_object_key = redactor.process_photo(photo, claim_id)
                
                if redacted_object_key:
                    # Note: We don't update the media record here
                    # The API will serve redacted versions by default
                    # Original is preserved for audit/legal purposes
                    total_redacted += 1
                else:
                    failed_redactions += 1
                    
            except Exception as e:
                logger.error(f"Failed to redact photo {photo.id}: {str(e)}")
                failed_redactions += 1
                
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="pii_redaction_result",
            model_name="opencv-haarcascade",
            model_version="opencv-4.x",
            artifact_json={
                "total_photos": len(photos),
                "total_redacted": total_redacted,
                "failed_redactions": failed_redactions,
                "total_faces_detected": total_faces,
                "total_plates_detected": total_plates
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"PII redaction complete for claim {claim_id}. Redacted {total_redacted}/{len(photos)} photos.")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_photos": len(photos),
            "total_redacted": total_redacted,
            "failed_redactions": failed_redactions,
            "total_faces_detected": total_faces,
            "total_plates_detected": total_plates
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"PII redaction failed for claim {claim_id}: {str(e)}")
        raise
        
    finally:
        db.close()
