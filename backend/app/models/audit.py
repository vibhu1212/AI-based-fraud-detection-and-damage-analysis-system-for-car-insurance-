"""
Audit trail and risk assessment models.
"""
from sqlalchemy import Column, String, Text, DateTime, Numeric, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base
from app.models.enums import RiskLevel


class AuditEvent(Base):
    """Audit event log for all claim actions."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(60), nullable=False)
    
    details = Column(JSON, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref="audit_events")
    actor = relationship("User")

    def __repr__(self):
        return f"<AuditEvent {self.action} by {self.actor_user_id}>"


class RiskAssessment(Base):
    """Risk assessment model (soft gate)."""
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_score = Column(Numeric(6, 4), nullable=True)
    risk_flags = Column(JSON, nullable=True)
    
    risk_model_name = Column(String(100), nullable=True)
    risk_model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref="risk_assessments")

    def __repr__(self):
        return f"<RiskAssessment {self.risk_level} score={self.risk_score}>"
