"""
Tests for extended auth functions.

Covers functions in app/api/auth.py at 0%:
- check_clinician_phi_access
- get_current_admin_or_doctor_user
- refresh_token
- request_password_reset
- confirm_password_reset

Run with:
    pytest tests/test_auth_extended.py -v
"""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from app.main import app as fastapi_app
from app.api.auth import check_clinician_phi_access
from app.models.user import User, UserRole
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


# =============================================================================
# check_clinician_phi_access Tests
# =============================================================================

class TestCheckClinicianPHIAccess:
    """Test check_clinician_phi_access function from app/api/auth.py."""

    def test_clinician_accesses_patient_sharing_on_does_not_raise(self, db_session):
        """Test clinician accessing patient with share_state='SHARING_ON' does not raise."""
        clinician = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        patient.share_state = "SHARING_ON"
        db_session.commit()
        
        # Should not raise
        check_clinician_phi_access(clinician, patient)

    def test_clinician_accesses_patient_sharing_off_raises_403(self, db_session):
        """Test clinician accessing patient with share_state='SHARING_OFF' raises HTTPException 403."""
        clinician = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        patient.share_state = "SHARING_OFF"
        db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            check_clinician_phi_access(clinician, patient)
        
        assert exc_info.value.status_code == 403
        assert "disabled data sharing" in exc_info.value.detail.lower()

    def test_clinician_accesses_patient_sharing_disable_requested_does_not_raise(self, db_session):
        """Test clinician accessing patient with share_state='SHARING_DISABLE_REQUESTED' does not raise."""
        clinician = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        patient.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()
        
        # Should not raise (pending disable request still allows access)
        check_clinician_phi_access(clinician, patient)


# =============================================================================
# get_current_admin_or_doctor_user Tests
# =============================================================================

class TestGetCurrentAdminOrDoctorUser:
    """Test get_current_admin_or_doctor_user dependency from app/api/auth.py."""

    def test_admin_token_gets_through(self, db_session):
        """Test admin token passes through dependency."""
        admin = make_user(db_session, "admin@example.com", "Admin", "admin")
        token = get_token(client, "admin@example.com")
        
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed (200 or other success code)
        # get_current_admin_or_doctor_user is used in user listing endpoints
        assert response.status_code in [200, 404]  # 404 if no other users exist

    def test_clinician_token_gets_through(self, db_session):
        """Test clinician token passes through dependency."""
        clinician = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        token = get_token(client, "doctor@example.com")
        
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed
        assert response.status_code in [200, 404]

    def test_patient_token_returns_403(self, db_session):
        """Test patient token returns 403."""
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        token = get_token(client, "patient@example.com")
        
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


# =============================================================================
# refresh_token Endpoint Tests
# =============================================================================

class TestRefreshTokenEndpoint:
    """Test POST /api/v1/refresh endpoint from app/api/auth.py."""

    def test_valid_refresh_token_returns_new_access_token(self, db_session):
        """Test valid refresh token returns new access_token."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        
        # Login to get initial tokens
        response = client.post(
            "/api/v1/login",
            data={"username": "alice@example.com", "password": "TestPass123"}
        )
        assert response.status_code == 200
        data = response.json()
        refresh_token = data["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_response = client.post(
            "/api/v1/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"

    def test_invalid_refresh_token_returns_401(self, db_session):
        """Test invalid refresh token returns 401."""
        response = client.post(
            "/api/v1/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_access_token_used_as_refresh_returns_401(self, db_session):
        """Test using access token as refresh token returns 401."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        access_token = get_token(client, "bob@example.com")
        
        # Try to use access token as refresh token
        response = client.post(
            "/api/v1/refresh",
            json={"refresh_token": access_token}
        )
        
        assert response.status_code == 401


# =============================================================================
# request_password_reset Endpoint Tests
# =============================================================================

class TestRequestPasswordReset:
    """Test POST /api/v1/reset-password endpoint from app/api/auth.py."""

    def test_valid_email_returns_200(self, db_session):
        """Test valid email returns 200 (even if no-op)."""
        user = make_user(db_session, "charlie@example.com", "Charlie", "patient")
        
        response = client.post(
            "/api/v1/reset-password",
            json={"email": "charlie@example.com"}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()

    def test_nonexistent_email_returns_200_no_enumeration(self, db_session):
        """Test nonexistent email returns 200 (prevents email enumeration)."""
        response = client.post(
            "/api/v1/reset-password",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200
        assert "message" in response.json()

    def test_invalid_email_format_returns_422(self, db_session):
        """Test invalid email format returns 422."""
        response = client.post(
            "/api/v1/reset-password",
            json={"email": "not-an-email"}
        )
        
        # Pydantic validation should catch invalid email
        assert response.status_code == 422


# =============================================================================
# confirm_password_reset Endpoint Tests
# =============================================================================

class TestConfirmPasswordReset:
    """Test POST /api/v1/reset-password/confirm endpoint from app/api/auth.py."""

    def test_invalid_token_returns_400(self, db_session):
        """Test invalid/expired token returns 400."""
        response = client.post(
            "/api/v1/reset-password/confirm",
            json={
                "token": "invalid.token.string",
                "new_password": "NewSecurePass123"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    def test_valid_token_updates_credential(self, db_session):
        """Test valid token + matching passwords updates credential."""
        from app.services.auth_service import AuthService
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        
        # Create a password reset token
        auth_service = AuthService()
        reset_token = auth_service.create_access_token(
            data={"user_id": user.user_id, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Confirm password reset with token
        response = client.post(
            "/api/v1/reset-password/confirm",
            json={
                "token": reset_token,
                "new_password": "NewSecurePass123"
            }
        )
        
        assert response.status_code == 200
        assert "successful" in response.json()["message"].lower()
        
        # Verify new password works
        db_session.refresh(user)
        assert auth_service.verify_password("NewSecurePass123", user.auth_credential.hashed_password)

    def test_expired_token_returns_400(self, db_session):
        """Test expired token returns 400."""
        from app.services.auth_service import AuthService
        user = make_user(db_session, "eve@example.com", "Eve", "patient")
        
        # Create an expired token (expired 1 hour ago)
        auth_service = AuthService()
        reset_token = auth_service.create_access_token(
            data={"user_id": user.user_id, "type": "password_reset"},
            expires_delta=timedelta(hours=-1)
        )
        
        response = client.post(
            "/api/v1/reset-password/confirm",
            json={
                "token": reset_token,
                "new_password": "NewSecurePass123"
            }
        )
        
        assert response.status_code == 400

    def test_wrong_token_type_returns_400(self, db_session):
        """Test using access token (wrong type) returns 400."""
        user = make_user(db_session, "frank@example.com", "Frank", "patient")
        
        # Use regular access token instead of password_reset token
        access_token = get_token(client, "frank@example.com")
        
        response = client.post(
            "/api/v1/reset-password/confirm",
            json={
                "token": access_token,
                "new_password": "NewSecurePass123"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid token type" in response.json()["detail"]
