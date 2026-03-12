"""
Claim request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from app.schemas.profile import ProfileResponse
from app.schemas.policy import PolicyResponse


class ClaimCreateRequest(BaseModel):
    """Request schema for creating a claim."""
    policy_id: Optional[UUID] = Field(None, description="Policy UUID (optional for demo mode)")
    incident_date: date = Field(..., description="Date of incident")
    incident_description: str = Field(..., description="Description of the incident")
    incident_location_lat: Optional[float] = Field(None, description="Incident latitude")
    incident_location_lng: Optional[float] = Field(None, description="Incident longitude")


class P0LocksStatus(BaseModel):
    """P0 Master Locks status."""
    quality_gate_passed: bool
    vin_hash_generated: bool
    damage_detected: bool
    damage_hash_generated: bool
    duplicate_check_completed: bool
    icve_estimate_generated: bool


class ClaimResponse(BaseModel):
    """Response schema for claim details."""
    id: UUID
    policy_id: UUID
    customer_id: UUID
    assigned_surveyor_id: Optional[UUID]
    status: str
    risk_level: str
    incident_date: Optional[date]
    incident_description: Optional[str]
    incident_location_lat: Optional[float]
    incident_location_lng: Optional[float]
    p0_locks: dict  # Changed from P0LocksStatus to dict for JSON compatibility
    vin_hash: Optional[str]
    submitted_at: Optional[datetime]
    analyzed_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Nested objects
    customer: Optional[ProfileResponse] = None
    policy: Optional[PolicyResponse] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        }
        
    @classmethod
    def from_orm(cls, obj):
        """Custom ORM conversion to handle enums properly."""
        data = {
            'id': obj.id,
            'policy_id': obj.policy_id,
            'customer_id': obj.customer_id,
            'assigned_surveyor_id': obj.assigned_surveyor_id,
            'status': obj.status.value if hasattr(obj.status, 'value') else str(obj.status),
            'risk_level': obj.risk_level.value if hasattr(obj.risk_level, 'value') else str(obj.risk_level),
            'incident_date': obj.incident_date,
            'incident_description': obj.incident_description,
            'incident_location_lat': obj.incident_location_lat,
            'incident_location_lng': obj.incident_location_lng,
            'p0_locks': obj.p0_locks or {},
            'vin_hash': obj.vin_hash,
            'submitted_at': obj.submitted_at,
            'analyzed_at': obj.analyzed_at,
            'reviewed_at': obj.reviewed_at,
            'closed_at': obj.closed_at,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'customer': obj.customer,
            'policy': obj.policy,
        }
        return cls(**data)


class ClaimListResponse(BaseModel):
    """Response schema for list of claims."""
    claims: List[ClaimResponse]
    total: int
    page: int
    page_size: int
