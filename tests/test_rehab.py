"""
Tests for rehab program endpoints.

Covers program creation, details/progress retrieval, progression updates,
session logging, and patient/clinician access patterns.
"""

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.models.rehab import RehabSessionLog
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


def _enable_phase_2_rehab(user, db_session) -> None:
    """Enable phase 2 rehab settings for a user."""
    user.rehab_phase = "phase_2"
    user.max_safe_hr = 180
    db_session.commit()


class TestRehabApi:
    """Rehab endpoint coverage for patient workflows."""

    def test_create_rehab_program_via_current_program_endpoint(self, db_session):
        """GET current program auto-creates a rehab program when phase is active."""
        patient = make_user(db_session, "rehab_create@example.com", "Rehab Create", "patient")
        _enable_phase_2_rehab(patient, db_session)
        token = get_token(client, "rehab_create@example.com")

        response = client.get(
            "/api/v1/rehab/current-program",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == patient.user_id
        assert payload["program_type"] == "phase_2_light"
        assert payload["status"] == "active"
        assert payload["current_session_plan"]["week_number"] == 1

    def test_get_rehab_program_details_and_progress(self, db_session):
        """GET current program returns nested plan and progress details."""
        patient = make_user(db_session, "rehab_details@example.com", "Rehab Details", "patient")
        _enable_phase_2_rehab(patient, db_session)
        token = get_token(client, "rehab_details@example.com")

        response = client.get(
            "/api/v1/rehab/current-program",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert "current_session_plan" in payload
        assert "progress_summary" in payload
        assert payload["progress_summary"]["sessions_required_this_week"] == 3

    def test_update_rehab_progression_via_complete_session(self, db_session):
        """POST complete-session updates progression counters."""
        patient = make_user(db_session, "rehab_update@example.com", "Rehab Update", "patient")
        _enable_phase_2_rehab(patient, db_session)
        token = get_token(client, "rehab_update@example.com")

        response = client.post(
            "/api/v1/rehab/complete-session",
            json={
                "actual_duration_minutes": 12,
                "avg_heart_rate": 92,
                "peak_heart_rate": 100,
                "activity_type": "walking",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["sessions_completed_this_week"] == 1
        assert payload["overall_sessions_completed"] == 1

    def test_list_rehab_sessions_via_session_logs(self, db_session):
        """Completed sessions are persisted in rehab session logs."""
        patient = make_user(db_session, "rehab_sessions@example.com", "Rehab Sessions", "patient")
        _enable_phase_2_rehab(patient, db_session)
        token = get_token(client, "rehab_sessions@example.com")

        for _ in range(2):
            response = client.post(
                "/api/v1/rehab/complete-session",
                json={
                    "actual_duration_minutes": 10,
                    "avg_heart_rate": 90,
                    "peak_heart_rate": 98,
                    "activity_type": "walking",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

        logs = db_session.query(RehabSessionLog).filter(
            RehabSessionLog.user_id == patient.user_id
        ).all()
        assert len(logs) == 2

    def test_phase_transition_logic_advances_week(self, db_session):
        """Three safe week-1 sessions advance phase 2 program to week 2."""
        patient = make_user(db_session, "rehab_transition@example.com", "Rehab Transition", "patient")
        _enable_phase_2_rehab(patient, db_session)
        token = get_token(client, "rehab_transition@example.com")

        for _ in range(3):
            response = client.post(
                "/api/v1/rehab/complete-session",
                json={
                    "actual_duration_minutes": 11,
                    "avg_heart_rate": 91,
                    "peak_heart_rate": 100,
                    "activity_type": "walking",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

        payload = response.json()
        assert payload["current_week"] == 2
        assert payload["sessions_completed_this_week"] == 0

    def test_clinician_vs_patient_access_patterns(self, db_session):
        """Patient with rehab phase has access; clinician without phase gets no program."""
        patient = make_user(db_session, "rehab_patient@example.com", "Rehab Patient", "patient")
        _enable_phase_2_rehab(patient, db_session)
        patient_token = get_token(client, "rehab_patient@example.com")

        clinician = make_user(db_session, "rehab_clinician@example.com", "Rehab Clinician", "clinician")
        clinician_token = get_token(client, "rehab_clinician@example.com")

        patient_response = client.get(
            "/api/v1/rehab/current-program",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert patient_response.status_code == 200

        clinician_response = client.get(
            "/api/v1/rehab/current-program",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert clinician_response.status_code == 404
