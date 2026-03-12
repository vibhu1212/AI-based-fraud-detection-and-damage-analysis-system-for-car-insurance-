"""
Authentication request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional


class SendOTPRequest(BaseModel):
    """Request schema for sending OTP."""
    phone: str = Field(..., description="Phone number with country code", example="+919876543210")


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    full_name: str = Field(..., description="Full name of the user")
    phone: str = Field(..., description="Phone number with country code", example="+919876543210")
    role: str = Field(..., description="User role (CUSTOMER or SURVEYOR)", example="CUSTOMER")


class SendOTPResponse(BaseModel):
    """Response schema for OTP sent."""
    message: str
    phone: str
    expires_in_seconds: int


class VerifyOTPRequest(BaseModel):
    """Request schema for verifying OTP."""
    phone: str = Field(..., description="Phone number with country code")
    otp: str = Field(..., description="6-digit OTP code", min_length=6, max_length=6)


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str  # user_id
    role: str
    exp: int
    type: str
