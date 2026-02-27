"""
Test helper factory functions.

Shared utility functions for creating test data (users, vitals, alerts, etc.)
across all test files. These factories eliminate boilerplate and ensure
consistent test data setup.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 18
# FACTORIES
#   - make_user()........................ Line 35  (Create user + auth credential)
#   - get_token()........................ Line 64  (Login and get JWT token)
#   - make_vital()........................ Line 77  (Create vital sign record)
#   - make_activity()..................... Line 102 (Create activity session)
#   - make_alert()........................ Line 129 (Create alert record)
#   - make_risk_assessment().............. Line 152 (Create risk assessment)
#   - make_recommendation()............... Line 177 (Create exercise recommendation)
#
# DESIGN:
# - No pytest dependencies (just plain functions for reuse)
# - All factories default existing records (skip if email/user exists)
# - Timestamps use UTC + timezone awareness
# - Return model instances directly for assertions
# =============================================================================
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.models.vital_signs import VitalSignRecord
from app.models.activity import ActivitySession
from app.models.alert import Alert
from app.models.risk_assessment import RiskAssessment
from app.models.recommendation import ExerciseRecommendation
from app.services.auth_service import AuthService


# =============================================================================
# MAKE_USER - Create user + auth credential in one call
# =============================================================================

def make_user(
    db: Session,
    email: str,
    name: str,
    role: str = "patient",
    password: str = "TestPass123"
) -> User:
    """
    Create a User and associated AuthCredential record.
    
    Skips creation if user with email already exists (idempotent).
    
    Args:
        db: SQLAlchemy session
        email: User email (unique)
        name: Full name
        role: UserRole (patient/clinician/admin), default "patient"
        password: Plain text password, default "TestPass123"
    
    Returns:
        User model instance (created or existing)
    
    Raises:
        ValueError: If role is invalid
    
    # WHY:
    # Tests need both User and AuthCredential. This factory creates both in
    # one call, preventing cascade issues and reducing boilerplate.
    """
    # Check if user exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    
    # Create user with role enum
    user_role = UserRole[role.upper()] if isinstance(role, str) else role
    user = User(
        email=email,
        full_name=name,
        age=30,
        role=user_role,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.flush()  # Get user.user_id without commit yet
    
    # Create auth credential
    auth_cred = AuthCredential(
        user_id=user.user_id,
        hashed_password=AuthService.hash_password(password)
    )
    db.add(auth_cred)
    db.commit()
    db.refresh(user)
    
    return user


# =============================================================================
# GET_TOKEN - Login and return JWT access token
# =============================================================================

def get_token(
    client,
    email: str,
    password: str = "TestPass123"
) -> str:
    """
    POST to /api/v1/login and return access_token.
    
    Args:
        client: FastAPI TestClient
        email: User email (username for login form)
        password: Plain text password
    
    Returns:
        JWT access_token string
    
    Raises:
        AssertionError: If login returns non-200 status
    
    # WHY:
    # Every test needs Bearer tokens for auth. This centralizes the login
    # logic so tests don't repeat client.post + assertions.
    """
    response = client.post(
        "/api/v1/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


# =============================================================================
# MAKE_VITAL - Create vital sign record
# =============================================================================

def make_vital(
    db: Session,
    user_id: int,
    heart_rate: int = 75,
    spo2: int = 98,
    systolic_bp: int = 120,
    diastolic_bp: int = 80,
    minutes_ago: int = 5
) -> VitalSignRecord:
    """
    Create a VitalSignRecord with current timestamp minus offset.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID (foreign key)
        heart_rate: BPM, default 75
        spo2: Oxygen saturation %, default 98
        systolic_bp: Systolic blood pressure, default 120
        diastolic_bp: Diastolic blood pressure, default 80
        minutes_ago: Age of reading in minutes (default 5 = 5 min ago)
    
    Returns:
        VitalSignRecord model instance
    """
    vital = VitalSignRecord(
        user_id=user_id,
        heart_rate=heart_rate,
        spo2=spo2,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        is_valid=True,
        confidence_score=1.0
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    
    return vital


# =============================================================================
# MAKE_ACTIVITY - Create activity session
# =============================================================================

def make_activity(
    db: Session,
    user_id: int,
    activity_type: str = "walking",
    avg_hr: int = 80,
    peak_hr: int = 110,
    min_hr: int = 65,
    avg_spo2: int = 97,
    duration: int = 30,
    completed: bool = True
) -> ActivitySession:
    """
    Create an ActivitySession record.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID (foreign key)
        activity_type: Activity type (walking/running/cycling/etc.), default "walking"
        avg_hr: Average heart rate, default 80
        peak_hr: Peak heart rate, default 110
        min_hr: Minimum heart rate, default 65
        avg_spo2: Average SpO2 %, default 97
        duration: Duration in minutes, default 30
        completed: Whether session is completed (has end_time), default True
    
    Returns:
        ActivitySession model instance
    """
    activity = ActivitySession(
        user_id=user_id,
        activity_type=activity_type,
        avg_heart_rate=avg_hr,
        peak_heart_rate=peak_hr,
        min_heart_rate=min_hr,
        avg_spo2=avg_spo2,
        duration_minutes=duration,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=duration),
        end_time=datetime.now(timezone.utc) if completed else None
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return activity


# =============================================================================
# MAKE_ALERT - Create alert record
# =============================================================================

def make_alert(
    db: Session,
    user_id: int,
    alert_type: str = "high_heart_rate",
    severity: str = "critical",
    acknowledged: bool = False
) -> Alert:
    """
    Create an Alert record.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID (foreign key)
        alert_type: Alert type (high_heart_rate/low_spo2/etc.), default "high_heart_rate"
        severity: Severity level (info/warning/critical), default "critical"
        acknowledged: Whether alert has been acknowledged, default False
    
    Returns:
        Alert model instance
    """
    alert = Alert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        title=f"Alert: {alert_type.replace('_', ' ').title()}",
        message=f"A {severity.lower()} alert was triggered.",
        acknowledged=acknowledged,
        created_at=datetime.now(timezone.utc)
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert


# =============================================================================
# MAKE_RISK_ASSESSMENT - Create risk assessment
# =============================================================================

def make_risk_assessment(
    db: Session,
    user_id: int,
    risk_score: float = 0.25,
    risk_level: str = "low"
) -> RiskAssessment:
    """
    Create a RiskAssessment record.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID (foreign key)
        risk_score: Risk score 0.0-1.0, default 0.25 (low)
        risk_level: Risk level (low/moderate/high), default "low"
    
    Returns:
        RiskAssessment model instance
    """
    assessment = RiskAssessment(
        user_id=user_id,
        risk_score=risk_score,
        risk_level=risk_level,
        assessment_date=datetime.now(timezone.utc),
        assessment_type="vitals_window",
        generated_by="cloud_ai"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    return assessment


# =============================================================================
# MAKE_RECOMMENDATION - Create exercise recommendation
# =============================================================================

def make_recommendation(
    db: Session,
    user_id: int,
    title: str = "Continue Safe Training",
    activity: str = "walking",
    intensity: str = "moderate",
    duration: int = 20
) -> ExerciseRecommendation:
    """
    Create an ExerciseRecommendation record.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID (foreign key)
        title: Recommendation title, default "Continue Safe Training"
        activity: Activity type, default "walking"
        intensity: Intensity level (light/moderate/vigorous), default "moderate"
        duration: Recommended duration in minutes, default 20
    
    Returns:
        ExerciseRecommendation model instance
    """
    recommendation = ExerciseRecommendation(
        user_id=user_id,
        title=title,
        activity_type=activity,
        intensity=intensity,
        duration_minutes=duration,
        created_at=datetime.now(timezone.utc)
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    
    return recommendation
