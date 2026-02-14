"""
Risk Assessment Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - RiskLevel........................ Line 25  (low, moderate, high, critical)
#
# SCHEMAS
#   - RiskAssessmentBase............... Line 35  (Common fields)
#   - RiskAssessmentCreate............. Line 50  (New assessment input)
#   - RiskAssessmentResponse........... Line 60  (Full assessment output)
#
# BUSINESS CONTEXT:
# - ML prediction result storage
# - Risk score 0.0-1.0 with level mapping
# =============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level categories."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessmentBase(BaseModel):
    """Base schema for risk assessments."""
    risk_level: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    assessment_type: Optional[str] = "realtime"
    generated_by: Optional[str] = "cloud_ai"
    input_heart_rate: Optional[int] = None
    input_spo2: Optional[float] = None
    input_hrv: Optional[float] = None
    input_blood_pressure_sys: Optional[int] = None
    input_blood_pressure_dia: Optional[int] = None
    primary_concern: Optional[str] = None


class RiskAssessmentCreate(RiskAssessmentBase):
    """Schema for creating a new risk assessment."""
    user_id: int
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = None
    inference_time_ms: Optional[float] = None
    risk_factors_json: Optional[str] = None


class RiskAssessmentUpdate(BaseModel):
    """Schema for updating a risk assessment."""
    alert_triggered: Optional[bool] = None
    activity_session_id: Optional[int] = None


class RiskAssessmentResponse(RiskAssessmentBase):
    """Schema for risk assessment responses."""
    assessment_id: int
    user_id: int
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = None
    inference_time_ms: Optional[float] = None
    risk_factors_json: Optional[str] = None
    alert_triggered: bool = False
    activity_session_id: Optional[int] = None
    assessment_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RiskAssessmentListResponse(BaseModel):
    """Schema for paginated risk assessment list."""
    assessments: list[RiskAssessmentResponse]
    total: int
    page: int
    per_page: int
