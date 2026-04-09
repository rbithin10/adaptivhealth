"""
Medication Reminder API endpoints.

Patient medication reminder settings and adherence tracking.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
#
# ENDPOINTS - PATIENT
#   - GET /medications/reminders....... Line 50  (Get all med reminders)
#   - PUT /medications/{id}/reminder... Line 95  (Update reminder settings)
#   - POST /medications/adherence...... Line 140 (Log taken/skipped)
#   - GET /medications/adherence/history Line 190 (Get adherence stats)
#
# BUSINESS CONTEXT:
# - Patients can set daily medication reminders
# - Track adherence for compliance monitoring
# - Mobile app uses this for local notifications
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime, timezone, timedelta, date
import logging

from app.database import get_db
from app.models.user import User
from app.models.medical_history import PatientMedication, MedicationStatus
from app.models.medication_adherence import MedicationAdherence
from app.schemas.medication_reminder import (
    ReminderCreate,
    ReminderSettingUpdate,
    ReminderResponse,
    AdherenceCreate,
    AdherenceResponse,
    AdherenceHistoryResponse,
)
from app.api.auth import get_current_user_session_or_bearer

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# CREATE REMINDER - Create/enable reminder settings for a medication
# =============================================================================
@router.post("/medications/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_medication_reminder(
    payload: ReminderCreate,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Create or enable reminder settings for a specific medication.

    Args:
        payload: ReminderCreate with medication_id, reminder_time, reminder_enabled
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        ReminderResponse with updated reminder values

    Raises:
        404: Medication not found or not owned by user
    """
    medication = (
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.medication_id == payload.medication_id,  # Match the specific medication
                PatientMedication.user_id == current_user.user_id  # Make sure it belongs to this user
            )
        )
        .first()
    )

    if medication is None:  # Medication doesn't exist or isn't this user's
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    medication.reminder_time = payload.reminder_time  # Set the daily reminder time
    medication.reminder_enabled = payload.reminder_enabled  # Turn the reminder on or off

    db.commit()  # Save changes to the database
    db.refresh(medication)

    logger.info(
        f"Medication reminder created: med_id={payload.medication_id}, user={current_user.user_id}, "
        f"time={payload.reminder_time}, enabled={payload.reminder_enabled}"
    )

    return ReminderResponse(
        medication_id=medication.medication_id,
        drug_name=medication.drug_name,
        dose=medication.dose,
        frequency=medication.frequency,
        reminder_time=medication.reminder_time,
        reminder_enabled=medication.reminder_enabled or False,
    )


# =============================================================================
# GET REMINDERS - Fetch all medication reminders for current user
# =============================================================================
@router.get("/medications/reminders", response_model=List[ReminderResponse])
async def get_medication_reminders(
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Get all active medications with reminder settings for the current user.

    Returns medications where status='active', including reminder_time
    and reminder_enabled fields for local notification scheduling.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        List of medications with reminder info
    """
    medications = (
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.user_id == current_user.user_id,  # Only this user's medications
                PatientMedication.status == MedicationStatus.ACTIVE.value  # Only currently active ones
            )
        )
        .all()
    )

    result = []
    for med in medications:  # Build a response for each active medication with its reminder settings
        result.append(ReminderResponse(
            medication_id=med.medication_id,
            drug_name=med.drug_name,
            dose=med.dose,
            frequency=med.frequency,
            reminder_time=getattr(med, 'reminder_time', None),
            reminder_enabled=getattr(med, 'reminder_enabled', False) or False,
        ))

    logger.info(
        f"Medication reminders fetched: user={current_user.user_id}, count={len(result)}"
    )

    return result


# =============================================================================
# UPDATE REMINDER - Update reminder settings for a specific medication
# =============================================================================
@router.put("/medications/{medication_id}/reminder", response_model=ReminderResponse)
async def update_medication_reminder(
    medication_id: int,
    settings: ReminderSettingUpdate,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Update reminder settings for a specific medication.

    Only the medication owner can update reminder settings.

    Args:
        medication_id: ID of the medication to update
        settings: New reminder_time and/or reminder_enabled values
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Updated medication reminder info

    Raises:
        404: Medication not found or not owned by user
    """
    medication = (
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.medication_id == medication_id,
                PatientMedication.user_id == current_user.user_id
            )
        )
        .first()
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    # Update fields if provided
    if settings.reminder_time is not None:  # Only change the time if a new value was sent
        medication.reminder_time = settings.reminder_time
    if settings.reminder_enabled is not None:  # Only toggle on/off if explicitly requested
        medication.reminder_enabled = settings.reminder_enabled

    db.commit()
    db.refresh(medication)

    logger.info(
        f"Medication reminder updated: med_id={medication_id}, user={current_user.user_id}, "
        f"time={medication.reminder_time}, enabled={medication.reminder_enabled}"
    )

    return ReminderResponse(
        medication_id=medication.medication_id,
        drug_name=medication.drug_name,
        dose=medication.dose,
        frequency=medication.frequency,
        reminder_time=medication.reminder_time,
        reminder_enabled=medication.reminder_enabled or False,
    )


# =============================================================================
# DELETE REMINDER - Disable and clear reminder settings for a medication
# =============================================================================
@router.delete("/medications/{medication_id}/reminder", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication_reminder(
    medication_id: int,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Disable and clear reminder settings for a specific medication.

    Args:
        medication_id: ID of the medication
        current_user: Authenticated user from JWT token
        db: Database session

    Raises:
        404: Medication not found or not owned by user
    """
    medication = (
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.medication_id == medication_id,
                PatientMedication.user_id == current_user.user_id
            )
        )
        .first()
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    medication.reminder_enabled = False  # Turn off the reminder
    medication.reminder_time = None  # Clear the scheduled time
    db.commit()  # Save changes

    logger.info(
        f"Medication reminder deleted: med_id={medication_id}, user={current_user.user_id}"
    )

    return None


# =============================================================================
# LOG ADHERENCE - Record whether medication was taken or skipped
# =============================================================================
@router.post("/medications/adherence", response_model=AdherenceResponse)
async def log_medication_adherence(
    data: AdherenceCreate,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Log whether a medication was taken or skipped for a given day.

    Creates or updates the adherence record for (medication_id, date).

    Args:
        data: AdherenceCreate with medication_id, date, and taken flag
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Created/updated adherence record

    Raises:
        404: Medication not found or not owned by user
    """
    # Verify medication belongs to user
    medication = (
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.medication_id == data.medication_id,
                PatientMedication.user_id == current_user.user_id
            )
        )
        .first()
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    scheduled_date = datetime.strptime(data.date, "%Y-%m-%d").date()  # Convert the date string to an actual date

    # Check for existing record
    existing = (  # See if we already logged this medication for this date
        db.query(MedicationAdherence)
        .filter(
            and_(
                MedicationAdherence.medication_id == data.medication_id,
                MedicationAdherence.scheduled_date == scheduled_date
            )
        )
        .first()
    )

    if existing:
        # Update existing record
        existing.taken = data.taken  # Update whether the medication was taken or skipped
        existing.responded_at = datetime.now(timezone.utc)  # Record when the user responded
        db.commit()
        db.refresh(existing)
        adherence = existing
    else:
        # Create new record
        adherence = MedicationAdherence(  # First time logging this medication for this date
            medication_id=data.medication_id,
            user_id=current_user.user_id,
            scheduled_date=scheduled_date,
            taken=data.taken,
            responded_at=datetime.now(timezone.utc),
        )
        db.add(adherence)
        db.commit()
        db.refresh(adherence)

    logger.info(
        f"Adherence logged: med_id={data.medication_id}, date={data.date}, "
        f"taken={data.taken}, user={current_user.user_id}"
    )

    return AdherenceResponse(
        adherence_id=adherence.adherence_id,
        medication_id=adherence.medication_id,
        drug_name=medication.drug_name,
        scheduled_date=adherence.scheduled_date,
        taken=adherence.taken,
        responded_at=adherence.responded_at,
    )


# =============================================================================
# GET ADHERENCE HISTORY - Get adherence stats over a time period
# =============================================================================
@router.get("/medications/adherence/history", response_model=AdherenceHistoryResponse)
async def get_adherence_history(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Get medication adherence history for the current user.

    Calculates total scheduled doses vs taken doses for adherence percentage.

    Args:
        days: Number of days to look back (default 7, max 90)
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Adherence history with entries and statistics
    """
    start_date = datetime.now(timezone.utc).date() - timedelta(days=days - 1)  # Start of the lookback window
    end_date = datetime.now(timezone.utc).date()  # Today

    # Get all active medications with reminders enabled
    medications = (  # Only count medications the user is actively tracking
        db.query(PatientMedication)
        .filter(
            and_(
                PatientMedication.user_id == current_user.user_id,
                PatientMedication.status == MedicationStatus.ACTIVE.value,
                PatientMedication.reminder_enabled == True
            )
        )
        .all()
    )

    # Calculate total scheduled (days * number of enabled meds)
    total_scheduled = len(medications) * days  # How many doses should have been taken

    # Get adherence records in date range
    adherence_records = (  # All logged responses (taken or skipped) in this period
        db.query(MedicationAdherence)
        .filter(
            and_(
                MedicationAdherence.user_id == current_user.user_id,
                MedicationAdherence.scheduled_date >= start_date,
                MedicationAdherence.scheduled_date <= end_date
            )
        )
        .order_by(MedicationAdherence.scheduled_date.desc())
        .all()
    )

    # Build medication id to name mapping
    med_names = {med.medication_id: med.drug_name for med in medications}  # Quick lookup from ID to drug name

    # Convert to response format
    entries = []
    total_taken = 0  # Count how many doses were actually taken
    for record in adherence_records:
        drug_name = med_names.get(record.medication_id, "Unknown")
        entries.append(AdherenceResponse(
            adherence_id=record.adherence_id,
            medication_id=record.medication_id,
            drug_name=drug_name,
            scheduled_date=record.scheduled_date,
            taken=record.taken,
            responded_at=record.responded_at,
        ))
        if record.taken is True:
            total_taken += 1

    # Calculate percentage
    adherence_percent = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0.0  # What % of doses were taken

    logger.info(
        f"Adherence history fetched: user={current_user.user_id}, days={days}, "
        f"scheduled={total_scheduled}, taken={total_taken}, percent={adherence_percent:.1f}%"
    )

    return AdherenceHistoryResponse(
        entries=entries,
        total_scheduled=total_scheduled,
        total_taken=total_taken,
        adherence_percent=round(adherence_percent, 1),
    )
