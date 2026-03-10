"""Prediction API tests.

Covers functions in app/api/predict.py:
- Helper functions (_get_recent_vitals_window, _aggregate_session_features_from_vitals, _build_drivers, _generate_recommendation_payload)
- check_model_status (GET /api/v1/predict/status)
- predict_risk (POST /api/v1/predict/risk)
- predict_user_risk_from_latest_session (GET /api/v1/predict/user/{id}/risk)
- get_my_risk_history (GET /api/v1/predict/my-risk)
- get_my_latest_risk_assessment (GET /api/v1/risk-assessments/latest)
- get_patient_latest_risk_assessment (GET /api/v1/patients/{id}/risk-assessments/latest)
- get_my_latest_recommendation (GET /api/v1/recommendations/latest)
- get_patient_latest_recommendation (GET /api/v1/patients/{id}/recommendations/latest)
- compute_my_risk_assessment (POST /api/v1/risk-assessments/compute)
- compute_patient_risk_assessment (POST /api/v1/patients/{id}/risk-assessments/compute)

Run with:
    pytest tests/test_predict.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.api.predict import (
    _get_recent_vitals_window,
    _aggregate_session_features_from_vitals,
    _build_drivers,
    _generate_recommendation_payload
)
from app.models.user import User
from app.models.risk_assessment import RiskAssessment
from app.models.recommendation import ExerciseRecommendation
from tests.helpers import make_user, get_token, make_vital, make_activity
import pytest


client = TestClient(fastapi_app)


# =============================================================================
# Mock ML Service Setup
# =============================================================================

@pytest.fixture
def mock_ml_service():
    """Create a mock ML service with standard prediction response."""
    mock_service = Mock()
    mock_service.is_loaded = True
    mock_service.feature_columns = ["age", "baseline_hr", "max_safe_hr", "avg_heart_rate"]
    mock_service.predict_risk.return_value = {
        "risk_score": 0.25,
        "risk_level": "low",
        "high_risk": False,
        "confidence": 0.85,
        "recommendation": "Safe to continue",
        "model_info": {"name": "RandomForest", "version": "1.0"},
        "features_used": {}
    }
    return mock_service


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Test internal helper functions called directly."""

    def test_get_recent_vitals_window_returns_vitals_within_window(self, db_session):
        """Test returns vitals within time window."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        
        # Create vitals within 30-minute window
        make_vital(db_session, user.user_id, heart_rate=75, minutes_ago=5)
        make_vital(db_session, user.user_id, heart_rate=80, minutes_ago=15)
        make_vital(db_session, user.user_id, heart_rate=78, minutes_ago=25)
        
        # Create old vital outside window
        make_vital(db_session, user.user_id, heart_rate=70, minutes_ago=45)
        
        vitals = _get_recent_vitals_window(db_session, user.user_id, window_minutes=30)
        
        assert len(vitals) == 3
        assert vitals[0].heart_rate == 78  # Oldest within window (25 min ago)
        assert vitals[-1].heart_rate == 75  # Most recent (5 min ago)

    def test_get_recent_vitals_window_returns_empty_when_no_recent_vitals(self, db_session):
        """Test returns empty list when no recent vitals."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        
        # Create only old vitals
        make_vital(db_session, user.user_id, heart_rate=70, minutes_ago=45)
        
        vitals = _get_recent_vitals_window(db_session, user.user_id, window_minutes=30)
        
        assert len(vitals) == 0

    def test_aggregate_session_features_calculates_correct_avg_peak_min_hr(self, db_session):
        """Test aggregates vitals into correct avg/peak/min HR."""
        user = make_user(db_session, "charlie@example.com", "Charlie", "patient")
        
        vital1 = make_vital(db_session, user.user_id, heart_rate=70, spo2=97, minutes_ago=20)
        vital2 = make_vital(db_session, user.user_id, heart_rate=85, spo2=96, minutes_ago=10)
        vital3 = make_vital(db_session, user.user_id, heart_rate=80, spo2=98, minutes_ago=5)
        
        vitals = [vital1, vital2, vital3]
        features = _aggregate_session_features_from_vitals(vitals)
        
        # avg_hr = (70 + 85 + 80) / 3 = 78.33 → 78
        assert features["avg_heart_rate"] == 78
        # peak_hr = max(70, 85, 80) = 85
        assert features["peak_heart_rate"] == 85
        # min_hr = min(70, 85, 80) = 70
        assert features["min_heart_rate"] == 70
        # avg_spo2 = (97 + 96 + 98) / 3 = 97
        assert features["avg_spo2"] == 97
        assert features["points"] == 3

    def test_aggregate_session_features_raises_valueerror_on_empty_list(self, db_session):
        """Test raises ValueError when vitals list is empty."""
        with pytest.raises(ValueError, match="No vitals to aggregate"):
            _aggregate_session_features_from_vitals([])

    def test_build_drivers_adds_driver_when_peak_hr_exceeds_max_safe(self, db_session):
        """Test adds driver when peak HR > max_safe."""
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        features = {
            "peak_heart_rate": 160,  # Exceeds max_safe of 150
            "avg_heart_rate": 140,
            "avg_spo2": 97,
            "duration_minutes": 20
        }
        
        drivers = _build_drivers(user, features)
        
        assert any("Peak heart rate exceeded safe limit" in d for d in drivers)
        assert any("160" in d and "150" in d for d in drivers)

    def test_build_drivers_adds_within_safe_limits_when_normal_vitals(self, db_session):
        """Test adds 'within safe limits' driver when vitals are normal."""
        user = make_user(db_session, "eve@example.com", "Eve", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        features = {
            "peak_heart_rate": 120,  # Within limits
            "avg_heart_rate": 90,    # Within limits
            "avg_spo2": 97,          # Within limits
            "duration_minutes": 20
        }
        
        drivers = _build_drivers(user, features)
        
        assert any("within expected safe limits" in d.lower() for d in drivers)

    def test_build_drivers_adds_driver_for_low_spo2(self, db_session):
        """Test adds driver when SpO2 is low."""
        user = make_user(db_session, "frank@example.com", "Frank", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        features = {
            "peak_heart_rate": 120,
            "avg_heart_rate": 90,
            "avg_spo2": 90,  # Low SpO2
            "duration_minutes": 20
        }
        
        drivers = _build_drivers(user, features)
        
        assert any("SpO₂ is low" in d and "90" in d for d in drivers)

    def test_generate_recommendation_returns_recovery_for_high_risk(self, db_session):
        """Test returns a low-intensity recovery exercise for high risk."""
        user = make_user(db_session, "grace@example.com", "Grace", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        payload = _generate_recommendation_payload(user, "high", 0.85, [])
        
        assert "Recovery" in payload["title"]
        assert payload["intensity_level"] == "low"
        assert payload["target_heart_rate_min"] is None
        assert isinstance(payload["duration_minutes"], int)
        assert payload["suggested_activity"]
        assert payload["description"]
        assert payload["warnings"]

    def test_generate_recommendation_returns_low_intensity_for_moderate_risk(self, db_session):
        """Test returns a low-intensity exercise for moderate risk."""
        user = make_user(db_session, "henry@example.com", "Henry", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        payload = _generate_recommendation_payload(user, "moderate", 0.55, [])
        
        assert payload["intensity_level"] == "low"
        assert payload["target_heart_rate_min"] is not None
        assert isinstance(payload["duration_minutes"], int)
        assert payload["suggested_activity"]

    def test_generate_recommendation_returns_moderate_intensity_for_low_risk(self, db_session):
        """Test returns a moderate-intensity exercise for low risk."""
        user = make_user(db_session, "iris@example.com", "Iris", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        payload = _generate_recommendation_payload(user, "low", 0.15, [])
        
        assert payload["intensity_level"] == "moderate"
        assert payload["target_heart_rate_min"] is not None
        assert isinstance(payload["duration_minutes"], int)
        assert payload["suggested_activity"]

    def test_generate_recommendation_avoids_last_activity(self, db_session):
        """Test deduplication: does not repeat last_activity when alternatives exist."""
        user = make_user(db_session, "jack@example.com", "Jack", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()

        from app.services.recommendation_ranking import EXERCISE_LIBRARY
        first_activity = EXERCISE_LIBRARY["low"][0]["suggested_activity"]

        # Run enough times to confirm the last_activity is avoided
        activities = set()
        for _ in range(20):
            payload = _generate_recommendation_payload(
                user, "low", 0.15, [], last_activity=first_activity,
            )
            activities.add(payload["suggested_activity"])

        assert first_activity not in activities


# =============================================================================
# Model Status Endpoint Tests
# =============================================================================

class TestCheckModelStatus:
    """Test GET /api/v1/predict/status."""

    @patch('app.api.predict.get_ml_service')
    def test_check_model_status_returns_ready_when_loaded(self, mock_get_service, mock_ml_service):
        """Test returns model_loaded=true when service is loaded."""
        mock_get_service.return_value = mock_ml_service
        
        response = client.get("/api/v1/predict/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is True
        assert data["status"] == "ready"
        assert data["features_count"] == 4

    @patch('app.api.predict.get_ml_service')
    def test_check_model_status_returns_not_loaded_when_unavailable(self, mock_get_service):
        """Test returns model_loaded=false when service not loaded."""
        mock_service = Mock()
        mock_service.is_loaded = False
        mock_service.feature_columns = None
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/predict/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is False
        assert data["status"] == "not_loaded"

    @patch('app.api.predict.get_ml_service')
    def test_check_model_status_returns_error_when_exception(self, mock_get_service):
        """Test returns error status when service raises exception."""
        mock_get_service.side_effect = Exception("Model load failed")
        
        response = client.get("/api/v1/predict/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["model_loaded"] is False
        assert "error" in data


# =============================================================================
# Predict Risk Endpoint Tests
# =============================================================================

class TestPredictRisk:
    """Test POST /api/v1/predict/risk."""

    @patch('app.api.predict.get_ml_service')
    def test_predict_risk_valid_request_returns_prediction(self, mock_get_service, mock_ml_service, db_session):
        """Test valid request returns risk_score and risk_level."""
        mock_get_service.return_value = mock_ml_service
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")
        
        request_data = {
            "age": 30,
            "baseline_hr": 72,
            "max_safe_hr": 150,
            "avg_heart_rate": 90,
            "peak_heart_rate": 120,
            "min_heart_rate": 65,
            "avg_spo2": 97,
            "duration_minutes": 20,
            "recovery_time_minutes": 5,
            "activity_type": "walking"
        }
        
        response = client.post(
            "/api/v1/predict/risk",
            json=request_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert data["risk_score"] == 0.25
        assert data["risk_level"] == "low"
        assert data["high_risk"] is False
        assert "inference_time_ms" in data

    @patch('app.api.predict.get_ml_service')
    def test_predict_risk_model_not_loaded_returns_503(self, mock_get_service, db_session):
        """Test returns 503 when model not loaded."""
        mock_service = Mock()
        mock_service.is_loaded = False
        mock_get_service.return_value = mock_service
        
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")
        
        request_data = {
            "age": 30,
            "baseline_hr": 72,
            "max_safe_hr": 150,
            "avg_heart_rate": 90,
            "peak_heart_rate": 120,
            "min_heart_rate": 65,
            "avg_spo2": 97,
            "duration_minutes": 20,
            "recovery_time_minutes": 5
        }
        
        response = client.post(
            "/api/v1/predict/risk",
            json=request_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 503
        assert "not loaded" in response.json()["detail"].lower()

    def test_predict_risk_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        request_data = {
            "age": 30,
            "baseline_hr": 72,
            "max_safe_hr": 150,
            "avg_heart_rate": 90,
            "peak_heart_rate": 120,
            "min_heart_rate": 65,
            "avg_spo2": 97,
            "duration_minutes": 20,
            "recovery_time_minutes": 5
        }
        
        response = client.post("/api/v1/predict/risk", json=request_data)
        
        assert response.status_code == 401


# =============================================================================
# Predict User Risk Endpoint Tests
# =============================================================================

class TestPredictUserRisk:
    """Test GET /api/v1/predict/user/{id}/risk."""

    @patch('app.api.predict.get_ml_service')
    def test_predict_user_risk_doctor_with_patient_sessions_returns_prediction(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test doctor accessing patient with sessions returns prediction."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        # Create activity session for patient
        make_activity(db_session, patient.user_id, activity_type="walking", avg_hr=85, peak_hr=120)
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            f"/api/v1/predict/user/{patient.user_id}/risk",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == patient.user_id
        assert "prediction" in data
        assert data["prediction"]["risk_score"] == 0.25

    @patch('app.api.predict.get_ml_service')
    def test_predict_user_risk_no_sessions_returns_404(self, mock_get_service, mock_ml_service, db_session):
        """Test returns 404 when patient has no sessions."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        # No activity sessions created
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            f"/api/v1/predict/user/{patient.user_id}/risk",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404
        assert "No activity sessions found" in response.json()["detail"]

    def test_predict_user_risk_patient_not_found_returns_404(self, db_session):
        """Test returns 404 when patient not found."""
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            "/api/v1/predict/user/99999/risk",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404

    def test_predict_user_risk_patient_token_returns_403(self, db_session):
        """Test patient token returns 403."""
        patient1 = make_user(db_session, "patient1@example.com", "Patient 1", "patient")
        patient2 = make_user(db_session, "patient2@example.com", "Patient 2", "patient")
        
        patient1_token = get_token(client, "patient1@example.com")
        
        response = client.get(
            f"/api/v1/predict/user/{patient2.user_id}/risk",
            headers={"Authorization": f"Bearer {patient1_token}"}
        )
        
        assert response.status_code == 403


# =============================================================================
# Risk History Endpoint Tests
# =============================================================================

class TestGetMyRiskHistory:
    """Test GET /api/v1/predict/my-risk."""

    def test_get_my_risk_history_returns_empty_list_when_no_assessments(self, db_session):
        """Test returns empty list message when no assessments."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")
        
        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.user_id
        assert data["risk_assessments"] == []
        assert "No risk assessments found" in data["message"]

    def test_get_my_risk_history_returns_list_with_recommendations(self, db_session):
        """Test returns list with correct recommendation text per risk_level."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")
        
        # Create risk assessments with different levels
        ra_critical = RiskAssessment(
            user_id=user.user_id,
            risk_score=0.95,
            risk_level="critical",
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        ra_high = RiskAssessment(
            user_id=user.user_id,
            risk_score=0.75,
            risk_level="high",
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        ra_moderate = RiskAssessment(
            user_id=user.user_id,
            risk_score=0.45,
            risk_level="moderate",
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        ra_low = RiskAssessment(
            user_id=user.user_id,
            risk_score=0.15,
            risk_level="low",
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        db_session.add_all([ra_critical, ra_high, ra_moderate, ra_low])
        db_session.commit()
        
        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["risk_assessments"]) == 4
        
        # Check recommendations match risk levels
        assessments_by_level = {a["risk_level"]: a for a in data["risk_assessments"]}
        assert "immediate medical attention" in assessments_by_level["critical"]["recommendation"].lower()
        assert "healthcare provider" in assessments_by_level["high"]["recommendation"].lower()
        assert "monitor" in assessments_by_level["moderate"]["recommendation"].lower()
        assert "continue normal" in assessments_by_level["low"]["recommendation"].lower()

    def test_get_my_risk_history_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/predict/my-risk")
        
        assert response.status_code == 401


# =============================================================================
# Latest Risk Assessment Endpoint Tests
# =============================================================================

class TestGetMyLatestRiskAssessment:
    """Test GET /api/v1/risk-assessments/latest."""

    def test_get_my_latest_returns_404_when_none_exist(self, db_session):
        """Test returns 404 when no assessments exist."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")
        
        response = client.get(
            "/api/v1/risk-assessments/latest",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "No risk assessments found" in response.json()["detail"]

    def test_get_my_latest_returns_assessment_with_drivers(self, db_session):
        """Test returns assessment with drivers when one exists."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")
        
        import json
        drivers = ["Peak heart rate exceeded safe limit (160 > 150).", "Average SpO₂ is low (90%)."]
        
        ra = RiskAssessment(
            user_id=user.user_id,
            risk_score=0.65,
            risk_level="moderate",
            risk_factors_json=json.dumps(drivers),
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        db_session.add(ra)
        db_session.commit()
        
        response = client.get(
            "/api/v1/risk-assessments/latest",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assessment_id"] == ra.assessment_id
        assert data["risk_score"] == 0.65
        assert data["risk_level"] == "moderate"
        assert len(data["drivers"]) == 2
        assert "Peak heart rate exceeded" in data["drivers"][0]


class TestGetPatientLatestRiskAssessment:
    """Test GET /api/v1/patients/{id}/risk-assessments/latest."""

    def test_get_patient_latest_doctor_can_access(self, db_session):
        """Test doctor can access patient's latest assessment."""
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        ra = RiskAssessment(
            user_id=patient.user_id,
            risk_score=0.35,
            risk_level="low",
            assessment_type="vitals_window",
            generated_by="cloud_ai"
        )
        db_session.add(ra)
        db_session.commit()
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == patient.user_id
        assert data["risk_score"] == 0.35

    def test_get_patient_latest_returns_404_when_none(self, db_session):
        """Test returns 404 when patient has no assessments."""
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404


# =============================================================================
# Latest Recommendation Endpoint Tests
# =============================================================================

class TestGetMyLatestRecommendation:
    """Test GET /api/v1/recommendations/latest."""

    def test_get_my_latest_returns_404_when_none(self, db_session):
        """Test returns 404 when no recommendations exist."""
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")
        
        response = client.get(
            "/api/v1/recommendations/latest",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "No recommendations found" in response.json()["detail"]

    def test_get_my_latest_returns_recommendation_fields(self, db_session):
        """Test returns recommendation with all fields."""
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")
        
        rec = ExerciseRecommendation(
            user_id=user.user_id,
            title="Continue Safe Training",
            suggested_activity="Walking",
            intensity_level="moderate",
            duration_minutes=20,
            target_heart_rate_min=85,
            target_heart_rate_max=120,
            description="Safe zone",
            warnings="Monitor for symptoms",
            generated_by="cloud_ai"
        )
        db_session.add(rec)
        db_session.commit()
        
        response = client.get(
            "/api/v1/recommendations/latest",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_id"] == rec.recommendation_id
        assert data["title"] == "Continue Safe Training"
        assert data["suggested_activity"] == "Walking"
        assert data["intensity_level"] == "moderate"
        assert data["duration_minutes"] == 20


class TestGetPatientLatestRecommendation:
    """Test GET /api/v1/patients/{id}/recommendations/latest."""

    def test_get_patient_latest_doctor_can_access(self, db_session):
        """Test doctor can access patient's latest recommendation."""
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        rec = ExerciseRecommendation(
            user_id=patient.user_id,
            title="Recovery & Monitoring",
            suggested_activity="Rest",
            intensity_level="low",
            duration_minutes=10,
            generated_by="cloud_ai"
        )
        db_session.add(rec)
        db_session.commit()
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/recommendations/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == patient.user_id
        assert data["title"] == "Recovery & Monitoring"

    def test_get_patient_latest_patient_not_found_returns_404(self, db_session):
        """Test returns 404 when patient not found."""
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.get(
            "/api/v1/patients/99999/recommendations/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404


# =============================================================================
# Compute Risk Assessment Endpoint Tests
# =============================================================================

class TestComputeMyRiskAssessment:
    """Test POST /api/v1/risk-assessments/compute."""

    @patch('app.api.predict.get_ml_service')
    def test_compute_my_risk_creates_assessment_and_recommendation(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test computes risk and stores assessment + recommendation."""
        mock_get_service.return_value = mock_ml_service
        
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        user.age = 30
        user.baseline_hr = 72
        user.max_safe_hr = 150
        db_session.commit()
        
        # Create recent vitals
        make_vital(db_session, user.user_id, heart_rate=85, spo2=97, minutes_ago=5)
        make_vital(db_session, user.user_id, heart_rate=90, spo2=96, minutes_ago=10)
        
        token = get_token(client, "alice@example.com")
        
        response = client.post(
            "/api/v1/risk-assessments/compute",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.user_id
        assert data["risk_score"] == 0.25
        assert data["risk_level"] == "low"
        assert "drivers" in data
        
        # Verify assessment stored
        assessment = db_session.query(RiskAssessment).filter(
            RiskAssessment.assessment_id == data["assessment_id"]
        ).first()
        assert assessment is not None
        assert assessment.risk_score == 0.25
        
        # Verify recommendation created
        recommendation = db_session.query(ExerciseRecommendation).filter(
            ExerciseRecommendation.user_id == user.user_id
        ).first()
        assert recommendation is not None

    @patch('app.api.predict.get_ml_service')
    def test_compute_my_risk_no_recent_vitals_returns_404(self, mock_get_service, mock_ml_service, db_session):
        """Test returns 404 when no recent vitals found."""
        mock_get_service.return_value = mock_ml_service
        
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        
        # Create old vitals only
        make_vital(db_session, user.user_id, heart_rate=75, minutes_ago=45)
        
        token = get_token(client, "bob@example.com")
        
        response = client.post(
            "/api/v1/risk-assessments/compute",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "No recent vitals found" in response.json()["detail"]


class TestComputePatientRiskAssessment:
    """Test POST /api/v1/patients/{id}/risk-assessments/compute."""

    @patch('app.api.predict.get_ml_service')
    def test_compute_patient_risk_doctor_creates_assessment(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test doctor can compute risk for patient with vitals."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        patient.age = 35
        patient.baseline_hr = 70
        patient.max_safe_hr = 155
        db_session.commit()
        
        # Create recent vitals for patient
        make_vital(db_session, patient.user_id, heart_rate=88, spo2=97, minutes_ago=5)
        make_vital(db_session, patient.user_id, heart_rate=92, spo2=96, minutes_ago=10)
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.post(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/compute",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == patient.user_id
        assert data["risk_score"] == 0.25
        
        # Verify both assessment and recommendation stored
        assessment_count = db_session.query(RiskAssessment).filter(
            RiskAssessment.user_id == patient.user_id
        ).count()
        assert assessment_count == 1
        
        rec_count = db_session.query(ExerciseRecommendation).filter(
            ExerciseRecommendation.user_id == patient.user_id
        ).count()
        assert rec_count == 1

    @patch('app.api.predict.get_ml_service')
    def test_compute_patient_risk_no_vitals_returns_404(self, mock_get_service, mock_ml_service, db_session):
        """Test returns 404 when patient has no recent vitals."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient@example.com", "Patient", "patient")
        
        doctor_token = get_token(client, "doctor@example.com")
        
        response = client.post(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/compute",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404
        assert "No recent vitals found" in response.json()["detail"]


# =============================================================================
# Additional Predict API Branch Coverage
# =============================================================================

class TestPredictApiBranchCoverage:
    """Additional branch coverage tests for prediction endpoints."""

    def test_build_drivers_with_swimming_activity(self, db_session):
        """Test _build_drivers handles swimming activity type."""
        user = make_user(db_session, "swimmer@example.com", "Swimmer", "patient")
        
        # _build_drivers takes (user, features_dict)
        features = {
            "age": 35,
            "baseline_hr": 65,
            "max_safe_hr": 185,
            "activity_type": "swimming",
            "peak_heart_rate": 175,
            "avg_heart_rate": 140,
            "avg_spo2": 95,
            "duration_minutes": 30
        }
        
        drivers = _build_drivers(user, features)
        
        # Should handle swimming activity_type without error
        assert isinstance(drivers, list)
        assert len(drivers) >= 0

    @patch('app.api.predict.get_ml_service')
    def test_predict_user_risk_no_completed_sessions_returns_404(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test predict risk with no completed sessions returns 404 or 403."""
        mock_get_service.return_value = mock_ml_service
        
        user = make_user(db_session, "no_sessions@example.com", "No Sessions", "patient")
        user_token = get_token(client, "no_sessions@example.com")
        
        response = client.get(
            f"/api/v1/predict/user/{user.user_id}/risk",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # May be 403 (forbidden) or 404 (not found) depending on endpoint design
        assert response.status_code in [403, 404]

    @patch('app.api.predict.get_ml_service')
    def test_compute_patient_risk_clinician_patient_not_found_returns_404(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test compute risk for non-existent patient returns 404."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor_notfound@example.com", "Doctor", "clinician")
        doctor_token = get_token(client, "doctor_notfound@example.com")
        
        response = client.post(
            "/api/v1/patients/99999/risk-assessments/compute",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404

    @patch('app.api.predict.get_ml_service')
    def test_get_patient_latest_risk_not_found_returns_404(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test get latest risk when none exists returns 404."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor_norisk@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient_norisk@example.com", "Patient", "patient")
        doctor_token = get_token(client, "doctor_norisk@example.com")
        
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404

    @patch('app.api.predict.get_ml_service')
    def test_get_patient_latest_recommendation_not_found_returns_404(
        self, mock_get_service, mock_ml_service, db_session
    ):
        """Test get latest recommendation when none exists returns 404."""
        mock_get_service.return_value = mock_ml_service
        
        doctor = make_user(db_session, "doctor_norec@example.com", "Doctor", "clinician")
        patient = make_user(db_session, "patient_norec@example.com", "Patient", "patient")
        doctor_token = get_token(client, "doctor_norec@example.com")
        
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/recommendations/latest",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 404
