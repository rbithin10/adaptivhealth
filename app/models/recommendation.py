"""
=============================================================================
ADAPTIV HEALTH - Exercise Recommendation Model
=============================================================================
Stores AI-generated workout recommendations.
New table added to AWS RDS via migration script.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - IntensityLevel................... Line 35  (low, moderate, high)
#   - RecommendationType............... Line 45  (exercise, rest, consult)
#
# CLASS: ExerciseRecommendation (SQLAlchemy Model)
#   - Primary Key...................... Line 55  (recommendation_id)
#   - Foreign Key...................... Line 60  (user_id → users, assessment_id)
#   - Recommendation Content........... Line 65  (title, activity, intensity)
#   - HR Targets....................... Line 75  (target_hr_min/max)
#   - Warnings......................... Line 85  (safety warnings text)
#   - Relationships.................... Line 95  (user, risk_assessment)
#
# BUSINESS CONTEXT:
# - Personalized exercise guidance
# - Risk-aware workout planning
# - Mobile app "Today's Workout" feature
# =============================================================================
"""

from enum import Enum
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# =============================================================================
# Enums
# =============================================================================

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


class ExerciseRecommendation(Base):
    """
    Exercise recommendation table - created by migration script.
    Stores personalized workout recommendations from the AI.
    """

    __tablename__ = "exercise_recommendations"

    # Primary Key
    recommendation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign Key
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # What the recommendation says to do
    title = Column(String(100), nullable=False)                # Short headline (e.g. "Light Walking Session")
    suggested_activity = Column(String(100), nullable=False)   # The specific exercise to do
    intensity_level = Column(String(20), default="moderate")   # How hard: low, moderate, high, or very_high
    duration_minutes = Column(Integer, nullable=False)         # How long the workout should last
    target_heart_rate_min = Column(Integer, nullable=True)     # Minimum safe heart rate to aim for
    target_heart_rate_max = Column(Integer, nullable=True)     # Maximum safe heart rate to stay under
    description = Column(Text, nullable=True)                  # Detailed instructions for the workout
    warnings = Column(Text, nullable=True)                     # Safety warnings specific to this patient

    # Recommendation tracking
    status = Column(String(20), default="pending")             # Whether the patient has started/completed it
    is_completed = Column(Boolean, default=False)              # True if the patient finished the recommended workout

    # Which AI generated this recommendation and how confident it was
    generated_by = Column(String(50), default="cloud_ai")      # Source: cloud_ai or edge_ai
    model_name = Column(String(100), nullable=True)            # Name of the model that made this recommendation
    confidence_score = Column(Float, nullable=True)            # How confident the AI is (0.0 to 1.0)
    based_on_risk_assessment_id = Column(Integer, nullable=True)  # Which risk assessment this was based on

    # When this recommendation is valid
    valid_from = Column(DateTime(timezone=True), server_default=func.now())  # Start of validity period
    valid_until = Column(DateTime(timezone=True), nullable=True)             # End of validity (None = no expiry)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="recommendations")

    # Table args
    __table_args__ = (
        Index('idx_rec_user_date', 'user_id', 'created_at'),
        {'extend_existing': True}
    )

    @property
    def id(self):
        return self.recommendation_id

    def __repr__(self):
        return f"<Recommendation(id={self.recommendation_id}, activity={self.suggested_activity})>"
