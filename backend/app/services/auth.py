"""
Authentication service for OTP and JWT token management.
"""
import random
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for OTP storage
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class AuthService:
    """Authentication service for OTP and JWT management."""
    
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    OTP_RATE_LIMIT_WINDOW = 3600  # 1 hour
    OTP_RATE_LIMIT_MAX = 100  # Relaxed for testing (was 5)
    
    @staticmethod
    def generate_otp() -> str:
        """
        Generate a 6-digit OTP.
        
        Returns:
            6-digit OTP string
        """
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def store_otp(phone: str, otp: str) -> bool:
        """
        Store OTP in Redis with expiry.
        
        Args:
            phone: Phone number
            otp: OTP code
            
        Returns:
            True if stored successfully
        """
        key = f"otp:{phone}"
        redis_client.setex(key, AuthService.OTP_EXPIRY_SECONDS, otp)
        return True
    
    @staticmethod
    def verify_otp(phone: str, otp: str) -> bool:
        """
        Verify OTP against stored value.
        
        Args:
            phone: Phone number
            otp: OTP code to verify
            
        Returns:
            True if OTP is valid
        """
        key = f"otp:{phone}"
        stored_otp = redis_client.get(key)
        
        if stored_otp and stored_otp == otp:
            # Delete OTP after successful verification
            redis_client.delete(key)
            return True
        return False
    
    @staticmethod
    def check_rate_limit(phone: str) -> bool:
        """
        Check if phone number has exceeded OTP request rate limit.
        
        Args:
            phone: Phone number
            
        Returns:
            True if within rate limit, False if exceeded
        """
        key = f"otp_rate:{phone}"
        count = redis_client.get(key)
        
        if count is None:
            # First request
            redis_client.setex(key, AuthService.OTP_RATE_LIMIT_WINDOW, 1)
            return True
        
        count = int(count)
        if count >= AuthService.OTP_RATE_LIMIT_MAX:
            return False
        
        # Increment counter
        redis_client.incr(key)
        return True
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Payload data to encode
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """
        Create JWT refresh token.
        
        Args:
            data: Payload data to encode
            
        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)


# Global auth service instance
auth_service = AuthService()
