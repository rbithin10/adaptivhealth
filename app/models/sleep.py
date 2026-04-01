"""
=============================================================================
ADAPTIV HEALTH - Sleep Entry Model
=============================================================================
Tracks sleep logs for recovery scoring and patient history.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Date, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SleepEntry(Base):
    """
    Sleep entry model for manual sleep logging.
    """

    __tablename__ = "sleep_entries"

    sleep_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date = Column(Date, nullable=False)
    bedtime = Column(DateTime(timezone=True), nullable=True)
    wake_time = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, nullable=True)
    quality_rating = Column(Integer, nullable=True)
    sleep_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sleep_entries")

    __table_args__ = (
        Index("idx_sleep_user_date", "user_id", "date"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"<SleepEntry(sleep_id={self.sleep_id}, user_id={self.user_id}, date={self.date})>"
