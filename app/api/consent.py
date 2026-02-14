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
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.alert import Alert
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Valid share states
SHARING_ON = "SHARING_ON"
SHARING_DISABLE_REQUESTED = "SHARING_DISABLE_REQUESTED"
SHARING_OFF = "SHARING_OFF"


class ConsentStatusResponse(BaseModel):
    share_state: str
    requested_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None


class DisableRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class ReviewRequest(BaseModel):
    decision: str = Field(..., description="approve or reject")
    reason: Optional[str] = Field(None, max_length=500)


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
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patient users can request to disable data sharing")

    if (current_user.share_state or SHARING_ON) == SHARING_OFF:
        raise HTTPException(status_code=400, detail="Sharing is already disabled")

    if (current_user.share_state or SHARING_ON) == SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="A disable request is already pending")

    current_user.share_state = SHARING_DISABLE_REQUESTED
    current_user.share_requested_at = datetime.now(timezone.utc)
    current_user.share_requested_by = current_user.user_id
    current_user.share_reason = body.reason
    current_user.share_decision = None
    current_user.share_reviewed_at = None
    current_user.share_reviewed_by = None

    # Create an alert for clinicians
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
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can manage their own consent")

    if (current_user.share_state or SHARING_ON) == SHARING_ON:
        raise HTTPException(status_code=400, detail="Sharing is already enabled")

    if (current_user.share_state or SHARING_ON) == SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="Cannot re-enable while a disable request is pending")

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
    if current_user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Only clinicians can review consent requests")

    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    patient = db.query(User).filter(User.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if (patient.share_state or SHARING_ON) != SHARING_DISABLE_REQUESTED:
        raise HTTPException(status_code=400, detail="No pending consent request for this patient")

    now = datetime.now(timezone.utc)
    patient.share_reviewed_at = now
    patient.share_reviewed_by = current_user.user_id
    patient.share_decision = body.decision

    if body.decision == "approve":
        patient.share_state = SHARING_OFF
        msg = "approved"
    else:
        patient.share_state = SHARING_ON
        msg = "rejected"

    if body.reason:
        patient.share_reason = body.reason

    db.commit()
    logger.info(f"Consent request for patient {patient_id} {msg} by clinician {current_user.user_id}")
    return {"message": f"Consent disable request {msg}."}
