"""
=============================================================================
ADAPTIV HEALTH - Configuration Settings
=============================================================================
Centralized application configuration using pydantic-settings.

Design principles:
- Clear separation of concerns
- Secure defaults
- Minimal over-engineering
- Compatible with local development and AWS deployment
=============================================================================
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # ---------------------------------------------------------------------
    # Application Info
    # ---------------------------------------------------------------------
    app_name: str = Field(default="Adaptiv Health API")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # ---------------------------------------------------------------------
    # Database Configuration
    # ---------------------------------------------------------------------
    # IMPORTANT:
    # Always override this in .env for PostgreSQL.
    # SQLite default is only for emergency local testing.
    database_url: str = Field(
        default="sqlite:///./adaptiv_health.db",
        description="Database connection string"
    )

    # ---------------------------------------------------------------------
    # Authentication / JWT
    # ---------------------------------------------------------------------
    secret_key: str = Field(
        ...,
        description="JWT signing secret key (min 32 chars)"
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    # ---------------------------------------------------------------------
    # Optional Application-Level PHI Encryption
    # ---------------------------------------------------------------------
    # NOTE:
    # PostgreSQL / AWS RDS already provides encryption at rest.
    # This key is OPTIONAL and only needed if you encrypt PHI at app-level.
    phi_encryption_key: Optional[str] = Field(
        default=None,
        description="Optional AES-256-GCM base64 key for PHI"
    )

    # ---------------------------------------------------------------------
    # CORS Configuration
    # ---------------------------------------------------------------------
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",   # React dashboard
            "http://localhost:5173",   # Vite dev server
            "http://localhost:8080",   # Flutter web
        ]
    )

    # ---------------------------------------------------------------------
    # Rate Limiting / Session Security
    # ---------------------------------------------------------------------
    rate_limit_per_minute: int = Field(default=60)
    session_timeout_minutes: int = Field(default=30)
    max_login_attempts: int = Field(default=3)
    lockout_duration_minutes: int = Field(default=5)

    # ---------------------------------------------------------------------
    # AWS (Optional – Production)
    # ---------------------------------------------------------------------
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = Field(default="us-east-1")
    s3_bucket_name: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Safe to use with FastAPI dependency injection.
    """
    return Settings()


# Convenience import
settings = get_settings()
