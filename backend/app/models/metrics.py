from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, JSON
from app.models.base import Base
import uuid

class ProcessMetric(Base):
    """
    Stores performance metrics for system processes and AI tasks.
    Used for monitoring system health and performance trends.
    """
    __tablename__ = "process_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String, ForeignKey("claims.id"), nullable=True, index=True)
    
    # Metric details
    metric_type = Column(String, nullable=False, index=True)  # e.g., 'task_duration', 'inference_time', 'error_rate'
    name = Column(String, nullable=False, index=True)         # e.g., 'damage_detection', 'vin_ocr'
    
    # Values
    value = Column(Float, nullable=False)                     # The numerical value (seconds, score, etc.)
    unit = Column(String, nullable=False)                     # e.g., 's', 'ms', 'percent', 'count'
    tags = Column(JSON, nullable=True)                        # Additional context (e.g., model_version, host)
    
    # Status (for outcome metrics)
    status = Column(String, nullable=True)                    # 'success', 'failure'
    error_type = Column(String, nullable=True)                # e.g., 'Timeout', 'ModelError'
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
