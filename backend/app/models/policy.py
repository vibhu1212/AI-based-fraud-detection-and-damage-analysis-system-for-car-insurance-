"""
Insurance policy models.
"""
from sqlalchemy import Column, String, Integer, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class Policy(Base):
    """Insurance policy model."""
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    policy_number = Column(String(80), unique=True, nullable=False)
    insurer_name = Column(String(255), nullable=False)
    
    vehicle_make = Column(String(100), nullable=True)
    vehicle_model = Column(String(100), nullable=True)
    vehicle_year = Column(Integer, nullable=True)
    registration_no = Column(String(20), nullable=True)
    chassis_number = Column(String(50), nullable=True)
    
    idv = Column(Numeric(12, 2), nullable=True)
    coverage_type = Column(String(50), nullable=True)
    
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="policies")

    def __repr__(self):
        return f"<Policy {self.policy_number}>"
