"""
=============================================================================
ADAPTIV HEALTH - User Management API
=============================================================================
FastAPI router for user profile and management endpoints.
Implements RBAC for patient, clinician, and admin access.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 35
# HELPER FUNCTIONS
#   - can_access_user.................. Line 61  (Access control check)
#
# ENDPOINTS - PATIENT (own profile)
#   - GET /me.......................... Line 101 (Get own profile)
#   - PUT /me.......................... Line 134 (Update own profile)
#   - PUT /me/medical-history.......... Line 178 (Update own medical history)
#   - GET /me/clinician................ Line 211 (Get assigned clinician)
#
# ENDPOINTS - CLINICIAN/ADMIN (user management)
#   - GET /............................ Line 258 (List users)
#   - GET /{id}....................... Line 320 (Get user details)
#   - PUT /{id}....................... Line 354 (Update user)
#   - POST /........................... Line 402 (Create user)
#   - DELETE /{id}.................... Line 462 (Delete user)
#   - POST /{id}/reset-password........ Line 501 (Reset user password)
#   - GET /{id}/medical-history........ Line 564 (Get patient history)
#   - PUT /{id}/assign-clinician....... Line 606 (Assign clinician to patient)
#
# BUSINESS CONTEXT:
# - Patients manage their own profile from mobile app
# - Clinicians view/manage assigned patients
# - Admins have full user management capabilities
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case
from typing import List, Optional
from pathlib import Path
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.medical_history import PatientMedicalHistory, PatientMedication, UploadedDocument
from app.schemas.user import (
    UserResponse, UserUpdate, MedicalHistoryUpdate,
    UserProfileResponse, UserListResponse, UserCreateAdmin
)
from app.schemas.medical_history import MedicalProfileSummary
from app.services.encryption import encryption_service
from app.api.auth import get_current_user, get_current_admin_user, get_current_doctor_user, get_current_admin_or_doctor_user, check_clinician_phi_access

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

def can_access_user(current_user: User, target_user: User) -> bool:
    """
    Check if current user can access target user's data.
    
    Access rules:
    - Users can access their own data
    - Clinicians can access patient data
    - Admins can access all data
    - Caregivers can access patient data (basic implementation)
    
    Args:
        current_user: The authenticated user
        target_user: The user whose data is being accessed
        
    Returns:
        True if access is allowed
    """
    # Check the simplest rule first: users can see their own data.
    if current_user.user_id == target_user.user_id:
        return True
    
    if current_user.role == UserRole.ADMIN:
        return True
    
    if current_user.role == UserRole.CLINICIAN and target_user.role == UserRole.PATIENT:
        return True
    
    return False


def _build_medical_profile_summaries(user_ids: list[int], db: Session) -> dict[int, MedicalProfileSummary]:
    """Return aggregated medical flags for the requested users."""
    if not user_ids:
        return {}

    summary_data = {
        uid: {
            "user_id": uid,
            "has_prior_mi": False,
            "has_heart_failure": False,
            "is_on_beta_blocker": False,
            "is_on_anticoagulant": False,
            "has_uploaded_document": False,
            "has_accessible_document": False,
            "active_condition_count": 0,
            "active_medication_count": 0,
        }
        for uid in user_ids
    }

    condition_rows = (
        db.query(
            PatientMedicalHistory.user_id,
            func.sum(case((PatientMedicalHistory.status == "active", 1), else_=0)).label("active_condition_count"),
            func.max(case(((PatientMedicalHistory.condition_type == "prior_mi") & (PatientMedicalHistory.status == "active"), 1), else_=0)).label("has_prior_mi"),
            func.max(case(((PatientMedicalHistory.condition_type == "heart_failure") & (PatientMedicalHistory.status == "active"), 1), else_=0)).label("has_heart_failure"),
        )
        .filter(PatientMedicalHistory.user_id.in_(user_ids))
        .group_by(PatientMedicalHistory.user_id)
        .all()
    )

    for row in condition_rows:
        data = summary_data.get(row.user_id)
        if not data:
            continue
        data["active_condition_count"] = row.active_condition_count or 0
        data["has_prior_mi"] = bool(row.has_prior_mi)
        data["has_heart_failure"] = bool(row.has_heart_failure)

    medication_rows = (
        db.query(
            PatientMedication.user_id,
            func.sum(case((PatientMedication.status == "active", 1), else_=0)).label("active_medication_count"),
            func.max(case(((PatientMedication.is_hr_blunting == True) & (PatientMedication.status == "active"), 1), else_=0)).label("is_on_beta_blocker"),
            func.max(case(((PatientMedication.is_anticoagulant == True) & (PatientMedication.status == "active"), 1), else_=0)).label("is_on_anticoagulant"),
        )
        .filter(PatientMedication.user_id.in_(user_ids))
        .group_by(PatientMedication.user_id)
        .all()
    )

    for row in medication_rows:
        data = summary_data.get(row.user_id)
        if not data:
            continue
        data["active_medication_count"] = row.active_medication_count or 0
        data["is_on_beta_blocker"] = bool(row.is_on_beta_blocker)
        data["is_on_anticoagulant"] = bool(row.is_on_anticoagulant)

    document_rows = (
        db.query(UploadedDocument.user_id, UploadedDocument.file_path)
        .filter(UploadedDocument.user_id.in_(user_ids))
        .all()
    )

    for row in document_rows:
        data = summary_data.get(row.user_id)
        if not data:
            continue
        data["has_uploaded_document"] = True
        if row.file_path and Path(row.file_path).is_file():
            data["has_accessible_document"] = True

    return {
        uid: MedicalProfileSummary(**values)
        for uid, values in summary_data.items()
    }


# =============================================================================
# Patient Endpoints
# =============================================================================

# =============================================
# GET_MY_PROFILE - User's own profile info
# Used by: Mobile app home screen, profile page
# Returns: UserProfileResponse with heart rate zones
# Roles: ALL authenticated users
# =============================================
@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile information.
    
    Returns basic profile data plus calculated heart rate zones.
    """
    # Calculate heart-rate zones when needed so they stay up to date.
    # Calculate heart rate zones
    hr_zones = current_user.get_heart_rate_zones() if current_user.age else None
    
    return UserProfileResponse(
        id=current_user.user_id,
        email=current_user.email,
        name=current_user.full_name,
        age=current_user.age,
        gender=current_user.gender,
        phone=current_user.phone,
        role=current_user.role,
        baseline_heart_rate=current_user.baseline_heart_rate,
        max_heart_rate=current_user.max_heart_rate,
        heart_rate_zones=hr_zones,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


# =============================================
# UPDATE_MY_PROFILE - Edit own profile fields
# Used by: Mobile app settings, profile editing
# Returns: UserResponse with updated data
# Roles: ALL authenticated users
# =============================================
@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    
    Only allows updating safe profile fields.
    """
    # Only change fields the user actually sent.
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Whitelist allowed fields for security
    allowed_fields = {
        'name', 'age', 'gender', 'phone',
        'weight_kg', 'height_cm',
        'emergency_contact_name', 'emergency_contact_phone',
        'rehab_phase',
        'activity_level', 'exercise_limitations', 'primary_goal',
        'stress_level', 'sleep_quality',
        'smoking_status', 'alcohol_frequency', 'sedentary_hours', 'phq2_score',
    }
    
    for field, value in update_data.items():
        if field in allowed_fields and hasattr(current_user, field):
            setattr(current_user, field, value)
    
    # If age changes, update max heart rate too.
    if 'age' in update_data and current_user.age:
        current_user.max_safe_hr = current_user.calculate_max_heart_rate()
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User profile updated: {current_user.user_id}")
    
    return current_user


# =============================================
# UPDATE_MEDICAL_HISTORY - Sensitive health data
# Used by: Mobile app onboarding, settings
# Returns: Success message (encrypted storage)
# Roles: PATIENT (own data only)
# =============================================
@router.put("/me/medical-history")
async def update_medical_history(
    medical_data: MedicalHistoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's medical history.
    
    Medical data is encrypted before storage for HIPAA compliance.
    """
    # Encrypt medical history before saving it.
    # Prepare medical data
    medical_dict = medical_data.model_dump(exclude_unset=True)
    
    if medical_dict:
        # Encrypt the medical history
        encrypted_history = encryption_service.encrypt_json(medical_dict)
        current_user.medical_history_encrypted = encrypted_history
        
        db.commit()
        
        logger.info(f"Medical history updated for user: {current_user.user_id}")
    
    return {"message": "Medical history updated successfully"}


# =============================================
# GET_ASSIGNED_CLINICIAN - Get patient's assigned clinician
# Used by: Mobile app messaging screen
# Returns: Clinician details
# Roles: PATIENT only
# =============================================
@router.get("/me/clinician")
async def get_my_assigned_clinician(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the clinician assigned to the current patient.
    
    Returns clinician details or null if not assigned.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint"
        )
    
    if not current_user.assigned_clinician_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No clinician assigned to this patient"
        )
    
    clinician = db.query(User).filter(User.user_id == current_user.assigned_clinician_id).first()
    if not clinician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned clinician not found"
        )
    
    return {
        "user_id": clinician.user_id,
        "full_name": clinician.full_name,
        "email": clinician.email,
        "phone": clinician.phone
    }


# =============================================================================
# Clinician/Admin Endpoints
# =============================================================================

# =============================================
# LIST_USERS - Paginated user directory
# Used by: Admin dashboard, clinician patient list
# Returns: UserListResponse with pagination
# Roles: DOCTOR, ADMIN
# =============================================
@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=500, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List users with pagination and filtering.
    
    Clinicians see ONLY their assigned patients (bidirectional data isolation).
    Patients can only query for clinicians (role=clinician).
    Admin/Clinician can query all roles.
    """
    # Access control: patients can only get clinician list
    if current_user.role == UserRole.PATIENT and role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients can only query clinician list"
        )
    # Build the query and apply any filters.
    query = db.query(User)
    
    # Clinicians see ONLY their assigned patients (data isolation)
    if current_user.role == UserRole.CLINICIAN:
        # Filter to show only patients assigned to this clinician
        query = query.filter(User.assigned_clinician_id == current_user.user_id)
        # Force role filter for patients
        query = query.filter(User.role == UserRole.PATIENT)
    
    # Apply role filter (admins and general queries)
    if role:
        query = query.filter(User.role == role)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_filter)) | (User.email.ilike(search_filter))
        )
    
    # Count total results for pagination.
    total = query.count()
    
    # Apply pagination
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    summaries = _build_medical_profile_summaries([u.user_id for u in users], db)
    for user in users:
        summary = summaries.get(user.user_id)
        if summary:
            user.medical_profile_summary = summary
    
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page
    )


# =============================================
# GET_USER - Individual user details
# Used by: Clinician patient view, admin user management
# Returns: UserResponse with full profile
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_or_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user.
    
    Admin/Clinician access only.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not can_access_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return user


# =============================================
# UPDATE_USER - Admin modifies user profile
# Used by: Admin dashboard user management
# Returns: Success message with updated user
# Roles: ADMIN only
# =============================================
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a user's information.
    
    Admin access only.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Whitelist allowed fields for security
    allowed_fields = {'name', 'age', 'gender', 'phone'}
    
    for field, value in update_data.items():
        if field in allowed_fields and hasattr(user, field):
            setattr(user, field, value)
    
    # Recalculate max HR if age changed
    if 'age' in update_data and user.age:
        user.max_safe_hr = user.calculate_max_heart_rate()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User updated by admin {current_user.user_id}: {user.user_id}")
    
    return {"message": "User updated successfully", "user": user}


# =============================================
# CREATE_USER - Admin creates new account
# Used by: Admin dashboard, user onboarding
# Returns: Success message with new user
# Roles: ADMIN only
# =============================================
@router.post("/")
async def create_user(
    user_data: UserCreateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    
    Admin access only.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    from app.services.auth_service import AuthService
    from app.models.auth_credential import AuthCredential
    auth_service = AuthService()
    hashed_password = auth_service.hash_password(user_data.password)
    
    # Create user (without hashed_password - that goes in AuthCredential)
    user = User(
        email=user_data.email,
        full_name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        phone=user_data.phone,
        role=user_data.role,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified
    )
    
    # Create SEPARATE AuthCredential record
    auth_cred = AuthCredential(
        user=user,
        hashed_password=hashed_password
    )
    
    # Add both records in single transaction
    db.add(user)
    db.add(auth_cred)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User created by admin {current_user.user_id}: {user.user_id} - {user.email}")
    
    return {"message": "User created successfully", "user": user}


# =============================================
# DEACTIVATE_USER - Soft delete user account
# Used by: Admin dashboard, account management
# Returns: Success message (audit compliant)
# Roles: ADMIN only
# =============================================
@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account.
    
    Admin access only. Soft delete for audit compliance.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = False
    db.commit()
    
    logger.info(f"User deactivated by admin {current_user.user_id}: {user.user_id}")
    
    return {"message": "User deactivated successfully"}


# =============================================
# ADMIN_RESET_PASSWORD - Set temporary password
# Used by: Admin dashboard, account recovery
# Returns: Success message (no PHI exposed)
# Roles: ADMIN only
# =============================================
@router.post("/{user_id}/reset-password")
async def admin_reset_user_password(
    user_id: int,
    body: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin sets a temporary password for a user.
    
    Admin access only. Used for account management.
    Does not expose any PHI.
    """
    from app.models.auth_credential import AuthCredential
    from app.services.auth_service import AuthService

    new_password = body.get("new_password")
    if not new_password or len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    if not any(c.isalpha() for c in new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must contain at least one letter"
        )
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must contain at least one digit"
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    auth_cred = user.auth_credential
    if not auth_cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User authentication not configured"
        )

    auth_service = AuthService()
    auth_cred.hashed_password = auth_service.hash_password(new_password)
    auth_cred.failed_login_attempts = 0
    auth_cred.locked_until = None
    db.commit()

    logger.info(f"Password reset by admin {current_user.user_id} for user {user_id}")
    return {"message": "Temporary password set successfully"}


# =============================================
# GET_USER_MEDICAL_HISTORY - Decrypt patient PHI
# Used by: Clinician dashboard, patient detail view
# Returns: Decrypted medical history JSON
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/{user_id}/medical-history")
async def get_user_medical_history(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get a user's medical history.
    
    Clinician access only (PHI). Returns decrypted medical data.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    check_clinician_phi_access(current_user, user)
    
    if not user.medical_history_encrypted:
        return {"medical_history": None, "message": "No medical history on record"}
    
    try:
        # Decrypt medical history
        medical_history = encryption_service.decrypt_json(user.medical_history_encrypted)
        return {"medical_history": medical_history}
    except Exception as e:
        logger.error(f"Failed to decrypt medical history for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve medical history"
        )


# =============================================
# ASSIGN_CLINICIAN - Admin assigns clinician to patient
# Used by: Admin dashboard (patient management)
# Returns: Success message with assignment
# Roles: ADMIN only
# =============================================
@router.put("/{user_id}/assign-clinician")
async def assign_clinician_to_patient(
    user_id: int,
    clinician_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Assign a clinician to a patient.
    
    Admin only. The clinician_id must be a user with role=clinician.
    """
    # Get patient
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if patient.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only assign clinicians to patient users"
        )
    
    # Get clinician
    clinician = db.query(User).filter(User.user_id == clinician_id).first()
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")
    
    if clinician.role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only assign users with clinician role"
        )
    
    # Assign clinician
    patient.assigned_clinician_id = clinician_id
    db.commit()
    db.refresh(patient)
    
    logger.info(f"Admin {current_user.user_id} assigned clinician {clinician_id} to patient {user_id}")
    
    return {
        "message": f"Successfully assigned clinician {clinician.full_name} to patient {patient.full_name}",
        "patient_id": patient.user_id,
        "clinician_id": clinician.user_id,
        "clinician_name": clinician.full_name
    }
