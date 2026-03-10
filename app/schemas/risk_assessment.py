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
    """How risky the patient's current health readings are."""
    LOW = "low"  # Everything looks normal
    MODERATE = "moderate"  # Some readings are slightly off
    HIGH = "high"  # Readings suggest potential danger
    CRITICAL = "critical"  # Immediate medical attention may be needed


class RiskAssessmentBase(BaseModel):
    """The core data every risk assessment contains."""
    risk_level: str  # Overall risk category (low, moderate, high, critical)
    risk_score: float = Field(..., ge=0.0, le=1.0)  # Number from 0 to 1 showing how risky (1 = highest risk)
    assessment_type: Optional[str] = "realtime"  # How it was assessed (realtime or batch)
    generated_by: Optional[str] = "cloud_ai"  # Which AI system made this assessment
    input_heart_rate: Optional[int] = None  # Heart rate used for this assessment
    input_spo2: Optional[float] = None  # Blood oxygen level used for this assessment
    input_hrv: Optional[float] = None  # Heart rate variability used for this assessment
    input_blood_pressure_sys: Optional[int] = None  # Systolic blood pressure used
    input_blood_pressure_dia: Optional[int] = None  # Diastolic blood pressure used
    primary_concern: Optional[str] = None  # Main health concern identified


class RiskAssessmentCreate(RiskAssessmentBase):
    """Data needed to save a new risk assessment."""
    user_id: int  # Which patient this assessment is for
    model_name: Optional[str] = None  # Name of the AI model that made the prediction
    model_version: Optional[str] = None  # Version of the AI model
    confidence: Optional[float] = None  # How confident the AI is in its prediction (0 to 1)
    inference_time_ms: Optional[float] = None  # How long the AI took to compute (in milliseconds)
    risk_factors_json: Optional[str] = None  # JSON string listing all the risk factors found


class RiskAssessmentUpdate(BaseModel):
    """Data for updating an existing risk assessment."""
    alert_triggered: Optional[bool] = None  # Did this assessment cause an alert to be created?
    activity_session_id: Optional[int] = None  # Link to the exercise session if applicable


class RiskAssessmentResponse(RiskAssessmentBase):
    """Full risk assessment data sent back to the app."""
    assessment_id: int  # Unique ID for this assessment
    user_id: int  # Which patient this belongs to
    model_name: Optional[str] = None  # AI model name
    model_version: Optional[str] = None  # AI model version
    confidence: Optional[float] = None  # AI confidence score
    inference_time_ms: Optional[float] = None  # AI processing time
    risk_factors_json: Optional[str] = None  # List of risk factors found
    alert_triggered: bool = False  # Whether an alert was created from this assessment
    activity_session_id: Optional[int] = None  # Linked exercise session (if any)
    assessment_date: Optional[datetime] = None  # When the assessment was performed
    created_at: Optional[datetime] = None  # When the record was saved

    class Config:
        from_attributes = True


class RiskAssessmentListResponse(BaseModel):
    """A page of risk assessments with pagination info."""
    assessments: list[RiskAssessmentResponse]  # The assessments on this page
    total: int  # Total number of assessments
    page: int  # Current page number
    per_page: int  # How many per page
