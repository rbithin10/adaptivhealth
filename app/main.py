"""
=============================================================================
ADAPTIV HEALTH - Main Application
=============================================================================
FastAPI application entry point with CORS, middleware, and route configuration.
Implements HIPAA-compliant health monitoring API.

Features:
- FastAPI with automatic OpenAPI documentation
- CORS support for web dashboard
- Rate limiting and security middleware
- Structured logging
- Health checks and monitoring
=============================================================================
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, check_db_connection
from app.api import auth, user, vital_signs

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


# =============================================================================
# Middleware
# =============================================================================

# CORS middleware for web dashboard and mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure for production
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global HTTP exception handler.
    
    Returns structured error responses.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_exception"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
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
        }
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

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on 0.0.0.0:8000")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )