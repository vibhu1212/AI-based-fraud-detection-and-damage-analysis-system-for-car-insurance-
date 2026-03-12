"""
Quality Gate Validation Task (P0 Lock 1)
Validates photo quality: blur, exposure, glare, vehicle presence
Enhanced with advanced reflection and lighting handling
"""
import cv2
import numpy as np
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.claim import Claim
from app.models.media import MediaAsset, QualityGateResult
from app.models.enums import ClaimStatus
from app.services.storage import StorageService
from app.services.quality_gate_enhanced import EnhancedQualityGateValidator
from app.config import settings
from typing import Dict, List, Tuple
import tempfile
import os

logger = get_task_logger(__name__)

# Quality gate version - updated for enhanced validation
QUALITY_GATE_VERSION = "2.0.0-enhanced"

# Feature flag for enhanced quality gate (can be disabled for rollback)
USE_ENHANCED_QUALITY_GATE = True


class QualityGateValidator:
    """
    Quality gate validation logic (Legacy - kept for backward compatibility)
    Use EnhancedQualityGateValidator for production
    """
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        # Thresholds
        self.BLUR_THRESHOLD = 100.0
        self.EXPOSURE_MIN = 40.0
        self.EXPOSURE_MAX = 220.0
        self.GLARE_THRESHOLD = 0.05
    
    def validate_blur(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect blur using Laplacian variance.
        Higher variance = sharper image.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        passed = laplacian_var >= self.BLUR_THRESHOLD
        return float(laplacian_var), passed
    
    def validate_exposure(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect under/over exposure using mean brightness.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        passed = self.EXPOSURE_MIN <= mean_brightness <= self.EXPOSURE_MAX
        return mean_brightness, passed
    
    def validate_glare(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect glare by finding bright spots.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Threshold for very bright pixels (>240)
        _, bright_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        bright_pixel_ratio = np.sum(bright_mask > 0) / (gray.shape[0] * gray.shape[1])
        passed = bright_pixel_ratio <= self.GLARE_THRESHOLD
        return float(bright_pixel_ratio), passed
    
    def validate_vehicle_presence(self, image: np.ndarray) -> Tuple[bool, bool]:
        """
        Mock vehicle presence check.
        In production, this would use a classifier.
        For demo, we assume vehicle is present if image is not too dark.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        # Simple heuristic: if image is not too dark, assume vehicle present
        vehicle_present = mean_brightness > 30.0
        return vehicle_present, vehicle_present
    
    def validate_photo(self, object_key: str) -> Dict:
        """
        Validate a single photo against all quality gates (Legacy method).
        """
        # Get file path from storage
        file_path = self.storage.download_file(object_key)
        
        if not file_path or not file_path.exists():
            raise ValueError(f"File not found in storage: {object_key}")
        
        try:
            # Load image with OpenCV
            image = cv2.imread(str(file_path))
            if image is None:
                raise ValueError(f"Failed to load image: {object_key}")
            
            # Run all validations
            blur_score, blur_passed = self.validate_blur(image)
            exposure_score, exposure_passed = self.validate_exposure(image)
            glare_score, glare_passed = self.validate_glare(image)
            vehicle_present, vehicle_passed = self.validate_vehicle_presence(image)
            
            # Determine overall pass/fail
            passed = all([blur_passed, exposure_passed, glare_passed, vehicle_passed])
            
            # Collect failure reasons
            failure_reasons = []
            if not blur_passed:
                failure_reasons.append(f"Image too blurry (score: {blur_score:.2f}, threshold: {self.BLUR_THRESHOLD})")
            if not exposure_passed:
                failure_reasons.append(f"Poor exposure (brightness: {exposure_score:.2f}, range: {self.EXPOSURE_MIN}-{self.EXPOSURE_MAX})")
            if not glare_passed:
                failure_reasons.append(f"Excessive glare (ratio: {glare_score:.4f}, threshold: {self.GLARE_THRESHOLD})")
            if not vehicle_passed:
                failure_reasons.append("Vehicle not detected in image")
            
            return {
                "passed": passed,
                "blur_score": blur_score,
                "exposure_score": exposure_score,
                "glare_score": glare_score,
                "vehicle_present": vehicle_present,
                "failure_reasons": failure_reasons if not passed else []
            }
        
        except Exception as e:
            raise ValueError(f"Error processing image {object_key}: {str(e)}")


@shared_task(name="app.tasks.quality_gate.validate_claim_quality")
def validate_claim_quality(claim_id: str) -> Dict:
    """
    Celery task: Validate all photos for a claim.
    Sets P0 Lock 1: quality_gate_passed
    
    Uses EnhancedQualityGateValidator for production-grade validation
    with advanced reflection and lighting handling.
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting quality gate validation for claim {claim_id} (Enhanced v{QUALITY_GATE_VERSION})")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        
        # Get all photos for claim
        photos = db.query(MediaAsset).filter(MediaAsset.claim_id == claim_id).all()
        if not photos:
            logger.warning(f"No photos found for claim {claim_id}")
            return {"status": "no_photos", "claim_id": claim_id}
        
        logger.info(f"Found {len(photos)} photos to validate")
        
        # Initialize storage service
        storage = StorageService()
        
        # Choose validator based on feature flag
        if USE_ENHANCED_QUALITY_GATE:
            logger.info("Using EnhancedQualityGateValidator (advanced reflection & lighting handling)")
            enhanced_validator = EnhancedQualityGateValidator()
        else:
            logger.info("Using legacy QualityGateValidator (basic validation)")
            legacy_validator = QualityGateValidator(storage)
        
        # Validate each photo
        all_passed = True
        results = []
        
        for photo in photos:
            logger.info(f"Validating photo {photo.id} ({photo.capture_angle})")
            
            try:
                # Get file path from storage
                file_path = storage.download_file(photo.object_key)
                
                if not file_path or not file_path.exists():
                    logger.error(f"File not found in storage: {photo.object_key}")
                    all_passed = False
                    results.append({
                        "photo_id": photo.id,
                        "passed": False,
                        "error": "File not found in storage"
                    })
                    continue
                
                # Load image
                image = cv2.imread(str(file_path))
                if image is None:
                    logger.error(f"Failed to load image: {photo.object_key}")
                    all_passed = False
                    results.append({
                        "photo_id": photo.id,
                        "passed": False,
                        "error": "Failed to load image"
                    })
                    continue
                
                # Run validation
                if USE_ENHANCED_QUALITY_GATE:
                    validation_result = enhanced_validator.validate_photo(image)
                else:
                    validation_result = legacy_validator.validate_photo(photo.object_key)
                
                # Extract metrics for database storage
                blur_score = validation_result.get("blur_score", 0.0)
                exposure_score = validation_result.get("exposure_score", 0.0)
                glare_score = validation_result.get("glare_score", 0.0)
                vehicle_present = validation_result.get("vehicle_present", False)
                passed = validation_result.get("passed", False)
                failure_reasons = validation_result.get("failure_reasons", [])
                
                # Store result in database
                quality_result = QualityGateResult(
                    claim_id=claim_id,
                    media_id=photo.id,
                    passed=passed,
                    blur_score=blur_score,
                    exposure_score=exposure_score,
                    glare_score=glare_score,
                    vehicle_present=vehicle_present,
                    failure_reasons=failure_reasons,
                    quality_gate_version=QUALITY_GATE_VERSION
                )
                db.add(quality_result)
                
                results.append({
                    "photo_id": photo.id,
                    "capture_angle": photo.capture_angle.value if photo.capture_angle else None,
                    "passed": passed,
                    "failure_reasons": failure_reasons
                })
                
                if not passed:
                    all_passed = False
                    logger.warning(f"Photo {photo.id} failed quality gate: {failure_reasons}")
                else:
                    logger.info(f"Photo {photo.id} passed quality gate")
            
            except Exception as e:
                logger.error(f"Error validating photo {photo.id}: {str(e)}", exc_info=True)
                all_passed = False
                results.append({
                    "photo_id": photo.id,
                    "passed": False,
                    "error": str(e)
                })
        
        # Update P0 lock and claim status
        if all_passed:
            logger.info(f"All photos passed quality gate for claim {claim_id}")
            claim.p0_locks["quality_gate_passed"] = True
            # Mark JSON field as modified for SQLAlchemy
            flag_modified(claim, "p0_locks")
            claim.status = ClaimStatus.ANALYZING
            logger.info(f"Claim {claim_id} transitioned to ANALYZING")
        else:
            logger.warning(f"Quality gate failed for claim {claim_id}")
            claim.p0_locks["quality_gate_passed"] = False
            flag_modified(claim, "p0_locks")
            claim.status = ClaimStatus.NEEDS_RESUBMIT
            logger.info(f"Claim {claim_id} transitioned to NEEDS_RESUBMIT")
        
        db.commit()
        
        # Trigger next task in pipeline if quality gate passed
        if all_passed:
            from app.core.celery_app import celery_app
            logger.info(f"Triggering VIN OCR task for claim {claim_id}")
            celery_app.send_task(
                'app.tasks.vin_ocr.extract_vin_and_hash',
                args=[str(claim_id)]
            )
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "all_passed": all_passed,
            "total_photos": len(photos),
            "results": results,
            "validator_version": QUALITY_GATE_VERSION
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Quality gate validation failed for claim {claim_id}: {str(e)}", exc_info=True)
        raise
    
    finally:
        db.close()
