"""
=============================================================================
ADAPTIV HEALTH - User Management API
=============================================================================
FastAPI router for user profile and management endpoints.
Implements RBAC for patient, clinician, and admin access.

Endpoints:
- GET /me - Get user profile
- PUT /me - Update user profile
- PUT /me/medical-history - Update medical history
- GET / - List users (admin/clinician)
- GET /{id} - Get user details (admin/clinician)
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse, UserUpdate, MedicalHistoryUpdate,
    UserProfileResponse, UserListResponse, UserCreateAdmin
)
from app.services.encryption import encryption_service
from app.api.auth import get_current_user, get_current_admin_user, get_current_doctor_user

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
    - Caregivers can access specific patient data (not implemented yet)
    
    Args:
        current_user: The authenticated user
        target_user: The user whose data is being accessed
        
    Returns:
        True if access is allowed
    """
    if current_user.id == target_user.id:
        return True
    
    if current_user.role == UserRole.ADMIN:
        return True
    
    if current_user.role == UserRole.CLINICIAN and target_user.role == UserRole.PATIENT:
        return True
    
    # TODO: Implement caregiver access with permissions
    # if current_user.role == UserRole.CAREGIVER and has_permission(current_user, target_user):
    #     return True
    
    return False


# =============================================================================
# Patient Endpoints
# =============================================================================

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile information.
    
    Returns basic profile data plus calculated heart rate zones.
    """
    # Calculate heart rate zones
    hr_zones = current_user.get_heart_rate_zones() if current_user.age else None
    
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
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
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    
    # Recalculate max HR if age changed
    if 'age' in update_data and current_user.age:
        current_user.max_heart_rate = current_user.calculate_max_heart_rate()
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User profile updated: {current_user.id}")
    
    return current_user


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
    # Prepare medical data
    medical_dict = medical_data.dict(exclude_unset=True)
    
    if medical_dict:
        # Encrypt the medical history
        encrypted_history = encryption_service.encrypt_json(medical_dict)
        current_user.medical_history_encrypted = encrypted_history
        
        db.commit()
        
        logger.info(f"Medical history updated for user: {current_user.id}")
    
    return {"message": "Medical history updated successfully"}


# =============================================================================
# Clinician/Admin Endpoints
# =============================================================================

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    List users with pagination and filtering.
    
    Admin/Clinician access only.
    """
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_filter)) | (User.email.ilike(search_filter))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user.
    
    Admin/Clinician access only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
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
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    # Recalculate max HR if age changed
    if 'age' in update_data and user.age:
        user.max_heart_rate = user.calculate_max_heart_rate()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User updated by admin {current_user.id}: {user.id}")
    
    return {"message": "User updated successfully", "user": user}


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
    auth_service = AuthService()
    hashed_password = auth_service.hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
        phone=user_data.phone,
        role=user_data.role,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User created by admin {current_user.id}: {user.id} - {user.email}")
    
    return {"message": "User created successfully", "user": user}


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
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = False
    db.commit()
    
    logger.info(f"User deactivated by admin {current_user.id}: {user.id}")
    
    return {"message": "User deactivated successfully"}


@router.get("/{user_id}/medical-history")
async def get_user_medical_history(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get a user's medical history.
    
    Admin/Clinician access only. Returns decrypted medical data.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
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