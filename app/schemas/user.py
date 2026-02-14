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


# =============================================================================
# Base User Schema
# =============================================================================

class UserBase(BaseModel):
    """
    Base user schema with common fields.
    Used for creating and updating users.
    """
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    age: Optional[int] = Field(None, ge=1, le=120, description="Age in years")
    gender: Optional[str] = Field(None, description="Gender (male, female, other, prefer not to say)")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    @field_validator('gender')
    def validate_gender(cls, v):
        # Keep gender values consistent.
        if v is not None:
            allowed = ['male', 'female', 'other', 'prefer not to say']
            if v.lower() not in allowed:
                raise ValueError(f'Gender must be one of: {allowed}')
        return v


# =============================================================================
# User Creation Schema
# =============================================================================

class UserCreate(UserBase):
    """
    Schema for creating new users.
    Includes password and role assignment.
    """
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    role: UserRole = Field(default=UserRole.PATIENT, description="User role")
    
    @field_validator('password')
    def validate_password_strength(cls, v):
        """
        Basic password strength validation.
        In production, consider more sophisticated checks.
        """
        # Simple rules so passwords are not too weak.
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v


# =============================================================================
# User Update Schema
# =============================================================================

class UserUpdate(BaseModel):
    """
    Schema for updating user information.
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    
    @field_validator('gender')
    def validate_gender(cls, v):
        # Same validation as UserBase for consistency across endpoints
        if v is not None:
            allowed = ['male', 'female', 'other', 'prefer not to say']
            if v.lower() not in allowed:
                raise ValueError(f'Gender must be one of: {allowed}')
        return v


# =============================================================================
# Medical History Update Schema
# =============================================================================

class MedicalHistoryUpdate(BaseModel):
    """
    Schema for updating user's medical history.
    Medical data is sensitive and will be encrypted.
    """
    conditions: Optional[List[str]] = Field(None, description="List of medical conditions")
    medications: Optional[List[str]] = Field(None, description="Current medications")
    allergies: Optional[List[str]] = Field(None, description="Known allergies")
    surgeries: Optional[List[str]] = Field(None, description="Past surgeries")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional medical notes")


# =============================================================================
# User Response Schema
# =============================================================================

class UserResponse(UserBase):
    """
    Schema for user data in API responses.
    Includes system-generated fields.
    """
    id: int = Field(..., description="User ID")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
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
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


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
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
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