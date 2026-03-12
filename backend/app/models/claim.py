"""
Claim workflow models including P0 Master Locks.
"""
from sqlalchemy import Column, String, Text, Date, DateTime, Numeric, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
import uuid
from app.models.base import Base
from app.models.enums import ClaimStatus, RiskLevel


class Claim(Base):
    """
    Claim model - central workflow anchor.
    P0 Master Locks enforced: AI Drafts, Human Approves.
    """
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    policy_id = Column(String(36), ForeignKey("policies.id", ondelete="RESTRICT"), nullable=False)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_surveyor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.CREATED)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.GREEN)
    
    incident_date = Column(Date, nullable=True)
    incident_description = Column(Text, nullable=True)
    
    incident_location_lat = Column(Numeric(10, 8), nullable=True)
    incident_location_lng = Column(Numeric(11, 8), nullable=True)
    
    # P0 Master Locks Status (enforced before DRAFT_READY)
    p0_locks = Column(JSON, nullable=False, default=lambda: {
        "quality_gate_passed": False,
        "vin_hash_generated": False,
        "damage_detected": False,
        "damage_hash_generated": False,
        "duplicate_check_completed": False,
        "icve_estimate_generated": False
    })
    
    # VIN data for duplicate detection
    vin_hash = Column(String(64), nullable=True, index=True)
    vin_image_object_key = Column(String(700), nullable=True)
    
    # PDF report URL
    report_pdf_url = Column(String(700), nullable=True)
    
    # Additional data (cost estimates, damage breakdown, etc.)
    extra_data = Column(JSON, nullable=True, default=lambda: {})
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    policy = relationship("Policy", backref="claims")
    customer = relationship("User", foreign_keys=[customer_id], backref="customer_claims")
    surveyor = relationship("User", foreign_keys=[assigned_surveyor_id], backref="surveyor_claims")

    def __repr__(self):
        return f"<Claim {self.id} {self.status}>"
    
    def can_transition_to_draft_ready(self) -> bool:
        """
        P0 Lock Enforcement: Check if all master locks are satisfied.
        """
        return all([
            self.p0_locks.get("quality_gate_passed", False),
            self.p0_locks.get("vin_hash_generated", False),
            self.p0_locks.get("damage_detected", False),
            self.p0_locks.get("damage_hash_generated", False),
            self.p0_locks.get("duplicate_check_completed", False),
            self.p0_locks.get("icve_estimate_generated", False)
        ])
    
    @property
    def claim_number(self) -> str:
        """Generate claim number from ID."""
        return f"CLM-{self.id[:8].upper()}"
    
    @property
    def vehicle_make(self) -> str:
        """Get vehicle make from policy."""
        return self.policy.vehicle_make if self.policy else "N/A"
    
    @property
    def vehicle_model(self) -> str:
        """Get vehicle model from policy."""
        return self.policy.vehicle_model if self.policy else "N/A"
    
    @property
    def vehicle_year(self) -> int:
        """Get vehicle year from policy."""
        return self.policy.vehicle_year if self.policy else None
    
    @property
    def vin(self) -> str:
        """Get VIN/chassis number from policy."""
        return self.policy.chassis_number if self.policy else None


class ClaimStateTransition(Base):
    """Audit log for claim state transitions."""
    __tablename__ = "claim_state_transitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    from_status = Column(Enum(ClaimStatus), nullable=True)
    to_status = Column(Enum(ClaimStatus), nullable=False)
    
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    # Relationships
    claim = relationship("Claim", backref=backref("state_transitions", cascade="all, delete-orphan"))
    actor = relationship("User")

    def __repr__(self):
        return f"<StateTransition {self.from_status} -> {self.to_status}>"
