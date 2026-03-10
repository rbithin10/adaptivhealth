"""
Cardiac Rehab Program Service.

Contains hardcoded program templates, session planning, completion logic,
and the progression gating algorithm.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# TEMPLATES............................ Line 30
# get_or_create_program().............. Line 95
# get_current_session_plan()........... Line 130
# complete_session()................... Line 175
# get_progress()...................... Line 260
# =============================================================================
"""

import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.models.rehab import RehabProgram, RehabSessionLog
from app.models.user import User
from app.schemas.rehab import (
    SessionPlanResponse,
    ProgressResponse,
    CompleteSessionRequest,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Program Templates (hardcoded — not stored in DB)
# =============================================================================

PHASE_2_LIGHT: List[Dict[str, Any]] = [
    # Week 1: 3 sessions/week, walking, 10 min, 50-60% max HR
    {
        "week": 1,
        "sessions_required": 3,
        "activities": ["walking"],
        "duration_minutes": 10,
        "hr_pct_low": 0.50,
        "hr_pct_high": 0.60,
        "description": "Gentle walking — build a daily habit. Keep effort easy and conversational.",
    },
    # Week 2: 3 sessions/week, walking, 15 min, 50-60% max HR
    {
        "week": 2,
        "sessions_required": 3,
        "activities": ["walking"],
        "duration_minutes": 15,
        "hr_pct_low": 0.50,
        "hr_pct_high": 0.60,
        "description": "Extend your walk to 15 minutes. Maintain a comfortable pace.",
    },
    # Week 3: 4 sessions/week, walking + stretching, 20 min, 55-65% max HR
    {
        "week": 3,
        "sessions_required": 4,
        "activities": ["walking", "stretching"],
        "duration_minutes": 20,
        "hr_pct_low": 0.55,
        "hr_pct_high": 0.65,
        "description": "Add light stretching. Aim for 20-minute sessions with a brisk pace.",
    },
    # Week 4: 4 sessions/week, walking + light resistance, 25 min, 55-65% max HR
    {
        "week": 4,
        "sessions_required": 4,
        "activities": ["walking", "stretching"],
        "duration_minutes": 25,
        "hr_pct_low": 0.55,
        "hr_pct_high": 0.65,
        "description": "Final week — 25-minute sessions with light resistance bands allowed.",
    },
]

PHASE_3_MAINTENANCE: Dict[str, Any] = {
    "sessions_required": 3,
    "activities": ["walking", "cycling", "yoga"],
    "duration_minutes": 30,
    "hr_pct_low": 0.60,
    "hr_pct_high": 0.70,
    "description": "Maintenance — mix of walking, cycling, and yoga. Stay consistent.",
}

# Map from user.rehab_phase to program_type
_PHASE_TO_PROGRAM = {
    "phase_2": "phase_2_light",
    "phase_3": "phase_3_maintenance",
}


# =============================================================================
# Service Functions
# =============================================================================

def get_or_create_program(user: User, db: Session) -> Optional[RehabProgram]:
    """
    Return the user's active rehab program, creating one if needed.

    Returns None when user.rehab_phase is 'not_in_rehab' or missing.
    """
    rehab_phase = getattr(user, "rehab_phase", None) or "not_in_rehab"
    if rehab_phase == "not_in_rehab":
        return None

    # Look for existing active program
    program = (
        db.query(RehabProgram)
        .filter(RehabProgram.user_id == user.user_id, RehabProgram.status == "active")
        .first()
    )
    if program:
        return program

    # Determine program type from phase
    program_type = _PHASE_TO_PROGRAM.get(rehab_phase)
    if not program_type:
        logger.warning(f"Unknown rehab_phase '{rehab_phase}' for user {user.user_id}")
        return None

    program = RehabProgram(
        user_id=user.user_id,
        program_type=program_type,
        current_week=1,
        current_session_in_week=0,
        status="active",
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    logger.info(f"Created rehab program '{program_type}' for user {user.user_id}")
    return program


def _get_week_template(program: RehabProgram) -> Dict[str, Any]:
    """Return the template dict for the program's current week."""
    if program.program_type == "phase_2_light":
        week_idx = min(program.current_week, len(PHASE_2_LIGHT)) - 1
        return PHASE_2_LIGHT[week_idx]
    # phase_3_maintenance — same template every week
    return PHASE_3_MAINTENANCE


def get_current_session_plan(program: RehabProgram, user: User) -> SessionPlanResponse:
    """
    Build the plan for the next session based on the current week template.
    """
    template = _get_week_template(program)  # Get this week's exercise plan
    max_hr = user.max_safe_hr or user.calculate_max_heart_rate()  # Get the patient's max safe heart rate

    # Calculate the target heart rate range for this week
    target_hr_min = int(max_hr * template["hr_pct_low"])  # Lower bound of safe HR during exercise
    target_hr_max = int(max_hr * template["hr_pct_high"])  # Upper bound of safe HR during exercise

    # Rotate through available activities (e.g., walking, stretching, cycling)
    activities = template["activities"]
    activity_idx = program.current_session_in_week % len(activities)  # Pick the next activity in rotation
    activity_type = activities[activity_idx]

    session_number = program.current_session_in_week + 1  # Next session number (1-based)

    return SessionPlanResponse(
        activity_type=activity_type,
        target_duration_minutes=template["duration_minutes"],
        target_hr_min=target_hr_min,
        target_hr_max=target_hr_max,
        week_number=program.current_week,
        session_number=session_number,
        description=template["description"],
    )


def complete_session(
    program: RehabProgram,
    session_data: CompleteSessionRequest,
    user: User,
    db: Session,
) -> ProgressResponse:
    """
    Record a completed session and evaluate the progression gate.

    Progression gate:
    - All required sessions for the week must be completed.
    - >= 80% of this week's sessions must have vitals_in_safe_range == True.
    If both conditions are met the program advances to the next week.
    """
    template = _get_week_template(program)  # Get the plan for this week
    max_hr = user.max_safe_hr or user.calculate_max_heart_rate()  # Patient's maximum safe heart rate
    hr_ceiling = int(max_hr * template["hr_pct_high"])  # The highest HR they should reach during exercise

    # Check if the patient's peak heart rate stayed within the safe zone
    safe = True
    if session_data.peak_heart_rate is not None:
        safe = session_data.peak_heart_rate <= hr_ceiling  # Was peak HR below the ceiling?

    session_number = program.current_session_in_week + 1  # This session's number

    # Record what happened during this session in the database
    log_entry = RehabSessionLog(
        program_id=program.program_id,
        user_id=user.user_id,
        week_number=program.current_week,
        session_number=session_number,
        activity_type=session_data.activity_type,
        target_duration_minutes=template["duration_minutes"],
        actual_duration_minutes=session_data.actual_duration_minutes,
        avg_heart_rate=session_data.avg_heart_rate,
        peak_heart_rate=session_data.peak_heart_rate,
        vitals_in_safe_range=safe,
    )
    db.add(log_entry)

    # Update how many sessions they've done this week
    program.current_session_in_week = session_number
    sessions_required = template["sessions_required"]  # How many sessions needed to advance

    # Progression gate: check if the patient is ready to move to the next week
    advanced = False
    if program.current_session_in_week >= sessions_required:  # Have they done enough sessions?
        # Count how many sessions this week had safe vitals
        week_logs = (
            db.query(RehabSessionLog)
            .filter(
                RehabSessionLog.program_id == program.program_id,
                RehabSessionLog.week_number == program.current_week,
            )
            .all()
        )
        all_logs = list(week_logs) + [log_entry]  # Include the current session too
        safe_count = sum(1 for lg in all_logs if lg.vitals_in_safe_range)  # How many were safe
        safe_pct = safe_count / len(all_logs) if all_logs else 0  # Percentage of safe sessions

        if safe_pct >= 0.80:  # At least 80% of sessions must have been safe to advance
            advanced = True
            program.current_session_in_week = 0  # Reset session counter for the new week
            program.current_week += 1  # Move to the next week

            # Check if the program is complete (Phase 2 has a fixed 4-week duration)
            if program.program_type == "phase_2_light" and program.current_week > len(PHASE_2_LIGHT):
                program.status = "completed"  # Program finished!
                logger.info(f"Rehab program completed for user {user.user_id}")
            elif program.program_type == "phase_3_maintenance":
                program.current_week = 1  # Maintenance loops back — start over

    db.commit()
    db.refresh(program)

    return get_progress(program, db)


def get_progress(program: RehabProgram, db: Session) -> ProgressResponse:
    """Build a progress summary for the given program."""
    template = _get_week_template(program)
    sessions_required = template["sessions_required"]

    total_sessions = (
        db.query(RehabSessionLog)
        .filter(RehabSessionLog.program_id == program.program_id)
        .count()
    )

    total_weeks = len(PHASE_2_LIGHT) if program.program_type == "phase_2_light" else None

    # Determine can_advance: all required sessions done + >= 80% safe
    can_advance = False
    if program.current_session_in_week >= sessions_required:
        week_logs = (
            db.query(RehabSessionLog)
            .filter(
                RehabSessionLog.program_id == program.program_id,
                RehabSessionLog.week_number == program.current_week,
            )
            .all()
        )
        if week_logs:
            safe_pct = sum(1 for lg in week_logs if lg.vitals_in_safe_range) / len(week_logs)
            can_advance = safe_pct >= 0.80

    return ProgressResponse(
        current_week=program.current_week,
        total_weeks=total_weeks,
        sessions_completed_this_week=program.current_session_in_week,
        sessions_required_this_week=sessions_required,
        overall_sessions_completed=total_sessions,
        can_advance=can_advance,
        program_status=program.status,
    )
