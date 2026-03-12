"""
Damage detection and hashing models (P0 Locks 3, 4, 5).
"""
from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base
from app.models.enums import DamageType, SeverityLevel, RepairAction


class DamageDetection(Base):
    """Damage detection model (P0 Lock 3)."""
    __tablename__ = "damage_detections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    
    damage_type = Column(Enum(DamageType), nullable=False)
    confidence = Column(Numeric(6, 4), nullable=False)
    
    # Bounding box coordinates
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)
    
    mask_object_key = Column(String(700), nullable=True)
    
    severity = Column(Enum(SeverityLevel), nullable=True)
    affected_part = Column(String(120), nullable=True)
    vehicle_part = Column(String(120), nullable=True)
    repair_action = Column(Enum(RepairAction), nullable=True)
    
    # Damage Hash (P0 Lock 4)
    damage_hash_phash = Column(String(64), nullable=True, index=True)
    damage_hash_orb = Column(JSON, nullable=True)  # ORB descriptors
    relative_coords = Column(JSON, nullable=True)  # Panel-relative coordinates
    
    # Surveyor modifications (Task 5.6)
    is_ai_generated = Column(Boolean, nullable=False, default=True)
    is_ai_detected = Column(Boolean, nullable=False, default=True)
    is_surveyor_confirmed = Column(Boolean, nullable=False, default=False)
    surveyor_modified = Column(Boolean, nullable=False, default=False)
    surveyor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    cost_override = Column(Numeric(12, 2), nullable=True)
    surveyor_notes = Column(String(1000), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref="damage_detections")
    media = relationship("MediaAsset", backref="damage_detections")

    def __repr__(self):
        return f"<DamageDetection {self.id} {self.damage_type} conf={self.confidence}>"
    
    @property
    def estimated_cost(self) -> float:
        """
        Calculate estimated cost for damage.
        Simple estimation based on damage type and severity.
        """
        # Base costs by damage type (in USD)
        base_costs = {
            'DENT': 300,
            'SCRATCH': 200,
            'CRACK': 500,
            'SHATTER': 800,
            'DEFORMATION': 1000,
            'PAINT_DAMAGE': 250,
            'RUST': 400,
            'MISSING_PART': 1500,
            'BROKEN_LIGHT': 350,
            'TIRE_DAMAGE': 200,
            'BUMPER_DAMAGE': 600,
            'WINDSHIELD': 400,
            'PANEL_DAMAGE': 800
        }
        
        # Severity multipliers
        severity_multipliers = {
            'MINOR': 0.7,
            'MODERATE': 1.0,
            'SEVERE': 1.5,
            'CRITICAL': 2.0
        }
        
        base = base_costs.get(self.damage_type.value if hasattr(self.damage_type, 'value') else str(self.damage_type), 500)
        multiplier = severity_multipliers.get(self.severity.value if hasattr(self.severity, 'value') else str(self.severity), 1.0) if self.severity else 1.0
        
        return base * multiplier


class DuplicateCheckResult(Base):
    """Duplicate detection results (P0 Lock 5)."""
    __tablename__ = "duplicate_check_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    # Matching results
    matched_claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=True)
    similarity_score = Column(Numeric(6, 4), nullable=True)
    hamming_distance = Column(Integer, nullable=True)
    orb_similarity = Column(Numeric(6, 4), nullable=True)
    
    # Decision
    fraud_action = Column(String(30), nullable=False)  # PROCEED, FLAG_REVIEW, HOLD
    match_window_days = Column(Integer, nullable=False, default=180)
    
    duplicate_check_version = Column(String(50), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", foreign_keys=[claim_id], backref="duplicate_check_results")
    matched_claim = relationship("Claim", foreign_keys=[matched_claim_id])

    def __repr__(self):
        return f"<DuplicateCheckResult {self.id} action={self.fraud_action}>"
