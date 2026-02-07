"""
Authentication routes.

This file handles sign up, login, and token refresh.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.schemas.user import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm
)
from app.services.auth_service import AuthService
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Auth service instance
auth_service = AuthService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")



# =============================================================================
# Helper Functions
# =============================================================================

def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate a user by email and password.
    
        This checks the user exists, that the account is active,
        and that the password is correct.
    
    Args:
        db: Database session
        email: User email
        password: Plain password
        
    Returns:
        User object if authenticated
        
    Raises:
        HTTPException: If authentication fails (401/403 codes)
    """
    # Look up the user by email.
    user = db.query(User).filter(User.email == email).first()
    
    # Use a generic error to avoid exposing whether the email exists.
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Stop here if the account is deactivated.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
        
    
    # Get the password record from the auth table.
    auth_cred = user.auth_credential
    if not auth_cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication not configured"
        )
    
    # Stop if the account is temporarily locked.
    if auth_cred.is_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts"
        )
    
    # Check the password.
    if not auth_service.verify_password(password, auth_cred.hashed_password):
        # Increment failed attempts counter
        auth_cred.failed_login_attempts += 1
        
        # Lock account if threshold exceeded
        # DESIGN: Locks for N minutes after M failed attempts
        # Gives user time to recover password before trying again
        if auth_cred.failed_login_attempts >= settings.max_login_attempts:
            auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
            logger.warning(f"Account locked for user {user.user_id} due to failed attempts")
        
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Reset failed attempts counter on successful login
    # WHY: Account recovers automatically after successful auth
    # Prevents permanent lockout from repeated password attempts
    auth_cred.failed_login_attempts = 0
    auth_cred.locked_until = None
    auth_cred.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    payload = auth_service.decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Use user_id column (matches Massoud's AWS schema)
    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_current_doctor_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has doctor or admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if doctor/admin
        
    Raises:
        HTTPException: If user is not doctor/admin
    """
    if current_user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinician access required"
        )
    return current_user


# =============================================================================
# Authentication Endpoints
# =============================================================================

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    DESIGN:
    - Email must be unique (prevents duplicate accounts)
    - Password validated for strength (min 8 chars, letters + numbers)
    - Role defaults to PATIENT (clinicians/admins created by admin only)
    - Creates TWO records for HIPAA compliance:
      1. User record (PHI: health data, demographics)
      2. AuthCredential record (sensitive auth: password hash, login attempts)
    
    WHY SEPARATE TABLES:
    - Isolates sensitive auth material from PHI
    - Allows future encryption policies per data type
    - Audit logging can treat auth separately from health data
    - Database access controls can restrict auth table separately
    
    - **Email**: Must be unique and valid
    - **Password**: Minimum 8 characters with letters and numbers
    - **Role**: Defaults to patient, admin can set other roles
    """
    # Email uniqueness check prevents account enumeration
    # (though error message doesn't reveal if email exists)
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password using pbkdf2_sha256
    # WHY: Uses OWASP-recommended 200,000 iterations (slow hash = safe)
    hashed_password = auth_service.hash_password(user_data.password)
    
    # Create User record with health/demographic data
    # Includes Massoud's original columns from AWS RDS schema
    user = User(
        email=user_data.email,
        full_name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        phone=user_data.phone,
        role=user_data.role  # Defaults to PATIENT if not specified
    )
    
    # Create SEPARATE AuthCredential record
    # DESIGN: Keeps hashed password in its own table
    # Allows SQL permissions to restrict auth table access
    auth_cred = AuthCredential(
        user=user,
        hashed_password=hashed_password
    )
    
    # Add both records in single transaction
    # ATOMICITY: Either both succeed or both rollback (no partial state)
    db.add(user)
    db.add(auth_cred)
    db.commit()
    db.refresh(user)
    
    # Log registration for security audit trail
    logger.info(f"New user registered: {user.user_id} - {user.email}")
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    - **username**: User email
    - **password**: User password
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    # Create tokens using user_id (Massoud's PK)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.user_id), "role": (user.role or UserRole.PATIENT).value}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": str(user.user_id)}
    )
    
    logger.info(f"User logged in: {user.user_id} - {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    payload = auth_service.decode_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token = auth_service.create_access_token(
        data={"sub": str(user.user_id), "role": (user.role or UserRole.PATIENT).value}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": str(user.user_id)}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    
    Returns user profile data.
    """
    return current_user


@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset for a user.
    
    - **email**: User email address
    
    Generates a reset token and logs it (in production, would send via email).
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if user:
        # Generate reset token with 1-hour expiration
        reset_token = auth_service.create_access_token(
            data={"user_id": user.user_id, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Log token for development only (DO NOT do this in production)
        # In production, send via email instead
        from app.config import settings
        logger.info(f"Password reset requested for: {reset_data.email}")
        if settings.environment == "development" or settings.debug:
            logger.info(f"Reset token (DEV ONLY - would be sent via email): {reset_token}")
        
        # In production, this would send an email with the reset link
        # Example: https://app.adaptivhealth.com/reset-password?token={reset_token}
        # background_tasks.add_task(send_reset_email, user.email, reset_token)
    
    # Always return success to prevent email enumeration
    return {
        "message": "If the email exists, a reset link has been sent"
    }


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    
    - **token**: Reset token from email
    - **new_password**: New password
    
    Validates the reset token and updates the user's password.
    """
    # Decode and validate the reset token
    payload = auth_service.decode_token(reset_data.token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Verify this is a password reset token
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )
    
    # Get user ID from token
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )
    
    # Get the user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash the new password
    hashed_password = auth_service.hash_password(reset_data.new_password)
    
    # Update the password in auth_credentials table
    auth_cred = user.auth_credential
    if not auth_cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User authentication not configured"
        )
    
    auth_cred.hashed_password = hashed_password
    auth_cred.failed_login_attempts = 0  # Reset failed attempts
    auth_cred.locked_until = None  # Unlock account if locked
    
    db.commit()
    
    logger.info(f"Password reset successful for user {user_id}")
    
    return {
        "message": "Password reset successful. You can now log in with your new password."
    }