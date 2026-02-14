"""
=============================================================================
ADAPTIV HEALTH - Activity Session Model
=============================================================================
SQLAlchemy model mapped to Massoud's AWS RDS 'activity_sessions' table.
3,000 workout sessions from cardiac rehabilitation patients.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - ActivityType..................... Line 30  (walking, running, cycling, etc.)
#   - ActivityPhase.................... Line 45  (warm_up, active, cool_down)
#
# CLASS: ActivitySession (SQLAlchemy Model)
#   - Primary Key...................... Line 60  (session_id)
#   - Foreign Key...................... Line 65  (user_id → users)
#   - Timing Columns................... Line 70  (start_time, end_time)
#   - Metrics Columns.................. Line 80  (avg_hr, peak_hr, calories)
#   - User Feedback.................... Line 100 (feeling_before, notes)
#   - Relationships.................... Line 115 (user)
#
# BUSINESS CONTEXT:
# - Workout tracking from mobile app
# - Feeds into ML risk prediction
# - HR zones and recovery time analysis
# =============================================================================
"""

from enum import Enum
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# =============================================================================
# Enums
# =============================================================================

class ActivityType(str, Enum):
    """Types of activities/exercises."""
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH_TRAINING = "strength_training"
    YOGA = "yoga"
    STRETCHING = "stretching"
    OTHER = "other"


class ActivityPhase(str, Enum):
    """Phases of activity."""
    WARM_UP = "warm_up"
    ACTIVE = "active"
    COOL_DOWN = "cool_down"
    RECOVERY = "recovery"


class ActivitySession(Base):
    """
    Maps to Massoud's 'activity_sessions' table on AWS RDS.
    3,000 rows of cardiac patient workout sessions with risk scores.
    """

    __tablename__ = "activity_sessions"

    # -------------------------------------------------------------------------
    # Primary Key - matches Massoud's session_id
    # -------------------------------------------------------------------------
    session_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Foreign Key
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Massoud's original columns (already in AWS RDS - 3K rows)
    # -------------------------------------------------------------------------
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    activity_type = Column(String(50), nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    peak_heart_rate = Column(Integer, nullable=True)
    min_heart_rate = Column(Integer, nullable=True)
    avg_spo2 = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Integer, nullable=True)
    recovery_time_minutes = Column(Integer, nullable=True)
    risk_score = Column(Float, nullable=True)  # 0.0 to 1.0 from ML model
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # -------------------------------------------------------------------------
    # Bithin's extra columns (to be added via ALTER TABLE)
    # -------------------------------------------------------------------------
    status = Column(String(20), default="completed", nullable=True)
    baseline_heart_rate = Column(Integer, nullable=True)
    recovery_score = Column(Float, nullable=True)
    alerts_triggered = Column(Integer, default=0, nullable=True)
    feeling_before = Column(String(20), nullable=True)
    feeling_after = Column(String(20), nullable=True)
    user_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="activity_sessions")

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_activity_user_date', 'user_id', 'start_time'),
        {'extend_existing': True}
    )

    # -------------------------------------------------------------------------
    # Convenience properties
    # -------------------------------------------------------------------------
    @property
    def id(self):
        """Alias for session_id."""
        return self.session_id

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<ActivitySession(session_id={self.session_id}, user_id={self.user_id}, type={self.activity_type})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "activity_type": self.activity_type,
            "avg_heart_rate": self.avg_heart_rate,
            "peak_heart_rate": self.peak_heart_rate,
            "min_heart_rate": self.min_heart_rate,
            "avg_spo2": self.avg_spo2,
            "duration_minutes": self.duration_minutes,
            "calories_burned": self.calories_burned,
            "recovery_time_minutes": self.recovery_time_minutes,
            "risk_score": self.risk_score,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
