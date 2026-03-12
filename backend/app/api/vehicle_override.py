"""
Vehicle Type Override API
Allows surveyors to manually correct vehicle classification
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.base import get_db
from app.models.claim import Claim
from app.models.enums import UserRole
from app.models.user import User
from app.api.dependencies import get_current_user
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter(prefix="/api/vehicle", tags=["vehicle"])


class VehicleTypeOverride(BaseModel):
    """Request to override vehicle type"""
    vehicle_type: str  # CAR, MOTORCYCLE, AUTO_RICKSHAW, TRUCK, BUS, VAN
    reason: Optional[str] = None


@router.post("/claims/{claim_id}/override-type")
async def override_vehicle_type(
    claim_id: str,
    override: VehicleTypeOverride,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Override vehicle classification for a claim
    Only surveyors and admins can override
    """
    # Check permissions
    if current_user.role not in [UserRole.SURVEYOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only surveyors can override vehicle type")
    
    # Get claim
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Validate vehicle type
    valid_types = ["CAR", "MOTORCYCLE", "AUTO_RICKSHAW", "TRUCK", "BUS", "VAN"]
    if override.vehicle_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid vehicle type. Must be one of: {valid_types}")
    
    # Store original classification
    if not claim.extra_data:
        claim.extra_data = {}
    
    original_type = claim.extra_data.get("vehicle_type", "UNKNOWN")
    original_confidence = claim.extra_data.get("vehicle_classification_confidence", 0.0)
    
    # Update vehicle type
    claim.extra_data["vehicle_type"] = override.vehicle_type
    claim.extra_data["vehicle_classification_method"] = "manual_override"
    claim.extra_data["vehicle_classification_override_by"] = str(current_user.id)
    claim.extra_data["vehicle_classification_override_reason"] = override.reason
    claim.extra_data["vehicle_classification_original_type"] = original_type
    claim.extra_data["vehicle_classification_original_confidence"] = original_confidence
    
    flag_modified(claim, "extra_data")
    
    db.commit()
    
    return {
        "status": "success",
        "claim_id": claim_id,
        "original_type": original_type,
        "new_type": override.vehicle_type,
        "overridden_by": str(current_user.id)
    }


@router.get("/claims/{claim_id}/classification")
async def get_vehicle_classification(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """Get vehicle classification details for a claim"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if not claim.extra_data:
        return {
            "vehicle_type": "UNKNOWN",
            "confidence": 0.0,
            "method": "none"
        }
    
    return {
        "vehicle_type": claim.extra_data.get("vehicle_type", "UNKNOWN"),
        "confidence": claim.extra_data.get("vehicle_classification_confidence", 0.0),
        "method": claim.extra_data.get("vehicle_classification_method", "unknown"),
        "display_name": claim.extra_data.get("vehicle_classification_display_name", "Unknown"),
        "raw_class": claim.extra_data.get("vehicle_classification_raw_class", "unknown"),
        "is_overridden": claim.extra_data.get("vehicle_classification_method") == "manual_override",
        "original_type": claim.extra_data.get("vehicle_classification_original_type"),
        "override_reason": claim.extra_data.get("vehicle_classification_override_reason")
    }
