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
    """Base schema for activity sessions."""
    activity_type: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    peak_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_spo2: Optional[int] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[int] = None
    recovery_time_minutes: Optional[int] = None
    feeling_before: Optional[str] = None
    feeling_after: Optional[str] = None
    user_notes: Optional[str] = None


class ActivitySessionCreate(ActivitySessionBase):
    """Schema for creating a new activity session."""
    start_time: datetime
    end_time: Optional[datetime] = None


class ActivitySessionUpdate(BaseModel):
    """Schema for updating an activity session."""
    end_time: Optional[datetime] = None
    activity_type: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    peak_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_spo2: Optional[int] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[int] = None
    recovery_time_minutes: Optional[int] = None
    status: Optional[str] = None
    feeling_after: Optional[str] = None
    user_notes: Optional[str] = None


class ActivitySessionResponse(ActivitySessionBase):
    """Schema for activity session responses."""
    session_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    risk_score: Optional[float] = None
    status: Optional[str] = None
    baseline_heart_rate: Optional[int] = None
    recovery_score: Optional[float] = None
    alerts_triggered: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
