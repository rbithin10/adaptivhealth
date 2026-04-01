"""
Clinical Note Schemas for API validation and responses.

# =============================================================================
# FILE MAP
# =============================================================================
# SCHEMAS
#   - ClinicalNoteCreate............... Line 20  (Create note input)
#   - ClinicalNoteUpdate............... Line 35  (Update note content)
#   - ClinicalNoteResponse............. Line 45  (Full note output)
# =============================================================================
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class ClinicalNoteCreate(BaseModel):
    """Schema for creating a new clinical note."""
    user_id: int = Field(..., description="Patient's user ID")
    content: str = Field(..., min_length=1, max_length=5000, description="Note content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


class ClinicalNoteUpdate(BaseModel):
    """Schema for updating an existing clinical note."""
    content: str = Field(..., min_length=1, max_length=5000, description="Updated note content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


class ClinicalNoteResponse(BaseModel):
    """Schema for clinical note response including clinician name."""
    note_id: int = Field(..., description="Unique note ID")
    user_id: int = Field(..., description="Patient's user ID")
    clinician_id: int = Field(..., description="Clinician's user ID")
    clinician_name: Optional[str] = Field(None, description="Clinician's full name")
    content: str = Field(..., description="Note content")
    created_at: datetime = Field(..., description="When the note was created")
    updated_at: datetime = Field(..., description="When the note was last updated")

    class Config:
        from_attributes = True
