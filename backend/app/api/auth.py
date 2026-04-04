"""
Authentication endpoints for OTP and JWT token management.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.models.user import User
from app.schemas.auth import (
    SendOTPRequest,
    RegisterRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    TokenResponse,
    RefreshTokenRequest
)
from app.services.auth import auth_service
from app.services.audit_logger import audit_logger
from app.config import settings
from app.api.dependencies import get_current_user

router = APIRouter()


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to phone number.
    
    For demo purposes, OTP is logged to console instead of sent via SMS.
    """
    # Check rate limiting
    if not auth_service.check_rate_limit(request.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again later."
        )
    
    # Check if user exists (handle both raw and +91 formats)
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user and len(request.phone) == 10:
        # Try with +91 prefix
        user = db.query(User).filter(User.phone == f"+91{request.phone}").first()
        
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this phone number"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate and store OTP
    otp = auth_service.generate_otp()
    # Always store OTP against the requested phone (raw input) to ensure match during verify
    auth_service.store_otp(request.phone, otp)
    
    # For demo: log OTP to console
    print(f"\n{'='*50}")
    print(f"🔐 OTP for {request.phone}: {otp}")
    print(f"{'='*50}\n")
    
    return SendOTPResponse(
        message="OTP sent successfully",
        phone=request.phone,
        expires_in_seconds=auth_service.OTP_EXPIRY_SECONDS
    )


@router.post("/register", response_model=SendOTPResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user and send OTP.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.phone == request.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered with this phone number"
        )
    
    # Check rate limiting
    if not auth_service.check_rate_limit(request.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

    # Create new user
    from app.models.enums import UserRole
    try:
        role_enum = UserRole(request.role.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be CUSTOMER or SURVEYOR"
        )

    new_user = User(
        name=request.full_name,
        phone=request.phone,
        role=role_enum,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate and store OTP
    otp = auth_service.generate_otp()
    auth_service.store_otp(request.phone, otp)
    
    # For demo: log OTP to console
    print(f"\n{'='*50}")
    print(f"🔐 REGISTER OTP for {request.phone}: {otp}")
    print(f"{'='*50}\n")
    
    return SendOTPResponse(
        message="Registration successful. OTP sent.",
        phone=request.phone,
        expires_in_seconds=auth_service.OTP_EXPIRY_SECONDS
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and issue JWT tokens.
    """
    # Check verification rate limit
    if not auth_service.check_verify_rate_limit(request.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )

    # Verify OTP
    if not auth_service.verify_otp(request.phone, request.otp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Get user
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user and len(request.phone) == 10:
        # Try with +91 prefix
        user = db.query(User).filter(User.phone == f"+91{request.phone}").first()
        
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate tokens
    token_data = {
        "sub": str(user.id),
        "role": user.role.value
    }
    
    access_token = auth_service.create_access_token(token_data)
    refresh_token = auth_service.create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    payload = auth_service.verify_token(request.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    token_data = {
        "sub": str(user.id),
        "role": user.role.value
    }
    
    access_token = auth_service.create_access_token(token_data)
    new_refresh_token = auth_service.create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )



@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and log the event.
    
    Note: JWT tokens are stateless, so we can't invalidate them server-side
    without maintaining a blacklist. For this MVP, we just log the logout event.
    The client is responsible for clearing tokens.
    """
    # Log logout event in audit trail
    audit_logger.log_logout(
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        db=db
    )
    
    return {
        "message": "Logout successful",
        "user_id": str(current_user.id)
    }
