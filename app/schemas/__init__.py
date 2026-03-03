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
    VitalSignsHistoryResponse,
    EdgeBatchItem,
    EdgeBatchSyncRequest,
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

# Nutrition schemas
from app.schemas.nutrition import (
    MealType,
    NutritionEntryBase,
    NutritionCreate,
    NutritionResponse,
    NutritionListResponse,
    NutritionRecommendationResponse,
    NutritionLogCreate,
    NutritionLogResponse,
)

# Message schemas
from app.schemas.message import (
    MessageCreate,
    MessageResponse,
    InboxSummaryResponse,
)

# Rehab schemas
from app.schemas.rehab import (
    SessionPlanResponse,
    ProgressResponse,
    RehabProgramResponse,
    CompleteSessionRequest,
)

# Medical history schemas
from app.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryResponse,
    MedicationCreate,
    MedicationUpdate,
    MedicationResponse,
    MedicalProfileResponse,
    MedicalExtractionStatusResponse,
    DocumentUploadResponse,
    ExtractionConfirmRequest,
)

# Medication reminder schemas
from app.schemas.medication_reminder import (
    ReminderSettingUpdate,
    ReminderCreate,
    ReminderResponse,
    AdherenceCreate,
    AdherenceResponse,
    AdherenceHistoryResponse,
)

# Food analysis schemas
from app.schemas.food_analysis import (
    FoodAnalysisResponse,
    BarcodeProductResponse,
)

# Natural language schemas
from app.schemas.nl import (
    RiskSummaryResponse,
    TodaysWorkoutResponse,
    AlertExplanationResponse,
    ProgressSummaryResponse,
    ChatRequest,
    ChatResponse,
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
    "VitalSignsHistoryResponse",
    "EdgeBatchItem",
    "EdgeBatchSyncRequest",
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
    # Nutrition
    "MealType",
    "NutritionEntryBase",
    "NutritionCreate",
    "NutritionResponse",
    "NutritionListResponse",
    "NutritionRecommendationResponse",
    "NutritionLogCreate",
    "NutritionLogResponse",

    # Messages
    "MessageCreate",
    "MessageResponse",
    "InboxSummaryResponse",

    # Rehab
    "SessionPlanResponse",
    "ProgressResponse",
    "RehabProgramResponse",
    "CompleteSessionRequest",

    # Medical history
    "MedicalHistoryCreate",
    "MedicalHistoryResponse",
    "MedicationCreate",
    "MedicationUpdate",
    "MedicationResponse",
    "MedicalProfileResponse",
    "MedicalExtractionStatusResponse",
    "DocumentUploadResponse",
    "ExtractionConfirmRequest",

    # Medication reminders
    "ReminderSettingUpdate",
    "ReminderCreate",
    "ReminderResponse",
    "AdherenceCreate",
    "AdherenceResponse",
    "AdherenceHistoryResponse",

    # Food analysis
    "FoodAnalysisResponse",
    "BarcodeProductResponse",

    # Natural language
    "RiskSummaryResponse",
    "TodaysWorkoutResponse",
    "AlertExplanationResponse",
    "ProgressSummaryResponse",
    "ChatRequest",
    "ChatResponse",
]

