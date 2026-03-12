"""
Health check endpoint for monitoring and load balancers.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from app.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    app_name: str
    version: str
    timestamp: datetime
    p0_locks_enforced: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: Application health status
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        p0_locks_enforced=True  # P0 Master Lock enforcement flag
    )
