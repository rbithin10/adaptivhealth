"""
Authentication routes.

This file handles sign up, login, and token refresh.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.......................... Line 20
# HELPER FUNCTIONS
#   - authenticate_user............ Line 45  (Validates email/password)
#   - get_current_user............. Line 120 (JWT token -> User object)
#   - get_current_admin_user....... Line 175 (Admin role check)
#   - check_clinician_phi_access... Line 195 (PHI consent check)
#   - get_current_doctor_user...... Line 215 (Clinician role check)
#
# ENDPOINTS
#   --- USER REGISTRATION (PUBLIC) ---
#   - POST /register............... Line 340 (Self-service patient signup)
#
#   --- USER REGISTRATION (ADMIN) ---
#   - POST /admin/register......... Line 415 (Admin creates clinicians/users)
#
#   --- LOGIN & TOKENS ---
#   - POST /login.................. Line 475 (Get JWT tokens)
#   - POST /refresh................ Line 512 (Refresh expired token)
#   - GET /me...................... Line 560 (Get current user info)
#
#   --- PASSWORD RESET ---
#   - POST /reset-password......... Line 580 (Request reset email)
#   - POST /reset-password/confirm. Line 625 (Set new password)
#
# BUSINESS CONTEXT:
# - PUBLIC /register: Patients self-register on mobile/web (PATIENT role only)
# - ADMIN /admin/register: Admins create clinicians and other users
# - Patients use /login on mobile app to authenticate
# - Clinicians use /login on dashboard to access patient data
# - Password reset flow used by all roles via mobile/web
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.models.recommendation import ExerciseRecommendation
from app.schemas.user import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm
)
from app.services.auth_service import AuthService, pwd_context
from app.services.email_service import email_service
from app.config import settings
from app.rate_limiter import limiter

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Auth service instance
auth_service = AuthService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/access")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/access", auto_error=False)

SESSION_COOKIE_NAME = "adaptiv_session"


class DashboardSessionLoginResponse(BaseModel):
    """Minimal dashboard login payload when using cookie-based auth."""
    id: int
    email: EmailStr
    role: str


def _resolve_authenticated_user_from_payload(payload: Optional[dict], db: Session) -> User:
    """Validate access-token payload and return the matching active user."""
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if this specific token has been revoked (e.g. after logout)
    jti = payload.get("jti")
    if jti:
        from app.models.token_blocklist import TokenBlocklist
        if db.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).first():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
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

    # Null role is a data-integrity error — fail loudly rather than silently
    # defaulting a clinician to PATIENT permissions
    if user.role is None:
        logger.error(f"User {user.user_id} has no assigned role — account misconfigured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account configuration error: role not assigned. Contact support."
        )

    return user


def _set_dashboard_session_cookie(response: Response, access_token: str) -> None:
    """Set HttpOnly dashboard session cookie for browser-based auth."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,  # Local HTTP dev only; use secure=True in production over HTTPS.
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_dashboard_session_cookie(response: Response) -> None:
    """Clear dashboard session cookie during logout."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=False,  # Local HTTP dev only; use secure=True in production over HTTPS.
        samesite="lax",
        path="/",
    )



# =============================================================================
# Helper Functions
# =============================================================================

# =============================================
# AUTHENTICATE_USER - Validates email and password for login
# Used by: Mobile app login, Dashboard login
# Returns: User object if credentials valid
# Raises: 401 (bad credentials), 403 (deactivated), 423 (locked)
# =============================================
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
        # DESIGN: Locks for 15 minutes after 3 failed attempts (NIST standard)
        # Gives user time to recover password before trying again
        if auth_cred.failed_login_attempts >= 3:
            auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
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

    # Rehash to Argon2id if still using old PBKDF2
    if pwd_context.needs_update(auth_cred.hashed_password):
        auth_cred.hashed_password = auth_service.hash_password(password)

    db.commit()
    
    return user


# =============================================
# GET_CURRENT_USER - Extracts user from JWT token
# Used by: ALL protected endpoints (dependency injection)
# Returns: User object from database
# Raises: 401 if token invalid, 403 if account deactivated
# =============================================
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
    return _resolve_authenticated_user_from_payload(payload, db)


def get_current_user_from_session_cookie(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Authenticate dashboard requests using the HttpOnly session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session cookie missing",
        )

    payload = auth_service.decode_token(session_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session cookie",
        )
    return _resolve_authenticated_user_from_payload(payload, db)


def get_current_user_session_or_bearer(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User:
    """Prefer dashboard cookie auth, fallback to bearer for mobile compatibility."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        payload = auth_service.decode_token(session_token)
        if payload:
            return _resolve_authenticated_user_from_payload(payload, db)

    if bearer_token:
        payload = auth_service.decode_token(bearer_token)
        if payload:
            return _resolve_authenticated_user_from_payload(payload, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# =============================================
# GET_CURRENT_ADMIN_USER - Ensures user is admin
# Used by: Admin-only endpoints (user creation, system config)
# Returns: User object if admin role
# Raises: 403 if not admin
# =============================================
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


# =============================================
# CHECK_CLINICIAN_PHI_ACCESS - Verifies clinician can view patient data
# Used by: Clinician endpoints that access patient health records
# Returns: None (passes silently if allowed)
# Raises: 403 if patient disabled data sharing
# =============================================
def check_clinician_phi_access(clinician: User, patient: User) -> None:
    """
    Verify a clinician may access a patient's PHI.
    
    Allowed when share_state is SHARING_ON or SHARING_DISABLE_REQUESTED.
    Blocked when share_state is SHARING_OFF.
    
    Raises:
        HTTPException 403 if access is denied.
    """
    share_state = getattr(patient, 'share_state', None) or "SHARING_ON"
    if share_state == "SHARING_OFF":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient has disabled data sharing"
        )


# =============================================
# GET_CURRENT_DOCTOR_USER - Ensures user is clinician (NOT admin)
# Used by: PHI endpoints - admins blocked from health data
# Returns: User object if clinician role
# Raises: 403 if admin or patient
# =============================================
def get_current_doctor_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has doctor role (NOT admin).
    
    Admin must NOT access PHI endpoints. Only clinicians can.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if clinician
        
    Raises:
        HTTPException: If user is not clinician
    """
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot access patient health data"
        )
    if current_user.role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinician access required"
        )
    return current_user


# =============================================
# GET_CURRENT_ADMIN_OR_DOCTOR_USER - Allows admin OR clinician
# Used by: User listing endpoints (no PHI), admin dashboard
# Returns: User object if admin or clinician role
# Raises: 403 if patient
# =============================================
def get_current_admin_or_doctor_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has admin or clinician role.
    
    Used for non-PHI endpoints like user listings where both
    admins and clinicians need access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if admin or clinician
        
    Raises:
        HTTPException: If user is patient
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.CLINICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or clinician access required"
        )
    return current_user


def get_current_admin_user_session_or_bearer(
    current_user: User = Depends(get_current_user_session_or_bearer)
) -> User:
    """Admin check for endpoints that allow cookie or bearer authentication."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_current_doctor_user_session_or_bearer(
    current_user: User = Depends(get_current_user_session_or_bearer)
) -> User:
    """Clinician-only check for endpoints that allow cookie or bearer authentication."""
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot access patient health data"
        )
    if current_user.role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinician access required"
        )
    return current_user


def get_current_admin_or_doctor_user_session_or_bearer(
    current_user: User = Depends(get_current_user_session_or_bearer)
) -> User:
    """Admin/clinician check for endpoints that allow cookie or bearer authentication."""
    if current_user.role not in (UserRole.ADMIN, UserRole.CLINICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or clinician access required"
        )
    return current_user


# =============================================================================
# Authentication Endpoints
# =============================================================================

# --- ENDPOINT: USER REGISTRATION (PUBLIC) ---

# =============================================
# REGISTER - Self-service patient registration
# Used by: Mobile app signup, Dashboard signup page
# Returns: UserResponse with new user details
# Roles: PUBLIC (anyone can register as PATIENT)
# =============================================
@router.post("/onboard", response_model=UserResponse)       # canonical backend name
@router.post("/auth/create", response_model=UserResponse)   # mobile alias
@router.post("/users/enroll", response_model=UserResponse)  # dashboard alias
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Self-service patient registration. Public endpoint.
    
    DESIGN:
    - Email must be unique (prevents duplicate accounts)
    - Password validated for strength (min 8 chars, letters + numbers)
    - Role ALWAYS set to PATIENT (cannot register as clinician/admin)
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
    - **Role**: Always set to PATIENT for self-service registration
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
    # SECURITY: Force role to PATIENT (ignore user-supplied role)
    user = User(
        email=user_data.email,
        full_name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        phone=user_data.phone,
        role=UserRole.PATIENT  # Self-service always creates patients
    )
    
    # Create SEPARATE AuthCredential record
    # DESIGN: Keeps hashed password in its own table
    # Allows SQL permissions to restrict auth table access
    auth_cred = AuthCredential(
        user=user,
        hashed_password=hashed_password
    )
    
    # Seed a default exercise recommendation so the Home screen
    # recommendation card works immediately (avoids 404 from
    # GET /recommendations/latest before the first risk assessment).
    default_rec = ExerciseRecommendation(
        user=user,
        title="Getting Started: Walking Plan",
        suggested_activity="walking",
        intensity_level="moderate",
        duration_minutes=20,
        description=(
            "Welcome to AdaptivHealth! Start with a 20-minute brisk walk "
            "at a comfortable pace. This plan will be personalised once "
            "your first health assessment is completed."
        ),
        warnings="Consult your physician before starting any exercise programme.",
        generated_by="system_default",
        confidence_score=1.0,
        status="active",
    )

    # Add all records in single transaction
    # ATOMICITY: Either all succeed or all rollback (no partial state)
    db.add(user)
    db.add(auth_cred)
    db.add(default_rec)
    db.commit()
    db.refresh(user)
    
    # Log registration for security audit trail
    logger.info(f"New user registered via self-service: {user.user_id} - {user.email}")
    
    return user


# =============================================
# REGISTER_USER_ADMIN - Admin creates users (clinicians, other admins)
# Used by: Admin dashboard (onboarding patients/clinicians)
# Returns: UserResponse with new user details
# Roles: ADMIN only
# =============================================
@router.post("/admin/register", response_model=UserResponse)
async def register_user_admin(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only user registration. Creates users with any role.
    
    Use this for creating clinicians and other admins.
    Self-service registration should use POST /register instead.
    """
    # Email uniqueness check
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = auth_service.hash_password(user_data.password)
    
    # Admin can set any role
    user = User(
        email=user_data.email,
        full_name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        phone=user_data.phone,
        role=user_data.role
    )
    
    # Create auth credential
    auth_cred = AuthCredential(
        user=user,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.add(auth_cred)

    # Seed a default recommendation for patients created by admins
    if (user_data.role or UserRole.PATIENT) == UserRole.PATIENT:
        default_rec = ExerciseRecommendation(
            user=user,
            title="Getting Started: Walking Plan",
            suggested_activity="walking",
            intensity_level="moderate",
            duration_minutes=20,
            description=(
                "Welcome to AdaptivHealth! Start with a 20-minute brisk walk "
                "at a comfortable pace. This plan will be personalised once "
                "your first health assessment is completed."
            ),
            warnings="Consult your physician before starting any exercise programme.",
            generated_by="system_default",
            confidence_score=1.0,
            status="active",
        )
        db.add(default_rec)

    db.commit()
    db.refresh(user)
    
    logger.info(f"User registered by admin {current_user.user_id}: {user.user_id} - {user.email} (role: {user.role})")
    
    return user


# --- ENDPOINT: LOGIN & TOKEN MANAGEMENT ---

# =============================================
# LOGIN - User authenticates with email/password
# Used by: Mobile app login screen, Dashboard login page
# Returns: JWT access_token + refresh_token
# Roles: ALL (patient, clinician, admin)
# =============================================
@router.post("/access", response_model=TokenResponse)         # canonical backend name
@router.post("/auth/signin", response_model=TokenResponse)    # mobile alias
@limiter.limit("5/minute")
async def login_with_tokens(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens for mobile clients.
    
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


@router.post("/session/start", response_model=DashboardSessionLoginResponse)
@limiter.limit("5/minute")
async def login_dashboard_session(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate dashboard user and set HttpOnly session cookie."""
    user = authenticate_user(db, form_data.username, form_data.password)

    access_token = auth_service.create_access_token(
        data={"sub": str(user.user_id), "role": (user.role or UserRole.PATIENT).value}
    )
    _set_dashboard_session_cookie(response, access_token)

    logger.info(f"Dashboard session started for user: {user.user_id} - {user.email}")
    return DashboardSessionLoginResponse(
        id=user.user_id,
        email=user.email,
        role=(user.role or UserRole.PATIENT).value,
    )


# =============================================
# REFRESH_TOKEN - Get new access token using refresh token
# Used by: Mobile app / Dashboard when access token expires
# Returns: New JWT access_token + refresh_token
# Roles: ALL (must have valid refresh token)
# =============================================
@router.post("/access/renew", response_model=TokenResponse)         # canonical backend name
@router.post("/auth/token/refresh", response_model=TokenResponse)   # mobile alias
@router.post("/session/extend", response_model=TokenResponse)       # dashboard alias
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
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
    
    # Check if this refresh token has been revoked
    jti = payload.get("jti")
    if jti:
        from app.models.token_blocklist import TokenBlocklist
        if db.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).first():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
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


# =============================================
# GET_CURRENT_USER_INFO - Returns logged-in user's profile
# Used by: Mobile app profile screen, Dashboard header
# Returns: UserResponse with user details
# Roles: ALL (authenticated users)
# =============================================
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    
    Returns user profile data.
    """
    return current_user


# --- ENDPOINT: PASSWORD RESET FLOW ---

# =============================================
# REQUEST_PASSWORD_RESET - User requests reset email
# Used by: Mobile app "Forgot Password", Dashboard login
# Returns: Success message (always, to prevent email enumeration)
# Roles: PUBLIC (no auth needed)
# =============================================
@router.post("/reset-password")
@limiter.limit("3/15minutes")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    _background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset for a user.
    
    - **email**: User email address
    
    Generates a reset token and sends it via SMTP when configured.
    Falls back to explicit dev-mode token logging only when enabled.
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if user:
        # Generate reset token with 1-hour expiration
        # WHY: Use "sub" key (same as access/refresh tokens) for consistency
        reset_token = auth_service.create_access_token(
            data={"sub": str(user.user_id), "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )

        logger.info(f"Password reset requested for: {reset_data.email}")

        reset_link = email_service.build_password_reset_link(reset_token)

        if email_service.is_smtp_configured():
            try:
                recipient_email = str(user.email)
                email_service.send_password_reset_email(
                    to_email=recipient_email,
                    reset_link=reset_link,
                )
                logger.info(
                    "Password reset email sent successfully",
                    extra={
                        "event": "password_reset_email_sent",
                        "user_id": user.user_id,
                        "recipient": recipient_email,
                    },
                )
            except Exception as exc:
                logger.error(
                    "Password reset email delivery failed",
                    extra={
                        "event": "password_reset_email_failed",
                        "user_id": user.user_id,
                        "recipient": str(user.email),
                        "error": str(exc),
                    },
                )
                if settings.password_reset_dev_token_logging and settings.environment != "production":
                    logger.info(f"Dev mode - reset token: {reset_token}")
        else:
            logger.warning(
                "SMTP is not configured for password reset email delivery",
                extra={
                    "event": "password_reset_smtp_not_configured",
                    "user_id": user.user_id,
                    "recipient": str(user.email),
                },
            )
            if settings.password_reset_dev_token_logging and settings.environment != "production":
                logger.info(f"Dev mode - reset token: {reset_token}")
    
    # Always return success to prevent email enumeration
    return {
        "message": "If the email exists, a reset link has been sent"
    }


# =============================================
# CONFIRM_PASSWORD_RESET - User sets new password with token
# Used by: Mobile app reset screen, Dashboard reset page
# Returns: Success message
# Roles: PUBLIC (token validates user)
# =============================================
@router.post("/reset-password/confirm")
@limiter.limit("5/15minutes")
async def confirm_password_reset(
    request: Request,
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
    
    # Get user ID from token ("sub" key — consistent with access/refresh tokens)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )
    
    # Get the user
    user = db.query(User).filter(User.user_id == int(user_id)).first()
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


# --- ENDPOINT: LOGOUT / TOKEN REVOCATION ---

# =============================================
# LOGOUT - Revoke the caller's access token
# Used by: Mobile app logout, Dashboard logout
# Returns: Success message
# Roles: ALL (authenticated users)
# =============================================
@router.post("/logout")
@router.post("/auth/signout")    # mobile alias
async def logout_mobile(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke the current access token.

    Adds the token's jti to the server-side blocklist so it is rejected
    on all subsequent requests even before its natural expiry.
    The client must also discard any stored refresh tokens.
    """
    from app.models.token_blocklist import TokenBlocklist

    payload = auth_service.decode_token(token)
    if payload:
        jti = payload.get("jti")
        if jti:
            expires_at = datetime.fromtimestamp(
                payload.get("exp", 0), tz=timezone.utc
            )
            existing = db.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).first()
            if not existing:
                db.add(TokenBlocklist(jti=jti, expires_at=expires_at))
                db.commit()

    logger.info(f"User logged out: {current_user.user_id}")
    return {"message": "Logged out successfully"}


@router.post("/session/end")
async def logout_dashboard_session(response: Response):
    """End dashboard cookie session and clear the HttpOnly cookie."""
    _clear_dashboard_session_cookie(response)
    return {"message": "Logged out successfully"}