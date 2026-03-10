"""
=============================================================================
ADAPTIV HEALTH - User Model
=============================================================================
SQLAlchemy model mapped to Massoud's AWS RDS 'users' table.
Adds authentication and security columns for Bithin's backend API.

Original AWS table: 100 users with cardiac patient data.
Extended with: hashed_password, role, security fields for HIPAA compliance.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - UserRole......................... Line 35  (PATIENT, CLINICIAN, ADMIN)
#
# CLASS: User (SQLAlchemy Model)
#   - Primary Key...................... Line 55  (user_id)
#   - Massoud's Columns................ Line 60  (email, full_name, age, etc.)
#   - Bithin's Auth Columns............ Line 85  (role, security fields)
#   - Consent Columns.................. Line 100 (data sharing state)
#   - Relationships.................... Line 125 (auth_credential, vitals, etc.)
#   - Properties....................... Line 135 (id, name, baseline_hr)
#   - Methods.......................... Line 164 (calculate_max_hr, hr_zones)
#
# BUSINESS CONTEXT:
# - Central user entity for all patient/clinician data
# - HIPAA-compliant with encrypted PHI fields
# - RBAC roles control API access
# =============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Float, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# Role enum for RBAC (Role-Based Access Control)
class UserRole(str, enum.Enum):
    """
    User roles matching SRS Section 2.2.
    - PATIENT: View own data, receive recommendations
    - CLINICIAN: View patient data, manage care
    - ADMIN: Full system access
    """
    PATIENT = "patient"
    CLINICIAN = "clinician"
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
    email = Column(String(255), unique=True, index=True, nullable=False)    # User's email address (used for login)
    full_name = Column(String(255), nullable=True)    # User's full name (e.g. "John Smith")
    age = Column(Integer, nullable=True)              # User's age in years
    gender = Column(String(10), nullable=True)        # Male, female, or other
    weight_kg = Column(Float, nullable=True)          # Body weight in kilograms
    height_cm = Column(Float, nullable=True)          # Height in centimetres
    medical_history = Column(Text, nullable=True)     # Free-text medical history notes
    risk_level = Column(String(20), nullable=True)    # AI-predicted cardiac risk: low, moderate, or high
    baseline_hr = Column(Integer, nullable=True)      # Resting heart rate (BPM) — used as a health reference
    max_safe_hr = Column(Integer, nullable=True)      # Maximum safe heart rate during exercise
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)  # When the account was created
    phone = Column(String(20), nullable=True)         # Contact phone number
    role = Column(Enum(UserRole), default=UserRole.PATIENT, server_default="patient", nullable=True)  # User role: patient, clinician, or admin

    # Account status flags
    is_active = Column(Boolean, default=True, nullable=True)    # Whether the account is active (False = deactivated)
    is_verified = Column(Boolean, default=False, nullable=True) # Whether the user has verified their email

    # Encrypted version of medical history for HIPAA-compliant storage
    medical_history_encrypted = Column(Text, nullable=True)

    # Emergency contact details — who to call if something goes wrong
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Automatically updated whenever the user record changes
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # -------------------------------------------------------------------------
    # Consent / Data Sharing (Phase 3) — controls whether clinicians can see patient data
    # -------------------------------------------------------------------------
    # Current sharing state: SHARING_ON, SHARING_DISABLE_REQUESTED, or SHARING_OFF
    share_state = Column(
        String(30), default="SHARING_ON", nullable=False,
        server_default="SHARING_ON"
    )
    share_requested_at = Column(DateTime(timezone=True), nullable=True)   # When the patient asked to change sharing
    share_requested_by = Column(Integer, nullable=True)                   # Who made the sharing request (user ID)
    share_reviewed_at = Column(DateTime(timezone=True), nullable=True)    # When a clinician reviewed the request
    share_reviewed_by = Column(Integer, nullable=True)                    # Which clinician reviewed it
    share_decision = Column(String(20), nullable=True)                    # The clinician's decision: approve or reject
    share_reason = Column(String(500), nullable=True)                     # Reason given for the request or decision
    
    # Which phase of cardiac rehab the patient is in (set during account setup)
    rehab_phase = Column(String(30), nullable=True, default="not_in_rehab")  # phase_2, phase_3, or not_in_rehab

    # Lifestyle & wellness data (collected when the patient first sets up their account)
    activity_level = Column(String(20), nullable=True)       # How active: none, light, moderate, or active
    exercise_limitations = Column(Text, nullable=True)       # Physical limitations as a list (e.g. joint pain, shortness of breath)
    primary_goal = Column(String(50), nullable=True)         # Main health goal: reduce BP, lose weight, post-surgery recovery, etc.
    stress_level = Column(Integer, nullable=True)            # Self-reported stress on a scale of 1-10
    sleep_quality = Column(String(10), nullable=True)        # Sleep quality: good, fair, or poor
    smoking_status = Column(String(20), nullable=True)       # Smoking status: never, former, or current
    alcohol_frequency = Column(String(20), nullable=True)    # Drinking habits: never, occasional, moderate, or heavy
    sedentary_hours = Column(Float, nullable=True)           # Hours spent sitting per day (0-24)
    phq2_score = Column(Integer, nullable=True)              # Depression screening score (0-6, higher = more concern)

    # Which clinician is responsible for this patient's care
    assigned_clinician_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)

    # -------------------------------------------------------------------------
    # Relationships — links this user to their related data in other tables
    # -------------------------------------------------------------------------
    # Login credentials (password hash, failed attempts, lockout) stored separately for security
    auth_credential = relationship(
        "AuthCredential", back_populates="user",
        cascade="all, delete-orphan", uselist=False,
        lazy="joined"  # Always load login info together with the user
    )
    
    # All heart rate, blood pressure, and SpO2 readings from this patient's wearable
    vital_signs = relationship(
        "VitalSignRecord", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # All workout/exercise sessions this patient has logged
    activity_sessions = relationship(
        "ActivitySession", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # AI-generated cardiac risk assessments for this patient
    risk_assessments = relationship(
        "RiskAssessment", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # Health alerts triggered for this patient (high HR, low SpO2, etc.)
    alerts = relationship(
        "Alert", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # Personalised exercise recommendations from the AI
    recommendations = relationship(
        "ExerciseRecommendation", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # Meals and nutrition entries logged by this patient
    nutrition_entries = relationship(
        "NutritionEntry", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic"
    )
    # Medical conditions (diabetes, hypertension, etc.) on file for this patient
    medical_conditions = relationship(
        "PatientMedicalHistory", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic",
        foreign_keys="[PatientMedicalHistory.user_id]"
    )
    # Medications the patient is currently taking or has taken
    medications = relationship(
        "PatientMedication", back_populates="user",
        cascade="all, delete-orphan", lazy="dynamic",
        foreign_keys="[PatientMedication.user_id]"
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

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, role={self.role})>"

    def calculate_max_heart_rate(self) -> int:
        """Estimate the maximum safe heart rate using the standard formula: 220 minus age."""
        if self.age:
            return 220 - self.age
        # Default to 180 BPM if we don't know the patient's age
        return 180

    def get_heart_rate_zones(self) -> dict:
        """Calculate the heart rate training zones used to guide safe exercise intensity."""
        # Use the doctor-set max HR, or calculate from age
        max_hr = self.max_safe_hr or self.calculate_max_heart_rate()
        # Each zone is a percentage range of the maximum heart rate
        return {
            "rest": (0, int(max_hr * 0.5)),            # Very light — barely moving
            "light": (int(max_hr * 0.5), int(max_hr * 0.6)),      # Light activity like slow walking
            "moderate": (int(max_hr * 0.6), int(max_hr * 0.7)),   # Moderate exercise like brisk walking
            "vigorous": (int(max_hr * 0.7), int(max_hr * 0.8)),   # Hard exercise like jogging
            "high": (int(max_hr * 0.8), int(max_hr * 0.9)),       # Very hard exercise
            "maximum": (int(max_hr * 0.9), max_hr),               # Maximum effort — use with caution
        }

    def is_account_locked(self) -> bool:
        """Check if the account is temporarily locked due to too many failed login attempts."""
        if self.auth_credential:
            return self.auth_credential.is_locked()
        return False
