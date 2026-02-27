"""
Test messaging system endpoints.

Tests patient-clinician messaging via REST polling.

Run with:
    pytest tests/test_messaging.py -v
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app as fastapi_app
from app.database import Base
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.services.auth_service import AuthService
import app.models as app_models

client = TestClient(fastapi_app)


def create_admin_user(db_session) -> None:
    existing = db_session.query(User).filter(User.email == "admin@test.com").first()
    if existing:
        return
    admin = User(
        email="admin@test.com",
        full_name="Admin User",
        age=40,
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    auth_cred = AuthCredential(
        user=admin,
        hashed_password=AuthService.hash_password("Admin1234")
    )
    db_session.add(auth_cred)
    db_session.commit()


@pytest.fixture
def admin_token(db_session):
    create_admin_user(db_session)
    login_response = client.post(
        "/api/v1/login",
        data={"username": "admin@test.com", "password": "Admin1234"}
    )
    assert login_response.status_code == 200, f"Admin login failed: {login_response.json()}"
    return login_response.json()["access_token"]


@pytest.fixture
def patient_token(admin_token):
    """Register and login a patient user."""
    # Register patient
    patient_data = {
        "email": "patient@example.com",
        "password": "TestPass123",
        "name": "Test Patient",
        "age": 35,
        "role": "patient"
    }
    client.post(
        "/api/v1/register",
        json=patient_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Login
    login_response = client.post(
        "/api/v1/login",
        data={"username": "patient@example.com", "password": "TestPass123"}
    )
    return login_response.json()["access_token"]


@pytest.fixture
def clinician_token(admin_token):
    """Register and login a clinician user."""
    # Register clinician
    clinician_data = {
        "email": "clinician@example.com",
        "password": "TestPass123",
        "name": "Dr. Smith",
        "age": 45,
        "role": "clinician"
    }
    client.post(
        "/api/v1/register",
        json=clinician_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Login
    login_response = client.post(
        "/api/v1/login",
        data={"username": "clinician@example.com", "password": "TestPass123"}
    )
    return login_response.json()["access_token"]


class TestMessaging:
    """Test messaging system endpoints."""

    def test_send_message_success(self, patient_token, clinician_token):
        """Test patient can send message to clinician."""
        # Get clinician user ID
        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        # Patient sends message
        message_data = {
            "receiver_id": clinician_id,
            "content": "Hello doctor, I have a question about my medication."
        }
        response = client.post(
            "/api/v1/messages",
            json=message_data,
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["receiver_id"] == clinician_id
        assert data["content"] == message_data["content"]
        assert data["is_read"] is False
        assert "message_id" in data
        assert "sent_at" in data

    def test_send_message_to_nonexistent_user(self, patient_token):
        """Test sending message to non-existent user fails."""
        message_data = {
            "receiver_id": 99999,
            "content": "Test message"
        }
        response = client.post(
            "/api/v1/messages",
            json=message_data,
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_send_message_empty_content(self, patient_token, clinician_token):
        """Test sending message with empty content fails validation."""
        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        message_data = {
            "receiver_id": clinician_id,
            "content": "   "  # Whitespace only
        }
        response = client.post(
            "/api/v1/messages",
            json=message_data,
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert response.status_code == 422  # Validation error

    def test_get_thread_bidirectional(self, patient_token, clinician_token):
        """Test thread retrieval shows messages in both directions."""
        # Get user IDs
        patient_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        patient_id = patient_response.json()["id"]

        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        # Patient sends first message
        client.post(
            "/api/v1/messages",
            json={
                "receiver_id": clinician_id,
                "content": "Patient message 1"
            },
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        # Clinician replies
        client.post(
            "/api/v1/messages",
            json={
                "receiver_id": patient_id,
                "content": "Clinician reply"
            },
            headers={"Authorization": f"Bearer {clinician_token}"}
        )

        # Patient sends second message
        client.post(
            "/api/v1/messages",
            json={
                "receiver_id": clinician_id,
                "content": "Patient message 2"
            },
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        # Patient retrieves thread
        thread_response = client.get(
            f"/api/v1/messages/thread/{clinician_id}",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert thread_response.status_code == 200
        messages = thread_response.json()
        assert len(messages) == 3
        assert messages[0]["content"] == "Patient message 1"
        assert messages[1]["content"] == "Clinician reply"
        assert messages[2]["content"] == "Patient message 2"

    def test_get_thread_ordered_by_time(self, patient_token, clinician_token):
        """Test thread messages are ordered by sent_at ascending."""
        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        # Send multiple messages
        for i in range(5):
            client.post(
                "/api/v1/messages",
                json={
                    "receiver_id": clinician_id,
                    "content": f"Message {i + 1}"
                },
                headers={"Authorization": f"Bearer {patient_token}"}
            )

        # Retrieve thread
        thread_response = client.get(
            f"/api/v1/messages/thread/{clinician_id}",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        messages = thread_response.json()
        sent_at_times = [datetime.fromisoformat(m["sent_at"].replace("Z", "+00:00")) for m in messages]
        
        # Verify ascending order
        for i in range(len(sent_at_times) - 1):
            assert sent_at_times[i] <= sent_at_times[i + 1]

    def test_mark_message_read(self, patient_token, clinician_token):
        """Test marking message as read (receiver only)."""
        # Get user IDs
        patient_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        patient_id = patient_response.json()["id"]

        # Clinician sends message to patient
        send_response = client.post(
            "/api/v1/messages",
            json={
                "receiver_id": patient_id,
                "content": "Test message"
            },
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        message_id = send_response.json()["message_id"]

        # Patient marks message as read
        read_response = client.post(
            f"/api/v1/messages/{message_id}/read",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert read_response.status_code == 200
        assert read_response.json()["is_read"] is True

    def test_mark_message_read_not_authorized(self, patient_token, clinician_token):
        """Test sender cannot mark their own message as read."""
        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        # Patient sends message
        send_response = client.post(
            "/api/v1/messages",
            json={
                "receiver_id": clinician_id,
                "content": "Test message"
            },
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        message_id = send_response.json()["message_id"]

        # Patient tries to mark own message as read (should fail)
        read_response = client.post(
            f"/api/v1/messages/{message_id}/read",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert read_response.status_code == 404  # Not found (authorization check)

    def test_get_thread_limit(self, patient_token, clinician_token):
        """Test thread limit parameter works."""
        clinician_response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {clinician_token}"}
        )
        clinician_id = clinician_response.json()["id"]

        # Send 10 messages
        for i in range(10):
            client.post(
                "/api/v1/messages",
                json={
                    "receiver_id": clinician_id,
                    "content": f"Message {i + 1}"
                },
                headers={"Authorization": f"Bearer {patient_token}"}
            )

        # Retrieve with limit=5
        thread_response = client.get(
            f"/api/v1/messages/thread/{clinician_id}?limit=5",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        messages = thread_response.json()
        assert len(messages) == 5

    def test_unauthorized_access(self):
        """Test messaging endpoints require authentication."""
        # Try to get thread without token
        response = client.get("/api/v1/messages/thread/1")
        assert response.status_code == 401

        # Try to send message without token
        response = client.post(
            "/api/v1/messages",
            json={"receiver_id": 1, "content": "Test"}
        )
        assert response.status_code == 401

        # Try to mark message read without token
        response = client.post("/api/v1/messages/1/read")
        assert response.status_code == 401
