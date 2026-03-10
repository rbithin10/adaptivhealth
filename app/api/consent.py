"""
Consent / data-sharing endpoints.

Manages the patient consent workflow for sharing health data with clinicians.

State machine:
  SHARING_ON  → patient requests disable → SHARING_DISABLE_REQUESTED
  SHARING_DISABLE_REQUESTED → clinician approves → SHARING_OFF
  SHARING_DISABLE_REQUESTED → clinician rejects → SHARING_ON
  SHARING_OFF → patient re-enables → SHARING_ON

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 30
# SCHEMAS.............................. Line 45
#
# ENDPOINTS - PATIENT (consent management)
#   - GET /consent/status.............. Line 55  (View consent status)
#   - POST /consent/disable............ Line 70  (Request disable sharing)
#   - POST /consent/enable............. Line 116 (Re-enable sharing)
#
# ENDPOINTS - CLINICIAN (consent review)
#   - GET /consent/pending............. Line 148 (List pending requests)
#   - POST /consent/{id}/review........ Line 176 (Approve/reject request)
#
# BUSINESS CONTEXT:
# - HIPAA compliance: patients control data sharing
# - Clinicians must review disable requests before data is hidden
# - Alerts created when sharing state changes
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
# Pydantic models define the shape of data we accept and return
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import logging

# Database session provider for each request
from app.database import get_db
# User model and roles (PATIENT, CLINICIAN, ADMIN)
from app.models.user import User, UserRole
# Alert model used to notify clinicians about consent changes
from app.models.alert import Alert
# Authentication helper to verify who is making the request
from app.api.auth import get_current_user

# Set up a logger for tracking consent-related events
logger = logging.getLogger(__name__)
# Group all consent endpoints under one router
router = APIRouter()

# These constants represent the three possible data-sharing states
SHARING_ON = "SHARING_ON"                           # Patient's data is visible to clinicians
SHARING_DISABLE_REQUESTED = "SHARING_DISABLE_REQUESTED"  # Patient asked to stop sharing, waiting for clinician review
SHARING_OFF = "SHARING_OFF"                          # Sharing is turned off (clinician approved the request)


class ConsentStatusResponse(BaseModel):
    """What the API returns when a patient checks their sharing status."""
    share_state: str                          # Current state: SHARING_ON, SHARING_DISABLE_REQUESTED, or SHARING_OFF
    requested_at: Optional[str] = None        # When the disable request was made (if any)
    reviewed_at: Optional[str] = None         # When a clinician reviewed the request (if any)
    decision: Optional[str] = None            # The clinician's decision: "approve" or "reject"
    reason: Optional[str] = None              # The reason given for the request or decision


class DisableRequest(BaseModel):
    """Data a patient sends when asking to stop sharing their health data."""
    reason: Optional[str] = Field(None, max_length=500)  # Optional explanation for why they want to opt out


class ReviewRequest(BaseModel):
    """Data a clinician sends when approving or rejecting a consent request."""
    decision: str = Field(..., description="approve or reject")           # Must be "approve" or "reject"
    reason: Optional[str] = Field(None, max_length=500)  # Optional note about the decision


# =============================================================================
# Patient endpoints
# =============================================================================

# =============================================
# GET_MY_CONSENT_STATUS - Current sharing state
# Used by: Mobile app settings, consent screen
# Returns: ConsentStatusResponse with state + history
# Roles: ALL authenticated users (own status)
# =============================================
@router.get("/consent/status", response_model=ConsentStatusResponse)
async def get_my_consent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current patient's sharing consent status."""
    return ConsentStatusResponse(
        share_state=current_user.share_state or SHARING_ON,
        requested_at=current_user.share_requested_at.isoformat() if current_user.share_requested_at else None,
        reviewed_at=current_user.share_reviewed_at.isoformat() if current_user.share_reviewed_at else None,
        decision=current_user.share_decision,
        reason=current_user.share_reason,
    )


# =============================================
# REQUEST_SHARING_DISABLE - Patient opts out
# Used by: Mobile app privacy settings
# Returns: Success message (creates pending request)
# Roles: PATIENT (own consent only)
# =============================================
@router.post("/consent/disable")
async def request_sharing_disable(
    body: DisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Patient requests to disable data sharing with clinicians.

    Does NOT stop sharing immediately — creates a pending request that a
    clinician must approve or reject.
    """
    # Only patients can control their own consent (clinicians manage via the review endpoint)
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patient users can request to disable data sharing")

    # If sharing is already off, there's nothing to disable
    if (current_user.share_state or SHARING_ON) == SHARING_OFF:
        raise HTTPException(status_code=400, detail="Sharing is already disabled")

    # If a request is already pending, don't create a duplicate
    if (current_user.share_state or SHARING_ON) == SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="A disable request is already pending")

    # Update the patient's consent state to "pending review"
    current_user.share_state = SHARING_DISABLE_REQUESTED
    current_user.share_requested_at = datetime.now(timezone.utc)
    current_user.share_requested_by = current_user.user_id
    current_user.share_reason = body.reason
    # Clear any previous review data since this is a new request
    current_user.share_decision = None
    current_user.share_reviewed_at = None
    current_user.share_reviewed_by = None

    # Create a warning alert so clinicians know a patient wants to opt out
    alert = Alert(
        user_id=current_user.user_id,
        alert_type="consent_disable_request",
        severity="warning",
        title="Patient Opt-Out Request",
        message=f"Patient {current_user.full_name or current_user.email} has requested to disable data sharing.",
        action_required="Review and approve/reject this consent request.",
        is_sent_to_clinician=True,
    )
    db.add(alert)
    # Save the state change and the new alert together
    db.commit()

    logger.info(f"Sharing disable requested by patient {current_user.user_id}")
    return {"message": "Sharing disable request submitted. A clinician will review it."}


# =============================================
# ENABLE_SHARING - Patient re-enables sharing
# Used by: Mobile app privacy settings
# Returns: Success message (immediate effect)
# Roles: PATIENT (own consent only)
# =============================================
@router.post("/consent/enable")
async def enable_sharing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient re-enables data sharing (from SHARING_OFF state)."""
    # Only patients can toggle their own sharing preferences
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can manage their own consent")

    # If sharing is already on, no action needed
    if (current_user.share_state or SHARING_ON) == SHARING_ON:
        raise HTTPException(status_code=400, detail="Sharing is already enabled")

    # Can't re-enable while a disable request is still being reviewed
    if (current_user.share_state or SHARING_ON) == SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="Cannot re-enable while a disable request is pending")

    # Switch sharing back on and clear all previous request/review data
    current_user.share_state = SHARING_ON
    current_user.share_requested_at = None
    current_user.share_requested_by = None
    current_user.share_decision = None
    current_user.share_reason = None
    current_user.share_reviewed_at = None
    current_user.share_reviewed_by = None
    db.commit()

    logger.info(f"Sharing re-enabled by patient {current_user.user_id}")
    return {"message": "Data sharing has been re-enabled."}


# =============================================================================
# Clinician endpoints
# =============================================================================

# =============================================
# LIST_PENDING_REQUESTS - Consent queue
# Used by: Clinician dashboard consent review
# Returns: List of pending disable requests
# Roles: CLINICIAN, ADMIN
# =============================================
@router.get("/consent/pending")
async def list_pending_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clinician: list all patients with pending disable requests."""
    if current_user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Clinician access required")

    pending = db.query(User).filter(
        User.share_state == SHARING_DISABLE_REQUESTED,
        User.role == UserRole.PATIENT
    ).all()

    return {
        "pending_requests": [
            {
                "user_id": p.user_id,
                "email": p.email,
                "full_name": p.full_name,
                "requested_at": p.share_requested_at.isoformat() if p.share_requested_at else None,
                "reason": p.share_reason,
            }
            for p in pending
        ]
    }


# =============================================
# REVIEW_CONSENT_REQUEST - Approve/reject opt-out
# Used by: Clinician dashboard consent queue
# Returns: Success message with new state
# Roles: CLINICIAN only
# =============================================
@router.post("/consent/{patient_id}/review")
async def review_consent_request(
    patient_id: int,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clinician approves or rejects a patient's sharing-disable request.

    - approve → share_state becomes SHARING_OFF
    - reject  → share_state returns to SHARING_ON
    """
    # Only clinicians can review consent requests
    if current_user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Only clinicians can review consent requests")

    # Make sure the decision is a valid choice
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    # Find the patient who made the consent request
    patient = db.query(User).filter(User.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Make sure there is actually a pending request to review
    if (patient.share_state or SHARING_ON) != SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="No pending consent request for this patient")

    # Record the review details
    now = datetime.now(timezone.utc)
    patient.share_reviewed_at = now              # When the review happened
    patient.share_reviewed_by = current_user.user_id  # Which clinician reviewed it
    patient.share_decision = body.decision       # "approve" or "reject"

    # Apply the decision: approve turns sharing off, reject turns it back on
    if body.decision == "approve":
        patient.share_state = SHARING_OFF
        msg = "approved"
    else:
        patient.share_state = SHARING_ON
        msg = "rejected"

    # Save the clinician's reason if they provided one
    if body.reason:
        patient.share_reason = body.reason

    # Save all changes to the database
    db.commit()
    logger.info(f"Consent request for patient {patient_id} {msg} by clinician {current_user.user_id}")
    return {"message": f"Consent disable request {msg}."}
