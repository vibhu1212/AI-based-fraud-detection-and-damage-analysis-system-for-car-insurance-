"""
Surveyor Assignment Service

Handles automatic assignment of claims to surveyors based on:
- Round-robin distribution for even workload
- Priority assignment of RED risk claims to senior surveyors
- Surveyor availability and workload tracking
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.claim import Claim, ClaimStatus
from app.models.user import User, UserRole
from app.config import settings


class SurveyorAssignmentService:
    """Service for automatic surveyor assignment"""
    
    def __init__(self, db: Session):
        self.db = db
        # Senior surveyor IDs from config (comma-separated)
        senior_ids = getattr(settings, 'SENIOR_SURVEYOR_IDS', '')
        self.senior_surveyor_ids = [
            sid.strip() for sid in senior_ids.split(',') if sid.strip()
        ]
    
    def get_available_surveyors(self, senior_only: bool = False) -> List[User]:
        """
        Get list of available surveyors
        
        Args:
            senior_only: If True, only return senior surveyors
            
        Returns:
            List of available surveyor User objects
        """
        query = self.db.query(User).filter(
            User.role == UserRole.SURVEYOR
        )
        
        if senior_only and self.senior_surveyor_ids:
            query = query.filter(User.id.in_(self.senior_surveyor_ids))
        
        return query.all()
    
    def get_surveyor_workload(self, surveyor_id: str) -> int:
        """
        Calculate current workload for a surveyor
        
        Workload = count of active claims (not APPROVED or REJECTED)
        
        Args:
            surveyor_id: Surveyor user ID
            
        Returns:
            Number of active claims assigned to surveyor
        """
        active_statuses = [
            ClaimStatus.DRAFT_READY,
            ClaimStatus.SURVEYOR_REVIEW,
            ClaimStatus.NEEDS_MORE_INFO
        ]
        
        workload = self.db.query(func.count(Claim.id)).filter(
            and_(
                Claim.assigned_surveyor_id == surveyor_id,
                Claim.status.in_(active_statuses)
            )
        ).scalar()
        
        return workload or 0
    
    def round_robin_assign(self, senior_only: bool = False) -> Optional[str]:
        """
        Assign to surveyor with least workload (round-robin)
        
        Args:
            senior_only: If True, only consider senior surveyors
            
        Returns:
            Surveyor ID with least workload, or None if no surveyors available
        """
        surveyors = self.get_available_surveyors(senior_only=senior_only)
        
        if not surveyors:
            return None
        
        # Calculate workload for each surveyor
        surveyor_workloads = [
            (surveyor.id, self.get_surveyor_workload(surveyor.id))
            for surveyor in surveyors
        ]
        
        # Sort by workload (ascending) and return surveyor with least workload
        surveyor_workloads.sort(key=lambda x: x[1])
        
        return surveyor_workloads[0][0]
    
    def assign_to_senior_surveyor(self) -> Optional[str]:
        """
        Assign to senior surveyor with least workload
        
        Used for RED risk claims that need experienced review
        
        Returns:
            Senior surveyor ID, or None if no senior surveyors available
        """
        return self.round_robin_assign(senior_only=True)
    
    def assign_claim(self, claim: Claim) -> Optional[str]:
        """
        Automatically assign a claim to a surveyor
        
        Logic:
        - RED risk claims -> Senior surveyors only
        - AMBER/GREEN risk claims -> All surveyors (round-robin)
        
        Args:
            claim: Claim object to assign
            
        Returns:
            Assigned surveyor ID, or None if assignment failed
        """
        # RED risk claims go to senior surveyors
        if claim.risk_level == "RED":
            surveyor_id = self.assign_to_senior_surveyor()
            
            # Fallback to any surveyor if no senior available
            if not surveyor_id:
                surveyor_id = self.round_robin_assign(senior_only=False)
        else:
            # AMBER and GREEN claims use standard round-robin
            surveyor_id = self.round_robin_assign(senior_only=False)
        
        return surveyor_id
