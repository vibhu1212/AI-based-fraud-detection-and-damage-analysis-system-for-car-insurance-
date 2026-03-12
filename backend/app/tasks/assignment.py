"""
Surveyor Assignment Task

Automatically assigns claims to surveyors when they reach DRAFT_READY status.
"""

import asyncio
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.models.claim import Claim, ClaimStateTransition
from app.models.user import User
from app.services.assignment import SurveyorAssignmentService
from app.services.audit_logger import audit_logger
from app.websocket.broadcaster import broadcaster

logger = get_task_logger(__name__)


@shared_task(name="app.tasks.assignment.assign_surveyor_to_claim")
def assign_surveyor_to_claim(claim_id: str) -> dict:
    """
    Assign a surveyor to a claim that has reached DRAFT_READY status.
    
    Assignment logic:
    - RED risk claims -> Senior surveyors only
    - AMBER/GREEN risk claims -> All surveyors (round-robin)
    
    Args:
        claim_id: Claim UUID
        
    Returns:
        dict with status, assigned_surveyor_id, and surveyor_name
    """
    db: Session = SessionLocal()
    
    try:
        logger.info(f"Starting surveyor assignment for claim {claim_id}")
        
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"status": "failed", "error": "Claim not found"}
        
        # Check if already assigned
        if claim.assigned_surveyor_id:
            logger.info(f"Claim {claim_id} already assigned to {claim.assigned_surveyor_id}")
            return {
                "status": "already_assigned",
                "assigned_surveyor_id": claim.assigned_surveyor_id
            }
        
        # Initialize assignment service
        assignment_service = SurveyorAssignmentService(db)
        
        # Assign surveyor based on risk level
        surveyor_id = assignment_service.assign_claim(claim)
        
        if not surveyor_id:
            logger.error(f"No surveyor available for assignment to claim {claim_id}")
            return {"status": "failed", "error": "No surveyor available"}
        
        # Get surveyor details
        surveyor = db.query(User).filter(User.id == surveyor_id).first()
        
        if not surveyor:
            logger.error(f"Surveyor {surveyor_id} not found")
            return {"status": "failed", "error": "Surveyor not found"}
        
        # Update claim with assigned surveyor
        claim.assigned_surveyor_id = surveyor_id
        db.commit()
        
        # Log assignment in audit trail
        audit_logger.log_claim_assignment(
            db=db,
            claim_id=claim_id,
            surveyor_id=surveyor_id,
            risk_level=claim.risk_level,
            assignment_reason=f"Auto-assigned based on {claim.risk_level} risk level"
        )
        
        logger.info(f"Claim {claim_id} assigned to surveyor {surveyor.name} ({surveyor_id})")
        
        # Broadcast assignment notification to surveyor
        try:
            asyncio.run(broadcaster.broadcast_surveyor_notification(
                surveyor_id=surveyor_id,
                claim_id=claim_id,
                claim_summary={
                    "policy_id": claim.policy_id,
                    "risk_level": claim.risk_level,
                    "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None
                }
            ))
            
            # Broadcast general assignment event
            asyncio.run(broadcaster.broadcast_claim_assigned(
                claim_id=claim_id,
                surveyor_id=surveyor_id,
                surveyor_name=surveyor.name
            ))
        except Exception as e:
            logger.warning(f"Failed to broadcast assignment notification: {e}")
            # Don't fail the task if broadcast fails
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "assigned_surveyor_id": surveyor_id,
            "surveyor_name": surveyor.name,
            "risk_level": claim.risk_level
        }
        
    except Exception as e:
        logger.error(f"Error assigning surveyor to claim {claim_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
