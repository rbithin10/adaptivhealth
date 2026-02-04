"""
=============================================================================
ADAPTIV HEALTH - User Model
=============================================================================
Stores user information including patients, clinicians, caregivers, and admins.
Implements RBAC (Role-Based Access Control) as specified in the SRS.
=============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    """
    User roles for Role-Based Access Control (RBAC).
    From SRS Section 2.2 - User Characteristics.
    
    Access Levels:
    - PATIENT: Can view own data, record vitals, receive recommendations
    - CAREGIVER: Limited access to patient data (with permission)
    - CLINICIAN: Can view patient data, medical histories, manage care
    - ADMIN: Full system access, user management
    """
    PATIENT = "patient"
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"
    ADMIN = "admin"


class User(Base):
    """
    User entity from Data Dictionary (Section 4.1).
    
    Stores personal, authentication, and role-related data for each system user.
    Medical history is encrypted for HIPAA compliance.
    
    Attributes:
        id: Unique identifier (Primary Key)
        email: User's email (unique, used for login)
        hashed_password: Bcrypt hashed password
        name: Full name
        age: User's age (for cardiovascular calculations)
        gender: Gender indicator
        role: User role (Patient, Clinician, Caregiver, Admin)
        medical_history_encrypted: Encrypted PHI data
        is_active: Account active status
        is_verified: Email verification status
        created_at: Account creation timestamp
    """
    
    __tablename__ = "users"
    
    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # -------------------------------------------------------------------------
    # Authentication Fields
    # -------------------------------------------------------------------------
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # -------------------------------------------------------------------------
    # Profile Information (from Data Dictionary)
    # -------------------------------------------------------------------------
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)  # male, female, other, prefer not to say
    phone = Column(String(20), nullable=True)
    
    # -------------------------------------------------------------------------
    # Role-Based Access Control
    # -------------------------------------------------------------------------
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=False, index=True)
    
    # -------------------------------------------------------------------------
    # Medical Information (PHI - Encrypted for HIPAA)
    # -------------------------------------------------------------------------
    # Stored as Fernet-encrypted JSON string
    medical_history_encrypted = Column(Text, nullable=True)
    
    # Baseline cardiovascular metrics (for AI calculations)
    baseline_heart_rate = Column(Integer, nullable=True)  # Resting HR
    max_heart_rate = Column(Integer, nullable=True)  # Calculated or measured max HR
    
    # -------------------------------------------------------------------------
    # Emergency Contact Information
    # -------------------------------------------------------------------------
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)
    
    # -------------------------------------------------------------------------
    # Account Status
    # -------------------------------------------------------------------------
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # -------------------------------------------------------------------------
    # Security Fields (HIPAA/SRS Requirements)
    # -------------------------------------------------------------------------
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    # One-to-Many: User has many vital sign records
    vital_signs = relationship(
        "VitalSignRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # One-to-Many: User has many activity sessions
    activity_sessions = relationship(
        "ActivitySession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # One-to-Many: User has many risk assessments
    risk_assessments = relationship(
        "RiskAssessment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # One-to-Many: User has many alerts
    alerts = relationship(
        "Alert",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # One-to-Many: User has many exercise recommendations
    recommendations = relationship(
        "ExerciseRecommendation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # -------------------------------------------------------------------------
    # Indexes for Performance
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_role', 'role'),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"
    
    def calculate_max_heart_rate(self) -> int:
        """
        Calculate estimated maximum heart rate using age-based formula.
        Formula: 220 - age (standard formula)
        
        Returns:
            Estimated max HR in BPM
        """
        if self.age:
            return 220 - self.age
        return 180  # Default for unknown age
    
    def get_heart_rate_zones(self) -> dict:
        """
        Calculate heart rate training zones.
        
        Returns:
            Dictionary with zone names and HR ranges
        """
        max_hr = self.max_heart_rate or self.calculate_max_heart_rate()
        
        return {
            "rest": (0, int(max_hr * 0.5)),
            "light": (int(max_hr * 0.5), int(max_hr * 0.6)),
            "moderate": (int(max_hr * 0.6), int(max_hr * 0.7)),
            "vigorous": (int(max_hr * 0.7), int(max_hr * 0.8)),
            "high": (int(max_hr * 0.8), int(max_hr * 0.9)),
            "maximum": (int(max_hr * 0.9), max_hr),
        }
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until:
            from datetime import datetime, timezone
            return self.locked_until > datetime.now(timezone.utc)
        return False