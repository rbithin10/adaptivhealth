"""
Tests for the registration endpoint.

Verifies that new users can register, duplicate emails are rejected,
and weak passwords are rejected.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment variables before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-thats-long-enough-32chars")
os.environ.setdefault("PHI_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE=")
os.environ.setdefault("DEBUG", "true")

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.services.auth_service import AuthService
import app.models as app_models

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_register.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    fastapi_app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(fastapi_app)


def create_admin_user() -> None:
    db = TestingSessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin@test.com").first()
        if existing:
            return
        admin = User(
            email="admin@test.com",
            full_name="Admin User",
            age=40,
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        auth_cred = AuthCredential(
            user=admin,
            hashed_password=AuthService.hash_password("Admin1234")
        )
        db.add(auth_cred)
        db.commit()
    finally:
        db.close()


@pytest.fixture
def admin_token(client):
    create_admin_user()
    resp = client.post(
        "/api/v1/login",
        data={"username": "admin@test.com", "password": "Admin1234"}
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return resp.json()["access_token"]


def register_user(client, payload, admin_token):
    return client.post(
        "/api/v1/register",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )


class TestRegistration:
    """Tests for POST /api/v1/register."""

    def test_register_success(self, client, admin_token):
        """A new user can register with valid data."""
        response = register_user(client, {
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "name": "Test User",
            "age": 30,
            "gender": "male",
            "phone": "555-0100",
        }, admin_token)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_register_duplicate_email(self, client, admin_token):
        """Registering with an already used email returns 400."""
        payload = {
            "email": "dupe@example.com",
            "password": "StrongPass1",
            "name": "First User",
        }
        register_user(client, payload, admin_token)

        response = register_user(client, payload, admin_token)
        assert response.status_code == 400

    def test_register_weak_password_no_digit(self, client, admin_token):
        """A password without digits is rejected."""
        response = register_user(client, {
            "email": "weak@example.com",
            "password": "NoDigitsHere",
            "name": "Weak Pass User",
        }, admin_token)
        assert response.status_code == 422

    def test_register_weak_password_too_short(self, client, admin_token):
        """A password shorter than 8 characters is rejected."""
        response = register_user(client, {
            "email": "short@example.com",
            "password": "Ab1",
            "name": "Short Pass User",
        }, admin_token)
        assert response.status_code == 422

    def test_register_weak_password_no_letter(self, client, admin_token):
        """A password without letters is rejected."""
        response = register_user(client, {
            "email": "nolet@example.com",
            "password": "12345678",
            "name": "No Letter User",
        }, admin_token)
        assert response.status_code == 422

    def test_register_missing_email(self, client, admin_token):
        """Omitting email returns a validation error."""
        response = register_user(client, {
            "password": "StrongPass1",
            "name": "No Email User",
        }, admin_token)
        assert response.status_code == 422

    def test_register_missing_name(self, client, admin_token):
        """Omitting name returns a validation error."""
        response = register_user(client, {
            "email": "noname@example.com",
            "password": "StrongPass1",
        }, admin_token)
        assert response.status_code == 422

    def test_register_then_login(self, client, admin_token):
        """A newly registered user can log in."""
        # Register
        register_user(client, {
            "email": "logintest@example.com",
            "password": "StrongPass1",
            "name": "Login Test",
        }, admin_token)

        # Login
        response = client.post("/api/v1/login", data={
            "username": "logintest@example.com",
            "password": "StrongPass1",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
