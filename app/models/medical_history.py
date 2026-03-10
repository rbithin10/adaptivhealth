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
    """Types of heart-related conditions and risk factors that patients may have."""
    PRIOR_MI = "prior_mi"  # Patient had a heart attack before
    CABG = "cabg"  # Patient had heart bypass surgery
    PCI_STENT = "pci_stent"  # Patient had a stent placed in their arteries
    HEART_FAILURE = "heart_failure"  # Heart doesn't pump blood well enough
    VALVE_DISEASE = "valve_disease"  # Problem with one of the heart's valves
    ATRIAL_FIBRILLATION = "atrial_fibrillation"  # Irregular heartbeat (upper chambers)
    OTHER_ARRHYTHMIA = "other_arrhythmia"  # Other types of irregular heartbeat
    HYPERTENSION = "hypertension"  # High blood pressure
    DIABETES_TYPE1 = "diabetes_type1"  # Type 1 diabetes (body can't make insulin)
    DIABETES_TYPE2 = "diabetes_type2"  # Type 2 diabetes (body can't use insulin well)
    DYSLIPIDEMIA = "dyslipidemia"  # Abnormal cholesterol or fat levels in blood
    CKD = "ckd"  # Chronic kidney disease
    COPD = "copd"  # Chronic lung disease that makes breathing hard
    PAD = "pad"  # Poor blood flow to the legs (peripheral artery disease)
    STROKE_TIA = "stroke_tia"  # Had a stroke or mini-stroke
    SMOKING = "smoking"  # Current or past smoker
    FAMILY_CVD = "family_cvd"  # Family history of heart disease
    OBESITY = "obesity"  # Significantly overweight (BMI 30+)
    OTHER = "other"  # Any other condition not listed above


class ConditionStatus(str, enum.Enum):
    ACTIVE = "active"  # The condition is currently affecting the patient
    RESOLVED = "resolved"  # The condition has been cured or gone away
    MANAGED = "managed"  # The condition is under control with treatment


class DrugClass(str, enum.Enum):
    """Types of medications commonly used in heart care."""
    BETA_BLOCKER = "beta_blocker"  # Slows heart rate and lowers blood pressure
    ACE_INHIBITOR = "ace_inhibitor"  # Relaxes blood vessels to lower blood pressure
    ARB = "arb"  # Similar to ACE inhibitors, relaxes blood vessels
    ANTIPLATELET = "antiplatelet"  # Prevents blood clots (like aspirin)
    ANTICOAGULANT = "anticoagulant"  # Thins the blood to prevent clots (like warfarin)
    STATIN = "statin"  # Lowers cholesterol levels
    DIURETIC = "diuretic"  # Removes extra fluid from the body (water pill)
    CCB = "ccb"  # Calcium channel blocker — relaxes blood vessels
    NITRATE = "nitrate"  # Opens blood vessels to relieve chest pain
    ANTIARRHYTHMIC = "antiarrhythmic"  # Corrects irregular heartbeats
    INSULIN = "insulin"  # Hormone injection to control blood sugar
    METFORMIN = "metformin"  # Pill to control blood sugar in type 2 diabetes
    SGLT2_INHIBITOR = "sglt2_inhibitor"  # Newer diabetes drug that also helps the heart
    OTHER = "other"  # Any other medication not listed above


class MedicationStatus(str, enum.Enum):
    ACTIVE = "active"  # Patient is currently taking this medication
    DISCONTINUED = "discontinued"  # Patient stopped taking this medication
    ON_HOLD = "on_hold"  # Temporarily paused


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"  # File was uploaded but not yet processed
    EXTRACTED = "extracted"  # AI has pulled out the key information
    REVIEWED = "reviewed"  # A clinician has checked and approved the extracted data
    FAILED = "failed"  # Something went wrong during extraction


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

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this history record
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)  # Which patient this belongs to

    condition_type = Column(String(50), nullable=False)  # What kind of condition (e.g. heart attack, diabetes)
    condition_detail = Column(String(255), nullable=True)  # Extra details the clinician wants to note
    diagnosis_date = Column(Date, nullable=True)  # When the condition was first diagnosed
    status = Column(String(20), nullable=False, default=ConditionStatus.ACTIVE.value)  # Is it active, resolved, or managed?
    notes_encrypted = Column(Text, nullable=True)  # Private clinician notes (encrypted for privacy)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # When this record was first created
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # When this record was last changed
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)  # Which clinician created this record
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)  # Which clinician last updated this record

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

    medication_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this medication record
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)  # Which patient takes this medication

    drug_class = Column(String(50), nullable=False)  # Category of drug (e.g. beta blocker, statin)
    drug_name = Column(String(100), nullable=False)  # Actual name of the drug (e.g. Metoprolol, Atorvastatin)
    dose = Column(String(50), nullable=True)  # How much to take (e.g. "50mg")
    frequency = Column(String(50), default="daily")  # How often (e.g. "daily", "twice daily")

    # Clinical flags that affect exercise safety and AI risk scoring
    is_hr_blunting = Column(Boolean, default=False)  # Does this drug slow down heart rate? (affects exercise targets)
    is_anticoagulant = Column(Boolean, default=False)  # Does this drug thin the blood? (affects exercise safety)

    # Reminder settings so patients get notified to take their medication
    reminder_time = Column(String(5), nullable=True)  # What time to remind them (e.g. "08:00")
    reminder_enabled = Column(Boolean, default=False)  # Should the app send reminders for this medication?

    status = Column(String(20), nullable=False, default=MedicationStatus.ACTIVE.value)  # Currently taking, stopped, or paused
    start_date = Column(Date, nullable=True)  # When the patient started this medication
    end_date = Column(Date, nullable=True)  # When the patient stopped (if applicable)
    prescribed_by = Column(String(100), nullable=True)  # Name of the doctor who prescribed it
    notes_encrypted = Column(Text, nullable=True)  # Private notes about this medication (encrypted)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # When this record was created
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # When this record was last changed
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)  # Which clinician created this record
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)  # Which clinician last updated this record

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

    document_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this document
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)  # Which patient this document belongs to

    filename = Column(String(255), nullable=False)  # Original name of the uploaded file
    file_path = Column(String(500), nullable=False)  # Where the file is stored on the server
    file_type = Column(String(20), nullable=False)  # Type of file (e.g. "pdf", "jpg")
    file_size_kb = Column(Integer, nullable=True)  # Size of the file in kilobytes
    status = Column(String(20), default=DocumentStatus.UPLOADED.value)  # Processing status: uploaded, extracted, reviewed, or failed
    extracted_json = Column(Text, nullable=True)  # The medical information AI pulled from the document

    uploaded_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)  # Which clinician uploaded this file
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # When the file was uploaded

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        {'extend_existing': True},
    )

    def __repr__(self) -> str:
        return f"<UploadedDocument(id={self.document_id}, user={self.user_id}, file={self.filename})>"
