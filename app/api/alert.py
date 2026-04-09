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

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
# StreamingResponse lets us send real-time updates to the dashboard via SSE
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
# desc sorts results newest first; and_ combines filter conditions; func lets us count/aggregate
from sqlalchemy import desc, and_, or_, func
from typing import Optional
from datetime import datetime, timedelta, timezone
# asyncio lets us run background loops for real-time streaming
import asyncio
import json
import logging

# Database session provider for each request
from app.database import get_db
# User model to look up patient and clinician accounts
from app.models.user import User
from app.models.user import UserRole
# Alert model represents a health warning stored in the database
from app.models.alert import Alert
# Data shapes for creating, updating, and returning alert information
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse
)
# Authentication helpers to verify who is making the request
from app.api.auth import (
    get_current_user_session_or_bearer,
    get_current_doctor_user_session_or_bearer,
    get_current_user_from_session_cookie,
    check_clinician_phi_access,
    auth_service,
)

# Set up a logger for this file so we can track alert-related events
logger = logging.getLogger(__name__)
# Create a router to group all alert-related API endpoints together
router = APIRouter()


def _get_doctor_user_from_token_query(token: str, db: Session) -> User:
    """Check the login token passed as a URL parameter and make sure the caller is a clinician or admin.
    This is needed for the real-time SSE stream where tokens come via query string instead of headers."""
    # Decode the login token to read who the user is
    payload = auth_service.decode_token(token)

    # Reject if the token is expired, malformed, or not an access token
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Pull the user ID from the token data
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Look up the user in the database
    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Block deactivated accounts from accessing the stream
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Only clinicians and admins are allowed to see the alert stream
    if user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinician access required",
        )

    return user


def _compute_alert_snapshot(db: Session, days: int) -> dict:
    """Build a summary of alert statistics for the dashboard — used by both the REST endpoint and SSE stream."""
    # Only look at alerts from the last N days
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Count only active alerts (not resolved) within the requested period.
    active_filter = and_(
        Alert.created_at >= since,
        or_(Alert.is_resolved == False, Alert.is_resolved.is_(None)),
        Alert.resolved_at.is_(None),
    )

    # Count how many active alerts exist at each severity level (critical, warning, etc.)
    severity_counts = db.query(
        Alert.severity,
        func.count(Alert.alert_id).label("count")
    ).filter(
        active_filter
    ).group_by(Alert.severity).all()

    # Count how many active alerts have NOT been acknowledged (still need attention)
    unacknowledged = db.query(func.count(Alert.alert_id)).filter(
        and_(
            active_filter,
            or_(Alert.acknowledged == False, Alert.acknowledged.is_(None)),
        )
    ).scalar()

    # Return the compiled statistics as a dictionary
    return {
        "period_days": days,
        "severity_breakdown": {
            severity: count for severity, count in severity_counts
        },
        "unacknowledged_count": int(unacknowledged or 0),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


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
    alert_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Get current user's alerts.
    
    Returns paginated list of alerts with optional filtering.
    """
    # Start by getting all alerts that belong to the currently logged-in user
    query = db.query(Alert).filter(Alert.user_id == current_user.user_id)
    
    # If the user wants to see only read or unread alerts, filter accordingly
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    
    # If the user wants to see only a specific severity level (e.g. "critical")
    if severity:
        query = query.filter(Alert.severity == severity)

    # If the user wants to see only a specific type of alert (e.g. "high_heart_rate")
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    # Count how many alerts match these filters (needed for pagination info)
    total = query.count()
    
    # Get one page of results, sorted newest first
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
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    Marks the alert as read/acknowledged by the user.
    """
    # Find the alert by its ID
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    # If no matching alert found, tell the user
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Access rules:
    # - Patients can acknowledge only their own alerts.
    # - Clinicians/Admin can acknowledge any alert, but clinicians must have PHI access.
    if current_user.role == UserRole.PATIENT and alert.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only acknowledge your own alerts"
        )

    if current_user.role in [UserRole.CLINICIAN, UserRole.ADMIN]:
        patient = db.query(User).filter(User.user_id == alert.user_id).first()
        if patient:
            check_clinician_phi_access(current_user, patient)

    # Mark the alert as seen/acknowledged so it no longer shows as new
    alert.acknowledged = True
    # Record when the alert was acknowledged
    alert.updated_at = datetime.now(timezone.utc)  # type: ignore
    
    # Save the changes to the database
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
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Resolve an alert with optional notes.
    
    Marks alert as resolved and records resolution details.
    """
    # Find the alert by its ID (any user's alert, since clinicians can resolve any)
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    # Access rules:
    # - Patients can resolve only their own alerts.
    # - Clinicians/Admin can resolve any alert, but clinicians must have PHI access.
    if current_user.role == UserRole.PATIENT and alert.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only resolve your own alerts"
        )

    if current_user.role in [UserRole.CLINICIAN, UserRole.ADMIN]:
        patient = db.query(User).filter(User.user_id == alert.user_id).first()
        if patient:
            check_clinician_phi_access(current_user, patient)
    
    # Resolving an alert implies it has been handled, so default to acknowledged.
    if update_data.acknowledged is not None:
        alert.acknowledged = update_data.acknowledged
    else:
        alert.acknowledged = True

    # Mark this alert as resolved (issue has been addressed)
    alert.is_resolved = True
    
    # Use the provided resolution time, or default to right now
    if update_data.resolved_at:
        alert.resolved_at = update_data.resolved_at
    else:
        alert.resolved_at = datetime.now(timezone.utc)
    
    # Record who resolved this alert (the clinician or admin)
    if update_data.resolved_by:
        alert.resolved_by = str(update_data.resolved_by)  # type: ignore
    else:
        alert.resolved_by = str(current_user.user_id)  # type: ignore
    
    # Save any notes the clinician wrote about how the alert was handled
    if update_data.resolution_notes:
        alert.resolution_notes = update_data.resolution_notes
    
    # Record the last time this alert was modified
    alert.updated_at = datetime.now(timezone.utc)  # type: ignore
    
    # Save all changes to the database
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
    current_user: User = Depends(get_current_user_session_or_bearer),
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
    current_user: User = Depends(get_current_doctor_user_session_or_bearer),
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
    response: Response,
    days: int = Query(1, ge=1, le=90),
    current_user: User = Depends(get_current_doctor_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Get alert statistics across all users.
    
    Admin/Clinician access only. Used for dashboard metrics.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return _compute_alert_snapshot(db, days)


@router.get("/alerts/stream")
async def stream_alert_statistics(
    request: Request,
    token: Optional[str] = Query(None, min_length=1),
    days: int = Query(7, ge=1, le=90),
    poll_seconds: float = Query(1.0, ge=0.5, le=10.0),
    db: Session = Depends(get_db),
):
    """Real-time stream that pushes alert updates to the clinician dashboard instantly.
    Uses Server-Sent Events (SSE) so the browser gets live updates without refreshing."""
    # Support both cookie-based dashboard auth and legacy token-query SSE auth.
    if token:
        user = _get_doctor_user_from_token_query(token, db)
    else:
        user = get_current_user_from_session_cookie(request, db)
        if user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinician access required for alert stream",
            )

    logger.info(f"Alerts SSE connected for clinician/admin user {user.user_id}")

    async def event_generator():
        # Track the last data we sent so we only push when something changes
        last_signature = ""
        # Count loops between heartbeat messages (keeps the connection alive)
        heartbeat_counter = 0

        while True:
            # Stop the stream if the dashboard has closed the connection
            if await request.is_disconnected():
                logger.info(f"Alerts SSE disconnected for user {user.user_id}")
                break

            # Get the latest alert statistics from the database
            snapshot = _compute_alert_snapshot(db, days)

            # Create a fingerprint of the current data to detect changes
            signature_obj = {
                "severity_breakdown": snapshot.get("severity_breakdown", {}),
                "unacknowledged_count": snapshot.get("unacknowledged_count", 0),
            }
            signature = json.dumps(signature_obj, sort_keys=True)

            # Only send data to the dashboard if something has actually changed
            if signature != last_signature:
                last_signature = signature
                payload = {
                    "event": "alerts_update",
                    "data": snapshot,
                }
                # Send the updated alert data as an SSE event
                yield f"event: alerts_update\ndata: {json.dumps(payload)}\n\n"

            # Send a heartbeat every ~15 seconds to keep the connection alive
            heartbeat_counter += 1
            if heartbeat_counter >= int(max(1, round(15.0 / poll_seconds))):
                heartbeat_counter = 0
                yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"

            # Wait before checking again (default 1 second between checks)
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
