"""
Activity Session Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - ActivityType..................... Line 20  (walking, running, etc.)
#   - ActivityPhase.................... Line 35  (warm_up, active, etc.)
#
# SCHEMAS
#   - ActivitySessionBase.............. Line 45  (Common fields)
#   - ActivitySessionCreate............ Line 55  (Start session input)
#   - ActivitySessionUpdate............ Line 65  (End session input)
#   - ActivitySessionResponse.......... Line 75  (Full session output)
#
# BUSINESS CONTEXT:
# - Workout session tracking from mobile
# - Feeds ML risk prediction
# =============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """Types of activities/exercises."""
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH_TRAINING = "strength_training"
    YOGA = "yoga"
    STRETCHING = "stretching"
    OTHER = "other"


class ActivityPhase(str, Enum):
    """Phases of activity."""
    WARM_UP = "warm_up"
    ACTIVE = "active"
    COOL_DOWN = "cool_down"
    RECOVERY = "recovery"


class ActivitySessionBase(BaseModel):
    """Shared fields for all activity session operations (create, update, view)."""
    activity_type: Optional[str] = None        # What kind of exercise (walking, cycling, yoga, etc.)
    avg_heart_rate: Optional[int] = None       # Average heart rate during the workout (BPM)
    peak_heart_rate: Optional[int] = None      # Highest heart rate reached during the workout
    min_heart_rate: Optional[int] = None       # Lowest heart rate during the workout
    avg_spo2: Optional[int] = None             # Average blood oxygen level during exercise
    duration_minutes: Optional[int] = None     # How long the workout lasted in minutes
    calories_burned: Optional[int] = None      # Estimated calories burned during the session
    recovery_time_minutes: Optional[int] = None  # Minutes until heart rate returned to normal
    feeling_before: Optional[str] = None       # How the patient felt before starting (e.g. "good", "tired")
    feeling_after: Optional[str] = None        # How the patient felt after finishing
    user_notes: Optional[str] = None           # Any free-text notes the patient wants to record


class ActivitySessionCreate(ActivitySessionBase):
    """Data the patient sends when starting a new workout session."""
    start_time: datetime                       # When the workout started
    end_time: Optional[datetime] = None        # When it ended (can be set later)


class ActivitySessionUpdate(BaseModel):
    """Data the patient sends when ending or updating a workout session."""
    end_time: Optional[datetime] = None        # When the workout finished
    activity_type: Optional[str] = None        # Can change the exercise type if needed
    avg_heart_rate: Optional[int] = None       # Final average heart rate for the session
    peak_heart_rate: Optional[int] = None      # Final peak heart rate
    min_heart_rate: Optional[int] = None       # Final minimum heart rate
    avg_spo2: Optional[int] = None             # Final average blood oxygen
    duration_minutes: Optional[int] = None     # Total duration in minutes
    calories_burned: Optional[int] = None      # Final calorie count
    recovery_time_minutes: Optional[int] = None  # Time to recover after exercise
    status: Optional[str] = None               # Session status (e.g. "completed", "cancelled")
    feeling_after: Optional[str] = None        # How the patient felt after the workout
    user_notes: Optional[str] = None           # Any free-text notes to add


class ActivitySessionResponse(ActivitySessionBase):
    """What the API returns when showing a workout session."""
    session_id: int                            # Unique ID for this workout session
    user_id: int                               # Which patient this session belongs to
    start_time: datetime                       # When the workout started
    end_time: Optional[datetime] = None        # When it ended (if completed)
    risk_score: Optional[float] = None         # AI-calculated cardiac risk during this session (0.0 to 1.0)
    status: Optional[str] = None               # Current status (active, completed, cancelled)
    baseline_heart_rate: Optional[int] = None  # Patient's resting heart rate for comparison
    recovery_score: Optional[float] = None     # How well the patient recovered after exercise
    alerts_triggered: Optional[int] = None     # Number of health alerts triggered during this session
    created_at: Optional[datetime] = None      # When this record was first created
    updated_at: Optional[datetime] = None      # When this record was last modified

    class Config:
        from_attributes = True
