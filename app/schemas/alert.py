"""
Alert Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - AlertType........................ Line 25  (high_hr, low_spo2, etc.)
#   - SeverityLevel.................... Line 40  (info, warning, critical)
#
# SCHEMAS
#   - AlertBase........................ Line 50  (Common fields)
#   - AlertCreate...................... Line 60  (New alert input)
#   - AlertUpdate...................... Line 70  (Resolution input)
#   - AlertResponse.................... Line 80  (Full alert output)
#   - AlertListResponse................ Line 95  (Paginated list)
#
# BUSINESS CONTEXT:
# - Alert management for patient safety
# - Threshold-triggered notifications
# =============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AlertType(str, Enum):
    """Types of health alerts the system can create."""
    HIGH_HEART_RATE = "high_heart_rate"  # Heart rate is too fast
    LOW_HEART_RATE = "low_heart_rate"  # Heart rate is too slow
    LOW_SPO2 = "low_spo2"  # Blood oxygen level dropped too low
    HIGH_BLOOD_PRESSURE = "high_blood_pressure"  # Blood pressure is too high
    IRREGULAR_RHYTHM = "irregular_rhythm"  # Heartbeat pattern is abnormal
    ABNORMAL_ACTIVITY = "abnormal_activity"  # Exercise activity looks unusual
    OTHER = "other"  # Any other type of alert


class SeverityLevel(str, Enum):
    """How serious the alert is."""
    INFO = "info"  # Just informational, nothing to worry about
    WARNING = "warning"  # Something to pay attention to
    CRITICAL = "critical"  # Needs immediate attention
    EMERGENCY = "emergency"  # Urgent — may need emergency help


class AlertBase(BaseModel):
    """The basic information every alert has."""
    alert_type: Optional[str] = None  # What kind of alert (e.g. high heart rate)
    severity: Optional[str] = None  # How serious it is (info, warning, critical, emergency)
    message: Optional[str] = None  # A human-readable description of the alert
    title: Optional[str] = None  # Short title for the alert
    action_required: Optional[str] = None  # What the patient or clinician should do
    trigger_value: Optional[str] = None  # The actual reading that caused the alert (e.g. "180 BPM")
    threshold_value: Optional[str] = None  # The safe limit that was exceeded (e.g. "150 BPM")


class AlertCreate(BaseModel):
    """Data needed to create a new alert."""
    user_id: int  # Which patient this alert is for
    alert_type: str  # What kind of alert
    severity: str  # How serious it is
    message: str  # Description of what happened
    title: Optional[str] = None  # Optional short title
    action_required: Optional[str] = None  # What action to take
    trigger_value: Optional[str] = None  # The value that triggered this alert
    threshold_value: Optional[str] = None  # The safe limit that was crossed


class AlertUpdate(BaseModel):
    """Data for updating an existing alert (e.g. acknowledging or resolving it)."""
    acknowledged: Optional[bool] = None  # Has someone seen and noted this alert?
    resolved_at: Optional[datetime] = None  # When was the alert resolved?
    resolved_by: Optional[int] = None  # Which clinician resolved it?
    resolution_notes: Optional[str] = None  # Notes about how it was resolved


class AlertResponse(AlertBase):
    """Full alert data sent back to the app or dashboard."""
    alert_id: int  # Unique ID for this alert
    user_id: int  # Which patient this alert belongs to
    acknowledged: bool  # Has it been seen and noted?
    risk_score: Optional[float] = None  # AI risk score at the time of the alert
    activity_session_id: Optional[int] = None  # If the alert happened during exercise
    resolved_at: Optional[datetime] = None  # When it was resolved
    resolved_by: Optional[int] = None  # Who resolved it
    resolution_notes: Optional[str] = None  # Notes about resolution
    created_at: Optional[datetime] = None  # When the alert was created
    updated_at: Optional[datetime] = None  # When it was last updated

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """A page of alerts with pagination info."""
    alerts: list[AlertResponse]  # The list of alerts on this page
    total: int  # Total number of alerts matching the query
    page: int  # Which page number this is
    per_page: int  # How many alerts per page
