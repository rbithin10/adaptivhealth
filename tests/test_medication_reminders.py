"""
Tests for medication reminder endpoints.

Covers reminder CRUD operations and authentication checks.
"""

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.models.medical_history import PatientMedication, MedicationStatus
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


def _create_medication(db_session, user_id: int) -> PatientMedication:
    """Create an active medication record for reminder tests."""
    medication = PatientMedication(
        user_id=user_id,
        drug_class="beta_blocker",
        drug_name="Metoprolol",
        dose="25mg",
        frequency="daily",
        status=MedicationStatus.ACTIVE.value,
        reminder_enabled=False,
        reminder_time=None,
    )
    db_session.add(medication)
    db_session.commit()
    db_session.refresh(medication)
    return medication


class TestMedicationReminderApi:
    """Medication reminder endpoint test coverage."""

    def test_create_medication_reminder_success(self, db_session):
        """POST creates/enables reminder for an owned medication."""
        user = make_user(db_session, "medrem_create@example.com", "Med Create", "patient")
        token = get_token(client, "medrem_create@example.com")
        medication = _create_medication(db_session, user.user_id)

        response = client.post(
            "/api/v1/medications/reminders",
            json={
                "medication_id": medication.medication_id,
                "reminder_time": "08:30",
                "reminder_enabled": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["medication_id"] == medication.medication_id
        assert payload["reminder_time"] == "08:30"
        assert payload["reminder_enabled"] is True

    def test_list_medication_reminders_success(self, db_session):
        """GET returns active medications with reminder fields."""
        user = make_user(db_session, "medrem_list@example.com", "Med List", "patient")
        token = get_token(client, "medrem_list@example.com")
        medication = _create_medication(db_session, user.user_id)
        medication.reminder_enabled = True
        medication.reminder_time = "09:00"
        db_session.commit()

        response = client.get(
            "/api/v1/medications/reminders",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["medication_id"] == medication.medication_id
        assert data[0]["reminder_enabled"] is True

    def test_update_medication_reminder_success(self, db_session):
        """PUT updates reminder time/enabled status for owned medication."""
        user = make_user(db_session, "medrem_update@example.com", "Med Update", "patient")
        token = get_token(client, "medrem_update@example.com")
        medication = _create_medication(db_session, user.user_id)

        response = client.put(
            f"/api/v1/medications/{medication.medication_id}/reminder",
            json={"reminder_time": "20:15", "reminder_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["reminder_time"] == "20:15"
        assert payload["reminder_enabled"] is True

    def test_delete_medication_reminder_success(self, db_session):
        """DELETE disables and clears reminder settings."""
        user = make_user(db_session, "medrem_delete@example.com", "Med Delete", "patient")
        token = get_token(client, "medrem_delete@example.com")
        medication = _create_medication(db_session, user.user_id)
        medication.reminder_enabled = True
        medication.reminder_time = "07:00"
        db_session.commit()

        response = client.delete(
            f"/api/v1/medications/{medication.medication_id}/reminder",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204
        db_session.refresh(medication)
        assert medication.reminder_enabled is False
        assert medication.reminder_time is None

    def test_reminder_unauthorized_access(self, db_session):
        """No token returns 401 for protected reminder endpoints."""
        user = make_user(db_session, "medrem_unauth@example.com", "Med Unauth", "patient")
        medication = _create_medication(db_session, user.user_id)

        response = client.get("/api/v1/medications/reminders")
        assert response.status_code == 401

        response = client.post(
            "/api/v1/medications/reminders",
            json={
                "medication_id": medication.medication_id,
                "reminder_time": "10:00",
                "reminder_enabled": True,
            },
        )
        assert response.status_code == 401
