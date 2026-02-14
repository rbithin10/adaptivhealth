"""
=============================================================================
ADAPTIV HEALTH - Alert Model
=============================================================================
SQLAlchemy model mapped to Massoud's AWS RDS 'alerts' table.
670 alert records from cardiac monitoring sessions.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - AlertType........................ Line 35  (high_hr, low_spo2, etc.)
#   - SeverityLevel.................... Line 50  (info, warning, critical)
#
# CLASS: Alert (SQLAlchemy Model)
#   - Primary Key...................... Line 65  (alert_id)
#   - Foreign Key...................... Line 70  (user_id → users)
#   - Alert Content.................... Line 75  (type, severity, message)
#   - Trigger Values................... Line 90  (threshold exceeded info)
#   - Resolution....................... Line 105 (acknowledged, resolved)
#   - Relationships.................... Line 130 (user)
#
# BUSINESS CONTEXT:
# - Auto-generated from vital sign thresholds
# - Push notification triggers
# - Resolution tracking for care workflow
# =============================================================================
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# =============================================================================
# Enums
# =============================================================================

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


class Alert(Base):
    """
    Maps to Massoud's 'alerts' table on AWS RDS.
    670 rows of cardiac alerts (high_hr, low_spo2).
    """

    __tablename__ = "alerts"

    # -------------------------------------------------------------------------
    # Primary Key - matches Massoud's alert_id
    # -------------------------------------------------------------------------
    alert_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

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
    # Massoud's original columns (already in AWS RDS - 670 rows)
    # -------------------------------------------------------------------------
    alert_type = Column(String(50), nullable=True)  # high_hr, low_spo2
    severity = Column(String(20), nullable=True)     # critical, warning
    message = Column(Text, nullable=True)
    acknowledged = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # -------------------------------------------------------------------------
    # Bithin's extra columns (to be added via ALTER TABLE)
    # -------------------------------------------------------------------------
    title = Column(String(100), nullable=True)
    action_required = Column(String(200), nullable=True)
    trigger_value = Column(String(100), nullable=True)
    threshold_value = Column(String(100), nullable=True)
    risk_score = Column(Float, nullable=True)
    activity_session_id = Column(Integer, nullable=True)

    # Notification tracking
    is_sent_to_user = Column(Boolean, default=False, nullable=True)
    is_sent_to_caregiver = Column(Boolean, default=False, nullable=True)
    is_sent_to_clinician = Column(Boolean, default=False, nullable=True)

    # Resolution tracking
    is_resolved = Column(Boolean, default=False, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="alerts")

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_alert_user_time', 'user_id', 'created_at'),
        {'extend_existing': True}
    )

    # -------------------------------------------------------------------------
    # Convenience properties
    # -------------------------------------------------------------------------
    @property
    def id(self):
        """Alias for alert_id."""
        return self.alert_id

    @property
    def severity_level(self):
        """Alias for severity."""
        return self.severity

    @property
    def alert_time(self):
        """Alias for created_at."""
        return self.created_at

    @property
    def is_acknowledged(self):
        """Alias for acknowledged."""
        return self.acknowledged

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Alert(alert_id={self.alert_id}, type={self.alert_type}, severity={self.severity})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.alert_id,
            "user_id": self.user_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "action_required": self.action_required,
            "acknowledged": self.acknowledged,
            "is_resolved": self.is_resolved,
            "trigger_value": self.trigger_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def acknowledge(self, by: str = "user") -> None:
        """Mark alert as acknowledged."""
        self.acknowledged = True

    def resolve(self, resolved_by: str = "user", notes: str = None) -> None:
        """Mark alert as resolved."""
        from datetime import datetime, timezone
        self.is_resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        if notes:
            self.resolution_notes = notes

    def get_severity_color(self) -> str:
        """Get color code for UI display."""
        colors = {
            "warning": "#F59E0B",
            "critical": "#EF4444",
        }
        return colors.get(self.severity, "#6B7280")
