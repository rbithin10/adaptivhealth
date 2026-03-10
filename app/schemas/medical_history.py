"""
Pydantic schemas for medical history, medications, and document extraction.

Request/response validation for the Medical Profile API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# =============================================================================
# Enums (mirrored from models for request validation)
# =============================================================================

class ConditionTypeEnum(str, Enum):
    """Types of heart-related conditions and risk factors."""
    prior_mi = "prior_mi"  # Previous heart attack
    cabg = "cabg"  # Heart bypass surgery
    pci_stent = "pci_stent"  # Stent placed in artery
    heart_failure = "heart_failure"  # Heart can't pump enough blood
    valve_disease = "valve_disease"  # Problem with a heart valve
    atrial_fibrillation = "atrial_fibrillation"  # Irregular heartbeat
    other_arrhythmia = "other_arrhythmia"  # Other heartbeat irregularity
    hypertension = "hypertension"  # High blood pressure
    diabetes_type1 = "diabetes_type1"  # Body can't make insulin
    diabetes_type2 = "diabetes_type2"  # Body can't use insulin well
    dyslipidemia = "dyslipidemia"  # Abnormal cholesterol levels
    ckd = "ckd"  # Chronic kidney disease
    copd = "copd"  # Chronic lung disease
    pad = "pad"  # Poor blood flow to legs
    stroke_tia = "stroke_tia"  # Had a stroke or mini-stroke
    smoking = "smoking"  # Current or past smoker
    family_cvd = "family_cvd"  # Family history of heart disease
    obesity = "obesity"  # Significantly overweight
    other = "other"  # Any other condition


class DrugClassEnum(str, Enum):
    """Categories of medications used in heart care."""
    beta_blocker = "beta_blocker"  # Slows heart rate, lowers blood pressure
    ace_inhibitor = "ace_inhibitor"  # Relaxes blood vessels
    arb = "arb"  # Similar to ACE inhibitor, relaxes vessels
    antiplatelet = "antiplatelet"  # Prevents blood clots (e.g. aspirin)
    anticoagulant = "anticoagulant"  # Thins blood to prevent clots
    statin = "statin"  # Lowers cholesterol
    diuretic = "diuretic"  # Removes extra fluid (water pill)
    ccb = "ccb"  # Calcium channel blocker, relaxes vessels
    nitrate = "nitrate"  # Opens blood vessels for chest pain relief
    antiarrhythmic = "antiarrhythmic"  # Corrects irregular heartbeat
    insulin = "insulin"  # Injection to control blood sugar
    metformin = "metformin"  # Pill for type 2 diabetes
    sglt2_inhibitor = "sglt2_inhibitor"  # Newer drug for diabetes and heart health
    other = "other"  # Any other medication type


# =============================================================================
# Medical History Schemas
# =============================================================================

class MedicalHistoryCreate(BaseModel):
    """Data needed to add a new condition to a patient's medical history."""
    condition_type: ConditionTypeEnum  # What type of condition (from the list above)
    condition_detail: Optional[str] = Field(None, max_length=255)  # Extra details about the condition
    diagnosis_date: Optional[date] = None  # When the condition was first diagnosed
    status: str = Field("active", pattern=r"^(active|resolved|managed)$")  # Is it active, resolved, or managed?
    notes: Optional[str] = Field(None, max_length=1000)  # Any additional clinician notes


class MedicalHistoryUpdate(BaseModel):
    """Data for updating an existing condition record."""
    condition_detail: Optional[str] = Field(None, max_length=255)  # Updated details about the condition
    diagnosis_date: Optional[date] = None  # Updated diagnosis date
    status: Optional[str] = Field(None, pattern=r"^(active|resolved|managed)$")  # New status
    notes: Optional[str] = Field(None, max_length=1000)  # Updated notes


class MedicalHistoryResponse(BaseModel):
    """Full condition record sent back to the app."""
    history_id: int  # Unique ID for this condition record
    user_id: int  # Which patient this belongs to
    condition_type: str  # Type of condition (e.g. heart failure, diabetes)
    condition_detail: Optional[str] = None  # Extra details about the condition
    diagnosis_date: Optional[date] = None  # When it was diagnosed
    status: str  # Current status: active, resolved, or managed
    notes: Optional[str] = None  # Clinician notes
    created_at: Optional[datetime] = None  # When the record was created
    updated_at: Optional[datetime] = None  # When it was last changed

    class Config:
        from_attributes = True


# =============================================================================
# Medication Schemas
# =============================================================================

class MedicationCreate(BaseModel):
    """Data needed to add a new medication to a patient's records."""
    drug_class: DrugClassEnum  # Category of medication (e.g. beta blocker, statin)
    drug_name: str = Field(..., min_length=1, max_length=100)  # Name of the drug
    dose: Optional[str] = Field(None, max_length=50)  # How much to take (e.g. "50mg")
    frequency: str = Field("daily", pattern=r"^(daily|twice_daily|three_times_daily|as_needed|weekly)$")  # How often to take it
    start_date: Optional[date] = None  # When the patient started this medication
    prescribed_by: Optional[str] = Field(None, max_length=100)  # Doctor who prescribed it
    notes: Optional[str] = Field(None, max_length=1000)  # Additional notes


class MedicationUpdate(BaseModel):
    drug_name: Optional[str] = Field(None, max_length=100)
    dose: Optional[str] = Field(None, max_length=50)
    frequency: Optional[str] = Field(None, pattern=r"^(daily|twice_daily|three_times_daily|as_needed|weekly)$")
    status: Optional[str] = Field(None, pattern=r"^(active|discontinued|on_hold)$")
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)


class MedicationResponse(BaseModel):
    """Full medication record sent back to the app."""
    medication_id: int  # Unique ID for this medication record
    user_id: int  # Which patient takes this medication
    drug_class: str  # Category of drug
    drug_name: str  # Name of the drug
    dose: Optional[str] = None  # Dosage amount
    frequency: str  # How often they take it
    is_hr_blunting: bool  # Does this drug slow heart rate? (affects exercise targets)
    is_anticoagulant: bool  # Does this drug thin blood? (affects exercise safety)
    status: str  # Active, discontinued, or on hold
    start_date: Optional[date] = None  # When they started taking it
    end_date: Optional[date] = None  # When they stopped (if applicable)
    prescribed_by: Optional[str] = None  # Doctor who prescribed it
    notes: Optional[str] = None  # Additional notes
    created_at: Optional[datetime] = None  # When record was created
    updated_at: Optional[datetime] = None  # When record was last changed

    class Config:
        from_attributes = True


class MedicalProfileSummary(BaseModel):
    """Quick snapshot of a patient's medical profile for AI and dashboards."""
    user_id: int  # Which patient this summary is for
    has_prior_mi: bool = False  # Did they have a heart attack before?
    has_heart_failure: bool = False  # Do they have heart failure?
    is_on_beta_blocker: bool = False  # Are they taking a heart-rate-slowing drug?
    is_on_anticoagulant: bool = False  # Are they on blood thinners?
    has_uploaded_document: bool = False  # Has a clinical document been uploaded?
    has_accessible_document: bool = False  # Is the uploaded document still accessible?
    active_condition_count: int = 0  # How many active conditions they have
    active_medication_count: int = 0  # How many medications they're currently taking


# =============================================================================
# Combined Medical Profile (conditions + medications + AI flags)
# =============================================================================

class MedicalProfileResponse(BaseModel):
    """Complete medical profile with conditions, medications, and AI-ready flags."""
    user_id: int  # Which patient this profile is for
    conditions: List[MedicalHistoryResponse]  # List of all their medical conditions
    medications: List[MedicationResponse]  # List of all their medications
    # Pre-computed flags so the AI and dashboard can quickly check key facts
    has_prior_mi: bool = False  # Had a heart attack before?
    has_heart_failure: bool = False  # Has heart failure?
    heart_failure_class: Optional[str] = None  # Severity class of heart failure (if applicable)
    is_on_beta_blocker: bool = False  # Taking a drug that slows heart rate?
    is_on_anticoagulant: bool = False  # On blood thinners?
    is_on_antiplatelet: bool = False  # On clot-prevention drugs?
    active_condition_count: int = 0  # Number of active medical conditions
    active_medication_count: int = 0  # Number of current medications
    uploaded_documents: List["UploadedDocumentSummaryResponse"] = []  # Clinical documents on file
    latest_document_url: Optional[str] = None  # Link to the most recent document
    has_document_storage_warning: bool = False  # Are any stored documents missing from storage?
    missing_document_count: int = 0  # How many documents can't be found on disk


class UploadedDocumentSummaryResponse(BaseModel):
    """Summary info about one uploaded clinical document."""
    document_id: int  # Unique ID for this document
    filename: str  # Original file name
    file_type: str  # File type (e.g. pdf, jpg)
    status: str  # Processing status: uploaded, extracted, reviewed, or failed
    created_at: Optional[datetime] = None  # When the file was uploaded
    view_url: str  # URL to view or download the document
    file_available: bool = True  # Can the file still be found on the server?


class MedicalExtractionStatusResponse(BaseModel):
    """Shows whether the AI document extraction system is ready to use."""
    feature: str  # Name of the extraction feature
    provider: str  # AI provider being used (e.g. Google)
    model: str  # AI model name (e.g. Gemini)
    gemini_key_configured: bool  # Is the API key set up in the config?
    gemini_sdk_available: bool  # Is the AI software library installed?
    ready: bool  # Can we actually extract data from documents right now?


# =============================================================================
# Document Extraction Schemas
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """What the server sends back after processing an uploaded clinical document."""
    document_id: int  # Unique ID for the uploaded document
    filename: str  # Original file name
    status: str  # Processing status after upload
    extracted_conditions: List[MedicalHistoryCreate] = []  # Medical conditions found in the document
    extracted_medications: List[MedicationCreate] = []  # Medications found in the document
    extraction_message: str = ""  # A message about how the extraction went


class ExtractionConfirmRequest(BaseModel):
    document_id: int
    conditions: List[MedicalHistoryCreate] = []
    medications: List[MedicationCreate] = []
