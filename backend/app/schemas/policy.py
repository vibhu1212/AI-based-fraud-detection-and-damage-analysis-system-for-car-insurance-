"""
Pydantic schemas for policy management.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class PolicyResponse(BaseModel):
    """Policy response schema"""
    id: str
    policy_number: str
    user_id: str
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    registration_no: Optional[str] = Field(None, alias="vehicle_registration")
    idv: Optional[float] = None
    valid_from: Optional[date] = Field(None, alias="start_date")
    valid_until: Optional[date] = Field(None, alias="expiry_date")
    
    class Config:
        from_attributes = True
        populate_by_name = True
