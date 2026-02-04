"""
=============================================================================
ADAPTIV HEALTH - Database Models Package
=============================================================================
SQLAlchemy ORM models for the Adaptiv Health system.
Based on Data Dictionary from Design Document Section 4.1.
=============================================================================
"""

from app.models.user import User, UserRole
from app.models.vital_signs import VitalSignRecord
from app.models.activity import ActivitySession, ActivityType, ActivityPhase
from app.models.risk_assessment import RiskAssessment, RiskLevel
from app.models.alert import Alert, AlertType, SeverityLevel
from app.models.recommendation import ExerciseRecommendation, IntensityLevel, RecommendationType

# Export all models for easy importing
__all__ = [
    # User
    "User",
    "UserRole",
    
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
]