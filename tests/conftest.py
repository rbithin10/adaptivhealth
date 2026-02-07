"""
Test configuration and shared fixtures for AdaptivHealth.

Provides:
- In-memory SQLite database for isolated testing
- Pre-configured FastAPI test client
- User creation helpers
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set SECRET_KEY before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-32chars!")
os.environ.setdefault("PHI_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE=")  # 32 bytes base64
os.environ.setdefault("DEBUG", "true")  # Skip TrustedHostMiddleware in tests

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional database session for tests."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client wired to the test database."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_service():
    """Return a fresh AuthService instance."""
    return AuthService()


@pytest.fixture
def test_user(db_session, auth_service):
    """Create a test patient user with auth credentials."""
    user = User(
        email="patient@test.com",
        full_name="Test Patient",
        age=35,
        gender="male",
        role=UserRole.PATIENT,
        is_active=True,
        is_verified=True,
    )
    auth_cred = AuthCredential(
        user=user,
        hashed_password=auth_service.hash_password("Password1"),
    )
    db_session.add(user)
    db_session.add(auth_cred)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session, auth_service):
    """Create a test admin user with auth credentials."""
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        age=40,
        gender="female",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    auth_cred = AuthCredential(
        user=user,
        hashed_password=auth_service.hash_password("AdminPass1"),
    )
    db_session.add(user)
    db_session.add(auth_cred)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def patient_token(test_user, auth_service):
    """Return a valid JWT access token for the test patient."""
    return auth_service.create_access_token(
        data={"sub": str(test_user.user_id), "role": "patient"}
    )


@pytest.fixture
def admin_token(test_admin, auth_service):
    """Return a valid JWT access token for the test admin."""
    return auth_service.create_access_token(
        data={"sub": str(test_admin.user_id), "role": "admin"}
    )
