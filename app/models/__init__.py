"""
Database tables (models).

Defines the structure of all tables in the database: users, vital signs,
alerts, recommendations, etc.
"""

from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.models.vital_signs import VitalSignRecord
from app.models.activity import ActivitySession, ActivityType, ActivityPhase
from app.models.risk_assessment import RiskAssessment, RiskLevel
from app.models.alert import Alert, AlertType, SeverityLevel
from app.models.recommendation import ExerciseRecommendation, IntensityLevel, RecommendationType
from app.models.nutrition import NutritionEntry, MealType
from app.models.message import Message
from app.models.rehab import RehabProgram, RehabSessionLog
from app.models.medical_history import (
    PatientMedicalHistory, PatientMedication, UploadedDocument,
    ConditionType, ConditionStatus, DrugClass, MedicationStatus, DocumentStatus,
)
from app.models.medication_adherence import MedicationAdherence
from app.models.token_blocklist import TokenBlocklist

# Export all models for easy importing
__all__ = [
    # User & Auth
    "User",
    "UserRole",
    "AuthCredential",
    "TokenBlocklist",

    # Vital Signs
    "VitalSignRecord",

    # Activity
    "ActivitySession",
    "ActivityType",
    "ActivityPhase",

    # Risk Assessment
    "RiskAssessment",
    "RiskLevel",

    # Alert
    "Alert",
    "AlertType",
    "SeverityLevel",

    # Recommendation
    "ExerciseRecommendation",
    "IntensityLevel",
    "RecommendationType",

    # Nutrition
    "NutritionEntry",
    "MealType",

    # Messages
    "Message",

    # Rehab Programs
    "RehabProgram",
    "RehabSessionLog",

    # Medical History & Medications
    "PatientMedicalHistory",
    "PatientMedication",
    "UploadedDocument",
    "ConditionType",
    "ConditionStatus",
    "DrugClass",
    "MedicationStatus",
    "DocumentStatus",

    # Medication Adherence
    "MedicationAdherence",
]