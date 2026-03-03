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
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class SafetyStatus(str):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    UNSAFE = "UNSAFE"


class ActivityType(str):
    WALKING = "WALKING"
    CYCLING = "CYCLING"
    OTHER = "OTHER"


class IntensityLevel(str):
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    VIGOROUS = "VIGOROUS"


class AlertType(str):
    HIGH_HEART_RATE = "HIGH_HEART_RATE"
    LOW_OXYGEN = "LOW_OXYGEN"
    OTHER = "OTHER"


class SeverityLevel(str):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendedAction(str):
    CONTINUE = "CONTINUE"
    SLOW_DOWN = "SLOW_DOWN"
    STOP_AND_REST = "STOP_AND_REST"
    CONTACT_DOCTOR = "CONTACT_DOCTOR"
    EMERGENCY = "EMERGENCY"


class TrendDirection(str):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    WORSENING = "WORSENING"


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
