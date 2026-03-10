"""Natural-language endpoint tests.

Covers summary endpoints plus chat and image-chat flows.

Run with:
    pytest tests/test_nl.py -v
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_alert, make_user


client = TestClient(fastapi_app)


def get_access_token(email, password="TestPass123"):
    response = client.post(
        "/api/v1/access",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# get_risk_summary Tests
# =============================================================================

class TestGetRiskSummary:
    """Test GET /api/v1/nl/risk-summary endpoint from app/api/nl_endpoints.py."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        make_user(db_session, "alice@example.com", "Alice", "patient")

        response = client.get("/api/v1/nl/risk-summary")

        assert response.status_code == 401

    @patch('app.api.nl_endpoints.build_risk_summary_text')
    def test_with_auth_returns_200_with_risk_summary_shape(self, mock_builder, db_session):
        """Test with auth + mocked builders returns 200 with RiskSummaryResponse shape."""
        mock_builder.return_value = "Your recent vitals look stable."
        
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_access_token(user.email)
        
        response = client.get(
            "/api/v1/nl/risk-summary?time_window_hours=24",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "time_window_hours" in data
        assert "risk_level" in data
        assert "risk_score" in data
        assert "key_factors" in data
        assert "safety_status" in data
        assert "nl_summary" in data
        assert data["nl_summary"] == "Your recent vitals look stable."


# =============================================================================
# get_todays_workout Tests
# =============================================================================

class TestGetTodaysWorkout:
    """Test GET /api/v1/nl/todays-workout endpoint from app/api/nl_endpoints.py."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401 (if endpoint requires auth)."""
        make_user(db_session, "charlie@example.com", "Charlie", "patient")

        response = client.get("/api/v1/nl/todays-workout")

        assert response.status_code == 401

    @patch('app.api.nl_endpoints.build_todays_workout_text')
    def test_with_auth_returns_200(self, mock_builder, db_session):
        """Test with auth returns 200."""
        mock_builder.return_value = "Try a light walk for 20 minutes."
        
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        token = get_access_token(user.email)
        
        response = client.get(
            "/api/v1/nl/todays-workout",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "date" in data
        assert "activity_type" in data
        assert "intensity_level" in data
        assert "duration_minutes" in data
        assert "target_hr_min" in data
        assert "target_hr_max" in data
        assert "risk_level" in data
        assert "nl_summary" in data
        assert data["nl_summary"] == "Try a light walk for 20 minutes."

    @patch('app.api.nl_endpoints.build_todays_workout_text')
    def test_with_date_param(self, mock_builder, db_session):
        """Test with date query parameter."""
        mock_builder.return_value = "Workout recommendation text."
        
        user = make_user(db_session, "eve@example.com", "Eve", "patient")
        token = get_access_token(user.email)
        target_date = "2026-02-22"
        
        response = client.get(
            f"/api/v1/nl/todays-workout?date={target_date}",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == target_date


# =============================================================================
# get_alert_explanation Tests
# =============================================================================

class TestGetAlertExplanation:
    """Test GET /api/v1/nl/alert-explanation endpoint from app/api/nl_endpoints.py."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401 (if endpoint requires auth)."""
        make_user(db_session, "frank@example.com", "Frank", "patient")

        response = client.get("/api/v1/nl/alert-explanation")

        assert response.status_code == 401

    @patch('app.api.nl_endpoints.build_alert_explanation_text')
    def test_with_valid_alert_returns_200(self, mock_builder, db_session):
        """Test with valid alert returns 200."""
        mock_builder.return_value = "Your heart rate reached 145 BPM. Slow down the pace."
        
        user = make_user(db_session, "grace@example.com", "Grace", "patient")
        token = get_access_token(user.email)
        alert = make_alert(db_session, user.user_id, alert_type="high_heart_rate", severity="warning")
        
        response = client.get(
            f"/api/v1/nl/alert-explanation?alert_id={alert.alert_id}",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "alert_id" in data
        assert "alert_type" in data
        assert "severity_level" in data
        assert "alert_time" in data
        assert "context" in data
        assert "recommended_action" in data
        assert "nl_summary" in data
        assert "heart rate" in data["nl_summary"].lower()


# =============================================================================
# get_progress_summary Tests
# =============================================================================

class TestGetProgressSummary:
    """Test GET /api/v1/nl/progress-summary endpoint from app/api/nl_endpoints.py."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401 (if endpoint requires auth)."""
        make_user(db_session, "henry@example.com", "Henry", "patient")

        response = client.get("/api/v1/nl/progress-summary")

        assert response.status_code == 401

    @patch('app.api.nl_endpoints.build_progress_summary_text')
    @patch('app.api.nl_endpoints.compute_trend')
    def test_with_auth_returns_200(self, mock_compute_trend, mock_builder, db_session):
        """Test with auth returns 200."""
        from app.schemas.nl import Trend
        
        mock_compute_trend.return_value = Trend(
            workout_frequency="IMPROVING",
            alerts="STABLE",
            risk="IMPROVING",
            overall="IMPROVING"
        )
        mock_builder.return_value = "Great progress! You completed 5 workouts this week."
        
        user = make_user(db_session, "iris@example.com", "Iris", "patient")
        token = get_access_token(user.email)
        
        response = client.get(
            "/api/v1/nl/progress-summary?range=7d",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "range" in data
        assert "current_period" in data
        assert "previous_period" in data
        assert "trend" in data
        assert "nl_summary" in data
        assert data["nl_summary"] == "Great progress! You completed 5 workouts this week."

    @patch('app.api.nl_endpoints.build_progress_summary_text')
    @patch('app.api.nl_endpoints.compute_trend')
    def test_with_30d_range(self, mock_compute_trend, mock_builder, db_session):
        """Test with 30d range parameter."""
        from app.schemas.nl import Trend
        
        mock_compute_trend.return_value = Trend(
            workout_frequency="STABLE",
            alerts="STABLE",
            risk="STABLE",
            overall="STABLE"
        )
        mock_builder.return_value = "You're maintaining a steady routine."
        
        user = make_user(db_session, "jane@example.com", "Jane", "patient")
        token = get_access_token(user.email)
        
        response = client.get(
            "/api/v1/nl/progress-summary?range=30d",
            headers=auth_header(token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["range"] == "30d"

    def test_invalid_range_returns_400(self, db_session):
        """Test invalid range parameter returns 400."""
        user = make_user(db_session, "kate@example.com", "Kate", "patient")
        token = get_access_token(user.email)
        
        response = client.get(
            "/api/v1/nl/progress-summary?range=invalid",
            headers=auth_header(token),
        )
        
        assert response.status_code == 400


def test_chat_endpoint_success(db_session, monkeypatch):
    """Authenticated users receive a chat response payload."""
    user = make_user(db_session, "chatuser@example.com", "Chat User", "patient")
    token = get_access_token(user.email)

    mocked_response = {
        "response": "Keep your HR in the target zone.",
        "source": "template",
    }
    monkeypatch.setattr(
        "app.services.chat_service.generate_chat_response",
        AsyncMock(return_value=mocked_response),
    )

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
    """Image chat returns 503 when Gemini is not configured."""
    user = make_user(db_session, "chatimg@example.com", "Chat Img", "patient")
    token = get_access_token(user.email)

    monkeypatch.setattr("app.api.nl_endpoints.settings.gemini_api_key", None)

    response = client.post(
        "/api/v1/nl/chat-with-image",
        files={"image": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"message": "Is this meal healthy?", "analysis_type": "food"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "Gemini API key not configured" in response.json()["detail"]
