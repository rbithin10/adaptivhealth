"""
Main app entry point.

Starts the server, sets up security rules, connects to the database,
and loads the AI model. Also handles startup and shutdown events.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import logging
import re
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, check_db_connection
from app.api import auth, user, vital_signs, predict, activity, alert, advanced_ml, consent, nl_endpoints, nutrition, messages, medical_history, medication_reminder, rehab, food_analysis
from app.rate_limiter import limiter
from app.services.ml_prediction import load_ml_model

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Adaptive Health API...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Check database connection
    if not check_db_connection():
        logger.error("Database connection check failed")
        raise RuntimeError("Cannot connect to database")
    
    # Load ML model (Massoud's trained Random Forest)
    # Uses absolute paths and joblib for production safety
    try:
        if load_ml_model():
            logger.info("ML model loaded successfully at startup")
        else:
            logger.warning("ML model failed to load - prediction endpoints will return 503")
    except Exception as e:
        logger.warning(f"ML model loading skipped due to error: {e}")
    
    logger.info("Adaptive Health API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Adaptive Health API...")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Adaptive Health API",
    description="HIPAA-compliant cardiovascular monitoring and AI-driven health platform",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json"
)

# SlowAPI rate limiter
app.state.limiter = limiter
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 with Retry-After header when rate limit is hit."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]


# =============================================================================
# Middleware
# =============================================================================

# CORS middleware for web dashboard and mobile app
# Using regex to allow any localhost/127.0.0.1 port for development
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"  # local dev
        r"|^https://(dashboard\.|www\.)?adaptivhealth\.com$"  # custom domain
        r"|^https://dashboard-adaptivhealthuowd\.xyz$"  # custom Vercel dashboard domain
        r"|^https?://adaptivhealth-alb-[\w-]+\.me-central-1\.elb\.amazonaws\.com(:\d+)?$"  # AWS ALB
        r"|^https?://[\w-]+\.cloudfront\.net(:\d+)?$"  # CloudFront CDN
        r"|^https?://[\w.-]+\.s3-website[.-][\w-]+\.amazonaws\.com(:\d+)?$"  # S3 static hosting
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # Allow all hosts — tighten before production go-live
    )


# =============================================================================
# Custom Middleware
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests.
    
    Includes timing and basic request info.
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        return response
        
    except Exception as e:
        # Log error
        process_time = time.time() - start_time
        logger.error(
            f"Error: {request.method} {request.url.path} - "
            f"Error: {str(e)} - Time: {process_time:.3f}s"
        )
        raise


# =============================================================================
# Exception Handlers
# =============================================================================

def _cors_headers(request: Request) -> dict:
    """Build CORS headers from request origin so error responses aren't blocked by the browser."""
    origin = request.headers.get("origin", "")
    # Allow localhost dev origins
    if re.match(r"^http://(localhost|127\.0\.0\.1):\d+$", origin):
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }

    # Allow the production dashboard origin explicitly so error responses
    # are not blocked by browsers when clients call the API.
    if origin == "https://dashboard-adaptivhealthuowd.xyz":
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }

    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global HTTP exception handler.

    Returns FastAPI standard error format for consistency with clients.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Logs error and returns generic response.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error"
            }
        },
        headers=_cors_headers(request),
    )


# =============================================================================
# API Routes
# =============================================================================

# Include API routers with prefixes
app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["Authentication"]
)

app.include_router(
    user.router,
    prefix="/api/v1/users",
    tags=["User Management"]
)

app.include_router(
    vital_signs.router,
    prefix="/api/v1",
    tags=["Vital Signs"]
)

# Activity routes
app.include_router(
    activity.router,
    prefix="/api/v1",
    tags=["Activities"]
)

# Alert routes
app.include_router(
    alert.router,
    prefix="/api/v1",
    tags=["Alerts"]
)

# ML Prediction routes
app.include_router(
    predict.router,
    prefix="/api/v1",
    tags=["AI Risk Prediction"]
)

# Advanced ML routes
app.include_router(
    advanced_ml.router,
    prefix="/api/v1",
    tags=["Advanced ML"]
)

# Consent routes
app.include_router(
    consent.router,
    prefix="/api/v1",
    tags=["Consent / Data Sharing"]
)

# Natural Language AI Coach routes
app.include_router(
    nl_endpoints.router,
    prefix="/api/v1/nl",
    tags=["AI Coach Natural Language"]
)

# Nutrition routes
app.include_router(
    nutrition.router,
    prefix="/api/v1",
    tags=["Nutrition"]
)

# Messages routes
app.include_router(
    messages.router,
    prefix="/api/v1",
    tags=["Messages"]
)

# Medical History & Medications routes
app.include_router(
    medical_history.router,
    prefix="/api/v1",
    tags=["Medical Profile"]
)

# Medication Reminders routes
app.include_router(
    medication_reminder.router,
    prefix="/api/v1",
    tags=["Medication Reminders"]
)

# Rehab Programs routes
app.include_router(
    rehab.router,
    prefix="/api/v1",
    tags=["Rehab Programs"]
)

# Food Analysis routes
app.include_router(
    food_analysis.router,
    prefix="/api/v1/food",
    tags=["Food Analysis"]
)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns API status and version.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": time.time()
    }


@app.get("/health/db")
async def database_health_check():
    """
    Database health check endpoint.
    
    Verifies database connectivity.
    """
    if check_db_connection():
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }
    else:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Adaptive Health API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# =============================================================================
# Startup Message
# =============================================================================

if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    
    logger.info(f"Starting server on 0.0.0.0:8080")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="info"
    )