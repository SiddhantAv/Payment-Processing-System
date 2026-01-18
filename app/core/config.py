"""
Application configuration settings.
Uses Pydantic Settings for environment variable management.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


# Get project root directory (parent of 'app' directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    DATABASE_URL: str  # Must be set via environment variable (no default for security)
    
    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Authorize.Net settings
    AUTHORIZE_NET_API_LOGIN_ID: str
    AUTHORIZE_NET_TRANSACTION_KEY: str
    AUTHORIZE_NET_ENVIRONMENT: str = "sandbox"  # sandbox or production
    
    # Application settings
    PROJECT_NAME: str = "Payment Processing System"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # CORS settings
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list, or "*" for all (dev only)
    
    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True


# Global settings instance
settings = Settings()
