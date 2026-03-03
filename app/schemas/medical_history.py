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
    prior_mi = "prior_mi"
    cabg = "cabg"
    pci_stent = "pci_stent"
    heart_failure = "heart_failure"
    valve_disease = "valve_disease"
    atrial_fibrillation = "atrial_fibrillation"
    other_arrhythmia = "other_arrhythmia"
    hypertension = "hypertension"
    diabetes_type1 = "diabetes_type1"
    diabetes_type2 = "diabetes_type2"
    dyslipidemia = "dyslipidemia"
    ckd = "ckd"
    copd = "copd"
    pad = "pad"
    stroke_tia = "stroke_tia"
    smoking = "smoking"
    family_cvd = "family_cvd"
    obesity = "obesity"
    other = "other"


class DrugClassEnum(str, Enum):
    beta_blocker = "beta_blocker"
    ace_inhibitor = "ace_inhibitor"
    arb = "arb"
    antiplatelet = "antiplatelet"
    anticoagulant = "anticoagulant"
    statin = "statin"
    diuretic = "diuretic"
    ccb = "ccb"
    nitrate = "nitrate"
    antiarrhythmic = "antiarrhythmic"
    insulin = "insulin"
    metformin = "metformin"
    sglt2_inhibitor = "sglt2_inhibitor"
    other = "other"


# =============================================================================
# Medical History Schemas
# =============================================================================

class MedicalHistoryCreate(BaseModel):
    condition_type: ConditionTypeEnum
    condition_detail: Optional[str] = Field(None, max_length=255)
    diagnosis_date: Optional[date] = None
    status: str = Field("active", pattern=r"^(active|resolved|managed)$")
    notes: Optional[str] = Field(None, max_length=1000)


class MedicalHistoryUpdate(BaseModel):
    condition_detail: Optional[str] = Field(None, max_length=255)
    diagnosis_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern=r"^(active|resolved|managed)$")
    notes: Optional[str] = Field(None, max_length=1000)


class MedicalHistoryResponse(BaseModel):
    history_id: int
    user_id: int
    condition_type: str
    condition_detail: Optional[str] = None
    diagnosis_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Medication Schemas
# =============================================================================

class MedicationCreate(BaseModel):
    drug_class: DrugClassEnum
    drug_name: str = Field(..., min_length=1, max_length=100)
    dose: Optional[str] = Field(None, max_length=50)
    frequency: str = Field("daily", pattern=r"^(daily|twice_daily|three_times_daily|as_needed|weekly)$")
    start_date: Optional[date] = None
    prescribed_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class MedicationUpdate(BaseModel):
    drug_name: Optional[str] = Field(None, max_length=100)
    dose: Optional[str] = Field(None, max_length=50)
    frequency: Optional[str] = Field(None, pattern=r"^(daily|twice_daily|three_times_daily|as_needed|weekly)$")
    status: Optional[str] = Field(None, pattern=r"^(active|discontinued|on_hold)$")
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)


class MedicationResponse(BaseModel):
    medication_id: int
    user_id: int
    drug_class: str
    drug_name: str
    dose: Optional[str] = None
    frequency: str
    is_hr_blunting: bool
    is_anticoagulant: bool
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribed_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MedicalProfileSummary(BaseModel):
    user_id: int
    has_prior_mi: bool = False
    has_heart_failure: bool = False
    is_on_beta_blocker: bool = False
    is_on_anticoagulant: bool = False
    has_uploaded_document: bool = False
    has_accessible_document: bool = False
    active_condition_count: int = 0
    active_medication_count: int = 0


# =============================================================================
# Combined Medical Profile (conditions + medications + AI flags)
# =============================================================================

class MedicalProfileResponse(BaseModel):
    user_id: int
    conditions: List[MedicalHistoryResponse]
    medications: List[MedicationResponse]
    # Pre-computed flags for AI and UI
    has_prior_mi: bool = False
    has_heart_failure: bool = False
    heart_failure_class: Optional[str] = None
    is_on_beta_blocker: bool = False
    is_on_anticoagulant: bool = False
    is_on_antiplatelet: bool = False
    active_condition_count: int = 0
    active_medication_count: int = 0
    uploaded_documents: List["UploadedDocumentSummaryResponse"] = []
    latest_document_url: Optional[str] = None
    has_document_storage_warning: bool = False
    missing_document_count: int = 0


class UploadedDocumentSummaryResponse(BaseModel):
    document_id: int
    filename: str
    file_type: str
    status: str
    created_at: Optional[datetime] = None
    view_url: str
    file_available: bool = True


class MedicalExtractionStatusResponse(BaseModel):
    feature: str
    provider: str
    model: str
    gemini_key_configured: bool
    gemini_sdk_available: bool
    ready: bool


# =============================================================================
# Document Extraction Schemas
# =============================================================================

class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    extracted_conditions: List[MedicalHistoryCreate] = []
    extracted_medications: List[MedicationCreate] = []
    extraction_message: str = ""


class ExtractionConfirmRequest(BaseModel):
    document_id: int
    conditions: List[MedicalHistoryCreate] = []
    medications: List[MedicationCreate] = []
