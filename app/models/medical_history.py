"""
=============================================================================
ADAPTIV HEALTH - Medical History & Medications Models
=============================================================================
SQLAlchemy models for structured patient medical history, medications,
and uploaded clinical documents.

Tables:
  - patient_medical_history: Coded cardiac conditions & risk factors
  - patient_medications: Current/past medications with clinical flags
  - uploaded_documents: Clinical documents uploaded for LLM extraction

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - ConditionType.................. Line 30  (prior_mi, cabg, hypertension, etc.)
#   - ConditionStatus................ Line 55  (active, resolved, managed)
#   - DrugClass...................... Line 62  (beta_blocker, ace_inhibitor, etc.)
#   - MedicationStatus............... Line 80  (active, discontinued, on_hold)
#   - DocumentStatus................. Line 87  (uploaded, extracted, reviewed, failed)
#
# CLASS: PatientMedicalHistory....... Line 95
# CLASS: PatientMedication........... Line 130
# CLASS: UploadedDocument............ Line 175
# =============================================================================
"""

from sqlalchemy import Column, Integer, String, Date, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# =============================================================================
# Enums
# =============================================================================

class ConditionType(str, enum.Enum):
    """Cardiac conditions and risk factors relevant to cardiac rehab."""
    PRIOR_MI = "prior_mi"
    CABG = "cabg"
    PCI_STENT = "pci_stent"
    HEART_FAILURE = "heart_failure"
    VALVE_DISEASE = "valve_disease"
    ATRIAL_FIBRILLATION = "atrial_fibrillation"
    OTHER_ARRHYTHMIA = "other_arrhythmia"
    HYPERTENSION = "hypertension"
    DIABETES_TYPE1 = "diabetes_type1"
    DIABETES_TYPE2 = "diabetes_type2"
    DYSLIPIDEMIA = "dyslipidemia"
    CKD = "ckd"
    COPD = "copd"
    PAD = "pad"
    STROKE_TIA = "stroke_tia"
    SMOKING = "smoking"
    FAMILY_CVD = "family_cvd"
    OBESITY = "obesity"
    OTHER = "other"


class ConditionStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    MANAGED = "managed"


class DrugClass(str, enum.Enum):
    """Medication classes relevant to cardiac rehab."""
    BETA_BLOCKER = "beta_blocker"
    ACE_INHIBITOR = "ace_inhibitor"
    ARB = "arb"
    ANTIPLATELET = "antiplatelet"
    ANTICOAGULANT = "anticoagulant"
    STATIN = "statin"
    DIURETIC = "diuretic"
    CCB = "ccb"
    NITRATE = "nitrate"
    ANTIARRHYTHMIC = "antiarrhythmic"
    INSULIN = "insulin"
    METFORMIN = "metformin"
    SGLT2_INHIBITOR = "sglt2_inhibitor"
    OTHER = "other"


class MedicationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    ON_HOLD = "on_hold"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    REVIEWED = "reviewed"
    FAILED = "failed"


# =============================================================================
# PatientMedicalHistory Model
# =============================================================================

class PatientMedicalHistory(Base):
    """
    Structured cardiac conditions and risk factors per patient.

    Uses coded condition_type enums for AI queryability,
    with free-text condition_detail for clinician notes.
    """
    __tablename__ = "patient_medical_history"

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    condition_type = Column(String(50), nullable=False)
    condition_detail = Column(String(255), nullable=True)
    diagnosis_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default=ConditionStatus.ACTIVE.value)
    notes_encrypted = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="medical_conditions")

    __table_args__ = (
        Index('idx_pmh_user_condition', 'user_id', 'condition_type'),
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return f"<PatientMedicalHistory(id={self.history_id}, user={self.user_id}, type={self.condition_type})>"


# =============================================================================
# PatientMedication Model
# =============================================================================

class PatientMedication(Base):
    """
    Patient medications with clinical flags for AI risk scoring.

    is_hr_blunting: True for beta-blockers and rate-limiting CCBs.
    is_anticoagulant: True for warfarin/DOACs — affects exercise safety.
    """
    __tablename__ = "patient_medications"

    medication_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    drug_class = Column(String(50), nullable=False)
    drug_name = Column(String(100), nullable=False)
    dose = Column(String(50), nullable=True)
    frequency = Column(String(50), default="daily")

    # Clinical flags for AI
    is_hr_blunting = Column(Boolean, default=False)
    is_anticoagulant = Column(Boolean, default=False)

    # Reminder settings (for patient local notifications)
    reminder_time = Column(String(5), nullable=True)  # HH:MM format e.g. "08:00"
    reminder_enabled = Column(Boolean, default=False)

    status = Column(String(20), nullable=False, default=MedicationStatus.ACTIVE.value)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    prescribed_by = Column(String(100), nullable=True)
    notes_encrypted = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="medications")

    __table_args__ = (
        Index('idx_pm_user_status', 'user_id', 'status'),
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return f"<PatientMedication(id={self.medication_id}, user={self.user_id}, drug={self.drug_name})>"


# =============================================================================
# UploadedDocument Model
# =============================================================================

class UploadedDocument(Base):
    """
    Clinical documents uploaded by clinicians for LLM-based extraction.

    Flow: upload → extract text → Gemini extraction → clinician review → save.
    """
    __tablename__ = "uploaded_documents"

    document_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size_kb = Column(Integer, nullable=True)
    status = Column(String(20), default=DocumentStatus.UPLOADED.value)
    extracted_json = Column(Text, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        {'extend_existing': True},
    )

    def __repr__(self) -> str:
        return f"<UploadedDocument(id={self.document_id}, user={self.user_id}, file={self.filename})>"
