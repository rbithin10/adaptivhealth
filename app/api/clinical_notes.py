"""
Clinical Notes API endpoints.

Clinician-authored notes per patient. Displayed in the AI Risk Summary panel
and used as context for future AI-generated summaries.

# =============================================================================
# FILE MAP
# =============================================================================
# ENDPOINTS
#   - GET  /clinical-notes/{user_id}... Line 50  (List notes for patient)
#   - POST /clinical-notes............. Line 85  (Create note)
#   - PATCH /clinical-notes/{note_id}.. Line 120 (Update note)
#   - DELETE /clinical-notes/{note_id}. Line 155 (Delete note)
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List
import logging

from app.database import get_db
from app.models.user import User
from app.models.clinical_note import ClinicalNote
from app.schemas.clinical_note import ClinicalNoteCreate, ClinicalNoteUpdate, ClinicalNoteResponse
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _note_to_response(note: ClinicalNote, db: Session) -> ClinicalNoteResponse:
    """Build a ClinicalNoteResponse, joining clinician name from users table."""
    clinician = db.query(User).filter(User.user_id == note.clinician_id).first()
    clinician_name = None
    if clinician:
        first = getattr(clinician, "first_name", None) or ""
        last = getattr(clinician, "last_name", None) or ""
        full = f"{first} {last}".strip()
        clinician_name = full if full else getattr(clinician, "email", None)

    return ClinicalNoteResponse(
        note_id=note.note_id,
        user_id=note.user_id,
        clinician_id=note.clinician_id,
        clinician_name=clinician_name,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


# =============================================================================
# GET — List all notes for a patient (newest first)
# =============================================================================
@router.get("/clinical-notes/{user_id}", response_model=List[ClinicalNoteResponse])
def get_clinical_notes(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all clinical notes for a patient, ordered newest first.

    Used by the AI Risk Summary panel to show longitudinal clinician context.
    """
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.user_id == user_id)
        .order_by(desc(ClinicalNote.created_at))
        .all()
    )
    return [_note_to_response(n, db) for n in notes]


# =============================================================================
# POST — Create a new note
# =============================================================================
@router.post("/clinical-notes", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
def create_clinical_note(
    payload: ClinicalNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new clinical note for a patient.

    The clinician_id is set automatically from the authenticated user.
    """
    note = ClinicalNote(
        user_id=payload.user_id,
        clinician_id=current_user.user_id,
        content=payload.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    logger.info(f"Clinical note {note.note_id} created for patient {payload.user_id} by clinician {current_user.user_id}")
    return _note_to_response(note, db)


# =============================================================================
# PATCH — Update note content
# =============================================================================
@router.patch("/clinical-notes/{note_id}", response_model=ClinicalNoteResponse)
def update_clinical_note(
    note_id: int,
    payload: ClinicalNoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the content of an existing clinical note."""
    note = db.query(ClinicalNote).filter(ClinicalNote.note_id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note.content = payload.content
    db.commit()
    db.refresh(note)
    return _note_to_response(note, db)


# =============================================================================
# DELETE — Remove a note
# =============================================================================
@router.delete("/clinical-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clinical_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a clinical note."""
    note = db.query(ClinicalNote).filter(ClinicalNote.note_id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    db.delete(note)
    db.commit()
    logger.info(f"Clinical note {note_id} deleted by clinician {current_user.user_id}")
