"""
Exercise Recommendation Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - IntensityLevel................... Line 25  (low, moderate, high)
#   - RecommendationType............... Line 35  (exercise, rest, consult)
#
# SCHEMAS
#   - RecommendationBase............... Line 45  (Common fields)
#   - RecommendationCreate............. Line 60  (New recommendation input)
#   - RecommendationResponse........... Line 70  (Full recommendation output)
#
# BUSINESS CONTEXT:
# - Personalized exercise guidance
# - Risk-adjusted workout targets
# =============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class IntensityLevel(str, Enum):
    """Intensity levels for exercises."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RecommendationType(str, Enum):
    """Types of recommendations."""
    EXERCISE = "exercise"
    REST = "rest"
    MEDICAL_CONSULTATION = "medical_consultation"
    MONITORING = "monitoring"


class RecommendationBase(BaseModel):
    """Base schema for recommendations."""
    title: str
    suggested_activity: str
    intensity_level: str = "moderate"
    duration_minutes: int
    target_heart_rate_min: Optional[int] = None
    target_heart_rate_max: Optional[int] = None
    description: Optional[str] = None
    warnings: Optional[str] = None


class RecommendationCreate(RecommendationBase):
    """Schema for creating a new recommendation."""
    user_id: int
    generated_by: Optional[str] = "cloud_ai"
    model_name: Optional[str] = None
    confidence_score: Optional[float] = None
    based_on_risk_assessment_id: Optional[int] = None


class RecommendationUpdate(BaseModel):
    """Schema for updating a recommendation."""
    status: Optional[str] = None
    is_completed: Optional[bool] = None
    valid_until: Optional[datetime] = None
    user_feedback: Optional[str] = None
    completed_at: Optional[datetime] = None


class RecommendationResponse(RecommendationBase):
    """Schema for recommendation responses."""
    recommendation_id: int
    user_id: int
    status: str = "pending"
    is_completed: bool = False
    generated_by: str = "cloud_ai"
    model_name: Optional[str] = None
    confidence_score: Optional[float] = None
    based_on_risk_assessment_id: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_feedback: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecommendationListResponse(BaseModel):
    """Schema for paginated recommendation list."""
    recommendations: list[RecommendationResponse]
    total: int
    page: int
    per_page: int
