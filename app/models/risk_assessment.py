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

    # Risk classification (ML output)
    risk_level = Column(String(20), nullable=False)  # low, moderate, high
    risk_score = Column(Float, nullable=False)  # 0.0 to 1.0

    # Assessment metadata
    assessment_type = Column(String(20), default="realtime")
    generated_by = Column(String(20), default="cloud_ai")

    # Input values (what the AI analyzed)
    input_heart_rate = Column(Integer, nullable=True)
    input_spo2 = Column(Float, nullable=True)
    input_hrv = Column(Float, nullable=True)
    input_blood_pressure_sys = Column(Integer, nullable=True)
    input_blood_pressure_dia = Column(Integer, nullable=True)

    # Model info
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    inference_time_ms = Column(Float, nullable=True)
    primary_concern = Column(String(100), nullable=True)
    risk_factors_json = Column(Text, nullable=True)

    # Action tracking
    alert_triggered = Column(Boolean, default=False)
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
