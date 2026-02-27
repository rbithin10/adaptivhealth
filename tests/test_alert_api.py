"""
Tests for alert API endpoints.

Covers functions in app/api/alert.py not already in other test files:
- check_duplicate_alert (helper function)
- get_alert_statistics (GET /api/v1/alerts/stats)
- create_alert deduplication (POST /api/v1/alerts with duplicate check)

Run with:
    pytest tests/test_alert_api.py -v
"""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.models.alert import Alert
from app.api.alert import check_duplicate_alert
from tests.helpers import make_user, get_token, make_alert


client = TestClient(fastapi_app)


class TestCheckDuplicateAlert:
    """Test check_duplicate_alert helper function."""

    def test_check_duplicate_returns_true_when_recent_alert_exists(self, db_session):
        """Test returns True when same alert_type was created < 5 min ago."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        
        # Create a recent alert
        make_alert(db_session, user.user_id, alert_type="high_heart_rate")
        
        # Check for duplicate
        is_duplicate = check_duplicate_alert(
            db_session,
            user.user_id,
            "high_heart_rate",
            window_minutes=5
        )
        
        assert is_duplicate is True

    def test_check_duplicate_returns_false_when_no_recent_alert(self, db_session):
        """Test returns False when no recent alert exists."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        
        # No alerts created
        
        # Check for duplicate
        is_duplicate = check_duplicate_alert(
            db_session,
            user.user_id,
            "high_heart_rate",
            window_minutes=5
        )
        
        assert is_duplicate is False

    def test_check_duplicate_returns_false_for_different_alert_type(self, db_session):
        """Test returns False when recent alert is different type."""
        user = make_user(db_session, "charlie@example.com", "Charlie", "patient")
        
        # Create alert of different type
        make_alert(db_session, user.user_id, alert_type="low_spo2")
        
        # Check for different type
        is_duplicate = check_duplicate_alert(
            db_session,
            user.user_id,
            "high_heart_rate",
            window_minutes=5
        )
        
        assert is_duplicate is False

    def test_check_duplicate_ignores_old_alerts(self, db_session):
        """Test returns False when alert is older than window."""
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        
        # Create an old alert (manually set created_at)
        alert = Alert(
            user_id=user.user_id,
            alert_type="high_heart_rate",
            severity="critical",
            title="Old Alert",
            message="This is an old alert",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        db_session.add(alert)
        db_session.commit()
        
        # Check with 5-minute window (should not find the 10-minute-old alert)
        is_duplicate = check_duplicate_alert(
            db_session,
            user.user_id,
            "high_heart_rate",
            window_minutes=5
        )
        
        assert is_duplicate is False


class TestGetAlertStatistics:
    """Test GET /api/v1/alerts/stats endpoint."""

    def test_get_alert_stats_doctor_access(self, db_session):
        """Test doctor gets stats dict with severity_breakdown and unacknowledged_count."""
        doctor = make_user(db_session, "doctor1@example.com", "Doctor 1", "clinician")
        patient = make_user(db_session, "patient1@example.com", "Patient 1", "patient")
        
        # Create alerts with different severities
        make_alert(db_session, patient.user_id, alert_type="high_heart_rate", severity="critical", acknowledged=False)
        make_alert(db_session, patient.user_id, alert_type="low_spo2", severity="critical", acknowledged=True)
        make_alert(db_session, patient.user_id, alert_type="high_blood_pressure", severity="warning", acknowledged=False)
        
        doctor_token = get_token(client, "doctor1@example.com")

        response = client.get(
            "/api/v1/alerts/stats?days=7",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "severity_breakdown" in data
        assert "unacknowledged_count" in data
        assert "period_days" in data
        assert "generated_at" in data
        
        # Verify counts
        assert data["period_days"] == 7
        assert data["unacknowledged_count"] == 2  # 2 unacknowledged alerts
        
        # Verify severity breakdown
        severity_breakdown = data["severity_breakdown"]
        assert "critical" in severity_breakdown
        assert "warning" in severity_breakdown
        assert severity_breakdown["critical"] == 2
        assert severity_breakdown["warning"] == 1

    def test_get_alert_stats_patient_forbidden(self, db_session):
        """Test patient token returns 403."""
        patient = make_user(db_session, "patient2@example.com", "Patient 2", "patient")
        patient_token = get_token(client, "patient2@example.com")

        response = client.get(
            "/api/v1/alerts/stats?days=7",
            headers={"Authorization": f"Bearer {patient_token}"}
        )

        assert response.status_code == 403

    def test_get_alert_stats_respects_days_filter(self, db_session):
        """Test stats endpoint respects days parameter."""
        doctor = make_user(db_session, "doctor2@example.com", "Doctor 2", "clinician")
        patient = make_user(db_session, "patient3@example.com", "Patient 3", "patient")
        
        # Create recent alert
        make_alert(db_session, patient.user_id, alert_type="high_heart_rate")
        
        doctor_token = get_token(client, "doctor2@example.com")

        # Request stats for last 7 days (should include the alert)
        response = client.get(
            "/api/v1/alerts/stats?days=7",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7

    def test_get_alert_stats_empty_when_no_alerts(self, db_session):
        """Test stats returns empty breakdown when no alerts exist."""
        doctor = make_user(db_session, "doctor3@example.com", "Doctor 3", "clinician")
        doctor_token = get_token(client, "doctor3@example.com")

        response = client.get(
            "/api/v1/alerts/stats?days=7",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["severity_breakdown"] == {}
        assert data["unacknowledged_count"] == 0


class TestCreateAlertDeduplication:
    """Test POST /api/v1/alerts with duplicate detection."""

    def test_create_alert_duplicate_within_5min_returns_409(self, db_session):
        """Test creating same alert_type twice within 5 min returns 409."""
        user = make_user(db_session, "alice_dup@example.com", "Alice Dup", "patient")
        token = get_token(client, "alice_dup@example.com")
        
        # Create first alert
        alert_data = {
            "user_id": user.user_id,
            "alert_type": "high_heart_rate",
            "severity": "critical",
            "title": "High Heart Rate",
            "message": "Heart rate exceeded threshold"
        }
        response1 = client.post(
            "/api/v1/alerts",
            json=alert_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response1.status_code == 200
        
        # Try to create duplicate immediately
        response2 = client.post(
            "/api/v1/alerts",
            json=alert_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"].lower()

    def test_create_alert_different_type_succeeds(self, db_session):
        """Test creating different alert_type succeeds even if recent alert exists."""
        user = make_user(db_session, "bob_dup@example.com", "Bob Dup", "patient")
        token = get_token(client, "bob_dup@example.com")
        
        # Create first alert
        alert_data_1 = {
            "user_id": user.user_id,
            "alert_type": "high_heart_rate",
            "severity": "critical",
            "title": "High Heart Rate",
            "message": "Heart rate exceeded threshold"
        }
        response1 = client.post(
            "/api/v1/alerts",
            json=alert_data_1,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response1.status_code == 200
        
        # Create different type
        alert_data_2 = {
            "user_id": user.user_id,
            "alert_type": "low_spo2",
            "severity": "critical",
            "title": "Low Oxygen",
            "message": "SpO2 below threshold"
        }
        response2 = client.post(
            "/api/v1/alerts",
            json=alert_data_2,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response2.status_code == 200

    def test_create_alert_succeeds_after_window(self, db_session):
        """Test creating alert succeeds if previous alert is old enough."""
        user = make_user(db_session, "charlie_dup@example.com", "Charlie Dup", "patient")
        
        # Create old alert (manually set created_at to 10 minutes ago)
        alert = Alert(
            user_id=user.user_id,
            alert_type="high_heart_rate",
            severity="critical",
            title="Old Alert",
            message="This is an old alert",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        db_session.add(alert)
        db_session.commit()
        
        # Now try to create same type (should succeed because > 5 min window)
        token = get_token(client, "charlie_dup@example.com")
        alert_data = {
            "user_id": user.user_id,
            "alert_type": "high_heart_rate",
            "severity": "critical",
            "title": "New High Heart Rate",
            "message": "Another high heart rate alert"
        }
        response = client.post(
            "/api/v1/alerts",
            json=alert_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
