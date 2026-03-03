"""
=============================================================================
ADAPTIV HEALTH - Medication Adherence Model
=============================================================================
Tracks whether patients have taken their scheduled medications.

Tables:
  - medication_adherence: Daily adherence records per medication

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CLASS: MedicationAdherence.......... Line 25
# =============================================================================
"""

from sqlalchemy import Column, Integer, Date, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MedicationAdherence(Base):
    """
    Daily medication adherence tracking.

    Records whether a patient took, skipped, or hasn't responded
    to their scheduled medication for a given day.

    taken: True = taken, False = skipped, None = no response yet
    """
    __tablename__ = "medication_adherence"

    adherence_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    medication_id = Column(
        Integer,
        ForeignKey("patient_medications.medication_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scheduled_date = Column(Date, nullable=False)
    taken = Column(Boolean, nullable=True)  # True=taken, False=skipped, None=no response
    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    medication = relationship("PatientMedication")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('medication_id', 'scheduled_date', name='uq_medication_date'),
        Index('idx_adherence_user_date', 'user_id', 'scheduled_date'),
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return f"<MedicationAdherence(id={self.adherence_id}, med={self.medication_id}, date={self.scheduled_date}, taken={self.taken})>"
