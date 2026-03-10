"""
Natural Language API Schemas.

Pydantic models for AI coach natural-language endpoints.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - RiskLevel........................ Line 25
#   - SafetyStatus..................... Line 30
#   - ActivityType..................... Line 35
#   - IntensityLevel................... Line 40
#   - AlertType........................ Line 45
#   - SeverityLevel.................... Line 50
#   - RecommendedAction................ Line 55
#   - TrendDirection................... Line 60
#
# RISK SUMMARY MODELS
#   - KeyFactors....................... Line 70
#   - RiskSummaryResponse.............. Line 80
#
# WORKOUT MODELS
#   - TodaysWorkoutResponse............ Line 95
#
# ALERT MODELS
#   - AlertContext..................... Line 110
#   - AlertExplanationResponse......... Line 120
#
# PROGRESS MODELS
#   - Period........................... Line 135
#   - Trend............................ Line 150
#   - ProgressSummaryResponse.......... Line 160
# =============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, date



# =============================================================================
# ENUMS
# =============================================================================

class RiskLevel(str):
    """How risky the patient's readings are."""
    LOW = "LOW"  # Everything looks normal
    MODERATE = "MODERATE"  # Some readings slightly off
    HIGH = "HIGH"  # Readings suggest potential danger


class SafetyStatus(str):
    """Whether it's safe for the patient to exercise."""
    SAFE = "SAFE"  # Good to go
    CAUTION = "CAUTION"  # Proceed carefully
    UNSAFE = "UNSAFE"  # Should not exercise right now


class ActivityType(str):
    """Types of exercise the patient can do."""
    WALKING = "WALKING"  # Walking at various speeds
    CYCLING = "CYCLING"  # Stationary or outdoor cycling
    OTHER = "OTHER"  # Any other exercise


class IntensityLevel(str):
    """How hard the exercise should be."""
    LIGHT = "LIGHT"  # Easy, gentle effort
    MODERATE = "MODERATE"  # Medium effort
    VIGOROUS = "VIGOROUS"  # High effort, demanding


class AlertType(str):
    """Types of health alerts the system can create."""
    HIGH_HEART_RATE = "HIGH_HEART_RATE"  # Heart rate too fast
    LOW_OXYGEN = "LOW_OXYGEN"  # Blood oxygen too low
    OTHER = "OTHER"  # Any other type of alert


class SeverityLevel(str):
    """How serious an alert is."""
    LOW = "LOW"  # Minor concern
    MEDIUM = "MEDIUM"  # Moderate concern
    HIGH = "HIGH"  # Serious, needs attention


class RecommendedAction(str):
    """What the patient should do based on their readings."""
    CONTINUE = "CONTINUE"  # Keep going, all is well
    SLOW_DOWN = "SLOW_DOWN"  # Reduce effort
    STOP_AND_REST = "STOP_AND_REST"  # Stop exercising and rest
    CONTACT_DOCTOR = "CONTACT_DOCTOR"  # Call your doctor soon
    EMERGENCY = "EMERGENCY"  # Call emergency services now


class TrendDirection(str):
    """Which direction a health metric is trending."""
    IMPROVING = "IMPROVING"  # Getting better
    STABLE = "STABLE"  # Staying the same
    WORSENING = "WORSENING"  # Getting worse


# =============================================================================
# RISK SUMMARY MODELS
# =============================================================================

class KeyFactors(BaseModel):
    """Key health factors for risk summary."""
    avg_heart_rate: int = Field(..., description="Average heart rate in BPM")
    max_heart_rate: int = Field(..., description="Maximum heart rate in BPM")
    avg_spo2: int = Field(..., ge=0, le=100, description="Average SpO2 percentage")
    alert_count: int = Field(..., ge=0, description="Number of alerts triggered")


class RiskSummaryResponse(BaseModel):
    """Natural language risk summary response."""
    user_id: int
    time_window_hours: int = Field(..., ge=1, description="Time window in hours")
    risk_level: Literal["LOW", "MODERATE", "HIGH"]
    risk_score: float = Field(..., ge=0.0, le=1.0)
    key_factors: KeyFactors
    safety_status: Literal["SAFE", "CAUTION", "UNSAFE"]
    nl_summary: str = Field(..., description="Natural language summary")


# =============================================================================
# WORKOUT MODELS
# =============================================================================

class TodaysWorkoutResponse(BaseModel):
    """Natural language workout recommendation response."""
    user_id: int
    date: date
    activity_type: str
    intensity_level: str
    duration_minutes: int = Field(..., ge=1)
    target_hr_min: int = Field(..., ge=40, le=220)
    target_hr_max: int = Field(..., ge=40, le=220)
    risk_level: str
    nl_summary: str = Field(..., description="Natural language workout plan")


# =============================================================================
# ALERT MODELS
# =============================================================================

class AlertContext(BaseModel):
    """Context information for an alert."""
    during_activity: bool
    activity_type: Optional[str] = None
    heart_rate: Optional[int] = Field(None, ge=0, le=300)
    spo2: Optional[int] = Field(None, ge=0, le=100)


class AlertExplanationResponse(BaseModel):
    """Natural language alert explanation response."""
    user_id: int
    alert_id: int
    alert_type: str
    severity_level: str
    alert_time: datetime
    context: AlertContext
    recommended_action: str
    nl_summary: str = Field(..., description="Natural language alert explanation")


# =============================================================================
# PROGRESS MODELS
# =============================================================================

class Period(BaseModel):
    """Activity and health metrics for a time period."""
    start: datetime
    end: datetime
    workout_count: int = Field(..., ge=0)
    total_active_minutes: int = Field(..., ge=0)
    avg_risk_level: Literal["LOW", "MODERATE", "HIGH"]
    time_in_safe_zone_minutes: int = Field(..., ge=0)
    time_above_safe_zone_minutes: int = Field(..., ge=0)
    alert_count: int = Field(..., ge=0)


class Trend(BaseModel):
    """Trend indicators across multiple dimensions."""
    workout_frequency: Literal["IMPROVING", "STABLE", "WORSENING"]
    alerts: Literal["IMPROVING", "STABLE", "WORSENING"]
    risk: Literal["IMPROVING", "STABLE", "WORSENING"]
    overall: Literal["IMPROVING", "STABLE", "WORSENING"]


class ProgressSummaryResponse(BaseModel):
    """Natural language progress summary response."""
    user_id: int
    range: str = Field(..., description="Time range (e.g., '7d', '30d')")
    current_period: Period
    previous_period: Period
    trend: Trend
    nl_summary: str = Field(..., description="Natural language progress summary")


# =============================================================================
# CHAT MODELS (Gemini-enhanced chatbot)
# =============================================================================

class ChatRequest(BaseModel):
    """Request for the hybrid chat endpoint."""
    message: str = Field(..., min_length=1, max_length=500, description="User's chat message")
    screen_context: Optional[str] = Field(None, description="Current screen the user is viewing")
    conversation_history: list[dict] = Field(
        default=[],
        description="Recent conversation messages [{role, text}, ...] for context"
    )


class ChatResponse(BaseModel):
    """Response from the hybrid chat endpoint."""
    response: str = Field(..., description="AI coach response text")
    source: str = Field(..., description="Response source: template, gemini, or fallback")
