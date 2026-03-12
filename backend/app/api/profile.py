"""
User profile management endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileUpdateResponse
)
from app.api.dependencies import get_current_user
from app.services.audit_logger import audit_logger
from datetime import datetime

router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information.
    
    Returns:
        ProfileResponse: User profile data
    """
    return ProfileResponse(
        id=str(current_user.id),
        name=current_user.name,
        phone=current_user.phone,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/profile", response_model=ProfileUpdateResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    
    Args:
        request: Profile update data (name, email, phone)
        
    Returns:
        ProfileUpdateResponse: Updated profile data
        
    Raises:
        HTTPException: If phone number already exists for another user
    """
    # Store original values for audit log
    before_state = {
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone
    }
    
    # Track what changed
    changes = {}
    
    # Update name if provided
    if request.name is not None and request.name != current_user.name:
        changes["name"] = {"old": current_user.name, "new": request.name}
        current_user.name = request.name
    
    # Update email if provided
    if request.email is not None and request.email != current_user.email:
        changes["email"] = {"old": current_user.email, "new": request.email}
        current_user.email = request.email
    
    # Update phone if provided
    if request.phone is not None and request.phone != current_user.phone:
        # Check if phone number already exists for another user
        existing_user = db.query(User).filter(
            User.phone == request.phone,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered to another user"
            )
        
        changes["phone"] = {"old": current_user.phone, "new": request.phone}
        current_user.phone = request.phone
    
    # If no changes, return current profile
    if not changes:
        return ProfileUpdateResponse(
            message="No changes made to profile",
            profile=ProfileResponse(
                id=str(current_user.id),
                name=current_user.name,
                phone=current_user.phone,
                email=current_user.email,
                role=current_user.role.value,
                is_active=current_user.is_active,
                created_at=current_user.created_at,
                updated_at=current_user.updated_at
            )
        )
    
    # Update timestamp
    current_user.updated_at = datetime.utcnow()
    
    # Commit changes
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
    
    # Log profile modification in audit trail
    after_state = {
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone
    }
    
    audit_logger.log_profile_modification(
        db=db,
        user_id=str(current_user.id),
        before_state=before_state,
        after_state=after_state,
        changes=changes
    )
    
    return ProfileUpdateResponse(
        message="Profile updated successfully",
        profile=ProfileResponse(
            id=str(current_user.id),
            name=current_user.name,
            phone=current_user.phone,
            email=current_user.email,
            role=current_user.role.value,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
    )
