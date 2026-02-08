"""
API route exports.
This file gathers all route groups in one place.
"""

from .auth import router as auth_router
from .user import router as user_router
from .vital_signs import router as vital_signs_router
from .predict import router as predict_router
from .activity import router as activity_router
from .alert import router as alert_router
from .advanced_ml import router as advanced_ml_router
from .consent import router as consent_router

# Export routers for the main app.
__all__ = [
    "auth_router",
    "user_router",
    "vital_signs_router",
    "predict_router",
    "activity_router",
    "alert_router",
    "advanced_ml_router",
    "consent_router",
]