"""
=============================================================================
ADAPTIV HEALTH - User Model
=============================================================================
SQLAlchemy model mapped to Massoud's AWS RDS 'users' table.
Adds authentication and security columns for Bithin's backend API.

Original AWS table: 100 users with cardiac patient data.
Extended with: hashed_password, role, security fields for HIPAA compliance.
=============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# Role enum for RBAC (Role-Based Access Control)
class UserRole(str, enum.Enum):
    """
    User roles matching SRS Section 2.2.
    - PATIENT: View own data, receive recommendations
    - CAREGIVER: Limited access to patient data
    - CLINICIAN: View patient data, manage care
    - ADMIN: Full system access
    """
    PATIENT = "patient"
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"
    ADMIN = "admin"


class User(Base):
    """
    Maps to Massoud's 'users' table on AWS RDS PostgreSQL.
    Keeps Massoud's original columns and adds Bithin's auth/security columns.
    """

    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # Primary Key - matches Massoud's user_id column
    # -------------------------------------------------------------------------
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Massoud's original columns (already in AWS RDS)
    # -------------------------------------------------------------------------
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    medical_history = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low/moderate/high from ML
    baseline_hr = Column(Integer, nullable=True)
    max_safe_hr = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=True)

    # PHI encryption for medical data
    medical_history_encrypted = Column(Text, nullable=True)

    # Emergency contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Updated timestamp
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # -------------------------------------------------------------------------
    # Relationships - use user_id as the FK reference
    # -------------------------------------------------------------------------
    # Authentication credentials (separate table for security)
    auth_credential = relationship(
        "AuthCredential", back_populates="user",
        cascade="all, delete-orphan", uselist=False,
        lazy="joined"  # Always load with user
    )
    
    vital_signs = relationship(
        "VitalSignRecord", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    activity_sessions = relationship(
        "ActivitySession", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    risk_assessments = relationship(
        "RiskAssessment", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    alerts = relationship(
        "Alert", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    recommendations = relationship(
        "ExerciseRecommendation", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_role', 'role'),
        {'extend_existing': True}
    )

    # -------------------------------------------------------------------------
    # Convenience properties to keep API compatibility
    # -------------------------------------------------------------------------
    @property
    def id(self):
        """Alias for user_id to keep API code working."""
        return self.user_id

    @property
    def name(self):
        """Alias for full_name to keep API code working."""
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    @property
    def baseline_heart_rate(self):
        """Alias for baseline_hr."""
        return self.baseline_hr

    @property
    def max_heart_rate(self):
        """Alias for max_safe_hr."""
        return self.max_safe_hr

    @max_heart_rate.setter
    def max_heart_rate(self, value):
        self.max_safe_hr = value

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, role={self.role})>"

    def calculate_max_heart_rate(self) -> int:
        """Calculate estimated max HR using 220 - age formula."""
        if self.age:
            return 220 - self.age
        return 180

    def get_heart_rate_zones(self) -> dict:
        """Calculate heart rate training zones."""
        max_hr = self.max_safe_hr or self.calculate_max_heart_rate()
        return {
            "rest": (0, int(max_hr * 0.5)),
            "light": (int(max_hr * 0.5), int(max_hr * 0.6)),
            "moderate": (int(max_hr * 0.6), int(max_hr * 0.7)),
            "vigorous": (int(max_hr * 0.7), int(max_hr * 0.8)),
            "high": (int(max_hr * 0.8), int(max_hr * 0.9)),
            "maximum": (int(max_hr * 0.9), max_hr),
        }

    def is_account_locked(self) -> bool:
        """Check if account is currently locked via auth_credential."""
        if self.auth_credential:
            return self.auth_credential.is_locked()
        return False
