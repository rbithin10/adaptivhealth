"""
Application settings.

Loads all configuration variables (database, security, API keys) from
environment variables. Makes the app work in different places
(local computer, testing server, or AWS cloud).
"""

from functools import lru_cache
from typing import Any, List, Optional

from pydantic import AliasChoices, Field, field_validator
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
    # PostgreSQL is required for all environments in this project.
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string"
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
    # Gemini API (Document Extraction)
    # ---------------------------------------------------------------------
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"),
        description="Google Gemini API key for document extraction (free tier from ai.google.dev)"
    )

    # ---------------------------------------------------------------------
    # SMTP / Email (Password Reset Delivery)
    # ---------------------------------------------------------------------
    smtp_host: Optional[str] = Field(default=None, description="SMTP host (e.g., smtp.sendgrid.net)")
    smtp_port: int = Field(default=587, description="SMTP port (587 for STARTTLS, 465 for SSL)")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username (SendGrid usually 'apikey')")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password or provider API key")
    smtp_from_email: Optional[str] = Field(default=None, description="From email address for transactional emails")
    smtp_from_name: str = Field(default="Adaptiv Health", description="From display name for outgoing email")
    smtp_use_tls: bool = Field(default=True, description="Use STARTTLS for SMTP connection")
    smtp_use_ssl: bool = Field(default=False, description="Use SSL-wrapped SMTP connection")

    # Frontend URL used in password reset links
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL used in reset-password links"
    )
    password_reset_path: str = Field(
        default="/reset-password",
        description="Frontend password reset route path"
    )

    # Explicit development fallback flag
    # SECURITY: Keep false in production. When true, reset tokens are logged for local testing.
    password_reset_dev_token_logging: bool = Field(
        default=False,
        description="Explicit dev-only flag to log reset tokens when SMTP is unavailable"
    )

    # ---------------------------------------------------------------------
    # CORS Configuration
    # ---------------------------------------------------------------------
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",   # React dashboard
            "http://localhost:5173",   # Vite dev server
            "http://localhost:5000",   # Flutter web
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
    aws_region: str = Field(default="me-central-1")
    s3_bucket_name: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @field_validator('database_url')
    def validate_postgresql_url(cls, v: str) -> str:
        """Ensure database URL is PostgreSQL-only."""
        value = v.strip().lower()
        if value.startswith("sqlite"):
            raise ValueError("SQLite is not supported. Use a PostgreSQL DATABASE_URL.")
        if not (
            value.startswith("postgresql://")
            or value.startswith("postgresql+")
            or value.startswith("postgres://")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL.")
        return v

    @field_validator("gemini_api_key", mode="before")
    def normalize_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        """Normalize optional Gemini key; treat blank values as missing."""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned or None
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Safe to use with FastAPI dependency injection.
    """
    settings_factory: Any = Settings
    return settings_factory()


# Convenience import
settings = get_settings()
