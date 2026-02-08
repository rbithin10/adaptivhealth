"""
Activity Session API endpoints.

Manages workout/activity sessions for cardiac patients.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.schemas.activity import (
    ActivitySessionCreate,
    ActivitySessionUpdate,
    ActivitySessionResponse
)
from app.api.auth import get_current_user, get_current_doctor_user

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Patient Endpoints
# =============================================================================

@router.post("/activities/start", response_model=ActivitySessionResponse)
async def start_activity_session(
    activity_data: ActivitySessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new activity session.
    
    Records the start time and initial parameters for a workout.
    """
    activity = ActivitySession(
        user_id=current_user.user_id,
        start_time=activity_data.start_time or datetime.now(timezone.utc),
        end_time=activity_data.end_time,
        activity_type=activity_data.activity_type,
        avg_heart_rate=activity_data.avg_heart_rate,
        peak_heart_rate=activity_data.peak_heart_rate,
        min_heart_rate=activity_data.min_heart_rate,
        avg_spo2=activity_data.avg_spo2,
        duration_minutes=activity_data.duration_minutes,
        calories_burned=activity_data.calories_burned,
        recovery_time_minutes=activity_data.recovery_time_minutes,
        feeling_before=activity_data.feeling_before,
        user_notes=activity_data.user_notes,
        status="active"
    )
    
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    logger.info(f"Activity session started: {activity.session_id} for user {current_user.user_id}")
    
    return activity


@router.post("/activities/end/{session_id}", response_model=ActivitySessionResponse)
async def end_activity_session(
    session_id: int,
    activity_data: ActivitySessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End an activity session and record final metrics.
    
    Updates the session with end time, final heart rates, and completion status.
    """
    activity = db.query(ActivitySession).filter(
        ActivitySession.session_id == session_id,
        ActivitySession.user_id == current_user.user_id
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity session not found"
        )
    
    # Update fields
    update_data = activity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(activity, field):
            setattr(activity, field, value)
    
    # Set end time if not provided
    if activity.end_time is None:
        activity.end_time = datetime.now(timezone.utc)  # type: ignore
    
    # Mark as completed
    if activity.status == "active":
        activity.status = "completed"  # type: ignore
    
    # Calculate duration if not set
    if activity.start_time and activity.end_time and activity.duration_minutes is None:
        delta = activity.end_time - activity.start_time  # type: ignore
        activity.duration_minutes = int(delta.total_seconds() / 60)  # type: ignore
    
    db.commit()
    db.refresh(activity)
    
    logger.info(f"Activity session ended: {activity.session_id} for user {current_user.user_id}")
    
    return activity


@router.get("/activities", response_model=list[ActivitySessionResponse])
async def get_my_activities(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's activity history.
    
    Returns list of all activity sessions for the current user.
    """
    query = db.query(ActivitySession).filter(
        ActivitySession.user_id == current_user.user_id
    )
    
    # Filter by activity type if specified
    if activity_type:
        query = query.filter(ActivitySession.activity_type == activity_type)
    
    # Order by most recent first
    activities = query.order_by(desc(ActivitySession.start_time))\
                     .limit(limit)\
                     .offset(offset)\
                     .all()
    
    return activities


# =============================================================================
# Clinician Endpoints
# =============================================================================

@router.get("/activities/user/{user_id}", response_model=list[ActivitySessionResponse])
async def get_user_activities(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get activity history for a specific user.
    
    Clinician/Admin access only.
    """
    activities = db.query(ActivitySession).filter(
        ActivitySession.user_id == user_id
    ).order_by(desc(ActivitySession.start_time))\
     .limit(limit)\
     .offset(offset)\
     .all()
    
    return activities


@router.get("/activities/{session_id}", response_model=ActivitySessionResponse)
async def get_activity_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific activity session.
    
    Users can only access their own sessions.
    """
    activity = db.query(ActivitySession).filter(
        ActivitySession.session_id == session_id
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity session not found"
        )
    
    # Check if user owns this activity (unless they're a clinician/admin)
    from app.models.user import UserRole
    if current_user.role not in [UserRole.CLINICIAN, UserRole.ADMIN]:
        if activity.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return activity
