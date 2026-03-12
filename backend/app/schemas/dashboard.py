"""
Pydantic schemas for customer dashboard.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ClaimSummary(BaseModel):
    """Summary of a claim for dashboard display"""
    id: str
    policy_id: str
    status: str
    risk_level: str
    incident_date: Optional[datetime]
    submitted_at: Optional[datetime]
    estimated_amount: Optional[float]
    has_updates: bool = False  # Indicates if there are new updates
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_claims: int
    pending_claims: int  # CREATED, SUBMITTED, ANALYZING, DRAFT_READY, SURVEYOR_REVIEW, NEEDS_MORE_INFO
    approved_claims: int
    rejected_claims: int


class CustomerDashboardResponse(BaseModel):
    """Customer dashboard response"""
    stats: DashboardStats
    recent_claims: List[ClaimSummary]
    pending_claims: List[ClaimSummary]
    approved_claims: List[ClaimSummary]
    rejected_claims: List[ClaimSummary]
