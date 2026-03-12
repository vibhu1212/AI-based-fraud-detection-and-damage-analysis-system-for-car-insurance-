"""
Audit trail API endpoints.
Provides access to audit logs for authorized users.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.base import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


# Response Models
class AuditEventResponse(BaseModel):
    id: str
    claim_id: str
    actor_user_id: Optional[str]
    actor_name: Optional[str]
    action: str
    details: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    total: int
    page: int
    page_size: int
    events: List[AuditEventResponse]


# Helper function to check if user can access audit logs
def can_access_audit_logs(user: User) -> bool:
    """Check if user has permission to access audit logs."""
    # Only surveyors and admins can access audit logs
    return user.role in ['SURVEYOR', 'ADMIN']


@router.get("/claims/{claim_id}", response_model=AuditTrailResponse)
async def get_claim_audit_trail(
    claim_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    actor_user_id: Optional[str] = Query(None, description="Filter by actor user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit trail for a specific claim.
    
    Requires surveyor or admin role.
    Supports pagination and filtering.
    """
    # Check permissions
    if not can_access_audit_logs(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only surveyors and admins can access audit logs"
        )
    
    # Build query
    query = db.query(AuditEvent).filter(AuditEvent.claim_id == claim_id)
    
    # Apply filters
    if action:
        query = query.filter(AuditEvent.action == action)
    
    if actor_user_id:
        query = query.filter(AuditEvent.actor_user_id == actor_user_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    events = query.order_by(desc(AuditEvent.created_at)).offset(offset).limit(page_size).all()
    
    # Enrich with actor names
    event_responses = []
    for event in events:
        event_dict = {
            "id": event.id,
            "claim_id": event.claim_id,
            "actor_user_id": event.actor_user_id,
            "actor_name": event.actor.name if event.actor else None,
            "action": event.action,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": event.created_at
        }
        event_responses.append(AuditEventResponse(**event_dict))
    
    return AuditTrailResponse(
        total=total,
        page=page,
        page_size=page_size,
        events=event_responses
    )


@router.get("/claims/{claim_id}/actions", response_model=List[str])
async def get_claim_action_types(
    claim_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of unique action types for a claim.
    Useful for filtering in the UI.
    """
    # Check permissions
    if not can_access_audit_logs(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only surveyors and admins can access audit logs"
        )
    
    # Get distinct action types
    actions = db.query(AuditEvent.action).filter(
        AuditEvent.claim_id == claim_id
    ).distinct().all()
    
    return [action[0] for action in actions]


@router.get("/claims/{claim_id}/actors", response_model=List[dict])
async def get_claim_actors(
    claim_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of users who have acted on a claim.
    Useful for filtering in the UI.
    """
    # Check permissions
    if not can_access_audit_logs(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only surveyors and admins can access audit logs"
        )
    
    # Get distinct actors
    from sqlalchemy import func
    actors = db.query(
        AuditEvent.actor_user_id,
        User.name
    ).join(
        User, AuditEvent.actor_user_id == User.id
    ).filter(
        AuditEvent.claim_id == claim_id,
        AuditEvent.actor_user_id.isnot(None)
    ).distinct().all()
    
    return [
        {"user_id": actor[0], "name": actor[1]}
        for actor in actors
    ]


@router.get("/claims/{claim_id}/timeline", response_model=List[AuditEventResponse])
async def get_claim_timeline(
    claim_id: str,
    limit: int = Query(20, ge=1, le=100, description="Number of recent events"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent audit events for a claim in timeline format.
    Returns most recent events first.
    """
    # Check permissions
    if not can_access_audit_logs(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only surveyors and admins can access audit logs"
        )
    
    # Get recent events
    events = db.query(AuditEvent).filter(
        AuditEvent.claim_id == claim_id
    ).order_by(desc(AuditEvent.created_at)).limit(limit).all()
    
    # Enrich with actor names
    event_responses = []
    for event in events:
        event_dict = {
            "id": event.id,
            "claim_id": event.claim_id,
            "actor_user_id": event.actor_user_id,
            "actor_name": event.actor.name if event.actor else "System",
            "action": event.action,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": event.created_at
        }
        event_responses.append(AuditEventResponse(**event_dict))
    
    return event_responses
