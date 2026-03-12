"""
Report draft and AI artifact models.
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class ReportDraft(Base):
    """LLM-generated report draft model."""
    __tablename__ = "report_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    draft_text = Column(Text, nullable=True)  # Legacy field
    final_text = Column(Text, nullable=True)  # Legacy field
    
    # New structured format (Task 5.8, 5.9)
    report_sections = Column(JSON, nullable=True)  # AI-generated sections
    surveyor_version = Column(JSON, nullable=True)  # Surveyor-modified sections
    ai_version = Column(JSON, nullable=True)  # Original AI version for comparison
    version = Column(Integer, nullable=False, default=1)
    surveyor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    llm_provider = Column(String(80), nullable=True)
    llm_model = Column(String(120), nullable=True)
    llm_prompt_hash = Column(String(64), nullable=True)
    llm_output_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    claim = relationship("Claim", backref="report_drafts")
    surveyor = relationship("User", foreign_keys=[surveyor_id])

    def __repr__(self):
        return f"<ReportDraft {self.id} v{self.version}>"


class AIArtifact(Base):
    """Raw AI outputs and model versioning."""
    __tablename__ = "ai_artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)
    
    artifact_type = Column(String(60), nullable=False)
    artifact_json = Column(JSON, nullable=False)
    
    model_name = Column(String(120), nullable=True)
    model_version = Column(String(60), nullable=False)
    
    inference_time_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref="ai_artifacts")
    media = relationship("MediaAsset", backref="ai_artifacts")

    def __repr__(self):
        return f"<AIArtifact {self.artifact_type} {self.model_name}>"
