"""
VIN OCR and Hashing Task (P0 Lock 2)
Extracts VIN from VIN photo and generates hash for duplicate detection
"""
import cv2
import numpy as np
import pytesseract
import hashlib
import re
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.report import AIArtifact
from app.models.enums import ClaimStatus, CaptureAngle
from app.services.storage import StorageService
from app.config import settings
from typing import Dict, Optional, Tuple

logger = get_task_logger(__name__)

# VIN validation pattern (17 alphanumeric characters, excluding I, O, Q)
VIN_PATTERN = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
VIN_OCR_VERSION = "tesseract-5.3.4"


class VINExtractor:
    """VIN extraction and validation logic"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
    
    def preprocess_vin_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess VIN photo for better OCR accuracy.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return morph
    
    def extract_vin(self, image: np.ndarray) -> Tuple[Optional[str], float, str]:
        """
        Extract VIN from preprocessed image using Tesseract OCR.
        
        Returns:
            (vin, confidence, raw_text)
        """
        # Preprocess image
        processed = self.preprocess_vin_image(image)
        
        # Try multiple OCR configurations
        configs = [
            '--psm 7 --oem 3',  # Single line, LSTM OCR
            '--psm 6 --oem 3',  # Uniform block of text
            '--psm 11 --oem 3', # Sparse text
        ]
        
        best_vin = None
        best_confidence = 0.0
        all_raw_texts = []
        
        for config in configs:
            # Perform OCR
            data = pytesseract.image_to_data(
                processed,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and confidence
            raw_text = pytesseract.image_to_string(processed, config=config).strip()
            all_raw_texts.append(raw_text)
            
            # Try to find VIN in the text
            # Remove spaces and special characters
            cleaned_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
            
            # Look for 17-character sequences
            for i in range(len(cleaned_text) - 16):
                potential_vin = cleaned_text[i:i+17]
                if self.validate_vin_format(potential_vin):
                    # Calculate average confidence for this VIN
                    confidences = [
                        float(conf) for conf in data['conf']
                        if conf != '-1' and conf != -1
                    ]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    
                    if avg_confidence > best_confidence:
                        best_vin = potential_vin
                        best_confidence = avg_confidence
        
        # If no valid VIN found, try a more lenient approach
        if not best_vin:
            # Combine all raw texts
            combined_text = ' '.join(all_raw_texts)
            cleaned = re.sub(r'[^A-Z0-9]', '', combined_text.upper())
            
            # Look for longest alphanumeric sequence
            if len(cleaned) >= 17:
                potential_vin = cleaned[:17]
                if self.validate_vin_format(potential_vin):
                    best_vin = potential_vin
                    best_confidence = 50.0  # Low confidence
        
        return best_vin, best_confidence, ' | '.join(all_raw_texts)
    
    def validate_vin_format(self, vin: str) -> bool:
        """
        Validate VIN format (17 characters, no I, O, Q).
        """
        if not vin or len(vin) != 17:
            return False
        
        # Check pattern (no I, O, Q allowed in VINs)
        if not VIN_PATTERN.match(vin):
            return False
        
        return True
    
    def generate_vin_hash(self, vin: str) -> str:
        """
        Generate SHA-256 hash of VIN for duplicate detection.
        """
        return hashlib.sha256(vin.encode('utf-8')).hexdigest()
    
    def process_vin_photo(self, object_key: str) -> Dict:
        """
        Process VIN photo: extract VIN and generate hash.
        """
        # Get file path from storage
        file_path = self.storage.download_file(object_key)
        
        if not file_path or not file_path.exists():
            raise ValueError(f"VIN photo not found in storage: {object_key}")
        
        # Load image
        image = cv2.imread(str(file_path))
        if image is None:
            raise ValueError(f"Failed to load VIN image: {object_key}")
        
        # Extract VIN
        vin, confidence, raw_text = self.extract_vin(image)
        
        if not vin:
            return {
                "success": False,
                "error": "Could not extract valid VIN from photo",
                "raw_text": raw_text,
                "confidence": confidence
            }
        
        # Generate VIN hash
        vin_hash = self.generate_vin_hash(vin)
        
        return {
            "success": True,
            "vin": vin,
            "vin_hash": vin_hash,
            "confidence": confidence,
            "raw_text": raw_text
        }


@shared_task(name="app.tasks.vin_ocr.extract_vin_and_hash")
def extract_vin_and_hash(claim_id: str) -> Dict:
    """
    Celery task: Extract VIN from VIN photo and generate hash.
    Sets P0 Lock 2: vin_hash_generated
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting VIN OCR extraction for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        
        # Check if quality gate passed
        if not claim.p0_locks.get("quality_gate_passed", False):
            logger.warning(f"Quality gate not passed for claim {claim_id}, skipping VIN OCR")
            return {
                "status": "skipped",
                "reason": "Quality gate not passed",
                "claim_id": claim_id
            }
        
        # Get VIN photo
        vin_photo = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim_id,
            MediaAsset.capture_angle == CaptureAngle.VIN
        ).first()
        
        if not vin_photo:
            logger.error(f"No VIN photo found for claim {claim_id}")
            return {
                "status": "error",
                "error": "No VIN photo found",
                "claim_id": claim_id
            }
        
        logger.info(f"Processing VIN photo {vin_photo.id}")
        
        # Initialize extractor
        storage = StorageService()
        extractor = VINExtractor(storage)
        
        # Process VIN photo
        result = extractor.process_vin_photo(vin_photo.object_key)
        
        if not result["success"]:
            logger.error(f"VIN extraction failed for claim {claim_id}: {result.get('error')}")
            
            # Store failure artifact
            artifact = AIArtifact(
                claim_id=claim_id,
                artifact_type="vin_ocr_failure",
                model_name="tesseract",
                model_version=VIN_OCR_VERSION,
                artifact_json={
                    "error": result.get("error"),
                    "raw_text": result.get("raw_text"),
                    "confidence": result.get("confidence")
                }
            )
            db.add(artifact)
            db.commit()
            
            return {
                "status": "failed",
                "claim_id": claim_id,
                "error": result.get("error"),
                "raw_text": result.get("raw_text")
            }
        
        # VIN extracted successfully
        vin = result["vin"]
        vin_hash = result["vin_hash"]
        confidence = result["confidence"]
        
        logger.info(f"VIN extracted successfully: {vin} (confidence: {confidence:.2f}%)")
        
        # Update claim with VIN hash
        claim.vin_hash = vin_hash
        claim.vin_image_object_key = vin_photo.object_key
        
        # Set P0 lock
        claim.p0_locks["vin_hash_generated"] = True
        flag_modified(claim, "p0_locks")
        
        # Store OCR artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="vin_ocr_result",
            model_name="tesseract",
            model_version=VIN_OCR_VERSION,
            artifact_json={
                "vin": vin,
                "vin_hash": vin_hash,
                "confidence": confidence,
                "raw_text": result.get("raw_text"),
                "photo_id": str(vin_photo.id)
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"VIN hash generated and P0 lock set for claim {claim_id}")
        
        # Trigger next task in pipeline: Damage Detection
        from app.core.celery_app import celery_app
        logger.info(f"Triggering damage detection task for claim {claim_id}")
        celery_app.send_task(
            'app.tasks.damage_detection.detect_damages',
            args=[str(claim_id)]
        )
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "vin": vin,
            "vin_hash": vin_hash,
            "confidence": confidence
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"VIN OCR extraction failed for claim {claim_id}: {str(e)}")
        raise
    
    finally:
        db.close()
