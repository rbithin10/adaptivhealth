"""
ADAPTIV HEALTH - Clinical Note Model
=====================================
SQLAlchemy model for clinician-authored notes on patients.
Notes are embedded in the AI Risk Summary panel and used as context
for future AI-generated summaries.

# =============================================================================
# FILE MAP
# =============================================================================
# CLASS: ClinicalNote (SQLAlchemy Model)
#   - Primary Key...................... Line 32  (note_id)
#   - Foreign Keys..................... Line 36  (user_id, clinician_id)
#   - Content.......................... Line 48  (content)
#   - Timestamps....................... Line 52  (created_at, updated_at)
#   - Indexes.......................... Line 58
# =============================================================================
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class ClinicalNote(Base):
    """
    Clinician-authored note attached to a patient.

    Displayed in the AI Risk Summary panel beneath the AI-generated summary.
    Ordered newest-first for clinical workflow.
    """

    __tablename__ = "clinical_notes"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    note_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    clinician_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------
    content = Column(Text, nullable=False)

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_clinical_notes_user_created", "user_id", "created_at"),
        {"extend_existing": True}
    )

    def __repr__(self):
        return f"<ClinicalNote(note_id={self.note_id}, user_id={self.user_id}, clinician_id={self.clinician_id})>"
