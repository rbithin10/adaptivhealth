"""
Schemas used by the API (request and response shapes).
"""

# User schemas
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserProfileResponse,
    UserListResponse,
    UserCreateAdmin,
    MedicalHistoryUpdate
)

# Vital signs schemas
from app.schemas.vital_signs import (
    VitalSignCreate,
    VitalSignResponse,
    VitalSignsHistoryResponse
)

# Activity schemas
from app.schemas.activity import (
    ActivityType,
    ActivityPhase,
    ActivitySessionBase,
    ActivitySessionCreate,
    ActivitySessionUpdate,
    ActivitySessionResponse
)

# Alert schemas
from app.schemas.alert import (
    AlertType,
    SeverityLevel,
    AlertBase,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse
)

# Risk assessment schemas
from app.schemas.risk_assessment import (
    RiskLevel,
    RiskAssessmentBase,
    RiskAssessmentCreate,
    RiskAssessmentUpdate,
    RiskAssessmentResponse,
    RiskAssessmentListResponse
)

# Recommendation schemas
from app.schemas.recommendation import (
    IntensityLevel,
    RecommendationType,
    RecommendationBase,
    RecommendationCreate,
    RecommendationUpdate,
    RecommendationResponse,
    RecommendationListResponse
)

__all__ = [
    # User
    "UserResponse",
    "UserUpdate",
    "UserProfileResponse",
    "UserListResponse",
    "UserCreateAdmin",
    "MedicalHistoryUpdate",
    # Vital signs
    "VitalSignCreate",
    "VitalSignResponse",
    "VitalSignListResponse",
    # Activity
    "ActivityType",
    "ActivityPhase",
    "ActivitySessionBase",
    "ActivitySessionCreate",
    "ActivitySessionUpdate",
    "ActivitySessionResponse",
    # Alert
    "AlertType",
    "SeverityLevel",
    "AlertBase",
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertListResponse",
    # Risk assessment
    "RiskLevel",
    "RiskAssessmentBase",
    "RiskAssessmentCreate",
    "RiskAssessmentUpdate",
    "RiskAssessmentResponse",
    "RiskAssessmentListResponse",
    # Recommendation
    "IntensityLevel",
    "RecommendationType",
    "RecommendationBase",
    "RecommendationCreate",
    "RecommendationUpdate",
    "RecommendationResponse",
    "RecommendationListResponse",
]

