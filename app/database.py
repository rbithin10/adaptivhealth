"""
Database setup.

Connects to the PostgreSQL database and manages sessions (conversations
with the database). Uses connection pooling so we reuse connections
instead of opening a new one for every single request.
"""

# SQLAlchemy is the library that lets Python talk to PostgreSQL
from sqlalchemy import create_engine, event, text
# declarative_base lets us define database tables as Python classes
from sqlalchemy.ext.declarative import declarative_base
# sessionmaker creates database session objects; Session is the type hint
from sqlalchemy.orm import sessionmaker, Session
# QueuePool keeps a pool of database connections ready to use
from sqlalchemy.pool import QueuePool
# Generator is a type hint for functions that "yield" values
from typing import Generator
# Logging lets us record what happens for debugging and auditing
import logging

# Import our app settings (database URL, environment, etc.)
from app.config import settings

# Set up a logger specifically for database-related messages
logger = logging.getLogger(__name__)

# =============================================================================
# Database Engine Configuration
# =============================================================================

# Check if we are running in production (live server) or development (local)
_is_production = settings.environment == "production"
# Tell PostgreSQL to always use UTC timezone for consistency
_connect_args: dict = {"options": "-c timezone=utc"}
# In production, force encrypted SSL connections to AWS RDS for security
if _is_production:
    _connect_args["sslmode"] = "require"
    _connect_args["sslrootcert"] = "/etc/ssl/certs/rds-ca.pem"

# Create the main database engine — this is the central connection manager
engine = create_engine(
    settings.database_url,          # The database address from our settings
    poolclass=QueuePool,            # Use a queue-based pool to reuse connections
    pool_pre_ping=True,             # Test each connection is alive before using it
    pool_size=10,                   # Keep 10 connections open and ready at all times
    max_overflow=20,                # Allow up to 20 extra connections during busy periods
    pool_recycle=3600,              # Replace connections after 1 hour to prevent timeouts
    echo=settings.debug,            # Print SQL queries to console when debug mode is on
    connect_args=_connect_args,     # Pass the timezone and SSL settings above
)

# =============================================================================
# Session Factory
# =============================================================================

# Create a factory that produces new database sessions on demand
# Each session is like a short conversation with the database
SessionLocal = sessionmaker(
    autocommit=False,   # We control when changes are saved (not automatic)
    autoflush=False,    # We control when pending changes are sent to the database
    bind=engine         # Connect these sessions to our engine above
)

# =============================================================================
# Base Model Class
# =============================================================================

# Every database table class (User, VitalSigns, etc.) inherits from this base
Base = declarative_base()


# =============================================================================
# Database Session Dependency
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session to each API request, then cleans up after.

    How it works:
        1. Opens a fresh database session when a request starts
        2. Hands the session to the route so it can read/write data
        3. Saves any changes if everything went well
        4. Undoes all changes if something went wrong
        5. Always closes the session when the request is done
    """
    # Open a new database session
    db = SessionLocal()
    try:
        # Hand over the session to the route that requested it
        yield db
        # If the route finished without errors, save all pending changes
        db.commit()
    except Exception as e:
        # If something went wrong, undo all changes to keep data consistent
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        # No matter what happened, close the session to free the connection
        db.close()


# =============================================================================
# Database Initialization
# =============================================================================

def init_db() -> None:
    """
    Create all database tables if they don't exist yet.

    Called automatically when the app starts up in development.
    In production, we use migration scripts instead for more control.
    """
    # Import every model file so SQLAlchemy knows which tables to create
    # Without these imports, SQLAlchemy wouldn't know about our tables
    from app.models import (
        user,
        auth_credential,
        vital_signs,
        activity,
        risk_assessment,
        alert,
        recommendation,
        nutrition,
        message,
        token_blocklist,
    )
    
    logger.info("Creating database tables...")
    
    # Look at all the model classes and create any missing tables in PostgreSQL
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database tables created successfully")


def drop_db() -> None:
    """
    Delete all database tables and their data.
    
    WARNING: This destroys everything! Only use during development or testing.
    """
    # Safety check — never allow this to run on the live production server
    if settings.environment == "production":
        raise RuntimeError("Cannot drop database in production!")
    
    logger.warning("Dropping all database tables...")
    # Remove every table that SQLAlchemy knows about from the database
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


# =============================================================================
# Database Health Check
# =============================================================================

def check_db_connection() -> bool:
    """
    Quick test to make sure we can actually talk to the database.
    Returns True if the connection works, False if something is wrong.
    """
    try:
        # Try running a simple query — if this works, the database is reachable
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
    Runs before every SQL query. In debug mode, logs what query is about to run.
    Helps developers see exactly what the app is asking the database to do.
    """
    if settings.debug:
        # Only show the first 100 characters to keep logs readable
        logger.debug(f"SQL: {statement[:100]}...")