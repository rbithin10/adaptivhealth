"""
Application settings.

Loads all configuration variables (database, security, API keys) from
environment variables. Makes the app work in different places
(local computer, testing server, or AWS cloud).
"""

# Caches the result so we only load settings once, not on every request
from functools import lru_cache
# Allows us to declare types like "Optional" (meaning a value can be missing)
from typing import Any, Optional

# Pydantic helps us validate settings and make sure nothing is misconfigured
from pydantic import AliasChoices, Field, field_validator
# BaseSettings reads values from environment variables or .env files automatically
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All the settings the app needs to run, loaded from environment variables.
    Think of this as a checklist of configuration values the app reads on startup.
    """

    # ---------------------------------------------------------------------
    # Application Info — basic identity of the running app
    # ---------------------------------------------------------------------
    # The current version number shown in API docs
    app_version: str = Field(default="1.0.0")
    # Which environment we are in: "development", "staging", or "production"
    environment: str = Field(default="development")
    # Turn on extra logging to help find bugs (should be False in production)
    debug: bool = Field(default=False)

    # ---------------------------------------------------------------------
    # Database Configuration — how we connect to PostgreSQL
    # ---------------------------------------------------------------------
    # The full connection address for our PostgreSQL database (required, no default)
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string"
    )

    # ---------------------------------------------------------------------
    # Authentication / JWT — settings for login tokens
    # ---------------------------------------------------------------------
    # A secret password the server uses to create and verify login tokens
    secret_key: str = Field(
        ...,
        description="JWT signing secret key (min 32 chars)"
    )
    # The encryption method used for tokens (HS256 is industry standard)
    algorithm: str = Field(default="HS256")
    # How many minutes before a login token expires and the user must refresh
    access_token_expire_minutes: int = Field(default=30)
    # How many days a refresh token lasts before the user must log in again
    refresh_token_expire_days: int = Field(default=7)

    # ---------------------------------------------------------------------
    # Optional Application-Level PHI Encryption
    # ---------------------------------------------------------------------
    # NOTE: PostgreSQL / AWS RDS already encrypts data at rest.
    # This extra key is only needed if you want double encryption on patient health info.
    phi_encryption_key: Optional[str] = Field(
        default=None,
        description="Optional AES-256-GCM base64 key for PHI"
    )

    # ---------------------------------------------------------------------
    # Gemini API — Google's AI used for reading uploaded medical documents
    # ---------------------------------------------------------------------
    # The API key for Google Gemini; accepts multiple environment variable names
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"),
        description="Google Gemini API key for document extraction (free tier from ai.google.dev)"
    )

    # ---------------------------------------------------------------------
    # SMTP / Email — used to send password reset emails to users
    # ---------------------------------------------------------------------
    # The mail server address (e.g., smtp.sendgrid.net or smtp.gmail.com)
    smtp_host: Optional[str] = Field(default=None, description="SMTP host (e.g., smtp.sendgrid.net)")
    # The port number the mail server listens on (587 is the most common)
    smtp_port: int = Field(default=587, description="SMTP port (587 for STARTTLS, 465 for SSL)")
    # The username to log in to the mail server
    smtp_username: Optional[str] = Field(default=None, description="SMTP username (SendGrid usually 'apikey')")
    # The password or API key to authenticate with the mail server
    smtp_password: Optional[str] = Field(default=None, description="SMTP password or provider API key")
    # The email address shown in the "From" field of outgoing emails
    smtp_from_email: Optional[str] = Field(default=None, description="From email address for transactional emails")
    # The display name shown next to the "From" email address
    smtp_from_name: str = Field(default="Adaptiv Health", description="From display name for outgoing email")
    # Whether to use TLS encryption when connecting to the mail server
    smtp_use_tls: bool = Field(default=True, description="Use STARTTLS for SMTP connection")
    # Whether to use SSL encryption (alternative to TLS, used on port 465)
    smtp_use_ssl: bool = Field(default=False, description="Use SSL-wrapped SMTP connection")

    # The web address of the frontend app, used to build password reset links
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL used in reset-password links"
    )
    # The page path on the frontend where users can set a new password
    password_reset_path: str = Field(
        default="/reset-password",
        description="Frontend password reset route path"
    )

    # When True, reset tokens are printed in the console for local testing
    # SECURITY: Must stay False in production to avoid leaking tokens
    password_reset_dev_token_logging: bool = Field(
        default=False,
        description="Explicit dev-only flag to log reset tokens when SMTP is unavailable"
    )

    class Config:
        # Look for settings in these files; .env.local overrides .env for local dev
        env_file = [".env", ".env.local"]
        env_file_encoding = "utf-8"
        # Environment variable names are not case-sensitive (DATABASE_URL = database_url)
        case_sensitive = False
        # Ignore any extra environment variables we don't recognise
        extra = "ignore"

    @field_validator('database_url')
    def validate_postgresql_url(cls, v: str) -> str:
        """Make sure the database address points to PostgreSQL and nothing else."""
        value = v.strip().lower()
        # We don't support SQLite — it can't handle multiple users at once
        if value.startswith("sqlite"):
            raise ValueError("SQLite is not supported. Use a PostgreSQL DATABASE_URL.")
        # The address must start with a PostgreSQL prefix
        if not (
            value.startswith("postgresql://")
            or value.startswith("postgresql+")
            or value.startswith("postgres://")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL.")
        return v

    @field_validator("gemini_api_key", mode="before")
    def normalize_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        """Clean up the Gemini API key — treat blank or whitespace-only values as missing."""
        if v is None:
            return None
        if isinstance(v, str):
            # Remove extra spaces around the key
            cleaned = v.strip()
            # If the key is empty after stripping, treat it as not provided
            return cleaned or None
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Create and cache the settings object so it is only loaded once.
    Every part of the app that needs settings will get the same instance.
    """
    settings_factory: Any = Settings
    return settings_factory()


# Create one shared settings object that any file can import directly
settings = get_settings()
