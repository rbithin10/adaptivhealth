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

    adherence_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this adherence record
    medication_id = Column(  # Which medication this record is tracking
        Integer,
        ForeignKey("patient_medications.medication_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(  # Which patient this record belongs to
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scheduled_date = Column(Date, nullable=False)  # The date the medication was supposed to be taken
    taken = Column(Boolean, nullable=True)  # Did they take it? True=yes, False=skipped, None=no answer yet
    responded_at = Column(DateTime(timezone=True), nullable=True)  # When the patient confirmed or skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # When this record was created

    # Relationships — connect to the medication and user tables
    medication = relationship("PatientMedication")  # Link to the specific medication details
    user = relationship("User")  # Link to the patient's profile

    __table_args__ = (
        UniqueConstraint('medication_id', 'scheduled_date', name='uq_medication_date'),  # Only one record per medication per day
        Index('idx_adherence_user_date', 'user_id', 'scheduled_date'),  # Speed up looking up a patient's records by date
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return f"<MedicationAdherence(id={self.adherence_id}, med={self.medication_id}, date={self.scheduled_date}, taken={self.taken})>"
