"""
Media assets and quality gate models.
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Numeric, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
import uuid
from app.models.base import Base
from app.models.enums import MediaType, CaptureAngle


class MediaAsset(Base):
    """Media asset model for photos and videos."""
    __tablename__ = "media_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    media_type = Column(Enum(MediaType), nullable=False, default=MediaType.IMAGE)
    capture_angle = Column(Enum(CaptureAngle), nullable=True)
    
    object_key = Column(String(700), nullable=False)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    sha256_hash = Column(String(64), nullable=False, index=True)
    
    exif_data = Column(JSON, nullable=True)
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref=backref("media_assets", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<MediaAsset {self.id} {self.capture_angle}>"


class QualityGateResult(Base):
    """Quality gate validation results (P0 Lock 1)."""
    __tablename__ = "quality_gate_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=True)
    
    passed = Column(Boolean, nullable=False)
    
    blur_score = Column(Numeric(6, 4), nullable=True)
    exposure_score = Column(Numeric(6, 4), nullable=True)
    glare_score = Column(Numeric(6, 4), nullable=True)
    occlusion_score = Column(Numeric(6, 4), nullable=True)
    vehicle_present = Column(Boolean, nullable=True)
    
    failure_reasons = Column(JSON, nullable=True)
    
    quality_gate_version = Column(String(50), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref=backref("quality_gate_results", cascade="all, delete-orphan"))
    media = relationship("MediaAsset", backref="quality_gate_results")

    def __repr__(self):
        return f"<QualityGateResult {self.id} passed={self.passed}>"
