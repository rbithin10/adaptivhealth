"""
=============================================================================
ADAPTIV HEALTH - Cardiac Rehab Program Models
=============================================================================
SQLAlchemy models for structured cardiac rehabilitation programs with
session tracking and week-by-week progression gating.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
#
# CLASS: RehabProgram
#   - program_id (PK)................. Line 35
#   - user_id (FK, unique)............ Line 38  (one active program per user)
#   - program_type.................... Line 42  ("phase_2_light" / "phase_3_maintenance")
#   - current_week.................... Line 44
#   - current_session_in_week......... Line 46  (completed this week)
#   - status.......................... Line 48  ("active" / "completed" / "paused")
#   - timestamps...................... Line 50
#
# CLASS: RehabSessionLog
#   - log_id (PK)..................... Line 70
#   - program_id (FK)................. Line 73
#   - session metrics................. Line 78
#   - vitals_in_safe_range............ Line 88  (peak HR within ceiling)
#
# BUSINESS CONTEXT:
# - Phase II: supervised early rehab (4-week template)
# - Phase III: long-term maintenance (repeating weekly template)
# - Progression gating: advance only when session count + safe-vitals met
# =============================================================================
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RehabProgram(Base):
    """
    One active cardiac rehab program per patient.

    program_type maps to a hardcoded template in rehab_service.py.
    Progression is tracked via current_week and current_session_in_week.
    """

    __tablename__ = "rehab_programs"

    program_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    program_type = Column(String(50), nullable=False)  # "phase_2_light" or "phase_3_maintenance"
    current_week = Column(Integer, nullable=False, default=1)
    current_session_in_week = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")  # active / completed / paused

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="rehab_program", uselist=False)
    session_logs = relationship(
        "RehabSessionLog",
        back_populates="program",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("idx_rehab_user_status", "user_id", "status"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<RehabProgram(program_id={self.program_id}, user={self.user_id}, "
            f"type={self.program_type}, week={self.current_week}, status={self.status})>"
        )


class RehabSessionLog(Base):
    """
    Individual completed session within a rehab program.

    Records actual performance vs. targets so the progression gate
    can verify that >= 80 % of sessions had safe vitals before advancing.
    """

    __tablename__ = "rehab_session_logs"

    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    program_id = Column(
        Integer,
        ForeignKey("rehab_programs.program_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    week_number = Column(Integer, nullable=False)
    session_number = Column(Integer, nullable=False)
    activity_type = Column(String(50), nullable=False)  # walking, stretching, cycling, yoga
    target_duration_minutes = Column(Integer, nullable=False)
    actual_duration_minutes = Column(Integer, nullable=False)
    avg_heart_rate = Column(Integer, nullable=True)
    peak_heart_rate = Column(Integer, nullable=True)
    vitals_in_safe_range = Column(Boolean, nullable=False, default=True)

    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    program = relationship("RehabProgram", back_populates="session_logs")

    __table_args__ = (
        Index("idx_rehab_log_program_week", "program_id", "week_number"),
        Index("idx_rehab_log_user", "user_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<RehabSessionLog(log_id={self.log_id}, week={self.week_number}, "
            f"session={self.session_number}, safe={self.vitals_in_safe_range})>"
        )
