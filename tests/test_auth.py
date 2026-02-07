"""
Tests for authentication endpoints and services.

Covers:
- User registration
- Login flow (success, failure, lockout)
- Token creation and validation
- Password reset
- Field name consistency (locked_until)
"""

import pytest
from datetime import timedelta, datetime, timezone
from app.services.auth_service import AuthService
from app.models.auth_credential import AuthCredential


# ============================================================================
# AuthService unit tests
# ============================================================================

class TestAuthService:
    """Tests for AuthService password and token helpers."""

    def test_hash_and_verify_password(self, auth_service):
        hashed = auth_service.hash_password("Secure123")
        assert auth_service.verify_password("Secure123", hashed)
        assert not auth_service.verify_password("Wrong123", hashed)

    def test_access_token_creation(self, auth_service):
        token = auth_service.create_access_token(data={"sub": "1", "role": "patient"})
        payload = auth_service.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

    def test_refresh_token_creation(self, auth_service):
        token = auth_service.create_refresh_token(data={"sub": "1"})
        payload = auth_service.decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_token_preserves_custom_type(self, auth_service):
        """Password-reset tokens set type='password_reset'; it must be kept."""
        token = auth_service.create_access_token(
            data={"user_id": 1, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )
        payload = auth_service.decode_token(token)
        assert payload["type"] == "password_reset"

    def test_expired_token_returns_none(self, auth_service):
        token = auth_service.create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-1),
        )
        assert auth_service.decode_token(token) is None


# ============================================================================
# AuthCredential model tests
# ============================================================================

class TestAuthCredential:
    """Tests for account-lockout logic using correct field names."""

    def test_locked_until_field_exists(self):
        """Verify the model uses 'locked_until', not 'account_locked_until'."""
        cred = AuthCredential(hashed_password="x")
        assert hasattr(cred, "locked_until")
        assert not hasattr(cred, "account_locked_until")

    def test_is_locked_when_locked_until_in_future(self):
        cred = AuthCredential(hashed_password="x")
        cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert cred.is_locked()

    def test_not_locked_when_locked_until_past(self):
        cred = AuthCredential(hashed_password="x")
        cred.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert not cred.is_locked()

    def test_not_locked_when_null(self):
        cred = AuthCredential(hashed_password="x")
        assert not cred.is_locked()


# ============================================================================
# Registration endpoint tests
# ============================================================================

class TestRegistration:
    """Tests for POST /api/v1/register."""

    def test_register_success(self, client):
        resp = client.post("/api/v1/register", json={
            "email": "new@test.com",
            "name": "New User",
            "password": "StrongPass1",
            "age": 30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@test.com"

    def test_register_duplicate_email(self, client, test_user):
        resp = client.post("/api/v1/register", json={
            "email": "patient@test.com",
            "name": "Dup",
            "password": "StrongPass1",
        })
        assert resp.status_code == 400

    def test_register_weak_password(self, client):
        resp = client.post("/api/v1/register", json={
            "email": "weak@test.com",
            "name": "Weak",
            "password": "short",
        })
        assert resp.status_code == 422  # Pydantic validation


# ============================================================================
# Login endpoint tests
# ============================================================================

class TestLogin:
    """Tests for POST /api/v1/login."""

    def test_login_success(self, client, test_user):
        resp = client.post("/api/v1/login", data={
            "username": "patient@test.com",
            "password": "Password1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        resp = client.post("/api/v1/login", data={
            "username": "patient@test.com",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/login", data={
            "username": "nobody@test.com",
            "password": "Anything1",
        })
        assert resp.status_code == 401


# ============================================================================
# Protected endpoint tests
# ============================================================================

class TestProtectedEndpoints:
    """Tests for token-protected routes."""

    def test_get_me_with_valid_token(self, client, patient_token):
        resp = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 200

    def test_get_me_without_token(self, client):
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401
