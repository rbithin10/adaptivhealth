"""
=============================================================================
ADAPTIV HEALTH - Risk Assessment Model
=============================================================================
Stores AI-generated cardiovascular risk evaluations.
New table added to AWS RDS via migration script.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - RiskLevel........................ Line 35  (low, moderate, high, critical)
#
# CLASS: RiskAssessment (SQLAlchemy Model)
#   - Primary Key...................... Line 50  (assessment_id)
#   - Foreign Key...................... Line 55  (user_id → users)
#   - Risk Score....................... Line 60  (0.0-1.0 float)
#   - Risk Factors JSON................ Line 70  (driver contributions)
#   - Metadata......................... Line 80  (model_version, inference_time)
#   - Relationships.................... Line 90  (user)
#
# BUSINESS CONTEXT:
# - ML model output storage
# - Risk trends over time
# - Audit trail for predictions
# =============================================================================
"""

from enum import Enum
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import json


# =============================================================================
# Enums
# =============================================================================

class RiskLevel(str, Enum):
    """Risk level categories."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(Base):
    """
    Risk Assessment table - created by migration script.
    Stores results from Massoud's ML model predictions.
    """

    __tablename__ = "risk_assessments"

    # Primary Key
    assessment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign Key
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The AI's overall risk classification: low, moderate, or high
    risk_level = Column(String(20), nullable=False)
    # Numeric risk score from 0.0 (no risk) to 1.0 (highest risk)
    risk_score = Column(Float, nullable=False)

    # How the assessment was done: "realtime" (live) or "batch" (bulk processing)
    assessment_type = Column(String(20), default="realtime")
    # Where the prediction came from: "cloud_ai" (server) or "edge_ai" (mobile app)
    generated_by = Column(String(20), default="cloud_ai")

    # The vital sign values the AI used to make its prediction
    input_heart_rate = Column(Integer, nullable=True)         # Heart rate in BPM
    input_spo2 = Column(Float, nullable=True)                 # Blood oxygen percentage
    input_hrv = Column(Float, nullable=True)                  # Heart rate variability
    input_blood_pressure_sys = Column(Integer, nullable=True) # Systolic blood pressure (top number)
    input_blood_pressure_dia = Column(Integer, nullable=True) # Diastolic blood pressure (bottom number)

    # Information about which AI model version made the prediction
    model_name = Column(String(100), nullable=True)           # Name of the ML model used
    model_version = Column(String(50), nullable=True)         # Version number of the model
    confidence = Column(Float, nullable=True)                 # How confident the AI is in its prediction (0.0 to 1.0)
    inference_time_ms = Column(Float, nullable=True)          # How many milliseconds the prediction took
    primary_concern = Column(String(100), nullable=True)      # The main health issue identified (e.g. "elevated_hr")
    risk_factors_json = Column(Text, nullable=True)           # Detailed breakdown of all risk factors as JSON

    # Whether this assessment automatically triggered a health alert
    alert_triggered = Column(Boolean, default=False)
    # Which workout session this assessment was generated during (if any)
    activity_session_id = Column(Integer, nullable=True)

    # Timestamps
    assessment_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="risk_assessments")

    # Table args
    __table_args__ = (
        Index('idx_risk_user_date', 'user_id', 'assessment_date'),
        {'extend_existing': True}
    )

    # Convenience
    @property
    def id(self):
        return self.assessment_id

    def __repr__(self):
        return f"<RiskAssessment(id={self.assessment_id}, score={self.risk_score}, level={self.risk_level})>"
