"""Medical history API tests.

Provides focused baseline coverage for patient self-service routes.
"""

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


def test_get_my_medical_history_empty_list(db_session):
    """New patient gets an empty list for /me/medical-history."""
    user = make_user(db_session, "medhist_empty@example.com", "Med Empty", "patient")
    token = get_token(client, user.email)

    response = client.get(
        "/api/v1/me/medical-history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 0


def test_get_my_medications_empty_list(db_session):
    """New patient gets an empty list for /me/medications."""
    user = make_user(db_session, "meds_empty@example.com", "Meds Empty", "patient")
    token = get_token(client, user.email)

    response = client.get(
        "/api/v1/me/medications",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 0


def test_get_my_medical_profile_success(db_session):
    """Patient can retrieve own computed medical profile payload."""
    user = make_user(db_session, "medprofile@example.com", "Med Profile", "patient")
    token = get_token(client, user.email)

    response = client.get(
        "/api/v1/me/medical-profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.user_id
    assert "conditions" in payload
    assert "medications" in payload
    assert isinstance(payload["conditions"], list)
    assert isinstance(payload["medications"], list)
