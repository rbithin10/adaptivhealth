"""
User data validation.

Defines what user information can be sent to the API and what
the API sends back. Checks that data is valid (like email is
formatted correctly, age is reasonable, etc.).

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# REQUEST SCHEMAS
#   - UserBase......................... Line 35  (Common fields)
#   - UserCreate....................... Line 55  (Registration input)
#   - UserUpdate....................... Line 85  (Profile update input)
#   - MedicalHistoryUpdate............. Line 108 (Health data input)
#   - LoginRequest..................... Line 170 (Login input)
#   - RefreshTokenRequest.............. Line 190 (Token refresh input)
#   - PasswordResetRequest............. Line 198 (Password reset email)
#   - PasswordResetConfirm............. Line 205 (Password reset token)
#   - UserCreateAdmin.................. Line 235 (Admin user creation)
#
# RESPONSE SCHEMAS
#   - UserResponse..................... Line 125 (Basic user output)
#   - UserProfileResponse.............. Line 145 (Full profile with HR zones)
#   - TokenResponse.................... Line 180 (JWT tokens)
#   - UserListResponse................. Line 225 (Paginated list)
#
# BUSINESS CONTEXT:
# - Pydantic validation for API I/O
# - Field constraints match DB schema
# =============================================================================
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole
from app.schemas.medical_history import MedicalProfileSummary


# =============================================================================
# Base User Schema
# =============================================================================

class UserBase(BaseModel):
    """
    Base user schema with common fields.
    Used for creating and updating users.
    """
    email: EmailStr = Field(..., description="User's email address")  # The user's email for login and communication
    name: str = Field(..., min_length=1, max_length=255, description="Full name")  # Their full name (1-255 characters)
    age: Optional[int] = Field(None, ge=1, le=120, description="Age in years")  # Patient's age (must be between 1 and 120)
    gender: Optional[str] = Field(None, description="Gender (male, female, other, prefer not to say)")  # Gender identity
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")  # Contact phone number
    
    @field_validator('gender')
    def validate_gender(cls, v):
        # Keep gender values consistent.
        if v is not None:
            allowed = ['male', 'female', 'other', 'prefer not to say']
            if v.lower() not in allowed:
                raise ValueError(f'Gender must be one of: {allowed}')  # pragma: no cover
        return v


# =============================================================================
# User Creation Schema
# =============================================================================

class UserCreate(UserBase):
    """
    Schema for creating new users.
    Includes password and role assignment.
    """
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")  # Account password (at least 8 chars with letters and numbers)
    role: UserRole = Field(default=UserRole.PATIENT, description="User role")  # What type of user: patient, clinician, or admin
    
    @field_validator('password')
    def validate_password_strength(cls, v):
        """
        Basic password strength validation.
        In production, consider more sophisticated checks.
        """
        # Simple rules so passwords are not too weak.
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')  # pragma: no cover
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')  # pragma: no cover
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')  # pragma: no cover
        return v


# =============================================================================
# User Update Schema
# =============================================================================

class UserUpdate(BaseModel):
    """
    Schema for updating user information.
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)  # Updated name (optional)
    age: Optional[int] = Field(None, ge=1, le=120)  # Updated age (optional)
    gender: Optional[str] = Field(None)  # Updated gender (optional)
    phone: Optional[str] = Field(None, max_length=20)  # Updated phone number (optional)
    weight_kg: Optional[float] = Field(None, ge=0, le=500, description="Weight in kilograms")  # Body weight in kilograms
    height_cm: Optional[float] = Field(None, ge=0, le=300, description="Height in centimetres")  # Body height in centimetres
    emergency_contact_name: Optional[str] = Field(None, max_length=255)  # Who to call in an emergency
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)  # Emergency contact's phone number
    rehab_phase: Optional[str] = Field(None, description="Cardiac rehab phase: phase_2, phase_3, or not_in_rehab")  # Which stage of cardiac rehab
    activity_level: Optional[str] = Field(None, description="Activity level: none, light, moderate, active")  # How active the patient is day-to-day
    exercise_limitations: Optional[str] = Field(None, description="JSON list of exercise limitations")  # Any exercises the patient should avoid
    primary_goal: Optional[str] = Field(None, description="Primary health goal")  # What the patient is working towards
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Stress level 1-10")  # Self-reported stress (1=low, 10=high)
    sleep_quality: Optional[str] = Field(None, description="Sleep quality: good, fair, poor")  # How well the patient sleeps
    smoking_status: Optional[str] = Field(None, description="Smoking status: never, former, current")  # Do they smoke?
    alcohol_frequency: Optional[str] = Field(None, description="Alcohol frequency: never, occasional, moderate, heavy")  # How often they drink alcohol
    sedentary_hours: Optional[float] = Field(None, ge=0, le=24, description="Sedentary hours per day (0-24)")  # Hours spent sitting each day
    phq2_score: Optional[int] = Field(None, ge=0, le=6, description="PHQ-2 depression screening score (0-6)")  # Depression screening score (higher = more concern)
    
    @field_validator('gender')
    def validate_gender(cls, v):
        # Same validation as UserBase for consistency across endpoints
        if v is not None:
            allowed = ['male', 'female', 'other', 'prefer not to say']
            if v.lower() not in allowed:
                raise ValueError(f'Gender must be one of: {allowed}')  # pragma: no cover
        return v

    @field_validator('activity_level')
    def validate_activity_level(cls, v):
        if v is not None:
            allowed = ['none', 'light', 'moderate', 'active']
            if v.lower() not in allowed:
                raise ValueError(f'Activity level must be one of: {allowed}')
        return v

    @field_validator('sleep_quality')
    def validate_sleep_quality(cls, v):
        if v is not None:
            allowed = ['good', 'fair', 'poor']
            if v.lower() not in allowed:
                raise ValueError(f'Sleep quality must be one of: {allowed}')
        return v

    @field_validator('smoking_status')
    def validate_smoking_status(cls, v):
        if v is not None:
            allowed = ['never', 'former', 'current']
            if v.lower() not in allowed:
                raise ValueError(f'Smoking status must be one of: {allowed}')
        return v

    @field_validator('alcohol_frequency')
    def validate_alcohol_frequency(cls, v):
        if v is not None:
            allowed = ['never', 'occasional', 'moderate', 'heavy']
            if v.lower() not in allowed:
                raise ValueError(f'Alcohol frequency must be one of: {allowed}')
        return v


# =============================================================================
# Medical History Update Schema
# =============================================================================

class MedicalHistoryUpdate(BaseModel):
    """
    Schema for updating user's medical history.
    Medical data is sensitive and will be encrypted.
    """
    conditions: Optional[List[str]] = Field(None, description="List of medical conditions")  # Health conditions the patient has
    medications: Optional[List[str]] = Field(None, description="Current medications")  # Medicines they are currently taking
    allergies: Optional[List[str]] = Field(None, description="Known allergies")  # Things they are allergic to
    surgeries: Optional[List[str]] = Field(None, description="Past surgeries")  # Surgeries they have had in the past
    notes: Optional[str] = Field(None, max_length=1000, description="Additional medical notes")  # Extra notes from the clinician


# =============================================================================
# User Response Schema
# =============================================================================

class UserResponse(UserBase):
    """
    Schema for user data in API responses.
    Includes system-generated fields.
    """
    id: int = Field(..., description="User ID")  # The unique number that identifies this user
    role: UserRole = Field(..., description="User role")  # Their role: patient, clinician, or admin
    is_active: bool = Field(..., description="Account active status")  # Is this account enabled?
    is_verified: bool = Field(..., description="Email verification status")  # Have they verified their email?
    assigned_clinician_id: Optional[int] = Field(None, description="ID of assigned clinician (for patients)")  # Which doctor is assigned to this patient
    rehab_phase: Optional[str] = Field(None, description="Cardiac rehab phase: phase_2, phase_3, or not_in_rehab")
    activity_level: Optional[str] = Field(None, description="Activity level")
    exercise_limitations: Optional[str] = Field(None, description="JSON list of exercise limitations")
    primary_goal: Optional[str] = Field(None, description="Primary health goal")
    stress_level: Optional[int] = Field(None, description="Stress level 1-10")
    sleep_quality: Optional[str] = Field(None, description="Sleep quality")
    smoking_status: Optional[str] = Field(None, description="Smoking status")
    alcohol_frequency: Optional[str] = Field(None, description="Alcohol frequency")
    sedentary_hours: Optional[float] = Field(None, description="Sedentary hours per day")
    phq2_score: Optional[int] = Field(None, description="PHQ-2 screening score")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    medical_profile_summary: Optional[MedicalProfileSummary] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# User Profile Response (for patients)
# =============================================================================

class UserProfileResponse(BaseModel):
    """
    User profile response for patient dashboard.
    Includes basic info and calculated metrics.
    """
    id: int
    email: EmailStr
    name: str
    age: Optional[int]
    gender: Optional[str]
    phone: Optional[str]
    role: UserRole
    baseline_heart_rate: Optional[int] = Field(None, description="Resting HR")
    max_heart_rate: Optional[int] = Field(None, description="Max HR")
    heart_rate_zones: Optional[dict] = Field(None, description="HR training zones")
    rehab_phase: Optional[str] = Field(None, description="Cardiac rehab phase")
    activity_level: Optional[str] = Field(None, description="Activity level")
    exercise_limitations: Optional[str] = Field(None, description="JSON list of exercise limitations")
    primary_goal: Optional[str] = Field(None, description="Primary health goal")
    stress_level: Optional[int] = Field(None, description="Stress level 1-10")
    sleep_quality: Optional[str] = Field(None, description="Sleep quality")
    smoking_status: Optional[str] = Field(None, description="Smoking status")
    alcohol_frequency: Optional[str] = Field(None, description="Alcohol frequency")
    sedentary_hours: Optional[float] = Field(None, description="Sedentary hours per day")
    phq2_score: Optional[int] = Field(None, description="PHQ-2 screening score")
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# Authentication Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """
    Schema for user login requests.
    """
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """
    Schema for authentication token responses.
    """
    access_token: str = Field(..., description="JWT access token")  # The key that proves you're logged in
    refresh_token: str = Field(..., description="JWT refresh token")  # A backup key to get a new access token when it expires
    token_type: str = Field(default="bearer", description="Token type")  # Always "bearer" — the standard way to use tokens
    expires_in: int = Field(..., description="Access token expiration time in seconds")  # How many seconds until the access token expires
    user: UserResponse = Field(..., description="User information")  # Basic info about the logged-in user


class RefreshTokenRequest(BaseModel):
    """
    Schema for token refresh requests.
    """
    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(BaseModel):
    """
    Schema for password reset requests.
    """
    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """
    Schema for password reset confirmation.
    """
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')  # pragma: no cover
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')  # pragma: no cover
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')  # pragma: no cover
        return v


# =============================================================================
# Admin Schemas
# =============================================================================

class UserListResponse(BaseModel):
    """
    Schema for paginated user list responses.
    """
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Users per page")


class UserCreateAdmin(UserCreate):
    """
    Admin schema for creating users.
    Allows setting all user properties.
    """
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verification status")