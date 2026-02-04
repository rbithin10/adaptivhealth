from .auth import router as auth_router
from .user import router as user_router
from .vital_signs import router as vital_signs_router

__all__ = ["auth_router", "user_router", "vital_signs_router"]