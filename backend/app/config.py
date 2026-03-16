"""
Configuration management using Pydantic Settings.
Loads environment variables with validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "InsurAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://localhost:5174",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./insurai.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str = "insurai-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours for dev
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Storage
    STORAGE_PATH: str = "./storage"
    
    # AI/ML
    OPENAI_API_KEY: Optional[str] = None
    OCR_ENGINE: str = "tesseract"
    DETECTION_MODEL_PATH: str = "./models/yolov8.pt"
    
    # Surveyor Assignment
    SENIOR_SURVEYOR_IDS: str = ""  # Comma-separated list of senior surveyor user IDs
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
