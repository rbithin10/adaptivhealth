"""
Alert API endpoints.

Manages health alerts and warnings for cardiac patients.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
# HELPER FUNCTIONS
#   - check_duplicate_alert............ Line 32  (Prevent alert spam)
#
# ENDPOINTS - PATIENT (own alerts)
#   - GET /alerts...................... Line 70  (List own alerts)
#   - PATCH /alerts/{id}/acknowledge... Line 110 (Mark alert seen)
#   - PATCH /alerts/{id}/resolve....... Line 143 (Resolve alert)
#   - POST /alerts..................... Line 193 (Create alert - internal)
#
# ENDPOINTS - CLINICIAN (patient alerts)
#   - GET /alerts/user/{id}............ Line 235 (List patient alerts)
#   - GET /alerts/stats................ Line 285 (Alert statistics)
#
# BUSINESS CONTEXT:
# - Alerts auto-create when vitals exceed thresholds
# - Mobile app shows alert badge, push notifications
# - Clinicians monitor patient alerts in dashboard
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import Optional
from datetime import datetime, timedelta, timezone
import logging

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse
)
from app.api.auth import get_current_user, get_current_doctor_user, check_clinician_phi_access

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Alert Deduplication Helper
# =============================================================================

def check_duplicate_alert(
    db: Session,
    user_id: int,
    alert_type: str,
    window_minutes: int = 5
) -> bool:
    """
    Check if a similar alert was created recently (within window_minutes).
    
    Prevents alert spam from triggering multiple notifications for the same issue.
    
    Args:
        db: Database session
        user_id: User ID
        alert_type: Type of alert to check
        window_minutes: Time window in minutes (default 5)
        
    Returns:
        True if duplicate exists, False otherwise
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    
    existing = db.query(Alert).filter(
        and_(
            Alert.user_id == user_id,
            Alert.alert_type == alert_type,
            Alert.created_at >= since
        )
    ).first()
    
    return existing is not None


# =============================================================================
# Patient Endpoints
# =============================================================================

# =============================================
# GET_MY_ALERTS - List user's health alerts
# Used by: Mobile app alerts screen, badge count
# Returns: AlertListResponse with pagination
# Roles: ALL authenticated users (own alerts)
# =============================================
@router.get("/alerts", response_model=AlertListResponse)
async def get_my_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    acknowledged: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's alerts.
    
    Returns paginated list of alerts with optional filtering.
    """
    query = db.query(Alert).filter(Alert.user_id == current_user.user_id)
    
    # Apply filters
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    # Count total for pagination
    total = query.count()
    
    # Get paginated results
    alerts = query.order_by(desc(Alert.created_at))\
                  .offset((page - 1) * per_page)\
                  .limit(per_page)\
                  .all()
    
    return AlertListResponse(
        alerts=[AlertResponse.model_validate(alert) for alert in alerts],
        total=total,
        page=page,
        per_page=per_page
    )


# =============================================
# ACKNOWLEDGE_ALERT - Mark alert as read
# Used by: Mobile app alert dismiss button
# Returns: AlertResponse with updated status
# Roles: ALL authenticated users (own alerts)
# =============================================
@router.patch("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    Marks the alert as read/acknowledged by the user.
    """
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.user_id == current_user.user_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.acknowledged = True
    alert.updated_at = datetime.now(timezone.utc)  # type: ignore
    
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert {alert_id} acknowledged by user {current_user.user_id}")
    
    return alert


# =============================================
# RESOLVE_ALERT - Close alert with resolution
# Used by: Mobile app alert detail, clinician review
# Returns: AlertResponse with resolution details
# Roles: ALL authenticated users (own alerts)
# =============================================
@router.patch("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    update_data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve an alert with optional notes.
    
    Marks alert as resolved and records resolution details.
    """
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.user_id == current_user.user_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update fields
    if update_data.acknowledged is not None:
        alert.acknowledged = update_data.acknowledged
    
    if update_data.resolved_at:
        alert.resolved_at = update_data.resolved_at
    else:
        alert.resolved_at = datetime.now(timezone.utc)
    
    if update_data.resolved_by:
        alert.resolved_by = str(update_data.resolved_by)  # type: ignore
    else:
        alert.resolved_by = str(current_user.user_id)  # type: ignore
    
    if update_data.resolution_notes:
        alert.resolution_notes = update_data.resolution_notes
    
    alert.updated_at = datetime.now(timezone.utc)  # type: ignore
    
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert {alert_id} resolved by user {current_user.user_id}")
    
    return alert


# =============================================
# CREATE_ALERT - Generate new health alert
# Used by: vital_signs.py auto-alerts, internal services
# Returns: AlertResponse with new alert
# Roles: INTERNAL (with deduplication protection)
# =============================================
@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new alert.
    
    Includes deduplication to prevent alert spam.
    """
    # Check for duplicate within 5-minute window
    if check_duplicate_alert(db, alert_data.user_id, alert_data.alert_type):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Similar alert already exists within the last 5 minutes"
        )
    
    alert = Alert(
        user_id=alert_data.user_id,
        alert_type=alert_data.alert_type,
        severity=alert_data.severity,
        message=alert_data.message,
        title=alert_data.title,
        action_required=alert_data.action_required,
        trigger_value=alert_data.trigger_value,
        threshold_value=alert_data.threshold_value
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert created: {alert.alert_id} for user {alert_data.user_id}")
    
    return alert


# =============================================================================
# Clinician Endpoints
# =============================================================================

# =============================================
# GET_USER_ALERTS - View patient's alerts
# Used by: Clinician dashboard patient detail
# Returns: AlertListResponse with pagination
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/alerts/user/{user_id}", response_model=AlertListResponse)
async def get_user_alerts(
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    acknowledged: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get alerts for a specific user.
    
    Clinician/Admin access only.
    """
    # Check consent
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    check_clinician_phi_access(current_user, patient)

    query = db.query(Alert).filter(Alert.user_id == user_id)
    
    # Apply filters
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    # Count total for pagination
    total = query.count()
    
    # Get paginated results
    alerts = query.order_by(desc(Alert.created_at))\
                  .offset((page - 1) * per_page)\
                  .limit(per_page)\
                  .all()
    
    return AlertListResponse(
        alerts=[AlertResponse.model_validate(alert) for alert in alerts],
        total=total,
        page=page,
        per_page=per_page
    )


# =============================================
# GET_ALERT_STATISTICS - Alert metrics dashboard
# Used by: Clinician/admin dashboard stats cards
# Returns: Severity breakdown, unacknowledged count
# Roles: DOCTOR, ADMIN
# =============================================
@router.get("/alerts/stats")
async def get_alert_statistics(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get alert statistics across all users.
    
    Admin/Clinician access only. Used for dashboard metrics.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Count alerts by severity
    from sqlalchemy import func
    severity_counts = db.query(
        Alert.severity,
        func.count(Alert.alert_id).label('count')
    ).filter(
        Alert.created_at >= since
    ).group_by(Alert.severity).all()
    
    # Count unacknowledged alerts
    unacknowledged = db.query(func.count(Alert.alert_id)).filter(
        and_(
            Alert.created_at >= since,
            Alert.acknowledged == False
        )
    ).scalar()
    
    return {
        "period_days": days,
        "severity_breakdown": {
            severity: count for severity, count in severity_counts
        },
        "unacknowledged_count": unacknowledged,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
