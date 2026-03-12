"""
Media asset request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class PhotoUploadResponse(BaseModel):
    """Response schema for photo upload."""
    id: UUID
    claim_id: UUID
    media_type: str
    capture_angle: Optional[str]
    object_key: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    width: Optional[int]
    height: Optional[int]
    sha256_hash: str
    uploaded_at: datetime
    presigned_url: str
    
    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """Response schema for list of photos."""
    id: UUID
    capture_angle: Optional[str]
    content_type: Optional[str]
    size_bytes: Optional[int]
    uploaded_at: datetime
    presigned_url: str
    
    class Config:
        from_attributes = True
