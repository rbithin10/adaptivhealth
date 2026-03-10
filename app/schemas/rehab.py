"""
Pydantic schemas for cardiac rehab program endpoints.

Covers program responses, session plans, session completion requests,
and progress summaries.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# =============================================================================
# Session Plan (nested inside program response)
# =============================================================================

class SessionPlanResponse(BaseModel):
    """Next session the patient should complete this week."""
    activity_type: str = Field(..., description="e.g. walking, stretching, cycling, yoga")  # What exercise to do
    target_duration_minutes: int = Field(..., description="How long the session should last")  # Minutes of exercise planned
    target_hr_min: int = Field(..., description="Lower bound of target HR range")  # Minimum safe heart rate during exercise
    target_hr_max: int = Field(..., description="Upper bound of target HR range")  # Maximum safe heart rate during exercise
    week_number: int  # Which week of the program this session is in
    session_number: int = Field(..., description="Which session in this week (1-based)")  # Session number within the week
    description: str = Field(..., description="Short human-friendly instruction")  # Plain English instructions for the patient


# =============================================================================
# Progress Summary
# =============================================================================

class ProgressResponse(BaseModel):
    """Progression status returned after completing a session or on request."""
    current_week: int  # Which week the patient is currently on
    total_weeks: Optional[int] = Field(None, description="4 for phase_2, null for phase_3")  # Total weeks in the program (null means ongoing)
    sessions_completed_this_week: int  # How many sessions done this week so far
    sessions_required_this_week: int  # How many sessions needed to progress
    overall_sessions_completed: int  # Total sessions done since the program started
    can_advance: bool = Field(..., description="True when week progression gate is met")  # Can the patient move to the next week?
    program_status: str = Field(..., description="active / completed / paused")  # Is the program running, finished, or on hold?


# =============================================================================
# Full Program Response
# =============================================================================

class RehabProgramResponse(BaseModel):
    """Full program state with embedded session plan and progress."""
    program_id: int
    user_id: int
    program_type: str
    current_week: int
    current_session_in_week: int
    status: str
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    current_session_plan: Optional[SessionPlanResponse] = None
    progress_summary: Optional[ProgressResponse] = None

    class Config:
        from_attributes = True


# =============================================================================
# Complete Session Request
# =============================================================================

class CompleteSessionRequest(BaseModel):
    """Payload sent after a patient finishes a rehab session."""
    actual_duration_minutes: int = Field(..., ge=1, description="How many minutes the patient exercised")  # Actual time spent exercising
    avg_heart_rate: Optional[int] = Field(None, ge=30, le=250, description="Average HR during session")  # Average heart rate during the workout
    peak_heart_rate: Optional[int] = Field(None, ge=30, le=250, description="Peak HR during session")  # Highest heart rate during the workout
    activity_type: str = Field(..., description="walking, stretching, cycling, yoga")  # What type of exercise was done
