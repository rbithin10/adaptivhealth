"""
Authentication helpers.

This file handles password hashing and token creation.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
# PASSWORD HASHING CONFIG.............. Line 35
# OAUTH2 SCHEME....................... Line 45
#
# CLASS: AuthService
#   - hash_password().................. Line 68  (PBKDF2 hash)
#   - verify_password()................ Line 83  (Check password match)
#   - create_access_token()............ Line 106 (JWT access token)
#   - create_refresh_token()........... Line 153 (JWT refresh token)
#   - decode_token()................... Line 186 (JWT validation)
#
# BUSINESS CONTEXT:
# - PBKDF2 with 200k rounds (OWASP recommended)
# - JWT tokens for stateless auth
# - Account locking after failed attempts (HIPAA)
# =============================================================================
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# Password Hashing Configuration
# =============================================================================

# Use PBKDF2 for password hashing (safe and compatible).
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=200000  # OWASP recommended minimum
)

# =============================================================================
# OAuth2 Scheme
# =============================================================================

# Read login tokens from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True
)

# Optional token reader (no error if missing).
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


# =============================================================================
# Authentication Service Class
# =============================================================================

class AuthService:
    """
    Handles authentication operations including:
    - Password hashing and verification
    - JWT token creation and validation
    - User authentication
    - Account locking after failed attempts (HIPAA requirement)
    """
    
    # -------------------------------------------------------------------------
    # Password Operations
    # -------------------------------------------------------------------------
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password so it is safe to store.
        
        We use PBKDF2 with many rounds to make guessing very slow.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string suitable for storage in auth_credentials table
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
                Check if the password matches what we stored.
                If anything goes wrong, return False.
        
        Args:
            plain_password: User's input password
            hashed_password: Stored hash from auth_credentials.password_hash
            
        Returns:
            True if password matches hash, False if mismatch or error
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # Token Operations
    # -------------------------------------------------------------------------
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a short-lived login token.
        It lets the app call protected APIs for a limited time.
        
        Args:
            data: Claims to include in token (typically {"user_id": X, "role": "patient"})
            expires_delta: Optional custom expiration (for testing or special cases)
            
        Returns:
            Encoded JWT token string ready for Authorization header
        """
        to_encode = data.copy()
        
        # Set expiration time for the token.
        if expires_delta:
            # Custom expiration (used for password reset tokens, etc.)
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # Default access token lifetime (30 minutes).
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        # Add standard fields (don't override type if already provided)
        to_encode.update({
            "exp": expire,  # Expiration time (unix timestamp)
            "iat": datetime.now(timezone.utc),  # Issued-at time
        })
        
        # Set type to "access" only if not already specified
        if "type" not in to_encode:
            to_encode["type"] = "access"
        
        # Encode the token with the app's secret key.
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """
        Create a longer-lived refresh token.
        This lets users stay logged in without typing passwords often.
        
        Args:
            data: Claims to include (user_id, role)
            
        Returns:
            Encoded JWT refresh token string
        """
        to_encode = data.copy()
        
        # Refresh tokens live longer than access tokens.
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        
        # Add standard fields.
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"  # Mark as refresh token (not reusable as access token)
        })
        
        # Encode and return the token.
        return jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode a token and check if it is still valid.
        Returns None if the token is expired or broken.
        
        Args:
            token: JWT token string from Authorization header (typically \"Bearer token\")
            
        Returns:
            Decoded payload dict if valid, None if expired/invalid/tampered
        """
        try:
            # Decode and validate the token.
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return payload
        except JWTError as e:
            # Token is invalid or expired.
            logger.warning(f"JWT decode error: {e}")
            return None
    
    # -------------------------------------------------------------------------
    