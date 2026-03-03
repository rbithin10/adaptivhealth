"""
Pydantic schemas for medication reminders and adherence tracking.

Request/response validation for the Medication Reminder API endpoints.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# SCHEMAS
#   - ReminderSettingUpdate............. Line 25  (Update reminder settings)
#   - ReminderResponse.................. Line 40  (Medication with reminder info)
#   - AdherenceCreate................... Line 60  (Log adherence input)
#   - AdherenceResponse................. Line 75  (Single adherence record)
#   - AdherenceHistoryResponse.......... Line 95  (Aggregated history)
# =============================================================================
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
import re


class ReminderSettingUpdate(BaseModel):
    """Schema for updating medication reminder settings."""
    reminder_time: Optional[str] = Field(
        None,
        description="Time for daily reminder in HH:MM format (e.g., '08:00', '20:00')"
    )
    reminder_enabled: Optional[bool] = Field(
        None,
        description="Whether reminder notifications are enabled"
    )

    @field_validator("reminder_time")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time is in HH:MM format."""
        if v is not None and not re.match(r"^[0-2][0-9]:[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (e.g., '08:00')")
        if v is not None:
            hour = int(v.split(":")[0])
            if hour > 23:
                raise ValueError("Hour must be between 00 and 23")
        return v


class ReminderCreate(BaseModel):
    """Schema for creating/enabling medication reminder settings."""
    medication_id: int = Field(..., description="ID of the medication")
    reminder_time: str = Field(
        ...,
        description="Time for daily reminder in HH:MM format (e.g., '08:00', '20:00')"
    )
    reminder_enabled: bool = Field(
        default=True,
        description="Whether reminder notifications are enabled"
    )

    @field_validator("reminder_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time is in HH:MM format."""
        if not re.match(r"^[0-2][0-9]:[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (e.g., '08:00')")
        hour = int(v.split(":")[0])
        if hour > 23:
            raise ValueError("Hour must be between 00 and 23")
        return v


class ReminderResponse(BaseModel):
    """Schema for medication with reminder info."""
    medication_id: int = Field(..., description="Unique medication ID")
    drug_name: str = Field(..., description="Name of the medication")
    dose: Optional[str] = Field(None, description="Dosage (e.g., '25mg')")
    frequency: str = Field(..., description="Frequency (e.g., 'daily')")
    reminder_time: Optional[str] = Field(None, description="Reminder time in HH:MM format")
    reminder_enabled: bool = Field(False, description="Whether reminder is enabled")

    class Config:
        from_attributes = True


class AdherenceCreate(BaseModel):
    """Schema for logging medication adherence."""
    medication_id: int = Field(..., description="ID of the medication")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    taken: bool = Field(..., description="True if taken, False if skipped")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class AdherenceResponse(BaseModel):
    """Schema for a single adherence record."""
    adherence_id: int = Field(..., description="Unique adherence record ID")
    medication_id: int = Field(..., description="ID of the medication")
    drug_name: str = Field(..., description="Name of the medication")
    scheduled_date: date = Field(..., description="Date the medication was scheduled")
    taken: Optional[bool] = Field(None, description="True=taken, False=skipped, None=no response")
    responded_at: Optional[datetime] = Field(None, description="When the response was recorded")

    class Config:
        from_attributes = True


class AdherenceHistoryResponse(BaseModel):
    """Schema for aggregated adherence history."""
    entries: List[AdherenceResponse] = Field(default_factory=list, description="List of adherence records")
    total_scheduled: int = Field(..., description="Total doses scheduled in period")
    total_taken: int = Field(..., description="Total doses taken in period")
    adherence_percent: float = Field(..., description="Percentage of doses taken (0-100)")

    class Config:
        from_attributes = True
