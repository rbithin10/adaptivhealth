"""
Tests for message endpoints.

Verifies patient-clinician messaging via REST polling.
"""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-thats-long-enough-32chars")
os.environ.setdefault("PHI_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE=")
os.environ.setdefault("DEBUG", "true")

from app.main import app as fastapi_app
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.services.auth_service import AuthService
import app.models as app_models


@pytest.fixture
def client():
    return TestClient(fastapi_app)


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
def admin_token(client, db_session):
    create_admin_user(db_session)
    resp = client.post(
        "/api/v1/login",
        data={"username": "admin@test.com", "password": "Admin1234"}
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return resp.json()["access_token"]


def register_user(client, email, password, name, admin_token, role=None):
    payload = {"email": email, "password": password, "name": name}
    if role:
        payload["role"] = role
    resp = client.post(
        "/api/v1/register",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return resp.json()


def login_user(client, email, password):
    resp = client.post("/api/v1/login", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestMessages:
    """Tests for message endpoints."""

    def test_send_and_fetch_thread(self, client, admin_token):
        patient = register_user(client, "patient@example.com", "StrongPass1", "Patient", admin_token)
        clinician = register_user(
            client,
            "clinician@example.com",
            "StrongPass1",
            "Clinician",
            admin_token,
            role=UserRole.CLINICIAN.value
        )

        patient_token = login_user(client, "patient@example.com", "StrongPass1")
        clinician_token = login_user(client, "clinician@example.com", "StrongPass1")

        send_resp = client.post(
            "/api/v1/messages",
            json={"receiver_id": clinician["id"], "content": "Hello doctor"},
            headers=auth_header(patient_token)
        )
        assert send_resp.status_code == 201
        message_data = send_resp.json()
        assert message_data["sender_id"] == patient["id"]
        assert message_data["receiver_id"] == clinician["id"]
        assert message_data["content"] == "Hello doctor"
        assert message_data["is_read"] is False

        send_resp_2 = client.post(
            "/api/v1/messages",
            json={"receiver_id": patient["id"], "content": "Hello patient"},
            headers=auth_header(clinician_token)
        )
        assert send_resp_2.status_code == 201

        thread_resp = client.get(
            f"/api/v1/messages/thread/{clinician['id']}",
            headers=auth_header(patient_token)
        )
        assert thread_resp.status_code == 200
        thread = thread_resp.json()
        assert len(thread) == 2
        assert thread[0]["content"] == "Hello doctor"
        assert thread[1]["content"] == "Hello patient"

    def test_thread_limit(self, client, admin_token):
        user_a = register_user(client, "usera@example.com", "StrongPass1", "User A", admin_token)
        user_b = register_user(client, "userb@example.com", "StrongPass1", "User B", admin_token)
        token_a = login_user(client, "usera@example.com", "StrongPass1")

        for i in range(3):
            client.post(
                "/api/v1/messages",
                json={"receiver_id": user_b["id"], "content": f"Message {i}"},
                headers=auth_header(token_a)
            )

        thread_resp = client.get(
            f"/api/v1/messages/thread/{user_b['id']}?limit=2",
            headers=auth_header(token_a)
        )
        assert thread_resp.status_code == 200
        assert len(thread_resp.json()) == 2

    def test_mark_read(self, client, admin_token):
        patient = register_user(client, "p2@example.com", "StrongPass1", "Patient2", admin_token)
        clinician = register_user(
            client,
            "c2@example.com",
            "StrongPass1",
            "Clinician2",
            admin_token,
            role=UserRole.CLINICIAN.value
        )

        patient_token = login_user(client, "p2@example.com", "StrongPass1")
        clinician_token = login_user(client, "c2@example.com", "StrongPass1")

        send_resp = client.post(
            "/api/v1/messages",
            json={"receiver_id": clinician["id"], "content": "Message to read"},
            headers=auth_header(patient_token)
        )
        message_id = send_resp.json()["message_id"]

        read_resp = client.post(
            f"/api/v1/messages/{message_id}/read",
            headers=auth_header(clinician_token)
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["is_read"] is True

    def test_mark_read_forbidden(self, client, admin_token):
        patient = register_user(client, "p3@example.com", "StrongPass1", "Patient3", admin_token)
        clinician = register_user(
            client,
            "c3@example.com",
            "StrongPass1",
            "Clinician3",
            admin_token,
            role=UserRole.CLINICIAN.value
        )
        other_user = register_user(client, "o3@example.com", "StrongPass1", "Other", admin_token)

        patient_token = login_user(client, "p3@example.com", "StrongPass1")
        other_token = login_user(client, "o3@example.com", "StrongPass1")

        send_resp = client.post(
            "/api/v1/messages",
            json={"receiver_id": clinician["id"], "content": "Hello"},
            headers=auth_header(patient_token)
        )
        message_id = send_resp.json()["message_id"]

        read_resp = client.post(
            f"/api/v1/messages/{message_id}/read",
            headers=auth_header(other_token)
        )
        assert read_resp.status_code == 404

    def test_thread_requires_auth(self, client, admin_token):
        user_a = register_user(client, "una@example.com", "StrongPass1", "User A", admin_token)
        resp = client.get(f"/api/v1/messages/thread/{user_a['id']}")
        assert resp.status_code == 401

    def test_send_requires_auth(self, client, admin_token):
        user_b = register_user(client, "unb@example.com", "StrongPass1", "User B", admin_token)
        resp = client.post(
            "/api/v1/messages",
            json={"receiver_id": user_b["id"], "content": "Hello"}
        )
        assert resp.status_code == 401

    def test_get_inbox_for_clinician_success(self, client, admin_token):
        """Clinician inbox returns conversation summaries with unread counts."""
        patient = register_user(client, "inbox_patient@example.com", "StrongPass1", "Inbox Patient", admin_token)
        clinician = register_user(
            client,
            "inbox_clinician@example.com",
            "StrongPass1",
            "Inbox Clinician",
            admin_token,
            role=UserRole.CLINICIAN.value,
        )

        patient_token = login_user(client, "inbox_patient@example.com", "StrongPass1")
        clinician_token = login_user(client, "inbox_clinician@example.com", "StrongPass1")

        send_resp = client.post(
            "/api/v1/messages",
            json={"receiver_id": clinician["id"], "content": "I need advice on my workout."},
            headers=auth_header(patient_token),
        )
        assert send_resp.status_code == 201

        inbox_resp = client.get(
            "/api/v1/messages/inbox",
            headers=auth_header(clinician_token),
        )
        assert inbox_resp.status_code == 200
        inbox = inbox_resp.json()
        assert len(inbox) >= 1
        assert any(item["patient_id"] == patient["id"] for item in inbox)

    def test_get_inbox_patient_forbidden(self, client, admin_token):
        """Patients cannot access clinician inbox endpoint."""
        register_user(client, "inbox_patient2@example.com", "StrongPass1", "Inbox Patient 2", admin_token)
        patient_token = login_user(client, "inbox_patient2@example.com", "StrongPass1")

        inbox_resp = client.get(
            "/api/v1/messages/inbox",
            headers=auth_header(patient_token),
        )
        assert inbox_resp.status_code == 403

    def test_messaging_conversations_compat_endpoint(self, client, admin_token):
        """GET /messaging/conversations returns spec-compatible conversation summaries."""
        patient = register_user(client, "conv_patient@example.com", "StrongPass1", "Conversation Patient", admin_token)
        clinician = register_user(
            client,
            "conv_clinician@example.com",
            "StrongPass1",
            "Conversation Clinician",
            admin_token,
            role=UserRole.CLINICIAN.value,
        )

        patient_token = login_user(client, "conv_patient@example.com", "StrongPass1")
        clinician_token = login_user(client, "conv_clinician@example.com", "StrongPass1")

        first_send = client.post(
            "/api/v1/messages",
            json={"receiver_id": clinician["id"], "content": "First message"},
            headers=auth_header(patient_token),
        )
        assert first_send.status_code == 201

        response = client.get(
            "/api/v1/messaging/conversations",
            headers=auth_header(clinician_token),
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["user_id"] == clinician["id"]
        assert payload["total_conversations"] >= 1
        assert len(payload["conversations"]) >= 1
        assert payload["conversations"][0]["conversation_id"].startswith("conv_")

    def test_conversation_messages_send_and_mark_read_compat(self, client, admin_token):
        """Compat endpoints for thread history, send, and mark-read work together."""
        patient = register_user(client, "conv2_patient@example.com", "StrongPass1", "Conv2 Patient", admin_token)
        clinician = register_user(
            client,
            "conv2_clinician@example.com",
            "StrongPass1",
            "Conv2 Clinician",
            admin_token,
            role=UserRole.CLINICIAN.value,
        )

        patient_token = login_user(client, "conv2_patient@example.com", "StrongPass1")
        clinician_token = login_user(client, "conv2_clinician@example.com", "StrongPass1")

        send_resp = client.post(
            f"/api/v1/messaging/conversations/conv_{clinician['id']}/messages",
            json={"content": "Hello from patient", "type": "text"},
            headers=auth_header(patient_token),
        )
        assert send_resp.status_code == 201
        sent_payload = send_resp.json()
        assert sent_payload["conversation_id"] == f"conv_{clinician['id']}"
        assert sent_payload["status"] == "sent"

        history_resp = client.get(
            f"/api/v1/messaging/conversations/conv_{patient['id']}/messages?limit=50&offset=0",
            headers=auth_header(clinician_token),
        )
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert history["conversation_id"] == f"conv_{patient['id']}"
        assert len(history["messages"]) >= 1

        read_resp = client.put(
            f"/api/v1/messaging/conversations/conv_{patient['id']}/read",
            headers=auth_header(clinician_token),
        )
        assert read_resp.status_code == 200
        read_payload = read_resp.json()
        assert read_payload["conversation_id"] == f"conv_{patient['id']}"
        assert "messages_marked_read" in read_payload

    def test_conversation_messages_invalid_id_returns_400(self, client, admin_token):
        """Invalid conversation_id format is rejected for compatibility route."""
        user = register_user(client, "convbad@example.com", "StrongPass1", "Conv Bad", admin_token)
        user_token = login_user(client, "convbad@example.com", "StrongPass1")

        response = client.get(
            "/api/v1/messaging/conversations/not_a_number/messages",
            headers=auth_header(user_token),
        )
        assert response.status_code == 400
