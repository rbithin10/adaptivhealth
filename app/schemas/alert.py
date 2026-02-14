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
    """Types of alerts."""
    HIGH_HEART_RATE = "high_heart_rate"
    LOW_HEART_RATE = "low_heart_rate"
    LOW_SPO2 = "low_spo2"
    HIGH_BLOOD_PRESSURE = "high_blood_pressure"
    IRREGULAR_RHYTHM = "irregular_rhythm"
    ABNORMAL_ACTIVITY = "abnormal_activity"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertBase(BaseModel):
    """Base schema for alerts."""
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    title: Optional[str] = None
    action_required: Optional[str] = None
    trigger_value: Optional[str] = None
    threshold_value: Optional[str] = None


class AlertCreate(BaseModel):
    """Schema for creating a new alert."""
    user_id: int
    alert_type: str
    severity: str
    message: str
    title: Optional[str] = None
    action_required: Optional[str] = None
    trigger_value: Optional[str] = None
    threshold_value: Optional[str] = None


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    acknowledged: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None


class AlertResponse(AlertBase):
    """Schema for alert responses."""
    alert_id: int
    user_id: int
    acknowledged: bool
    risk_score: Optional[float] = None
    activity_session_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""
    alerts: list[AlertResponse]
    total: int
    page: int
    per_page: int
