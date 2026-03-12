"""
ICVE (Insurance Cost Valuation Engine) models (P0 Lock 6).
Deterministic pricing - never AI-generated.
"""
from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class ICVEEstimate(Base):
    """ICVE cost estimate model (P0 Lock 6)."""
    __tablename__ = "icve_estimates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    icve_rule_version = Column(String(50), nullable=False)
    
    currency = Column(String(3), nullable=False, default="INR")
    
    parts_subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    labour_subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_total = Column(Numeric(12, 2), nullable=False, default=0)
    
    deductible_amount = Column(Numeric(12, 2), nullable=False, default=0)
    depreciation_amount = Column(Numeric(12, 2), nullable=False, default=0)
    
    total_estimate = Column(Numeric(12, 2), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    claim = relationship("Claim", backref="icve_estimates")

    def __repr__(self):
        return f"<ICVEEstimate {self.id} total={self.total_estimate} {self.currency}>"
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal (parts + labour)."""
        return float(self.parts_subtotal + self.labour_subtotal)
    
    @property
    def gst_amount(self) -> float:
        """Get GST/tax amount."""
        return float(self.tax_total)
    
    @property
    def gst_rate(self) -> float:
        """Calculate GST rate (assuming 18% GST in India)."""
        if self.subtotal > 0:
            return float(self.tax_total / self.subtotal)
        return 0.18  # Default 18% GST


class ICVELineItem(Base):
    """ICVE line item breakdown."""
    __tablename__ = "icve_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    icve_estimate_id = Column(String(36), ForeignKey("icve_estimates.id", ondelete="CASCADE"), nullable=False)
    
    item_type = Column(String(30), nullable=False)  # PART, LABOUR, TAX, FEE, ADJUSTMENT
    item_code = Column(String(80), nullable=True)
    item_name = Column(String(255), nullable=False)
    
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    amount = Column(Numeric(12, 2), nullable=False)
    
    meta = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    icve_estimate = relationship("ICVEEstimate", backref="line_items")

    def __repr__(self):
        return f"<ICVELineItem {self.item_name} {self.amount}>"
