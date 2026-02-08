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
from app.main import app

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


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


class TestRegistration:
    """Tests for POST /api/v1/register."""

    def test_register_success(self, client):
        """A new user can register with valid data."""
        response = client.post("/api/v1/register", json={
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "name": "Test User",
            "age": 30,
            "gender": "male",
            "phone": "555-0100",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_register_duplicate_email(self, client):
        """Registering with an already used email returns 400."""
        payload = {
            "email": "dupe@example.com",
            "password": "StrongPass1",
            "name": "First User",
        }
        client.post("/api/v1/register", json=payload)

        response = client.post("/api/v1/register", json=payload)
        assert response.status_code == 400

    def test_register_weak_password_no_digit(self, client):
        """A password without digits is rejected."""
        response = client.post("/api/v1/register", json={
            "email": "weak@example.com",
            "password": "NoDigitsHere",
            "name": "Weak Pass User",
        })
        assert response.status_code == 422

    def test_register_weak_password_too_short(self, client):
        """A password shorter than 8 characters is rejected."""
        response = client.post("/api/v1/register", json={
            "email": "short@example.com",
            "password": "Ab1",
            "name": "Short Pass User",
        })
        assert response.status_code == 422

    def test_register_weak_password_no_letter(self, client):
        """A password without letters is rejected."""
        response = client.post("/api/v1/register", json={
            "email": "nolet@example.com",
            "password": "12345678",
            "name": "No Letter User",
        })
        assert response.status_code == 422

    def test_register_missing_email(self, client):
        """Omitting email returns a validation error."""
        response = client.post("/api/v1/register", json={
            "password": "StrongPass1",
            "name": "No Email User",
        })
        assert response.status_code == 422

    def test_register_missing_name(self, client):
        """Omitting name returns a validation error."""
        response = client.post("/api/v1/register", json={
            "email": "noname@example.com",
            "password": "StrongPass1",
        })
        assert response.status_code == 422

    def test_register_then_login(self, client):
        """A newly registered user can log in."""
        # Register
        client.post("/api/v1/register", json={
            "email": "logintest@example.com",
            "password": "StrongPass1",
            "name": "Login Test",
        })

        # Login
        response = client.post("/api/v1/login", data={
            "username": "logintest@example.com",
            "password": "StrongPass1",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
