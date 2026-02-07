"""
Tests for user management endpoints.

Covers:
- Profile retrieval
- Profile update with field whitelist (security fix)
- Admin user management
- Access control (RBAC)
"""

import pytest


class TestUserProfile:
    """Tests for GET/PUT /api/v1/users/me."""

    def test_get_profile(self, client, patient_token):
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "patient@test.com"
        assert data["name"] == "Test Patient"

    def test_update_profile_allowed_fields(self, client, patient_token):
        resp = client.put(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"name": "Updated Name", "age": 36},
        )
        assert resp.status_code == 200

    def test_update_profile_rejects_role_change(self, client, patient_token, db_session):
        """Security: users must NOT be able to escalate their role via profile update."""
        resp = client.put(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"name": "Hacker", "role": "admin"},
        )
        # Request may succeed (role field ignored) or be rejected
        assert resp.status_code in (200, 422)

        # Verify role is still patient (not escalated)
        from app.models.user import User
        user = db_session.query(User).filter(User.email == "patient@test.com").first()
        assert user.role.value == "patient"


class TestAdminUserManagement:
    """Tests for admin-only user endpoints."""

    def test_list_users_as_admin(self, client, admin_token, test_user):
        resp = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_users_as_patient_denied(self, client, patient_token):
        resp = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert resp.status_code == 403

    def test_create_user_as_admin(self, client, admin_token):
        resp = client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newdoc@test.com",
                "name": "New Doc",
                "password": "DocPass123",
                "role": "clinician",
            },
        )
        assert resp.status_code == 200

    def test_deactivate_user(self, client, admin_token, test_user):
        resp = client.delete(
            f"/api/v1/users/{test_user.user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
