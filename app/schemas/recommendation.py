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
    """How hard the exercise should be."""
    LOW = "low"  # Easy, gentle activity
    MODERATE = "moderate"  # Medium effort, slightly challenging
    HIGH = "high"  # Vigorous, demanding activity
    VERY_HIGH = "very_high"  # Maximum effort (rarely recommended for cardiac patients)


class RecommendationType(str, Enum):
    """What kind of recommendation the AI is giving."""
    EXERCISE = "exercise"  # A specific workout or activity to do
    REST = "rest"  # Take a break and rest
    MEDICAL_CONSULTATION = "medical_consultation"  # See your doctor
    MONITORING = "monitoring"  # Keep watching your readings closely


class RecommendationBase(BaseModel):
    """The basic info every exercise recommendation contains."""
    title: str  # Short name for the recommendation (e.g. "Morning Walk")
    suggested_activity: str  # What exercise to do (e.g. "walking", "stretching")
    intensity_level: str = "moderate"  # How hard to push (low, moderate, high)
    duration_minutes: int  # How long the exercise should last
    target_heart_rate_min: Optional[int] = None  # Lowest safe heart rate during exercise
    target_heart_rate_max: Optional[int] = None  # Highest safe heart rate during exercise
    description: Optional[str] = None  # Detailed explanation of the recommendation
    warnings: Optional[str] = None  # Safety warnings the patient should know


class RecommendationCreate(RecommendationBase):
    """Data needed to create a new recommendation."""
    user_id: int  # Which patient this recommendation is for
    generated_by: Optional[str] = "cloud_ai"  # Which AI system generated it
    model_name: Optional[str] = None  # Name of the AI model used
    confidence_score: Optional[float] = None  # How confident the AI is (0 to 1)
    based_on_risk_assessment_id: Optional[int] = None  # Which risk assessment triggered this


class RecommendationUpdate(BaseModel):
    """Data for updating a recommendation (e.g. marking it as completed)."""
    status: Optional[str] = None  # New status (pending, accepted, completed, dismissed)
    is_completed: Optional[bool] = None  # Did the patient finish this exercise?
    valid_until: Optional[datetime] = None  # When this recommendation expires
    user_feedback: Optional[str] = None  # What the patient said about the recommendation
    completed_at: Optional[datetime] = None  # When the patient completed it


class RecommendationResponse(RecommendationBase):
    """Full recommendation data sent back to the app."""
    recommendation_id: int  # Unique ID for this recommendation
    user_id: int  # Which patient it's for
    status: str = "pending"  # Current status (pending, accepted, completed, dismissed)
    is_completed: bool = False  # Has the patient done this exercise?
    generated_by: str = "cloud_ai"  # Which AI made it
    model_name: Optional[str] = None  # AI model name
    confidence_score: Optional[float] = None  # AI confidence level
    based_on_risk_assessment_id: Optional[int] = None  # Linked risk assessment
    valid_from: Optional[datetime] = None  # When this recommendation starts being valid
    valid_until: Optional[datetime] = None  # When it expires
    created_at: Optional[datetime] = None  # When it was created
    updated_at: Optional[datetime] = None  # When it was last updated
    user_feedback: Optional[str] = None  # Patient's feedback
    completed_at: Optional[datetime] = None  # When the patient completed it

    class Config:
        from_attributes = True


class RecommendationListResponse(BaseModel):
    """A page of recommendations with pagination info."""
    recommendations: list[RecommendationResponse]  # Recommendations on this page
    total: int  # Total number of recommendations
    page: int  # Current page number
    per_page: int  # How many per page
