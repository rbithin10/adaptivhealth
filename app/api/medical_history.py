"""
Medical History & Medications API endpoints.

Structured cardiac history, medications, and combined medical profile
for clinician management and AI risk-scoring integration.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
# HELPER: build_medical_profile........ Line 50
#
# CLINICIAN ENDPOINTS
#   - GET  /patients/{id}/medical-history........... Line 100
#   - POST /patients/{id}/medical-history........... Line 130
#   - PUT  /patients/{id}/medical-history/{hid}..... Line 175
#   - DELETE /patients/{id}/medical-history/{hid}... Line 220
#   - GET  /patients/{id}/medications............... Line 255
#   - POST /patients/{id}/medications............... Line 285
#   - PUT  /patients/{id}/medications/{mid}......... Line 335
#   - DELETE /patients/{id}/medications/{mid}........ Line 380
#   - GET  /patients/{id}/medical-profile........... Line 410
#
# PATIENT ENDPOINTS (read-only, own data)
#   - GET  /me/medical-history...................... Line 440
#   - GET  /me/medications.......................... Line 465
#   - GET  /me/medical-profile...................... Line 490
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import logging
import uuid
from cryptography.fernet import InvalidToken
from pydantic import ValidationError

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.medical_history import PatientMedicalHistory, PatientMedication, UploadedDocument
from app.schemas.medical_history import (
    MedicalHistoryCreate, MedicalHistoryUpdate, MedicalHistoryResponse,
    MedicationCreate, MedicationUpdate, MedicationResponse,
    MedicalProfileResponse, DocumentUploadResponse, ExtractionConfirmRequest,
    MedicalExtractionStatusResponse,
)
from app.api.auth import get_current_user, get_current_doctor_user, check_clinician_phi_access

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_document_view_url(user_id: int, document_id: int) -> str:
    """Build relative API URL for authenticated document viewing."""
    return f"/api/v1/patients/{user_id}/documents/{document_id}/view"


@router.get("/medical-extraction/status", response_model=MedicalExtractionStatusResponse)
async def get_medical_extraction_status(
    clinician: User = Depends(get_current_doctor_user),
):
    """Return document extraction readiness status for clinicians/admins."""
    del clinician  # endpoint requires role check only

    gemini_key_configured = bool(settings.gemini_api_key)

    try:
        import google.generativeai as genai  # noqa: F401
        gemini_sdk_available = True
    except Exception:
        gemini_sdk_available = False

    return MedicalExtractionStatusResponse(
        feature="medical_document_extraction",
        provider="google_gemini",
        model="gemini-2.5-flash",
        gemini_key_configured=gemini_key_configured,
        gemini_sdk_available=gemini_sdk_available,
        ready=gemini_key_configured and gemini_sdk_available,
    )


# =============================================================================
# Helper: Build Medical Profile with AI Flags
# =============================================================================

def build_medical_profile(user_id: int, db: Session) -> MedicalProfileResponse:
    """
    Build combined medical profile with pre-computed AI flags.

    Queries conditions and medications, then computes boolean flags
    used by risk scoring and exercise recommendations.
    """
    conditions = (
        db.query(PatientMedicalHistory)
        .filter(PatientMedicalHistory.user_id == user_id)
        .order_by(desc(PatientMedicalHistory.created_at))
        .all()
    )

    medications = (
        db.query(PatientMedication)
        .filter(PatientMedication.user_id == user_id)
        .order_by(desc(PatientMedication.created_at))
        .all()
    )

    uploaded_documents = (
        db.query(UploadedDocument)
        .filter(UploadedDocument.user_id == user_id)
        .order_by(desc(UploadedDocument.created_at))
        .all()
    )

    # Compute AI flags from conditions
    active_conditions = [c for c in conditions if c.status == "active"]
    active_meds = [m for m in medications if m.status == "active"]

    has_prior_mi = any(c.condition_type == "prior_mi" for c in active_conditions)
    has_heart_failure = any(c.condition_type == "heart_failure" for c in active_conditions)

    # Extract NYHA class from condition_detail (e.g., "NYHA Class II" → "II")
    heart_failure_class = None
    for c in active_conditions:
        if c.condition_type == "heart_failure" and c.condition_detail:
            detail = c.condition_detail.upper()
            for cls in ["IV", "III", "II", "I"]:
                if cls in detail:
                    heart_failure_class = cls
                    break

    # Compute AI flags from medications
    is_on_beta_blocker = any(m.drug_class == "beta_blocker" for m in active_meds)
    is_on_anticoagulant = any(m.is_anticoagulant for m in active_meds)
    is_on_antiplatelet = any(m.drug_class == "antiplatelet" for m in active_meds)

    # Build response objects (decrypt notes for authorized viewers)
    from app.services.encryption import decrypt_phi

    condition_responses = []
    for c in conditions:
        resp = MedicalHistoryResponse(
            history_id=c.history_id,
            user_id=c.user_id,
            condition_type=c.condition_type,
            condition_detail=c.condition_detail,
            diagnosis_date=c.diagnosis_date,
            status=c.status,
            notes=decrypt_phi(c.notes_encrypted),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        condition_responses.append(resp)

    medication_responses = []
    for m in medications:
        resp = MedicationResponse(
            medication_id=m.medication_id,
            user_id=m.user_id,
            drug_class=m.drug_class,
            drug_name=m.drug_name,
            dose=m.dose,
            frequency=m.frequency,
            is_hr_blunting=m.is_hr_blunting,
            is_anticoagulant=m.is_anticoagulant,
            status=m.status,
            start_date=m.start_date,
            end_date=m.end_date,
            prescribed_by=m.prescribed_by,
            notes=decrypt_phi(m.notes_encrypted),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        medication_responses.append(resp)

    document_responses = []
    for doc in uploaded_documents:
        is_available = Path(doc.file_path).is_file()
        document_responses.append(
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "status": doc.status,
                "created_at": doc.created_at,
                "view_url": _build_document_view_url(user_id, doc.document_id),
                "file_available": is_available,
            }
        )

    first_available = next((d for d in document_responses if d.get("file_available")), None)
    latest_document_url = first_available["view_url"] if first_available else None
    missing_document_count = sum(1 for d in document_responses if not d.get("file_available", False))

    return MedicalProfileResponse(
        user_id=user_id,
        conditions=condition_responses,
        medications=medication_responses,
        has_prior_mi=has_prior_mi,
        has_heart_failure=has_heart_failure,
        heart_failure_class=heart_failure_class,
        is_on_beta_blocker=is_on_beta_blocker,
        is_on_anticoagulant=is_on_anticoagulant,
        is_on_antiplatelet=is_on_antiplatelet,
        active_condition_count=len(active_conditions),
        active_medication_count=len(active_meds),
        uploaded_documents=document_responses,
        latest_document_url=latest_document_url,
        has_document_storage_warning=missing_document_count > 0,
        missing_document_count=missing_document_count,
    )


def _get_patient_or_404(patient_id: int, db: Session) -> User:
    """Fetch patient by ID or raise 404."""
    patient = db.query(User).filter(User.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


# =============================================================================
# Clinician Endpoints — Medical History
# =============================================================================

@router.get("/patients/{patient_id}/medical-history", response_model=List[MedicalHistoryResponse])
async def get_patient_medical_history(
    patient_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Get a patient's medical conditions (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    conditions = (
        db.query(PatientMedicalHistory)
        .filter(PatientMedicalHistory.user_id == patient_id)
        .order_by(desc(PatientMedicalHistory.created_at))
        .all()
    )

    from app.services.encryption import decrypt_phi
    results = []
    for c in conditions:
        results.append(MedicalHistoryResponse(
            history_id=c.history_id, user_id=c.user_id,
            condition_type=c.condition_type, condition_detail=c.condition_detail,
            diagnosis_date=c.diagnosis_date, status=c.status,
            notes=decrypt_phi(c.notes_encrypted),
            created_at=c.created_at, updated_at=c.updated_at,
        ))

    logger.info(f"Clinician {clinician.user_id} viewed medical history for patient {patient_id}")
    return results


@router.post("/patients/{patient_id}/medical-history", response_model=MedicalHistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_patient_condition(
    patient_id: int,
    data: MedicalHistoryCreate,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Add a medical condition to a patient's history (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    from app.services.encryption import encrypt_phi

    try:
        condition = PatientMedicalHistory(
            user_id=patient_id,
            condition_type=data.condition_type.value,
            condition_detail=data.condition_detail,
            diagnosis_date=data.diagnosis_date,
            status=data.status,
            notes_encrypted=encrypt_phi(data.notes) if data.notes else None,
            created_by=clinician.user_id,
            updated_by=clinician.user_id,
        )
        db.add(condition)
        db.commit()
        db.refresh(condition)

        logger.info(
            f"Condition added: history_id={condition.history_id}, patient={patient_id}, "
            f"type={data.condition_type.value}, by clinician {clinician.user_id}"
        )

        return MedicalHistoryResponse(
            history_id=condition.history_id, user_id=condition.user_id,
            condition_type=condition.condition_type, condition_detail=condition.condition_detail,
            diagnosis_date=condition.diagnosis_date, status=condition.status,
            notes=data.notes,
            created_at=condition.created_at, updated_at=condition.updated_at,
        )
    except (SQLAlchemyError, ValueError, InvalidToken) as e:
        db.rollback()
        logger.error(f"Failed to add condition for patient {patient_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add condition")


@router.put("/patients/{patient_id}/medical-history/{history_id}", response_model=MedicalHistoryResponse)
async def update_patient_condition(
    patient_id: int,
    history_id: int,
    data: MedicalHistoryUpdate,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Update a medical condition (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    condition = db.query(PatientMedicalHistory).filter(
        PatientMedicalHistory.history_id == history_id,
        PatientMedicalHistory.user_id == patient_id,
    ).first()
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    from app.services.encryption import encrypt_phi, decrypt_phi

    try:
        if data.condition_detail is not None:
            condition.condition_detail = data.condition_detail
        if data.diagnosis_date is not None:
            condition.diagnosis_date = data.diagnosis_date
        if data.status is not None:
            condition.status = data.status
        if data.notes is not None:
            condition.notes_encrypted = encrypt_phi(data.notes) if data.notes else None
        condition.updated_by = clinician.user_id

        db.commit()
        db.refresh(condition)

        logger.info(f"Condition updated: history_id={history_id}, patient={patient_id}, by clinician {clinician.user_id}")

        return MedicalHistoryResponse(
            history_id=condition.history_id, user_id=condition.user_id,
            condition_type=condition.condition_type, condition_detail=condition.condition_detail,
            diagnosis_date=condition.diagnosis_date, status=condition.status,
            notes=decrypt_phi(condition.notes_encrypted),
            created_at=condition.created_at, updated_at=condition.updated_at,
        )
    except (SQLAlchemyError, ValueError, InvalidToken) as e:
        db.rollback()
        logger.error(f"Failed to update condition {history_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update condition")


@router.delete("/patients/{patient_id}/medical-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_condition(
    patient_id: int,
    history_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Remove a medical condition (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    condition = db.query(PatientMedicalHistory).filter(
        PatientMedicalHistory.history_id == history_id,
        PatientMedicalHistory.user_id == patient_id,
    ).first()
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    try:
        db.delete(condition)
        db.commit()
        logger.info(f"Condition deleted: history_id={history_id}, patient={patient_id}, by clinician {clinician.user_id}")
        return None
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete condition {history_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete condition")


# =============================================================================
# Clinician Endpoints — Medications
# =============================================================================

@router.get("/patients/{patient_id}/medications", response_model=List[MedicationResponse])
async def get_patient_medications(
    patient_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Get a patient's medications (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    medications = (
        db.query(PatientMedication)
        .filter(PatientMedication.user_id == patient_id)
        .order_by(desc(PatientMedication.created_at))
        .all()
    )

    from app.services.encryption import decrypt_phi
    results = []
    for m in medications:
        results.append(MedicationResponse(
            medication_id=m.medication_id, user_id=m.user_id,
            drug_class=m.drug_class, drug_name=m.drug_name,
            dose=m.dose, frequency=m.frequency,
            is_hr_blunting=m.is_hr_blunting, is_anticoagulant=m.is_anticoagulant,
            status=m.status, start_date=m.start_date, end_date=m.end_date,
            prescribed_by=m.prescribed_by,
            notes=decrypt_phi(m.notes_encrypted),
            created_at=m.created_at, updated_at=m.updated_at,
        ))

    logger.info(f"Clinician {clinician.user_id} viewed medications for patient {patient_id}")
    return results


@router.post("/patients/{patient_id}/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def add_patient_medication(
    patient_id: int,
    data: MedicationCreate,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Add a medication to a patient (clinician only). Auto-sets clinical flags."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    from app.services.encryption import encrypt_phi

    # Auto-set clinical flags based on drug class
    is_hr_blunting = data.drug_class.value in ("beta_blocker",)
    is_anticoagulant = data.drug_class.value in ("anticoagulant",)

    try:
        medication = PatientMedication(
            user_id=patient_id,
            drug_class=data.drug_class.value,
            drug_name=data.drug_name,
            dose=data.dose,
            frequency=data.frequency,
            is_hr_blunting=is_hr_blunting,
            is_anticoagulant=is_anticoagulant,
            start_date=data.start_date,
            prescribed_by=data.prescribed_by,
            notes_encrypted=encrypt_phi(data.notes) if data.notes else None,
            created_by=clinician.user_id,
            updated_by=clinician.user_id,
        )
        db.add(medication)
        db.commit()
        db.refresh(medication)

        logger.info(
            f"Medication added: medication_id={medication.medication_id}, patient={patient_id}, "
            f"drug={data.drug_name}, class={data.drug_class.value}, "
            f"hr_blunting={is_hr_blunting}, anticoagulant={is_anticoagulant}, "
            f"by clinician {clinician.user_id}"
        )

        return MedicationResponse(
            medication_id=medication.medication_id, user_id=medication.user_id,
            drug_class=medication.drug_class, drug_name=medication.drug_name,
            dose=medication.dose, frequency=medication.frequency,
            is_hr_blunting=medication.is_hr_blunting, is_anticoagulant=medication.is_anticoagulant,
            status=medication.status, start_date=medication.start_date, end_date=medication.end_date,
            prescribed_by=medication.prescribed_by,
            notes=data.notes,
            created_at=medication.created_at, updated_at=medication.updated_at,
        )
    except (SQLAlchemyError, ValueError, InvalidToken) as e:
        db.rollback()
        logger.error(f"Failed to add medication for patient {patient_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add medication")


@router.put("/patients/{patient_id}/medications/{medication_id}", response_model=MedicationResponse)
async def update_patient_medication(
    patient_id: int,
    medication_id: int,
    data: MedicationUpdate,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Update a medication (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    medication = db.query(PatientMedication).filter(
        PatientMedication.medication_id == medication_id,
        PatientMedication.user_id == patient_id,
    ).first()
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    from app.services.encryption import encrypt_phi, decrypt_phi

    try:
        if data.drug_name is not None:
            medication.drug_name = data.drug_name
        if data.dose is not None:
            medication.dose = data.dose
        if data.frequency is not None:
            medication.frequency = data.frequency
        if data.status is not None:
            medication.status = data.status
        if data.end_date is not None:
            medication.end_date = data.end_date
        if data.notes is not None:
            medication.notes_encrypted = encrypt_phi(data.notes) if data.notes else None
        medication.updated_by = clinician.user_id

        db.commit()
        db.refresh(medication)

        logger.info(f"Medication updated: medication_id={medication_id}, patient={patient_id}, by clinician {clinician.user_id}")

        return MedicationResponse(
            medication_id=medication.medication_id, user_id=medication.user_id,
            drug_class=medication.drug_class, drug_name=medication.drug_name,
            dose=medication.dose, frequency=medication.frequency,
            is_hr_blunting=medication.is_hr_blunting, is_anticoagulant=medication.is_anticoagulant,
            status=medication.status, start_date=medication.start_date, end_date=medication.end_date,
            prescribed_by=medication.prescribed_by,
            notes=decrypt_phi(medication.notes_encrypted),
            created_at=medication.created_at, updated_at=medication.updated_at,
        )
    except (SQLAlchemyError, ValueError, InvalidToken) as e:
        db.rollback()
        logger.error(f"Failed to update medication {medication_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update medication")


@router.delete("/patients/{patient_id}/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_medication(
    patient_id: int,
    medication_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Remove a medication (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    medication = db.query(PatientMedication).filter(
        PatientMedication.medication_id == medication_id,
        PatientMedication.user_id == patient_id,
    ).first()
    if not medication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    try:
        db.delete(medication)
        db.commit()
        logger.info(f"Medication deleted: medication_id={medication_id}, patient={patient_id}, by clinician {clinician.user_id}")
        return None
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete medication {medication_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete medication")


# =============================================================================
# Clinician Endpoint — Combined Medical Profile
# =============================================================================

@router.get("/patients/{patient_id}/medical-profile", response_model=MedicalProfileResponse)
async def get_patient_medical_profile(
    patient_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Get combined medical profile with AI flags (clinician only)."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    profile = build_medical_profile(patient_id, db)
    logger.info(f"Clinician {clinician.user_id} viewed medical profile for patient {patient_id}")
    return profile


@router.get("/patients/{patient_id}/documents/{document_id}/view")
async def view_uploaded_document(
    patient_id: int,
    document_id: int,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """Stream an uploaded patient document for authorized clinicians/admins."""
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    document = (
        db.query(UploadedDocument)
        .filter(
            UploadedDocument.document_id == document_id,
            UploadedDocument.user_id == patient_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = Path(document.file_path)
    if not file_path.exists() or not file_path.is_file():
        logger.warning(
            f"Document file missing on disk: doc={document_id}, patient={patient_id}, path={document.file_path}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")

    return FileResponse(
        path=str(file_path),
        filename=document.filename,
        media_type="application/pdf" if (document.file_type or "").lower() == "pdf" else "text/plain",
    )


# =============================================================================
# Patient Endpoints (read-only, own data)
# =============================================================================

@router.get("/me/medical-history", response_model=List[MedicalHistoryResponse])
async def get_my_medical_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View own medical conditions (patient, read-only)."""
    conditions = (
        db.query(PatientMedicalHistory)
        .filter(PatientMedicalHistory.user_id == current_user.user_id)
        .order_by(desc(PatientMedicalHistory.created_at))
        .all()
    )

    from app.services.encryption import decrypt_phi
    return [
        MedicalHistoryResponse(
            history_id=c.history_id, user_id=c.user_id,
            condition_type=c.condition_type, condition_detail=c.condition_detail,
            diagnosis_date=c.diagnosis_date, status=c.status,
            notes=decrypt_phi(c.notes_encrypted),
            created_at=c.created_at, updated_at=c.updated_at,
        )
        for c in conditions
    ]


@router.get("/me/medications", response_model=List[MedicationResponse])
async def get_my_medications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View own medications (patient, read-only)."""
    medications = (
        db.query(PatientMedication)
        .filter(PatientMedication.user_id == current_user.user_id)
        .order_by(desc(PatientMedication.created_at))
        .all()
    )

    from app.services.encryption import decrypt_phi
    return [
        MedicationResponse(
            medication_id=m.medication_id, user_id=m.user_id,
            drug_class=m.drug_class, drug_name=m.drug_name,
            dose=m.dose, frequency=m.frequency,
            is_hr_blunting=m.is_hr_blunting, is_anticoagulant=m.is_anticoagulant,
            status=m.status, start_date=m.start_date, end_date=m.end_date,
            prescribed_by=m.prescribed_by,
            notes=decrypt_phi(m.notes_encrypted),
            created_at=m.created_at, updated_at=m.updated_at,
        )
        for m in medications
    ]


@router.get("/me/medical-profile", response_model=MedicalProfileResponse)
async def get_my_medical_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View own combined medical profile with AI flags (patient, read-only)."""
    return build_medical_profile(current_user.user_id, db)


# =============================================================================
# Document Upload & Gemini Extraction
# =============================================================================

# Upload directory (project root / uploads / {user_id} /)
UPLOAD_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE_MB = 5
ALLOWED_EXTENSIONS = {"pdf", "txt"}


@router.post("/patients/{patient_id}/upload-document", response_model=DocumentUploadResponse)
async def upload_patient_document(
    patient_id: int,
    file: UploadFile = File(...),
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Upload a clinical document (PDF/TXT) and extract structured medical data
    using Google Gemini AI.

    Returns extracted conditions and medications for clinician review
    before saving to the database.
    """
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file contents and check size
    contents = await file.read()
    file_size_kb = len(contents) // 1024
    if file_size_kb > MAX_FILE_SIZE_MB * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size_kb}KB). Maximum: {MAX_FILE_SIZE_MB}MB"
        )

    # Save to disk: uploads/{user_id}/{uuid}_{filename}
    user_dir = UPLOAD_BASE_DIR / str(patient_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = user_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"Document saved: {file_path} ({file_size_kb}KB) by clinician {clinician.user_id}")

    # Save document record
    doc = UploadedDocument(
        user_id=patient_id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=ext,
        file_size_kb=file_size_kb,
        status="uploaded",
        uploaded_by=clinician.user_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Call Gemini extraction
    from app.services.document_extraction import extract_medical_data
    from app.config import get_settings
    settings = get_settings()

    extraction_result = await extract_medical_data(
        file_path=str(file_path),
        file_type=ext,
        gemini_api_key=settings.gemini_api_key,
    )

    # Store raw extraction result
    import json
    doc.extracted_json = json.dumps(extraction_result)
    doc.status = "extracted" if not extraction_result.get("error") else "failed"
    db.commit()

    # Convert raw dicts to validated Pydantic schemas (best-effort)
    extracted_conditions = []
    for c in extraction_result.get("conditions", []):
        try:
            extracted_conditions.append(MedicalHistoryCreate(
                condition_type=c.get("condition_type", "other"),
                condition_detail=c.get("condition_detail"),
                status=c.get("status", "active"),
            ))
        except (ValidationError, ValueError, KeyError, TypeError):
            logger.warning(f"Skipping invalid extracted condition: {c}")

    extracted_medications = []
    for m in extraction_result.get("medications", []):
        try:
            extracted_medications.append(MedicationCreate(
                drug_class=m.get("drug_class", "other"),
                drug_name=m.get("drug_name", "Unknown"),
                dose=m.get("dose"),
                frequency=m.get("frequency", "daily"),
            ))
        except (ValidationError, ValueError, KeyError, TypeError):
            logger.warning(f"Skipping invalid extracted medication: {m}")

    error_msg = extraction_result.get("error") or ""
    extraction_message = (
        f"Extracted {len(extracted_conditions)} conditions and {len(extracted_medications)} medications. "
        "Please review and edit before confirming."
    ) if not error_msg else error_msg

    return DocumentUploadResponse(
        document_id=doc.document_id,
        filename=file.filename,
        status=doc.status,
        extracted_conditions=extracted_conditions,
        extracted_medications=extracted_medications,
        extraction_message=extraction_message,
    )


@router.post("/patients/{patient_id}/confirm-extraction", response_model=MedicalProfileResponse)
async def confirm_document_extraction(
    patient_id: int,
    data: ExtractionConfirmRequest,
    clinician: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Clinician confirms (and optionally edits) extracted data from a document.
    Saves the reviewed conditions and medications to the database.
    """
    patient = _get_patient_or_404(patient_id, db)
    check_clinician_phi_access(clinician, patient)

    # Verify document exists
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.document_id == data.document_id,
        UploadedDocument.user_id == patient_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.services.encryption import encrypt_phi

    try:
        # Save confirmed conditions
        for c in data.conditions:
            condition = PatientMedicalHistory(
                user_id=patient_id,
                condition_type=c.condition_type.value,
                condition_detail=c.condition_detail,
                diagnosis_date=c.diagnosis_date,
                status=c.status,
                notes_encrypted=encrypt_phi(c.notes) if c.notes else None,
                created_by=clinician.user_id,
                updated_by=clinician.user_id,
            )
            db.add(condition)

        # Save confirmed medications (with auto-set clinical flags)
        for m in data.medications:
            is_hr_blunting = m.drug_class.value in ("beta_blocker",)
            is_anticoagulant = m.drug_class.value in ("anticoagulant",)
            medication = PatientMedication(
                user_id=patient_id,
                drug_class=m.drug_class.value,
                drug_name=m.drug_name,
                dose=m.dose,
                frequency=m.frequency,
                is_hr_blunting=is_hr_blunting,
                is_anticoagulant=is_anticoagulant,
                start_date=m.start_date,
                prescribed_by=m.prescribed_by,
                notes_encrypted=encrypt_phi(m.notes) if m.notes else None,
                created_by=clinician.user_id,
                updated_by=clinician.user_id,
            )
            db.add(medication)

        # Update document status
        doc.status = "reviewed"
        db.commit()

        logger.info(
            f"Extraction confirmed: doc={data.document_id}, patient={patient_id}, "
            f"{len(data.conditions)} conditions + {len(data.medications)} medications, "
            f"by clinician {clinician.user_id}"
        )

        # Return updated profile
        return build_medical_profile(patient_id, db)

    except (SQLAlchemyError, ValueError, InvalidToken) as e:
        db.rollback()
        logger.error(f"Failed to confirm extraction for patient {patient_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to save extracted data: {str(e)}")
