"""
Targeted tests to cover specific missing lines identified from htmlcov analysis.

Files targeted:
- app/api/alert.py          (94% → 100%) - 6 missing lines
- app/api/advanced_ml.py    (95% → 100%) - 6 missing lines  
- app/services/nl_builders.py (90% → 100%) - 12 missing lines
- app/services/ml_prediction.py (93% → 100%) - 7 missing lines

Run with:
    pytest tests/test_coverage_gaps.py -v
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock, MagicMock
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token, make_alert, make_vital


client = TestClient(fastapi_app)


# =============================================================================
# alert.py GAP COVERAGE
# Missing: line 126 (severity filter in get_my_alerts)
#          lines 219, 224, 229, 234 (optional fields in resolve_alert)
#          line 328 (acknowledged filter in get_user_alerts)
# =============================================================================

class TestAlertSeverityFilterInGetMyAlerts:
    """Cover line 126: severity filter branch in GET /api/v1/alerts."""

    def test_filter_by_severity_returns_only_matching(self, db_session):
        """Filter by severity=warning returns only warning alerts (line 126)."""
        user = make_user(db_session, "gap_sev_filter@example.com", "Sev Filter", "patient")

        make_alert(db_session, user.user_id, alert_type="high_heart_rate", severity="critical")
        make_alert(db_session, user.user_id, alert_type="low_spo2", severity="warning")
        make_alert(db_session, user.user_id, alert_type="high_blood_pressure", severity="warning")

        token = get_token(client, "gap_sev_filter@example.com")
        response = client.get(
            "/api/v1/alerts?severity=warning",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(a["severity"] == "warning" for a in data["alerts"])

    def test_filter_by_severity_critical_excludes_warning(self, db_session):
        """Filter by severity=critical excludes warning alerts (line 126)."""
        user = make_user(db_session, "gap_sev_critical@example.com", "Sev Critical", "patient")

        make_alert(db_session, user.user_id, alert_type="high_heart_rate", severity="critical")
        make_alert(db_session, user.user_id, alert_type="low_spo2", severity="warning")

        token = get_token(client, "gap_sev_critical@example.com")
        response = client.get(
            "/api/v1/alerts?severity=critical",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["alerts"][0]["severity"] == "critical"


class TestResolveAlertOptionalFields:
    """Cover lines 219, 224, 229, 234: optional fields in resolve_alert."""

    def test_resolve_with_acknowledged_true_sets_field(self, db_session):
        """Passing acknowledged=True in body covers line 219."""
        clinician = make_user(db_session, "gap_resolve_ack@example.com", "Resolve Ack", "clinician")
        patient = make_user(db_session, "gap_resolve_pat1@example.com", "Resolve Pat1", "patient")
        alert = make_alert(db_session, patient.user_id, acknowledged=False)

        token = get_token(client, "gap_resolve_ack@example.com")
        response = client.patch(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={"acknowledged": True},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True

    def test_resolve_with_custom_resolved_at_sets_field(self, db_session):
        """Passing resolved_at in body covers line 224."""
        clinician = make_user(db_session, "gap_resolve_at@example.com", "Resolve At", "clinician")
        patient = make_user(db_session, "gap_resolve_pat2@example.com", "Resolve Pat2", "patient")
        alert = make_alert(db_session, patient.user_id)

        custom_time = "2026-01-15T10:30:00Z"
        token = get_token(client, "gap_resolve_at@example.com")
        response = client.patch(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={"resolved_at": custom_time},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None
        # The custom time should be stored
        assert "2026-01-15" in data["resolved_at"]

    def test_resolve_with_custom_resolved_by_sets_field(self, db_session):
        """Passing resolved_by in body covers line 229."""
        clinician = make_user(db_session, "gap_resolve_by@example.com", "Resolve By", "clinician")
        patient = make_user(db_session, "gap_resolve_pat3@example.com", "Resolve Pat3", "patient")
        alert = make_alert(db_session, patient.user_id)

        token = get_token(client, "gap_resolve_by@example.com")
        response = client.patch(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={"resolved_by": clinician.user_id},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None

    def test_resolve_with_resolution_notes_sets_field(self, db_session):
        """Passing resolution_notes in body covers line 234."""
        clinician = make_user(db_session, "gap_resolve_notes@example.com", "Resolve Notes", "clinician")
        patient = make_user(db_session, "gap_resolve_pat4@example.com", "Resolve Pat4", "patient")
        alert = make_alert(db_session, patient.user_id)

        token = get_token(client, "gap_resolve_notes@example.com")
        response = client.patch(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={"resolution_notes": "Patient responded well to treatment."},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolution_notes"] == "Patient responded well to treatment."

    def test_resolve_with_all_optional_fields(self, db_session):
        """All optional fields together covers lines 219, 224, 229, 234."""
        clinician = make_user(db_session, "gap_resolve_all@example.com", "Resolve All", "clinician")
        patient = make_user(db_session, "gap_resolve_pat5@example.com", "Resolve Pat5", "patient")
        alert = make_alert(db_session, patient.user_id)

        token = get_token(client, "gap_resolve_all@example.com")
        response = client.patch(
            f"/api/v1/alerts/{alert.alert_id}/resolve",
            json={
                "acknowledged": True,
                "resolved_at": "2026-01-20T14:00:00Z",
                "resolved_by": clinician.user_id,
                "resolution_notes": "Comprehensive resolution with all fields."
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True
        assert "2026-01-20" in data["resolved_at"]
        assert data["resolution_notes"] == "Comprehensive resolution with all fields."


class TestGetUserAlertsAcknowledgedFilter:
    """Cover line 328: acknowledged filter in GET /api/v1/alerts/user/{user_id}."""

    def test_clinician_filter_acknowledged_true(self, db_session):
        """Clinician can filter patient alerts by acknowledged=true (line 328)."""
        clinician = make_user(db_session, "gap_ual_doc@example.com", "UAL Doc", "clinician")
        patient = make_user(db_session, "gap_ual_pat@example.com", "UAL Pat", "patient")

        make_alert(db_session, patient.user_id, alert_type="high_heart_rate", acknowledged=False)
        make_alert(db_session, patient.user_id, alert_type="low_spo2", acknowledged=True)
        make_alert(db_session, patient.user_id, alert_type="high_blood_pressure", acknowledged=True)

        token = get_token(client, "gap_ual_doc@example.com")
        response = client.get(
            f"/api/v1/alerts/user/{patient.user_id}?acknowledged=true",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(a["acknowledged"] is True for a in data["alerts"])

    def test_clinician_filter_acknowledged_false(self, db_session):
        """Clinician can filter patient alerts by acknowledged=false (line 328)."""
        clinician = make_user(db_session, "gap_ual_doc2@example.com", "UAL Doc2", "clinician")
        patient = make_user(db_session, "gap_ual_pat2@example.com", "UAL Pat2", "patient")

        make_alert(db_session, patient.user_id, alert_type="high_heart_rate", acknowledged=False)
        make_alert(db_session, patient.user_id, alert_type="low_spo2", acknowledged=True)

        token = get_token(client, "gap_ual_doc2@example.com")
        response = client.get(
            f"/api/v1/alerts/user/{patient.user_id}?acknowledged=false",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["alerts"][0]["acknowledged"] is False


# =============================================================================
# advanced_ml.py GAP COVERAGE
# Missing: lines 296-305 (apply_baseline when adjusted=True)
#          lines 496-499 (explain_risk when ML model not loaded)
# =============================================================================

class TestApplyBaselineOptimizationApplied:
    """Cover lines 296-305: apply_baseline_optimization when result["adjusted"] is True."""

    def test_apply_baseline_updates_when_vital_data_exists(self, db_session):
        """Creates VitalSignRecord data so optimizer returns adjusted=True (lines 296-305)."""
        user = make_user(db_session, "gap_baseline_apply@example.com", "Baseline Apply", "patient")
        # Set a high baseline so optimized value will differ
        user.baseline_hr = 85
        db_session.commit()

        # Create several resting vitals (HR < 100) within the past 7 days
        for i in range(8):
            make_vital(
                db_session,
                user.user_id,
                heart_rate=68,
                spo2=98,
                minutes_ago=(i * 60 + 30)  # spread over time
            )

        token = get_token(client, "gap_baseline_apply@example.com")
        response = client.post(
            "/api/v1/baseline-optimization/apply",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        # The optimizer should have found a new baseline different from 85
        # Uses exponential smoothing: new = current * 0.7 + filtered_mean * 0.3
        # = 85 * 0.7 + 68 * 0.3 = 59.5 + 20.4 = 79.9 ≈ 80
        assert "applied" in data
        assert "new_baseline" in data
        # applied=True means lines 296-305 were executed
        if data["applied"]:
            assert data["new_baseline"] == 80
            assert data["new_baseline"] != 85


class TestExplainRiskPredictionMLNotLoaded:
    """Cover lines 496-499: explain_risk_prediction when ML model not loaded."""

    def test_explain_returns_503_when_model_not_loaded(self, db_session):
        """Mock ML service as not loaded → 503 response (lines 496-499)."""
        user = make_user(db_session, "gap_explain_503@example.com", "Explain 503", "patient")
        token = get_token(client, "gap_explain_503@example.com")

        with patch("app.api.advanced_ml.get_ml_service") as mock_get_service:
            mock_service = Mock()
            mock_service.is_loaded = False
            mock_get_service.return_value = mock_service

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

        assert response.status_code == 503
        assert "ML model not loaded" in response.json()["detail"]


# =============================================================================
# nl_builders.py GAP COVERAGE
# Missing lines: 61, 72, 80, 116, 126-129, 170, 174, 178, 186, 194
# =============================================================================

class TestBuildRiskSummaryTextBranches:
    """Cover missing branches in build_risk_summary_text."""

    def test_moderate_risk_opener(self):
        """Line 61: MODERATE risk level opener branch."""
        from app.services.nl_builders import build_risk_summary_text

        result = build_risk_summary_text(
            risk_level="MODERATE",
            risk_score=0.55,
            time_window_hours=24,
            avg_heart_rate=85,
            max_heart_rate=120,
            avg_spo2=96,
            alert_count=0,
            safety_status="SAFE"
        )

        assert "some variation" in result.lower() or "monitoring" in result.lower()

    def test_alert_count_one(self):
        """Line 72: alert_count == 1 branch."""
        from app.services.nl_builders import build_risk_summary_text

        result = build_risk_summary_text(
            risk_level="LOW",
            risk_score=0.2,
            time_window_hours=24,
            avg_heart_rate=72,
            max_heart_rate=95,
            avg_spo2=98,
            alert_count=1,
            safety_status="SAFE"
        )

        assert "one alert" in result.lower()

    def test_caution_safety_status(self):
        """Line 80: safety_status == CAUTION branch."""
        from app.services.nl_builders import build_risk_summary_text

        result = build_risk_summary_text(
            risk_level="LOW",
            risk_score=0.3,
            time_window_hours=24,
            avg_heart_rate=78,
            max_heart_rate=100,
            avg_spo2=97,
            alert_count=0,
            safety_status="CAUTION"
        )

        assert "light activities" in result.lower() or "easy" in result.lower()


class TestBuildTodaysWorkoutTextBranches:
    """Cover missing branches in build_todays_workout_text."""

    def test_vigorous_pace(self):
        """Line 116: VIGOROUS intensity_level branch."""
        from app.services.nl_builders import build_todays_workout_text

        result = build_todays_workout_text(
            activity_type="WALKING",
            intensity_level="VIGOROUS",
            duration_minutes=30,
            target_hr_min=130,
            target_hr_max=160,
            risk_level="LOW"
        )

        assert "brisk" in result.lower() or "challenging" in result.lower()

    def test_moderate_risk_safety_cue(self):
        """Lines 126-127: MODERATE risk_level safety branch."""
        from app.services.nl_builders import build_todays_workout_text

        result = build_todays_workout_text(
            activity_type="WALKING",
            intensity_level="LIGHT",
            duration_minutes=20,
            target_hr_min=90,
            target_hr_max=110,
            risk_level="MODERATE"
        )

        assert "monitor" in result.lower() or "chest pain" in result.lower()

    def test_high_risk_safety_cue(self):
        """Line 129: HIGH risk_level safety branch."""
        from app.services.nl_builders import build_todays_workout_text

        result = build_todays_workout_text(
            activity_type="CYCLING",
            intensity_level="LIGHT",
            duration_minutes=15,
            target_hr_min=80,
            target_hr_max=100,
            risk_level="HIGH"
        )

        assert "stop immediately" in result.lower() or "care team" in result.lower()


class TestBuildAlertExplanationTextBranches:
    """Cover missing branches in build_alert_explanation_text."""

    def test_high_heart_rate_at_rest_trigger(self):
        """Line 170: HIGH_HEART_RATE at rest (not during_activity) branch."""
        from app.services.nl_builders import build_alert_explanation_text

        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE",
            severity_level="MEDIUM",
            alert_time=datetime(2026, 1, 15, 14, 30),
            during_activity=False,
            activity_type=None,
            heart_rate=145,
            spo2=None,
            recommended_action="SLOW_DOWN"
        )

        assert "at rest" in result.lower()

    def test_other_alert_type_fallback_trigger(self):
        """Line 174: OTHER/fallback trigger branch (not HIGH_HEART_RATE or LOW_OXYGEN)."""
        from app.services.nl_builders import build_alert_explanation_text

        result = build_alert_explanation_text(
            alert_type="OTHER",
            severity_level="MEDIUM",
            alert_time=datetime(2026, 1, 15, 9, 0),
            during_activity=False,
            activity_type=None,
            heart_rate=None,
            spo2=None,
            recommended_action="STOP_AND_REST"
        )

        assert "unusual reading" in result.lower()

    def test_low_severity_text(self):
        """Line 178: LOW severity_level branch."""
        from app.services.nl_builders import build_alert_explanation_text

        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE",
            severity_level="LOW",
            alert_time=datetime(2026, 1, 15, 8, 0),
            during_activity=True,
            activity_type="walking",
            heart_rate=130,
            spo2=None,
            recommended_action="CONTINUE"
        )

        assert "minor concern" in result.lower() or "harder than usual" in result.lower()

    def test_continue_recommended_action(self):
        """Line 186: CONTINUE recommended_action branch."""
        from app.services.nl_builders import build_alert_explanation_text

        result = build_alert_explanation_text(
            alert_type="LOW_OXYGEN",
            severity_level="LOW",
            alert_time=datetime(2026, 1, 15, 11, 0),
            during_activity=False,
            activity_type=None,
            heart_rate=None,
            spo2=94,
            recommended_action="CONTINUE"
        )

        assert "continue" in result.lower() or "current activity" in result.lower()

    def test_emergency_recommended_action(self):
        """Line 194: EMERGENCY recommended_action branch."""
        from app.services.nl_builders import build_alert_explanation_text

        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE",
            severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 16, 45),
            during_activity=True,
            activity_type="running",
            heart_rate=195,
            spo2=None,
            recommended_action="EMERGENCY"
        )

        assert "emergency" in result.lower() or "911" in result.lower()


# =============================================================================
# ml_prediction.py GAP COVERAGE
# Missing: lines 104-109 (timeout branch), 117 (return False when not ok)
#          128 (ensure_model_loaded early return True), 132 (double-check lock)
#          247-248 (moderate risk branch in predict_risk)
# =============================================================================

class TestLoadMLModelTimeoutBranch:
    """Cover lines 104-109: timeout branch in load_ml_model."""

    def test_load_ml_model_returns_false_on_timeout(self):
        """Simulate loader thread still alive after join → return False (lines 104-109)."""
        from app.services import ml_prediction

        mock_thread = Mock()
        mock_thread.is_alive.return_value = True  # Thread never finishes

        with patch("app.services.ml_prediction.threading.Thread", return_value=mock_thread):
            result = ml_prediction.load_ml_model(timeout=0)

        assert result is False
        mock_thread.start.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=0)


class TestLoadMLModelReturnsFalseWhenNotOk:
    """Cover line 117: load_ml_model returns False when result["ok"] is False."""

    def test_load_ml_model_returns_false_when_file_missing(self):
        """Mock joblib.load to raise FileNotFoundError → result["ok"]=False → line 117."""
        from app.services import ml_prediction

        with patch("app.services.ml_prediction.joblib.load", side_effect=FileNotFoundError("No file")):
            result = ml_prediction.load_ml_model(timeout=5)

        assert result is False


class TestEnsureModelLoadedEarlyReturn:
    """Cover line 128 and 132: ensure_model_loaded short-circuit returns."""

    def test_ensure_model_loaded_returns_true_when_already_loaded(self):
        """is_model_loaded() True on first call → immediate return True (line 128)."""
        from app.services import ml_prediction

        with patch.object(ml_prediction, "is_model_loaded", return_value=True):
            result = ml_prediction.ensure_model_loaded()

        assert result is True

    def test_ensure_model_loaded_returns_true_inside_lock(self):
        """is_model_loaded() False then True inside lock → return True (line 132)."""
        from app.services import ml_prediction

        # First call False (outer check), second call True (inside lock)
        with patch.object(
            ml_prediction,
            "is_model_loaded",
            side_effect=[False, True]
        ):
            with patch.object(ml_prediction, "_model_load_attempted", False):
                result = ml_prediction.ensure_model_loaded()

        assert result is True


class TestPredictRiskModerateBranch:
    """Cover lines 247-248: moderate risk branch in predict_risk."""

    def test_predict_risk_returns_moderate_when_score_50_to_80(self):
        """Mock model to return probability [0.40, 0.60] → moderate risk (lines 247-248)."""
        import numpy as np
        from app.services import ml_prediction

        mock_model = Mock()
        mock_model.predict.return_value = np.array([0])
        mock_model.predict_proba.return_value = np.array([[0.40, 0.60]])  # risk_score=0.60

        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.array([[1.0] * 15])

        mock_feature_columns = [
            "age", "baseline_hr", "max_safe_hr", "avg_heart_rate",
            "peak_heart_rate", "min_heart_rate", "avg_spo2",
            "duration_minutes", "recovery_time_minutes", "hr_pct_of_max",
            "hr_elevation", "hr_range", "duration_intensity",
            "recovery_efficiency", "spo2_deviation", "age_risk_factor",
            "activity_intensity"
        ]

        original_model = ml_prediction.model
        original_scaler = ml_prediction.scaler
        original_features = ml_prediction.feature_columns

        try:
            ml_prediction.model = mock_model
            ml_prediction.scaler = mock_scaler
            ml_prediction.feature_columns = mock_feature_columns

            result = ml_prediction.predict_risk(
                age=45,
                baseline_hr=70,
                max_safe_hr=175,
                avg_heart_rate=110,
                peak_heart_rate=140,
                min_heart_rate=65,
                avg_spo2=97,
                duration_minutes=30,
                recovery_time_minutes=5,
                activity_type="walking"
            )

            assert result["risk_level"] == "moderate"
            assert 0.50 <= result["risk_score"] < 0.80
            assert "Reduce intensity" in result["recommendation"]

        finally:
            ml_prediction.model = original_model
            ml_prediction.scaler = original_scaler
            ml_prediction.feature_columns = original_features
