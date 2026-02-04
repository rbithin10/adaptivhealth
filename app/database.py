"""
=============================================================================
ADAPTIV HEALTH - Database Configuration
=============================================================================
Sets up SQLAlchemy connection to PostgreSQL.
Implements connection pooling and session management for high performance.
=============================================================================
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config import settings

# Configure logging for database operations
logger = logging.getLogger(__name__)

# =============================================================================
# Database Engine Configuration
# =============================================================================

# Create database engine with connection pooling
# pool_pre_ping: Checks connections are alive before using (prevents stale connections)
# pool_size: Number of persistent connections in the pool
# max_overflow: Additional connections allowed during high load
# pool_recycle: Recycle connections after this many seconds (prevents timeouts)
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.debug,  # Log SQL queries in debug mode
    connect_args={} if "sqlite" in settings.database_url else {
        "options": "-c timezone=utc"  # Force UTC timezone for PostgreSQL
    }
)

# =============================================================================
# Session Factory
# =============================================================================

# Session factory - creates new database sessions
# autocommit=False: Transactions are explicit
# autoflush=False: Don't auto-flush changes (more control)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =============================================================================
# Base Model Class
# =============================================================================

# Base class for all SQLAlchemy models
Base = declarative_base()


# =============================================================================
# Database Session Dependency
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Creates a new session for each request and ensures proper cleanup.
    
    Usage in routes:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Lifecycle:
        1. Creates session at request start
        2. Yields session for use in route
        3. Commits on success (if changes made)
        4. Rolls back on error
        5. Always closes session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit any pending changes
    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()  # Always close the session


# =============================================================================
# Database Initialization
# =============================================================================

def init_db() -> None:
    """
    Initialize database tables.
    
    Called on application startup in development.
    In production, use Alembic migrations instead.
    
    This imports all models to register them with SQLAlchemy,
    then creates any missing tables.
    """
    # Import all models so SQLAlchemy knows about them
    # This is necessary for Base.metadata to have all table definitions
    from app.models import (
        user,
        vital_signs,
        activity,
        risk_assessment,
        alert,
        recommendation
    )
    
    logger.info("Creating database tables...")
    
    # Create all tables that don't exist
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database tables created successfully")


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This destroys all data! Only use in development/testing.
    """
    if settings.environment == "production":
        raise RuntimeError("Cannot drop database in production!")
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


# =============================================================================
# Database Health Check
# =============================================================================

def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


# =============================================================================
# Event Listeners (Audit Logging for HIPAA)
# =============================================================================

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Event listener for SQL query logging.
    Useful for audit trails and debugging.
    """
    if settings.debug:
        logger.debug(f"SQL: {statement[:100]}...")  # Log first 100 chars