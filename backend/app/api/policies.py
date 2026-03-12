"""
Policy management endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.models.base import get_db
from app.models.user import User
from app.models.policy import Policy
from app.schemas.policy import PolicyResponse
from app.api.dependencies import get_current_customer

router = APIRouter()


@router.get("", response_model=List[PolicyResponse])
async def list_policies(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get all policies for the logged-in customer.
    Only customers can access their own policies.
    """
    policies = db.query(Policy).filter(
        Policy.user_id == current_user.id
    ).order_by(Policy.created_at.desc()).all()
    
    return policies


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get a specific policy by ID.
    Only the policy owner can access it.
    """
    from fastapi import HTTPException
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.user_id == current_user.id
    ).first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found or does not belong to you"
        )
    
    return policy
