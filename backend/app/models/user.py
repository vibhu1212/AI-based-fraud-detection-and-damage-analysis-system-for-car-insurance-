"""
User and authentication models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
import uuid
from app.models.base import Base
from app.models.enums import UserRole


class User(Base):
    """User model for customers, surveyors, and admins."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    
    password_hash = Column(String(255), nullable=True)  # NULL for OTP-only
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User {self.id} {self.name} ({self.role})>"
    
    @property
    def full_name(self) -> str:
        """Get full name (alias for name field)."""
        return self.name or "Unknown User"
