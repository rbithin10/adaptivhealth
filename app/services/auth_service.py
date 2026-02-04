"""
=============================================================================
ADAPTIV HEALTH - Authentication Service
=============================================================================
Implements OAuth 2.0 with JWT tokens for secure authentication.
Includes password hashing, token management, and RBAC support.

Security Features (HIPAA/SRS Requirements):
- Bcrypt password hashing
- JWT access and refresh tokens
- Account lockout after failed attempts
- Role-based access control
- Session timeout enforcement
=============================================================================
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Callable
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
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

# bcrypt is the recommended algorithm for password hashing
# It automatically handles salt generation and is resistant to rainbow table attacks
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor - higher = more secure but slower
)

# =============================================================================
# OAuth2 Scheme
# =============================================================================

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True
)

# Optional OAuth2 scheme (doesn't raise error if no token)
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
        Hash a plain password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Password to verify
            hashed_password: Stored hash to compare against
            
        Returns:
            True if password matches, False otherwise
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
        Create a JWT access token.
        
        Args:
            data: Payload data (usually contains user_id and role)
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        # Encode the token
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
        
        Args:
            data: Payload data
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        return jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None
    
    # -------------------------------------------------------------------------
    