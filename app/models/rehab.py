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

    program_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this rehab program

    user_id = Column(  # Which patient is enrolled in this program
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Each patient can only have one active program
        index=True,
    )

    program_type = Column(String(50), nullable=False)  # Which program template: "phase_2_light" (early rehab) or "phase_3_maintenance" (long-term)
    current_week = Column(Integer, nullable=False, default=1)  # Which week of the program the patient is on
    current_session_in_week = Column(Integer, nullable=False, default=0)  # How many exercise sessions completed this week
    status = Column(String(20), nullable=False, default="active")  # Program state: active, completed, or paused

    started_at = Column(DateTime(timezone=True), server_default=func.now())  # When the patient started this program
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # When progress was last updated

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

    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this session log

    program_id = Column(  # Which rehab program this session belongs to
        Integer,
        ForeignKey("rehab_programs.program_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(  # Which patient completed this session
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    week_number = Column(Integer, nullable=False)  # Which week of the program this session was in
    session_number = Column(Integer, nullable=False)  # Session number within the week (e.g. 1st, 2nd, 3rd)
    activity_type = Column(String(50), nullable=False)  # What exercise was done: walking, stretching, cycling, yoga
    target_duration_minutes = Column(Integer, nullable=False)  # How long the session was supposed to last
    actual_duration_minutes = Column(Integer, nullable=False)  # How long the patient actually exercised
    avg_heart_rate = Column(Integer, nullable=True)  # Patient's average heart rate during the session
    peak_heart_rate = Column(Integer, nullable=True)  # Highest heart rate reached during the session
    vitals_in_safe_range = Column(Boolean, nullable=False, default=True)  # Were the patient's vitals safe throughout?

    completed_at = Column(DateTime(timezone=True), server_default=func.now())  # When the session was finished

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
