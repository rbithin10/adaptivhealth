"""
Tests for NL chat endpoints.

Adds focused coverage for:
- POST /api/v1/nl/chat
- POST /api/v1/nl/chat-with-image
"""

from io import BytesIO
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


def test_chat_endpoint_success(db_session, monkeypatch):
    """Authenticated users receive hybrid chat response payload."""
    user = make_user(db_session, "chatuser@example.com", "Chat User", "patient")
    token = get_token(client, user.email)

    mocked_response = {"response": "Keep your HR in the target zone.", "source": "template"}
    monkeypatch.setattr("app.services.chat_service.generate_chat_response", AsyncMock(return_value=mocked_response))

    response = client.post(
        "/api/v1/nl/chat",
        json={"message": "What should I do today?", "conversation_history": []},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Keep your HR in the target zone."
    assert payload["source"] == "template"


def test_chat_with_image_missing_key_returns_503(db_session, monkeypatch):
    """Image chat endpoint returns 503 when Gemini key is not configured."""
    user = make_user(db_session, "chatimg@example.com", "Chat Img", "patient")
    token = get_token(client, user.email)

    monkeypatch.setattr("app.api.nl_endpoints.settings.gemini_api_key", None)

    response = client.post(
        "/api/v1/nl/chat-with-image",
        files={"image": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"message": "Is this meal healthy?", "analysis_type": "food"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "Gemini API key not configured" in response.json()["detail"]
