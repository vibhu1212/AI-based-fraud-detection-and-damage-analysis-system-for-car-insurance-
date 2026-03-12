"""
Pydantic schemas for user profile management.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ProfileResponse(BaseModel):
    """User profile response schema."""
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """User profile update request schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+919876543210"
            }
        }


class ProfileUpdateResponse(BaseModel):
    """User profile update response schema."""
    message: str
    profile: ProfileResponse
