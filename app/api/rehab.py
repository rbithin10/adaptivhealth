"""
Cardiac Rehab Program API endpoints.

Structured rehabilitation programs with session tracking and
progression gating for Phase II and Phase III cardiac patients.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 18
#
# ENDPOINTS
#   - GET  /rehab/current-program...... Line 35  (Get or create program + plan)
#   - POST /rehab/complete-session..... Line 75  (Record a completed session)
#   - GET  /rehab/progress............. Line 110 (Progress summary only)
#
# BUSINESS CONTEXT:
# - Patients see their next session plan and weekly progress
# - Progression gates ensure safe vitals before advancing weeks
# - Phase II (4-week light) and Phase III (maintenance) templates
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user_session_or_bearer
from app.schemas.rehab import (
    RehabProgramResponse,
    CompleteSessionRequest,
    ProgressResponse,
)
from app.services.rehab_service import (
    get_or_create_program,
    get_current_session_plan,
    complete_session,
    get_progress,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================
# GET CURRENT PROGRAM + SESSION PLAN
# Used by: Mobile rehab program screen, home screen card
# Returns: RehabProgramResponse with nested plan & progress
# Roles: ALL authenticated users
# =============================================
@router.get("/rehab/current-program", response_model=RehabProgramResponse)
def get_current_rehab_program(
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """
    Retrieve the authenticated user's active rehab program.

    Auto-creates a program if the user has a rehab_phase set but no
    active program yet. Returns 404 when user is not in rehab.
    """
    program = get_or_create_program(current_user, db)  # Find or create a rehab program for this patient
    if not program:  # Patient hasn't been assigned to a rehab phase yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rehab program active. Update your rehab phase in Profile.",
        )

    session_plan = get_current_session_plan(program, current_user)  # Build today's exercise plan
    progress = get_progress(program, db)  # Calculate overall progress stats

    return RehabProgramResponse(  # Send back the full program with plan and progress
        program_id=program.program_id,
        user_id=program.user_id,
        program_type=program.program_type,
        current_week=program.current_week,
        current_session_in_week=program.current_session_in_week,
        status=program.status,
        started_at=program.started_at,
        updated_at=program.updated_at,
        current_session_plan=session_plan,
        progress_summary=progress,
    )


# =============================================
# COMPLETE A SESSION
# Used by: Mobile app after workout completes
# Returns: ProgressResponse with updated stats
# Roles: ALL authenticated users
# =============================================
@router.post("/rehab/complete-session", response_model=ProgressResponse)
def complete_rehab_session(
    request: CompleteSessionRequest,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """
    Record a completed rehab session and evaluate week progression.

    Returns updated progress, including whether the patient advanced
    to the next week.
    """
    program = get_or_create_program(current_user, db)  # Find the user's active rehab program
    if not program:  # No program exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rehab program active.",
        )
    if program.status != "active":  # Can't log sessions for a paused or completed program
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Program is '{program.status}', cannot log sessions.",
        )

    progress = complete_session(program, request, current_user, db)  # Record the session and check if the patient can advance
    return progress


# =============================================
# GET PROGRESS ONLY
# Used by: Mobile home screen card, dashboard
# Returns: ProgressResponse
# Roles: ALL authenticated users
# =============================================
@router.get("/rehab/progress", response_model=ProgressResponse)
def get_rehab_progress(
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """
    Return the current progress summary without modifying any state.
    """
    program = get_or_create_program(current_user, db)  # Find the user's active rehab program
    if not program:  # No program on record
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rehab program active.",
        )

    return get_progress(program, db)  # Return progress stats without changing anything
