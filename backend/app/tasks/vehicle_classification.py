"""
Vehicle Classification Task (P0 Lock 2.5 - Between VIN and Damage Detection)
Classifies vehicle type to enable vehicle-specific damage detection and cost estimation
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pathlib import Path
from typing import Dict

from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.report import AIArtifact
from app.services.storage import StorageService
from app.services.vehicle_classifier import VehicleClassifier

logger = get_task_logger(__name__)


@shared_task(name="app.tasks.vehicle_classification.classify_vehicle")
def classify_vehicle(claim_id: str) -> Dict:
    """
    Celery task: Classify vehicle type from photos.
    Sets P0 Lock 2.5: vehicle_classified
    Stores vehicle type in claim.extra_data for use by damage detection and cost estimation
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting vehicle classification for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        
        # Check previous locks
        if not claim.p0_locks.get("vin_hash_generated", False):
            logger.warning(f"VIN hash not generated for claim {claim_id}, skipping vehicle classification")
            return {"status": "skipped", "reason": "VIN hash not generated"}
        
        # Get all photos (prefer front view for vehicle classification)
        photos = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim_id
        ).all()
        
        if not photos:
            logger.warning(f"No photos found for claim {claim_id}")
            return {"status": "error", "error": "No photos found"}
        
        storage = StorageService()
        classifier = VehicleClassifier()
        
        # Check if classifier is available
        if not classifier.is_available():
            logger.warning("Vehicle classifier not available, using default vehicle type (CAR)")
            # Set default vehicle type
            if not claim.extra_data:
                claim.extra_data = {}
            claim.extra_data["vehicle_type"] = "CAR"
            claim.extra_data["vehicle_classification_confidence"] = 0.0
            claim.extra_data["vehicle_classification_method"] = "default"
            flag_modified(claim, "extra_data")
            
            # Set P0 lock
            claim.p0_locks["vehicle_classified"] = True
            flag_modified(claim, "p0_locks")
            
            db.commit()
            
            return {
                "status": "completed",
                "claim_id": claim_id,
                "vehicle_type": "CAR",
                "confidence": 0.0,
                "method": "default"
            }
        
        # Try to classify from each photo until we get a confident result
        best_result = None
        best_confidence = 0.0
        all_results = []  # Track all classifications for voting
        
        for photo in photos:
            try:
                # Get file path from storage
                file_path = storage.download_file(photo.object_key)
                
                if not file_path or not file_path.exists():
                    logger.warning(f"Photo not found in storage: {photo.object_key}")
                    continue
                
                # Run classification with higher threshold for better accuracy
                result = classifier.classify(str(file_path), confidence_threshold=0.85)
                
                if result:
                    all_results.append(result)
                    
                    if result["confidence"] > best_confidence:
                        best_result = result
                        best_confidence = result["confidence"]
                        
                        # If we have very high confidence, stop searching
                        if best_confidence > 0.9:
                            logger.info(f"Very high confidence classification found: {best_result['vehicle_type']} ({best_confidence:.2f})")
                            break
                        
            except Exception as e:
                logger.error(f"Failed to classify photo {photo.id}: {str(e)}")
                continue
        
        # Apply voting logic if we have multiple classifications
        if len(all_results) > 1:
            # Count votes for each vehicle type
            votes = {}
            for result in all_results:
                vtype = result["vehicle_type"]
                votes[vtype] = votes.get(vtype, 0) + result["confidence"]
            
            # Get most voted type
            most_voted = max(votes.items(), key=lambda x: x[1])
            logger.info(f"Voting results: {votes}, Winner: {most_voted[0]}")
            
            # If voting winner differs from best confidence, use voting if it has strong support
            if most_voted[0] != best_result["vehicle_type"] and most_voted[1] > best_confidence * 1.5:
                logger.info(f"Using voting result {most_voted[0]} over best confidence {best_result['vehicle_type']}")
                # Find the result with this vehicle type
                for result in all_results:
                    if result["vehicle_type"] == most_voted[0]:
                        best_result = result
                        break
        
        # Apply heuristic corrections for common misclassifications
        if best_result and best_confidence < 0.95:
            raw_class = best_result["raw_class"]
            
            # Auto-rickshaws are often misclassified - apply stricter rules
            if best_result["vehicle_type"] == "AUTO_RICKSHAW":
                # If confidence is not very high, default to CAR
                if best_confidence < 0.90:
                    logger.warning(f"Low confidence for AUTO_RICKSHAW ({best_confidence:.2f}), defaulting to CAR")
                    best_result["vehicle_type"] = "CAR"
                    best_result["display_name"] = "Car"
                    best_result["confidence"] = 0.5  # Mark as uncertain
                    best_result["method"] = "heuristic_correction"
        
        # Use best result or default to CAR
        if best_result:
            vehicle_type = best_result["vehicle_type"]
            confidence = best_result["confidence"]
            raw_class = best_result["raw_class"]
            display_name = best_result["display_name"]
            method = "model"
        else:
            logger.warning("No confident classification found, defaulting to CAR")
            vehicle_type = "CAR"
            confidence = 0.0
            raw_class = "car"
            display_name = "Car"
            method = "default"
        
        # Store vehicle type in claim extra_data
        if not claim.extra_data:
            claim.extra_data = {}
        claim.extra_data["vehicle_type"] = vehicle_type
        claim.extra_data["vehicle_classification_confidence"] = confidence
        claim.extra_data["vehicle_classification_raw_class"] = raw_class
        claim.extra_data["vehicle_classification_display_name"] = display_name
        claim.extra_data["vehicle_classification_method"] = method
        flag_modified(claim, "extra_data")
        
        # Set P0 lock
        claim.p0_locks["vehicle_classified"] = True
        flag_modified(claim, "p0_locks")
        
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="vehicle_classification_result",
            model_name="yolov8n_vehicle_classifier",
            model_version="v12_epoch28",
            artifact_json={
                "vehicle_type": vehicle_type,
                "confidence": confidence,
                "raw_class": raw_class,
                "display_name": display_name,
                "method": method,
                "photos_analyzed": len(photos)
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"Vehicle classification complete for claim {claim_id}. "
                   f"Type: {vehicle_type} ({display_name}), Confidence: {confidence:.2f}")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "vehicle_type": vehicle_type,
            "confidence": confidence,
            "display_name": display_name,
            "method": method
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Vehicle classification failed for claim {claim_id}: {str(e)}")
        raise
    
    finally:
        db.close()
