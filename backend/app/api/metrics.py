"""
Metrics Dashboard API
Exposes system performance metrics for monitoring
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.models.base import get_db
from app.services.metrics_collector import metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])

class MetricDataPoint(BaseModel):
    time: str
    value: float
    status: Optional[str] = None

class MetricSummary(BaseModel):
    name: str
    avg_value: float
    min_value: float
    max_value: float
    request_count: int
    error_rate: float
    trend: List[MetricDataPoint]

class DashboardResponse(BaseModel):
    time_range_hours: int
    total_events: int
    metrics: List[MetricSummary]

@router.get("/dashboard", response_model=DashboardResponse)
async def get_metrics_dashboard(
    time_range: int = Query(24, description="Hours of history to fetch"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type (e.g. execution_time)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated performance metrics for the system dashboard.
    """
    try:
        data = metrics_collector.get_aggregated_metrics(
            time_range_hours=time_range,
            metric_type=metric_type
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track")
async def track_metric(
    name: str,
    value: float,
    unit: str,
    metric_type: str = "custom",
    claim_id: Optional[str] = None,
    status: str = "success"
):
    """
    Manually track a metric (useful for frontend reporting)
    """
    metrics_collector.track_metric(
        name=name,
        value=value,
        unit=unit,
        metric_type=metric_type,
        claim_id=claim_id,
        status=status,
        tags={"source": "api"}
    )
    return {"status": "recorded"}
