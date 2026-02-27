"""
Tests for activity session endpoints.

Covers all 5 functions in app/api/activity.py:
- start_activity_session (POST /api/v1/activities/start)
- end_activity_session (POST /api/v1/activities/end/{session_id})
- get_my_activities (GET /api/v1/activities)
- get_user_activities (GET /api/v1/activities/user/{user_id})
- get_activity_session (GET /api/v1/activities/{session_id})

Run with:
    pytest tests/test_activity.py -v
"""

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token, make_activity


client = TestClient(fastapi_app)


class TestStartActivitySession:
    """Test POST /api/v1/activities/start."""

    def test_start_activity_valid_payload(self, db_session):
        """Test starting activity with valid payload creates active session."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")

        activity_data = {
            "start_time": "2026-02-21T10:00:00Z",
            "activity_type": "walking",
            "avg_heart_rate": 80,
            "peak_heart_rate": 110,
            "min_heart_rate": 65
        }
        response = client.post(
            "/api/v1/activities/start",
            json=activity_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activity_type"] == "walking"
        assert data["status"] == "active"
        assert "session_id" in data

    def test_start_activity_minimal_payload(self, db_session):
        """Test starting activity with minimal payload (just activity_type) works."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")

        activity_data = {
            "start_time": "2026-02-21T10:00:00Z",
            "activity_type": "running"
        }
        response = client.post(
            "/api/v1/activities/start",
            json=activity_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activity_type"] == "running"
        assert data["status"] == "active"

    def test_start_activity_no_auth(self, db_session):
        """Test starting activity without auth returns 401."""
        activity_data = {
            "activity_type": "walking"
        }
        response = client.post(
            "/api/v1/activities/start",
            json=activity_data
        )

        assert response.status_code == 401


class TestEndActivitySession:
    """Test POST /api/v1/activities/end/{session_id}."""

    def test_end_activity_sets_status_completed(self, db_session):
        """Test ending activity sets status to completed."""
        user = make_user(db_session, "charlie@example.com", "Charlie", "patient")
        activity = make_activity(db_session, user.user_id, completed=False)
        token = get_token(client, "charlie@example.com")

        update_data = {
            "avg_heart_rate": 85,
            "peak_heart_rate": 120
        }
        response = client.post(
            f"/api/v1/activities/end/{activity.session_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["avg_heart_rate"] == 85

    def test_end_activity_calculates_duration(self, db_session):
        """Test ending activity calculates duration if not provided."""
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        activity = make_activity(db_session, user.user_id, completed=False, duration=0)
        token = get_token(client, "dave@example.com")

        update_data = {}
        response = client.post(
            f"/api/v1/activities/end/{activity.session_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        # Duration should be calculated
        assert data["duration_minutes"] is not None

    def test_end_activity_not_found(self, db_session):
        """Test ending non-existent session returns 404."""
        user = make_user(db_session, "eve@example.com", "Eve", "patient")
        token = get_token(client, "eve@example.com")

        update_data = {}
        response = client.post(
            "/api/v1/activities/end/99999",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_end_activity_cannot_end_other_users_session(self, db_session):
        """Test patient cannot end another user's session (404)."""
        user1 = make_user(db_session, "frank@example.com", "Frank", "patient")
        user2 = make_user(db_session, "grace@example.com", "Grace", "patient")
        
        # User2 creates a session
        activity = make_activity(db_session, user2.user_id, completed=False)
        
        # User1 tries to end it
        user1_token = get_token(client, "frank@example.com")
        update_data = {}
        response = client.post(
            f"/api/v1/activities/end/{activity.session_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        # Should return 404 (not found) because query filters by user_id
        assert response.status_code == 404


class TestGetMyActivities:
    """Test GET /api/v1/activities (patient's own sessions)."""

    def test_get_my_activities_empty(self, db_session):
        """Test get my activities returns empty list when none exist."""
        user = make_user(db_session, "alice_activities@example.com", "Alice A", "patient")
        token = get_token(client, "alice_activities@example.com")

        response = client.get(
            "/api/v1/activities",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_my_activities_returns_correct_count(self, db_session):
        """Test get my activities returns correct count after creating sessions."""
        user = make_user(db_session, "bob_activities@example.com", "Bob A", "patient")
        
        # Create 3 activities
        make_activity(db_session, user.user_id, activity_type="walking")
        make_activity(db_session, user.user_id, activity_type="running")
        make_activity(db_session, user.user_id, activity_type="cycling")
        
        token = get_token(client, "bob_activities@example.com")

        response = client.get(
            "/api/v1/activities",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_my_activities_filter_by_activity_type(self, db_session):
        """Test activity_type filter works."""
        user = make_user(db_session, "charlie_activities@example.com", "Charlie A", "patient")
        
        # Create mixed activities
        make_activity(db_session, user.user_id, activity_type="walking")
        make_activity(db_session, user.user_id, activity_type="walking")
        make_activity(db_session, user.user_id, activity_type="running")
        
        token = get_token(client, "charlie_activities@example.com")

        response = client.get(
            "/api/v1/activities?activity_type=walking",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["activity_type"] == "walking" for item in data)

    def test_get_my_activities_pagination(self, db_session):
        """Test limit/offset pagination works."""
        user = make_user(db_session, "dave_activities@example.com", "Dave A", "patient")
        
        # Create 10 activities
        for i in range(10):
            make_activity(db_session, user.user_id, activity_type="walking")
        
        token = get_token(client, "dave_activities@example.com")

        # Get first 5
        response = client.get(
            "/api/v1/activities?limit=5&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Get next 5
        response = client.get(
            "/api/v1/activities?limit=5&offset=5",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestGetUserActivities:
    """Test GET /api/v1/activities/user/{user_id} (clinician access)."""

    def test_get_user_activities_doctor_access(self, db_session):
        """Test doctor can access patient activities."""
        patient = make_user(db_session, "patient1@example.com", "Patient 1", "patient")
        doctor = make_user(db_session, "doctor1@example.com", "Doctor 1", "clinician")
        
        # Create patient activities
        make_activity(db_session, patient.user_id, activity_type="walking")
        make_activity(db_session, patient.user_id, activity_type="running")
        
        doctor_token = get_token(client, "doctor1@example.com")

        response = client.get(
            f"/api/v1/activities/user/{patient.user_id}",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_user_activities_patient_forbidden(self, db_session):
        """Test patient token returns 403 when accessing other patient."""
        patient1 = make_user(db_session, "patient_a@example.com", "Patient A", "patient")
        patient2 = make_user(db_session, "patient_b@example.com", "Patient B", "patient")
        
        make_activity(db_session, patient2.user_id, activity_type="walking")
        
        patient1_token = get_token(client, "patient_a@example.com")

        response = client.get(
            f"/api/v1/activities/user/{patient2.user_id}",
            headers={"Authorization": f"Bearer {patient1_token}"}
        )

        assert response.status_code == 403

    def test_get_user_activities_user_not_found(self, db_session):
        """Test accessing activities for non-existent user returns 404."""
        doctor = make_user(db_session, "doctor2@example.com", "Doctor 2", "clinician")
        doctor_token = get_token(client, "doctor2@example.com")

        response = client.get(
            "/api/v1/activities/user/99999",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetActivitySession:
    """Test GET /api/v1/activities/{session_id}."""

    def test_get_activity_session_owner_access(self, db_session):
        """Test owner can access own session."""
        user = make_user(db_session, "eve_session@example.com", "Eve S", "patient")
        activity = make_activity(db_session, user.user_id, activity_type="walking")
        token = get_token(client, "eve_session@example.com")

        response = client.get(
            f"/api/v1/activities/{activity.session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == activity.session_id

    def test_get_activity_session_clinician_access(self, db_session):
        """Test clinician can access any session."""
        patient = make_user(db_session, "patient2@example.com", "Patient 2", "patient")
        doctor = make_user(db_session, "doctor3@example.com", "Doctor 3", "clinician")
        
        activity = make_activity(db_session, patient.user_id, activity_type="walking")
        
        doctor_token = get_token(client, "doctor3@example.com")

        response = client.get(
            f"/api/v1/activities/{activity.session_id}",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == activity.session_id

    def test_get_activity_session_patient_forbidden(self, db_session):
        """Test patient cannot access another patient's session (403)."""
        patient1 = make_user(db_session, "patient_c@example.com", "Patient C", "patient")
        patient2 = make_user(db_session, "patient_d@example.com", "Patient D", "patient")
        
        activity = make_activity(db_session, patient2.user_id, activity_type="walking")
        
        patient1_token = get_token(client, "patient_c@example.com")

        response = client.get(
            f"/api/v1/activities/{activity.session_id}",
            headers={"Authorization": f"Bearer {patient1_token}"}
        )

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()

    def test_get_activity_session_not_found(self, db_session):
        """Test accessing non-existent session returns 404."""
        user = make_user(db_session, "frank_session@example.com", "Frank S", "patient")
        token = get_token(client, "frank_session@example.com")

        response = client.get(
            "/api/v1/activities/99999",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Additional Activity Branch Coverage
# =============================================================================

class TestActivityBranchCoverage:
    """Additional branch coverage for activity endpoints."""

    def test_end_activity_session_already_completed(self, db_session):
        """Test ending already-completed session handles gracefully."""
        user = make_user(db_session, "completed_activity@example.com", "Completed", "patient")
        activity = make_activity(db_session, user.user_id, "walking", True, 30)
        token = get_token(client, "completed_activity@example.com")
        
        # Try to end already-completed session
        end_data = {
            "end_time": "2026-02-21T11:00:00Z",
            "final_heart_rate": 75,
            "final_spo2": 98,
            "total_calories_burned": 250
        }
        
        response = client.post(
            f"/api/v1/activities/end/{activity.session_id}",
            json=end_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should either return 200 (idempotent) or 400 (cannot re-end)
        assert response.status_code in [200, 400, 409]
