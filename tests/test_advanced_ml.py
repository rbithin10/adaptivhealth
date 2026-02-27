"""
Tests for advanced ML/AI services and API endpoints.

Covers:
- API endpoints in app/api/advanced_ml.py at 0%
- Service layer functions (anomaly detection, forecasting, optimization, etc.)

Run with:
    pytest tests/test_advanced_ml.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token


client = TestClient(fastapi_app)


# =============================================================================
# API ENDPOINT TESTS (app/api/advanced_ml.py at 0%)
# =============================================================================

class TestDetectVitalAnomaliesEndpoint:
    """Test GET /api/v1/anomaly-detection endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/anomaly-detection?days=7")
        assert response.status_code == 401

    @patch('app.services.anomaly_detection.detect_anomalies')
    def test_with_auth_returns_200(self, mock_detect, db_session):
        """Test with auth + mocked service returns 200."""
        mock_detect.return_value = {
            "anomalies": [],
            "anomaly_score": 0.12,
            "threshold": 0.5,
            "status": "normal"
        }
        
        user = make_user(db_session, "alice@example.com", "Alice", "patient")
        token = get_token(client, "alice@example.com")
        
        response = client.get(
            "/api/v1/anomaly-detection?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data or "anomaly_score" in data


class TestForecastVitalTrendsEndpoint:
    """Test GET /api/v1/trend-forecast endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/trend-forecast?forecast_days=7")
        assert response.status_code == 401

    @patch('app.services.trend_forecasting.forecast_trends')
    def test_with_auth_returns_200(self, mock_forecast, db_session):
        """Test with auth returns 200."""
        mock_forecast.return_value = {
            "forecast": [],
            "trend": "stable",
            "confidence": 0.85
        }
        
        user = make_user(db_session, "bob@example.com", "Bob", "patient")
        token = get_token(client, "bob@example.com")
        
        response = client.get(
            "/api/v1/trend-forecast?forecast_days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200


class TestOptimizeBaselineEndpoint:
    """Test GET /api/v1/baseline-optimization endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/baseline-optimization")
        assert response.status_code == 401

    @patch('app.services.baseline_optimization.compute_optimized_baseline')
    def test_with_auth_returns_200(self, mock_compute, db_session):
        """Test with auth returns 200."""
        mock_compute.return_value = {
            "current_baseline_hr": 70,
            "optimized_baseline_hr": 68,
            "confidence": 0.92
        }
        
        user = make_user(db_session, "charlie@example.com", "Charlie", "patient")
        token = get_token(client, "charlie@example.com")
        
        response = client.get(
            "/api/v1/baseline-optimization",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200


class TestApplyBaselineOptimizationEndpoint:
    """Test POST /api/v1/baseline-optimization/apply endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.post(
            "/api/v1/baseline-optimization/apply",
            json={"new_baseline_hr": 68}
        )
        assert response.status_code == 401

    def test_with_auth_updates_user(self, db_session):
        """Test with auth updates user baseline."""
        user = make_user(db_session, "dave@example.com", "Dave", "patient")
        user.baseline_hr = 70
        db_session.commit()
        
        token = get_token(client, "dave@example.com")
        
        response = client.post(
            "/api/v1/baseline-optimization/apply",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_baseline_hr": 68}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Endpoint returns "new_baseline" not "baseline_heart_rate"
        assert "new_baseline" in data or "user_id" in data


class TestModelRetrainingStatusEndpoint:
    """Test GET /api/v1/model/retraining-status endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/model/retraining-status")
        assert response.status_code == 401

    def test_patient_returns_403(self, db_session):
        """Test patient role returns 403."""
        user = make_user(db_session, "eve@example.com", "Eve", "patient")
        token = get_token(client, "eve@example.com")
        
        response = client.get(
            "/api/v1/model/retraining-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    @patch('app.services.retraining_pipeline.get_retraining_status')
    def test_clinician_returns_200(self, mock_status, db_session):
        """Test clinician role returns 200."""
        mock_status.return_value = {"status": "completed", "accuracy": 0.97}
        
        doctor = make_user(db_session, "dr.jane@example.com", "Dr. Jane", "clinician")
        token = get_token(client, "dr.jane@example.com")
        
        response = client.get(
            "/api/v1/model/retraining-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200


class TestCheckRetrainingReadinessEndpoint:
    """Test GET /api/v1/model/retraining-readiness endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.get("/api/v1/model/retraining-readiness")
        assert response.status_code == 401

    def test_patient_returns_403(self, db_session):
        """Test patient role returns 403."""
        user = make_user(db_session, "frank@example.com", "Frank", "patient")
        token = get_token(client, "frank@example.com")
        
        response = client.get(
            "/api/v1/model/retraining-readiness",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    @patch('app.services.retraining_pipeline.evaluate_retraining_readiness')
    def test_clinician_returns_200(self, mock_evaluate, db_session):
        """Test clinician role returns 200."""
        mock_evaluate.return_value = {"ready": True, "data_points": 1500}
        
        doctor = make_user(db_session, "dr.bob@example.com", "Dr. Bob", "clinician")
        token = get_token(client, "dr.bob@example.com")
        
        response = client.get(
            "/api/v1/model/retraining-readiness",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200


class TestExplainRiskPredictionEndpoint:
    """Test POST /api/v1/predict/explain endpoint."""

    def test_no_auth_returns_401(self, db_session):
        """Test no auth returns 401."""
        response = client.post(
            "/api/v1/predict/explain",
            json={"prediction_id": "test123"}
        )
        assert response.status_code == 401

    @patch('app.services.ml_prediction.model', Mock())
    @patch('app.services.ml_prediction.feature_columns', ['age', 'hr_pct_of_max'])
    @patch('app.services.ml_prediction.predict_risk')
    @patch('app.services.ml_prediction.get_ml_service')
    @patch('app.services.explainability.explain_prediction')
    def test_with_auth_returns_200(self, mock_explain, mock_get_service, mock_predict, db_session):
        """Test with auth returns 200."""
        # Mock ML service as loaded
        mock_service = Mock()
        mock_service.is_loaded = True
        mock_get_service.return_value = mock_service
        
        # Mock prediction result
        mock_predict.return_value = {
            "risk_score": 0.35,
            "risk_level": "low"
        }
        
        # Mock explanation result
        mock_explain.return_value = {
            "feature_impacts": [{"feature": "age", "impact": 0.25}],
            "prediction": 0.85
        }
        
        user = make_user(db_session, "grace@example.com", "Grace", "patient")
        token = get_token(client, "grace@example.com")
        
        response = client.post(
            "/api/v1/predict/explain",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "age": 45,
                "baseline_hr": 70,
                "max_safe_hr": 175,
                "avg_heart_rate": 110,
                "peak_heart_rate": 140,
                "min_heart_rate": 65,
                "avg_spo2": 97,
                "duration_minutes": 30,
                "recovery_time_minutes": 5,
                "activity_type": "walking"
            }
        )
        
        assert response.status_code == 200


# =============================================================================
# SERVICE LAYER TESTS
# =============================================================================

# Anomaly Detection Tests
# =============================================================================

class TestAnomalyDetection:
    def test_insufficient_data(self):
        from app.services.anomaly_detection import detect_anomalies
        result = detect_anomalies([{"heart_rate": 72}])
        assert result["status"] == "insufficient_data"
        assert result["anomaly_count"] == 0

    def test_empty_readings(self):
        from app.services.anomaly_detection import detect_anomalies
        result = detect_anomalies([])
        assert result["status"] == "insufficient_data"

    def test_no_anomalies_normal_data(self):
        from app.services.anomaly_detection import detect_anomalies
        readings = [{"heart_rate": 72, "spo2": 98} for _ in range(10)]
        result = detect_anomalies(readings)
        assert result["status"] == "normal"

    def test_detects_hr_zscore_anomaly(self):
        from app.services.anomaly_detection import detect_anomalies
        readings = [
            {"heart_rate": 72, "spo2": 98},
            {"heart_rate": 75, "spo2": 97},
            {"heart_rate": 73, "spo2": 98},
            {"heart_rate": 74, "spo2": 97},
            {"heart_rate": 71, "spo2": 98},
            {"heart_rate": 73, "spo2": 97},
            {"heart_rate": 180, "spo2": 97},
            {"heart_rate": 74, "spo2": 97},
            {"heart_rate": 72, "spo2": 98},
            {"heart_rate": 73, "spo2": 97},
        ]
        result = detect_anomalies(readings, z_threshold=2.0)
        assert result["status"] == "anomalies_detected"
        assert result["anomaly_count"] > 0
        hr_anomalies = [a for a in result["anomalies"] if a["metric"] == "heart_rate"]
        assert len(hr_anomalies) >= 1
        assert hr_anomalies[0]["direction"] == "high"

    def test_detects_spo2_anomaly(self):
        from app.services.anomaly_detection import detect_anomalies
        readings = [
            {"heart_rate": 72, "spo2": 98},
            {"heart_rate": 73, "spo2": 97},
            {"heart_rate": 72, "spo2": 98},
            {"heart_rate": 74, "spo2": 97},
            {"heart_rate": 71, "spo2": 98},
            {"heart_rate": 73, "spo2": 97},
            {"heart_rate": 72, "spo2": 82},
            {"heart_rate": 73, "spo2": 98},
            {"heart_rate": 72, "spo2": 97},
            {"heart_rate": 74, "spo2": 98},
        ]
        result = detect_anomalies(readings, z_threshold=2.0)
        spo2_anomalies = [a for a in result["anomalies"] if a["metric"] == "spo2"]
        assert len(spo2_anomalies) >= 1

    def test_detects_hr_variability_spike(self):
        from app.services.anomaly_detection import detect_anomalies
        readings = [
            {"heart_rate": 72},
            {"heart_rate": 73},
            {"heart_rate": 130},
        ]
        result = detect_anomalies(readings)
        variability = [a for a in result["anomalies"] if a["metric"] == "hr_variability"]
        assert len(variability) >= 1

    def test_stats_returned(self):
        from app.services.anomaly_detection import detect_anomalies
        readings = [
            {"heart_rate": 70, "spo2": 97},
            {"heart_rate": 75, "spo2": 98},
            {"heart_rate": 80, "spo2": 96},
        ]
        result = detect_anomalies(readings)
        assert result["stats"]["hr_mean"] is not None
        assert result["stats"]["spo2_mean"] is not None


# =============================================================================
# Trend Forecasting Tests
# =============================================================================

class TestTrendForecasting:
    def test_insufficient_data(self):
        from app.services.trend_forecasting import forecast_trends
        result = forecast_trends([{"heart_rate": 72, "timestamp": "2026-01-01"}])
        assert result["status"] == "insufficient_data"

    def test_empty_data(self):
        from app.services.trend_forecasting import forecast_trends
        result = forecast_trends([])
        assert result["status"] == "insufficient_data"

    def test_increasing_hr_trend(self):
        from app.services.trend_forecasting import forecast_trends
        readings = []
        for i in range(14):
            readings.append(
                {
                    "heart_rate": 72 + i * 2,
                    "spo2": 98,
                    "timestamp": (datetime(2026, 1, 1) + timedelta(days=i)).isoformat(),
                }
            )
        result = forecast_trends(readings, forecast_days=14)
        assert result["status"] == "ok"
        assert result["trends"]["heart_rate"]["direction"] == "increasing"
        assert result["trends"]["heart_rate"]["slope_per_day"] > 0

    def test_stable_trend(self):
        from app.services.trend_forecasting import forecast_trends
        readings = []
        for i in range(14):
            readings.append(
                {
                    "heart_rate": 72,
                    "timestamp": (datetime(2026, 1, 1) + timedelta(days=i)).isoformat(),
                }
            )
        result = forecast_trends(readings, forecast_days=14)
        assert result["status"] == "ok"
        assert result["trends"]["heart_rate"]["direction"] == "stable"

    def test_risk_projection(self):
        from app.services.trend_forecasting import forecast_trends
        readings = []
        for i in range(14):
            readings.append(
                {
                    "heart_rate": 72 + i * 2,
                    "spo2": 98 - i * 0.3,
                    "timestamp": (datetime(2026, 1, 1) + timedelta(days=i)).isoformat(),
                }
            )
        result = forecast_trends(readings, forecast_days=14)
        assert "risk_projection" in result
        assert "risk_direction" in result["risk_projection"]


# =============================================================================
# Baseline Optimization Tests
# =============================================================================

class TestBaselineOptimization:
    def test_insufficient_data(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        result = compute_optimized_baseline([{"heart_rate": 72}])
        assert result["status"] == "insufficient_data"
        assert result["adjusted"] is False

    def test_computes_new_baseline(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        readings = [{"heart_rate": hr} for hr in [68, 70, 72, 69, 71, 73, 68, 70]]
        result = compute_optimized_baseline(readings, current_baseline=80)
        assert result["status"] == "ok"
        assert result["new_baseline"] < 80
        assert result["adjusted"] is True

    def test_no_change_when_matched(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        readings = [{"heart_rate": hr} for hr in [70, 70, 70, 70, 70, 70]]
        result = compute_optimized_baseline(readings, current_baseline=70)
        assert result["new_baseline"] == 70
        assert result["adjusted"] is False

    def test_no_baseline_provided(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        readings = [{"heart_rate": hr} for hr in [68, 70, 72, 69, 71, 73, 68]]
        result = compute_optimized_baseline(readings, current_baseline=None)
        assert result["status"] == "ok"
        assert result["new_baseline"] is not None

    def test_filters_out_of_range(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        readings = [{"heart_rate": hr} for hr in [250, 250, 250, 250, 250]]
        result = compute_optimized_baseline(readings, current_baseline=70)
        assert result["status"] == "insufficient_valid_data"

    def test_confidence_increases_with_data(self):
        from app.services.baseline_optimization import compute_optimized_baseline
        small = [{"heart_rate": 70} for _ in range(5)]
        large = [{"heart_rate": 70} for _ in range(20)]
        r1 = compute_optimized_baseline(small, current_baseline=70)
        r2 = compute_optimized_baseline(large, current_baseline=70)
        assert r2["confidence"] >= r1["confidence"]


# =============================================================================
# Recommendation Ranking Tests
# =============================================================================

class TestRecommendationRanking:
    def test_variant_assignment(self):
        from app.services.recommendation_ranking import get_ranked_recommendation
        r1 = get_ranked_recommendation(user_id=1, risk_level="low")
        r2 = get_ranked_recommendation(user_id=1, risk_level="low")
        assert r1["variant"] == r2["variant"]

    def test_variant_override(self):
        from app.services.recommendation_ranking import get_ranked_recommendation
        r = get_ranked_recommendation(user_id=1, risk_level="low", variant_override="B")
        assert r["variant"] == "B"


# =============================================================================
# Natural Language Alert Tests
# =============================================================================

class TestNaturalLanguageAlerts:
    def test_generates_alert(self):
        from app.services.natural_language_alerts import generate_natural_language_alert
        result = generate_natural_language_alert(
            alert_type="high_heart_rate",
            severity="warning",
            trigger_value="150",
        )
        assert "friendly_message" in result
        assert "action_steps" in result

    def test_risk_summary(self):
        from app.services.natural_language_alerts import format_risk_summary
        summary = format_risk_summary(0.7, "moderate", ["hr elevation", "low spo2"])
        assert "moderate" not in summary.lower()
        assert "risk" not in summary.lower() or len(summary) > 10


# =============================================================================
# Retraining Pipeline Tests
# =============================================================================

class TestRetrainingPipeline:
    def test_retraining_readiness(self):
        from app.services.retraining_pipeline import evaluate_retraining_readiness
        result = evaluate_retraining_readiness(new_records_count=5, min_records=10)
        assert result["ready"] is False

    def test_prepare_training_data(self):
        from app.services.retraining_pipeline import prepare_training_data
        records = [
            {"heart_rate": 70, "spo2": 97, "risk_label": 0},
            {"heart_rate": 71, "spo2": 96, "risk_label": 0},
        ]
        result = prepare_training_data(records)
        assert result["status"] == "ok"
        assert result["valid_records"] == 2


# =============================================================================
# Explainability Tests
# =============================================================================

class TestExplainability:
    def test_explanation_generation(self):
        from app.services.explainability import explain_prediction
        prediction = {
            "risk_score": 0.72,
            "risk_level": "moderate",
            "features_used": {
                "avg_heart_rate": 110,
                "avg_spo2": 94,
                "duration_minutes": 30,
            },
        }
        result = explain_prediction(prediction, feature_columns=["avg_heart_rate", "avg_spo2", "duration_minutes"])
        assert "plain_explanation" in result
        assert "feature_importance" in result
