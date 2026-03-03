"""
Final coverage gap tests to reach 100%.

Targets remaining uncovered lines across:
- app/api/auth.py          (authenticate_user deactivated/no-auth-cred, confirm_password_reset edges)
- app/api/user.py          (admin_reset_password success, empty medical update, profile age=None)
- app/api/predict.py       (predict_risk exception, _build_drivers elevated avg + sustained, get_recommendation branches)
- app/api/vital_signs.py   (BP alert with diastolic=None fallback)
- app/api/messages.py      (mark_message_read already read)
- app/services/ml_prediction.py     (engineer_features zero guards)
- app/services/trend_forecasting.py (_linear_forecast denominator=0)
- app/services/natural_language_alerts.py (missing name/trigger_value)
- app/services/explainability.py    (neutral feature direction, empty explanation)
- app/services/nl_builders.py       (singular diffs, worsening trend, unknown activity)

Run with:
    pytest tests/test_final_coverage.py -v
"""

import asyncio
import base64
import importlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import get_db
from app.main import app as fastapi_app
from tests.helpers import make_user, get_token, make_vital, make_alert, make_activity


client = TestClient(fastapi_app)


# =============================================================================
# auth.py — authenticate_user: deactivated user login attempt
# =============================================================================

class TestAuthenticateUserDeactivated:
    """Cover authenticate_user when user.is_active is False."""

    def test_login_deactivated_user_returns_403(self, db_session):
        """Deactivated user attempting login gets 403."""
        user = make_user(db_session, "deact_login@example.com", "Deact Login", "patient")
        user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/v1/login",
            data={"username": "deact_login@example.com", "password": "TestPass123"}
        )

        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


class TestAuthenticateUserNoAuthCred:
    """Cover authenticate_user when user has no auth_credential."""

    def test_login_user_without_auth_credential_returns_401(self, db_session):
        """User with no AuthCredential record gets 401."""
        from app.models.user import User, UserRole

        orphan = User(
            email="orphan_login@example.com",
            full_name="Orphan Login",
            role=UserRole.PATIENT,
            is_active=True,
        )
        db_session.add(orphan)
        db_session.commit()

        response = client.post(
            "/api/v1/login",
            data={"username": "orphan_login@example.com", "password": "TestPass123"}
        )

        assert response.status_code == 401
        assert "not configured" in response.json()["detail"].lower()


# =============================================================================
# auth.py — confirm_password_reset edge branches
# =============================================================================

class TestConfirmPasswordResetEdges:
    """Cover confirm_password_reset edge cases."""

    def test_reset_token_missing_user_id_returns_400(self, db_session):
        """Reset token with no user_id in payload returns 400."""
        from app.services.auth_service import AuthService
        svc = AuthService()
        token = svc.create_access_token(
            data={"type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )

        response = client.post(
            "/api/v1/reset-password/confirm",
            json={"token": token, "new_password": "NewPass123"}
        )

        assert response.status_code == 400
        assert "Invalid token payload" in response.json()["detail"]

    def test_reset_token_user_not_found_returns_404(self, db_session):
        """Reset token referencing non-existent user returns 404."""
        from app.services.auth_service import AuthService
        svc = AuthService()
        token = svc.create_access_token(
            data={"user_id": 999999, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )

        response = client.post(
            "/api/v1/reset-password/confirm",
            json={"token": token, "new_password": "NewPass123"}
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_reset_token_user_no_auth_cred_returns_404(self, db_session):
        """Reset token for user without auth credential returns 404."""
        from app.models.user import User, UserRole
        from app.services.auth_service import AuthService

        orphan = User(
            email="orphan_reset@example.com",
            full_name="Orphan Reset",
            role=UserRole.PATIENT,
            is_active=True,
        )
        db_session.add(orphan)
        db_session.commit()

        svc = AuthService()
        token = svc.create_access_token(
            data={"user_id": orphan.user_id, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )

        response = client.post(
            "/api/v1/reset-password/confirm",
            json={"token": token, "new_password": "NewPass123"}
        )

        assert response.status_code == 404
        assert "authentication not configured" in response.json()["detail"].lower()


# =============================================================================
# user.py — admin_reset_password SUCCESS path
# =============================================================================

class TestAdminResetPasswordSuccess:
    """Cover the success path of admin reset password."""

    def test_admin_resets_password_successfully(self, db_session):
        """Admin sets a temporary password — success path."""
        admin = make_user(db_session, "admin_rp@example.com", "Admin RP", "admin")
        patient = make_user(db_session, "patient_rp@example.com", "Patient RP", "patient")
        admin_token = get_token(client, "admin_rp@example.com")

        response = client.post(
            f"/api/v1/users/{patient.user_id}/reset-password",
            json={"new_password": "NewTemp1234"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert "Temporary password set" in response.json()["message"]

        # Verify new password works
        login_resp = client.post(
            "/api/v1/login",
            data={"username": "patient_rp@example.com", "password": "NewTemp1234"}
        )
        assert login_resp.status_code == 200

    def test_admin_reset_password_too_short_returns_400(self, db_session):
        """Password shorter than 8 characters returns 400."""
        admin = make_user(db_session, "admin_rp2@example.com", "Admin RP2", "admin")
        patient = make_user(db_session, "patient_rp2@example.com", "Patient RP2", "patient")
        admin_token = get_token(client, "admin_rp2@example.com")

        response = client.post(
            f"/api/v1/users/{patient.user_id}/reset-password",
            json={"new_password": "Ab1"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]


# =============================================================================
# user.py — get_my_profile when age is None (hr_zones = None)
# =============================================================================

class TestMyProfileAgeNone:
    """Cover get_my_profile when user has no age set."""

    def test_profile_without_age_returns_null_hr_zones(self, db_session):
        """User with age=None should get null heart_rate_zones."""
        user = make_user(db_session, "no_age_profile@example.com", "No Age", "patient")
        user.age = None
        db_session.commit()

        token = get_token(client, "no_age_profile@example.com")
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["heart_rate_zones"] is None


# =============================================================================
# user.py — update_medical_history with empty body
# =============================================================================

class TestUpdateMedicalHistoryEmpty:
    """Cover update_medical_history when no fields are set."""

    def test_empty_medical_update_returns_success(self, db_session):
        """Empty medical history update still returns success."""
        user = make_user(db_session, "empty_med@example.com", "Empty Med", "patient")
        token = get_token(client, "empty_med@example.com")

        response = client.put(
            "/api/v1/users/me/medical-history",
            json={},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "updated" in response.json()["message"].lower()


# =============================================================================
# predict.py — predict_risk exception path (500)
# =============================================================================

class TestPredictRiskException:
    """Cover predict_risk when service.predict_risk raises an exception."""

    def test_predict_risk_service_exception_returns_500(self, db_session):
        """If ML service raises during prediction, return 500."""
        user = make_user(db_session, "predict_err@example.com", "Predict Err", "patient")
        token = get_token(client, "predict_err@example.com")

        mock_service = Mock()
        mock_service.is_loaded = True
        mock_service.predict_risk.side_effect = RuntimeError("Model crashed")

        with patch("app.api.predict.get_ml_service", return_value=mock_service):
            response = client.post(
                "/api/v1/predict/risk",
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
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 500
        assert "Prediction failed" in response.json()["detail"]


# =============================================================================
# predict.py — _build_drivers: elevated avg HR, sustained high intensity
# =============================================================================

class TestBuildDriversAdditional:
    """Cover remaining _build_drivers branches."""

    def test_build_drivers_elevated_avg_heartrate(self, db_session):
        """avg - baseline >= 25 triggers elevated HR driver."""
        from app.api.predict import _build_drivers

        user = make_user(db_session, "driver_avg@example.com", "Driver Avg", "patient")
        user.baseline_hr = 70
        user.max_safe_hr = 190
        db_session.commit()

        features = {
            "peak_heart_rate": 180,  # within max_safe
            "avg_heart_rate": 100,   # 100 - 70 = 30 >= 25
            "avg_spo2": 97,
            "duration_minutes": 20,
        }

        drivers = _build_drivers(user, features)
        assert any("elevated" in d.lower() for d in drivers)

    def test_build_drivers_sustained_high_intensity(self, db_session):
        """Duration >= 45 and peak > 0.8*max_safe triggers sustained driver."""
        from app.api.predict import _build_drivers

        user = make_user(db_session, "driver_sustain@example.com", "Driver Sustain", "patient")
        user.baseline_hr = 70
        user.max_safe_hr = 180
        db_session.commit()

        features = {
            "peak_heart_rate": 170,  # 170 > 0.8*180=144  ✔
            "avg_heart_rate": 90,    # 90-70=20 <25 (no elevated HR)
            "avg_spo2": 97,
            "duration_minutes": 50,  # >=45  ✔
        }

        drivers = _build_drivers(user, features)
        assert any("sustained" in d.lower() or "long duration" in d.lower() for d in drivers)


# =============================================================================
# predict.py — get_my_risk_history: inner get_recommendation all branches
# =============================================================================

class TestRiskHistoryRecommendationBranches:
    """Cover get_recommendation inner function for all risk levels."""

    def _create_assessment(self, db, user_id, level, score):
        from app.models.risk_assessment import RiskAssessment
        ra = RiskAssessment(
            user_id=user_id,
            risk_level=level,
            risk_score=score,
            assessment_type="test",
        )
        db.add(ra)
        db.commit()
        return ra

    def test_history_includes_critical_recommendation(self, db_session):
        """Critical risk level → 'Seek immediate medical attention'."""
        user = make_user(db_session, "hist_crit@example.com", "Hist Crit", "patient")
        self._create_assessment(db_session, user.user_id, "critical", 0.95)
        token = get_token(client, "hist_crit@example.com")

        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        recs = [a["recommendation"] for a in response.json()["risk_assessments"]]
        assert any("immediate" in r.lower() for r in recs)

    def test_history_includes_high_recommendation(self, db_session):
        """High risk level → 'Contact your healthcare provider'."""
        user = make_user(db_session, "hist_high@example.com", "Hist High", "patient")
        self._create_assessment(db_session, user.user_id, "high", 0.75)
        token = get_token(client, "hist_high@example.com")

        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        recs = [a["recommendation"] for a in response.json()["risk_assessments"]]
        assert any("contact" in r.lower() or "provider" in r.lower() for r in recs)

    def test_history_includes_moderate_recommendation(self, db_session):
        """Moderate risk → 'Monitor your vitals'."""
        user = make_user(db_session, "hist_mod@example.com", "Hist Mod", "patient")
        self._create_assessment(db_session, user.user_id, "moderate", 0.55)
        token = get_token(client, "hist_mod@example.com")

        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        recs = [a["recommendation"] for a in response.json()["risk_assessments"]]
        assert any("monitor" in r.lower() for r in recs)

    def test_history_includes_low_recommendation(self, db_session):
        """Low risk → 'Continue normal activities'."""
        user = make_user(db_session, "hist_low@example.com", "Hist Low", "patient")
        self._create_assessment(db_session, user.user_id, "low", 0.15)
        token = get_token(client, "hist_low@example.com")

        response = client.get(
            "/api/v1/predict/my-risk",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        recs = [a["recommendation"] for a in response.json()["risk_assessments"]]
        assert any("continue" in r.lower() for r in recs)


# =============================================================================
# predict.py — _aggregate_session_features_from_vitals: no spo2 defaults 97
# =============================================================================

class TestAggregateNoSpo2:
    """Cover _aggregate_session_features when no spo2 values."""

    def test_no_spo2_defaults_to_97(self, db_session):
        """Vitals with spo2=None → avg_spo2 defaults to 97."""
        from app.api.predict import _aggregate_session_features_from_vitals

        user = make_user(db_session, "no_spo2@example.com", "No SpO2", "patient")
        v1 = make_vital(db_session, user.user_id, heart_rate=75, spo2=98, minutes_ago=10)
        # Manually set spo2 to None
        v1.spo2 = None
        db_session.commit()

        features = _aggregate_session_features_from_vitals([v1])

        assert features["avg_spo2"] == 97  # default


# =============================================================================
# vital_signs.py — check_vitals_for_alerts: BP with diastolic=None
# =============================================================================

class TestVitalsAlertBpDiastolicNone:
    """Cover BP alert with blood_pressure_diastolic=None fallback."""

    def test_high_bp_alert_with_null_diastolic_uses_na(self, db_session):
        """High BP alert shows N/A for diastolic when None."""
        from app.api.vital_signs import check_vitals_for_alerts
        from app.schemas.vital_signs import VitalSignCreate

        user = make_user(db_session, "bp_na@example.com", "BP NA", "patient")

        vital_data = VitalSignCreate(
            heart_rate=80,
            spo2=98,
            blood_pressure_systolic=170,    # > 160 → alert
            blood_pressure_diastolic=None,  # None → "N/A" fallback
        )

        check_vitals_for_alerts(user.user_id, vital_data, db=db_session)

        from app.models.alert import Alert
        alert = db_session.query(Alert).filter(
            Alert.user_id == user.user_id,
            Alert.alert_type == "high_blood_pressure"
        ).first()

        assert alert is not None
        assert "N/A" in alert.trigger_value


# =============================================================================
# messages.py — mark_message_read: already read → skip
# =============================================================================

class TestMarkMessageAlreadyRead:
    """Cover mark_message_read when message was already read."""

    def test_mark_already_read_message_no_error(self, db_session):
        """Re-marking an already-read message should not fail."""
        from app.models.message import Message

        sender = make_user(db_session, "msg_sender3@example.com", "Sender3", "clinician")
        receiver = make_user(db_session, "msg_receiver3@example.com", "Receiver3", "patient")

        msg = Message(
            sender_id=sender.user_id,
            receiver_id=receiver.user_id,
            content="Already read test",
            is_read=True,  # Already read
        )
        db_session.add(msg)
        db_session.commit()

        token = get_token(client, "msg_receiver3@example.com")
        response = client.post(
            f"/api/v1/messages/{msg.message_id}/read",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert msg.is_read is True


# =============================================================================
# ml_prediction.py — engineer_features: zero guards
# =============================================================================

class TestEngineerFeaturesZeroGuards:
    """Cover division-by-zero guards in engineer_features."""

    def test_max_safe_hr_zero_no_crash(self):
        """max_safe_hr=0 should not crash (guarded division)."""
        from app.services.ml_prediction import engineer_features

        features = engineer_features(
            age=45,
            baseline_hr=70,
            max_safe_hr=0,
            avg_heart_rate=110,
            peak_heart_rate=140,
            min_heart_rate=65,
            avg_spo2=97,
            duration_minutes=30,
            recovery_time_minutes=5,
            activity_type="walking"
        )

        assert isinstance(features, dict)
        assert "hr_pct_of_max" in features

    def test_duration_minutes_zero_no_crash(self):
        """duration_minutes=0 should not crash (guarded division)."""
        from app.services.ml_prediction import engineer_features

        features = engineer_features(
            age=45,
            baseline_hr=70,
            max_safe_hr=175,
            avg_heart_rate=110,
            peak_heart_rate=140,
            min_heart_rate=65,
            avg_spo2=97,
            duration_minutes=0,
            recovery_time_minutes=5,
            activity_type="walking"
        )

        assert isinstance(features, dict)
        assert "duration_intensity" in features


# =============================================================================
# trend_forecasting.py — _linear_forecast: denominator=0 (all same x)
# =============================================================================

class TestLinearForecastDenominatorZero:
    """Cover _linear_forecast when all x values are identical."""

    def test_all_same_timestamps_slope_is_zero(self):
        """When all x values are the same, slope should be 0."""
        from app.services.trend_forecasting import _linear_forecast

        # All same x values → denominator = 0 → slope = 0
        series = [(1.0, 72.0), (1.0, 73.0), (1.0, 74.0), (1.0, 71.0), (1.0, 72.0), (1.0, 73.0), (1.0, 74.0)]

        result = _linear_forecast(series, forecast_days=3)

        assert result["slope_per_day"] == 0.0


# =============================================================================
# natural_language_alerts.py — missing patient_name, missing trigger_value
# =============================================================================

class TestNLAlertsMissingFields:
    """Cover generate_natural_language_alert with missing optional fields."""

    def test_generate_alert_without_patient_name(self):
        """No patient_name → no greeting line."""
        from app.services.natural_language_alerts import generate_natural_language_alert

        result = generate_natural_language_alert(
            alert_type="high_heart_rate",
            severity="warning",
            trigger_value="185 BPM",
            patient_name=None,
        )

        assert isinstance(result, dict)
        assert "friendly_message" in result
        # No greeting when no patient_name
        assert not result["friendly_message"].startswith("Hi ")

    def test_generate_alert_without_trigger_value(self):
        """No trigger_value → generic template (no {value})."""
        from app.services.natural_language_alerts import generate_natural_language_alert

        result = generate_natural_language_alert(
            alert_type="high_heart_rate",
            severity="critical",
            trigger_value=None,
            patient_name="Alice",
        )

        assert isinstance(result, dict)
        assert "friendly_message" in result
        assert "{value}" not in result["friendly_message"]

    def test_format_risk_summary_moderate(self):
        """Moderate risk level coverage."""
        from app.services.natural_language_alerts import format_risk_summary

        result = format_risk_summary(
            risk_score=0.55,
            risk_level="moderate",
            drivers=["Elevated HR"],
        )

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# explainability.py — _generate_feature_explanation neutral, empty explain
# =============================================================================

class TestExplainabilityNeutralDirection:
    """Cover neutral direction in feature explanation."""

    def test_generate_feature_explanation_neutral(self):
        """Feature at typical value → neutral explanation."""
        from app.services.explainability import _generate_feature_explanation

        result = _generate_feature_explanation("age", 55.0, 55.0, "neutral")

        assert "typical" in result.lower() or "within" in result.lower()

    def test_generate_feature_explanation_increasing(self):
        """Feature above typical → increasing explanation."""
        from app.services.explainability import _generate_feature_explanation

        result = _generate_feature_explanation("age", 65.0, 55.0, "increasing")

        assert "higher" in result.lower()

    def test_explain_prediction_empty_features_used(self):
        """explain_prediction with empty features_used → fallback explanation."""
        from app.services.explainability import explain_prediction

        result = explain_prediction(
            prediction_result={
                "risk_score": 0.3,
                "risk_level": "low",
                "features_used": {},
            },
            feature_columns=[],
            model=None,
        )

        assert "plain_explanation" in result
        assert isinstance(result["plain_explanation"], str)


# =============================================================================
# nl_builders.py — singular diffs, worsening trend, unknown activity
# =============================================================================

class TestNLBuildersSingularAndWorsening:
    """Cover singular diff text, worsening trend, unknown activity."""

    def test_progress_summary_singular_workout(self):
        """1 workout diff → singular word."""
        from app.services.nl_builders import build_progress_summary_text, compute_trend
        from app.schemas.nl import Period, Trend
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        current = Period(
            start=now - timedelta(days=7), end=now,
            workout_count=3, total_active_minutes=90,
            avg_risk_level="LOW", time_in_safe_zone_minutes=80,
            time_above_safe_zone_minutes=10, alert_count=1,
        )
        previous = Period(
            start=now - timedelta(days=14), end=now - timedelta(days=7),
            workout_count=2, total_active_minutes=60,
            avg_risk_level="LOW", time_in_safe_zone_minutes=55,
            time_above_safe_zone_minutes=5, alert_count=0,
        )
        trend = compute_trend(current, previous)

        result = build_progress_summary_text(current, previous, trend)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_compute_trend_worsening(self):
        """All worsening signals → WORSENING."""
        from app.services.nl_builders import compute_trend
        from app.schemas.nl import Period
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        current = Period(
            start=now - timedelta(days=7), end=now,
            workout_count=1, total_active_minutes=30,
            avg_risk_level="HIGH", time_in_safe_zone_minutes=10,
            time_above_safe_zone_minutes=20, alert_count=5,
        )
        previous = Period(
            start=now - timedelta(days=14), end=now - timedelta(days=7),
            workout_count=5, total_active_minutes=150,
            avg_risk_level="LOW", time_in_safe_zone_minutes=140,
            time_above_safe_zone_minutes=10, alert_count=1,
        )

        result = compute_trend(current, previous)

        assert result.overall == "WORSENING"

    def test_get_activity_friendly_name_unknown(self):
        """Unknown activity type → fallback 'activity'."""
        from app.services.nl_builders import _get_activity_friendly_name

        result = _get_activity_friendly_name("underwater_hockey")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_todays_workout_with_unknown_activity(self):
        """Workout text with unknown activity type → still produces text."""
        from app.services.nl_builders import build_todays_workout_text

        result = build_todays_workout_text(
            activity_type="OTHER",
            intensity_level="MODERATE",
            duration_minutes=30,
            target_hr_min=100,
            target_hr_max=140,
            risk_level="LOW",
        )

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# predict.py — _generate_recommendation_payload: critical risk
# =============================================================================

class TestRecommendationPayloadCritical:
    """Cover critical risk path in _generate_recommendation_payload."""

    def test_critical_risk_returns_recovery(self, db_session):
        """Critical risk level → same pool as high (recovery)."""
        from app.api.predict import _generate_recommendation_payload

        user = make_user(db_session, "rec_crit@example.com", "Rec Crit", "patient")
        user.baseline_hr = 72
        user.max_safe_hr = 180
        db_session.commit()

        payload = _generate_recommendation_payload(user, "critical", 0.92, [])

        assert "Recovery" in payload["title"]
        assert payload["intensity_level"] == "low"
        assert payload["target_heart_rate_min"] is None


# =============================================================================
# predict.py — _build_drivers defaults with None baseline/max_safe
# =============================================================================

class TestBuildDriversDefaultsNone:
    """Cover _build_drivers with baseline_hr=None, max_safe_hr=None."""

    def test_build_drivers_with_none_baselines(self, db_session):
        """User with None baseline_hr and max_safe_hr → fallback defaults."""
        from app.api.predict import _build_drivers

        user = make_user(db_session, "driver_none@example.com", "Driver None", "patient")
        user.baseline_hr = None
        user.max_safe_hr = None
        user.age = None
        db_session.commit()

        features = {
            "peak_heart_rate": 120,
            "avg_heart_rate": 80,
            "avg_spo2": 97,
            "duration_minutes": 20,
        }

        drivers = _build_drivers(user, features)
        assert isinstance(drivers, list)
        assert len(drivers) > 0


# =============================================================================
# vital_signs.py — check_vitals_for_alerts: multiple alerts in one call
# =============================================================================

class TestMultipleAlerts:
    """Cover bulk-insert of multiple alerts from one vital submission."""

    def test_high_hr_and_low_spo2_creates_two_alerts(self, db_session):
        """Submit vitals with both high HR and low SpO2 → 2 alerts."""
        from app.api.vital_signs import check_vitals_for_alerts
        from app.schemas.vital_signs import VitalSignCreate
        from app.models.alert import Alert

        user = make_user(db_session, "multi_alert@example.com", "Multi Alert", "patient")

        vital_data = VitalSignCreate(
            heart_rate=200,   # > 180
            spo2=85,          # < 90
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
        )

        check_vitals_for_alerts(user.user_id, vital_data, db=db_session)

        alerts = db_session.query(Alert).filter(Alert.user_id == user.user_id).all()
        alert_types = {a.alert_type for a in alerts}

        assert "high_heart_rate" in alert_types
        assert "low_spo2" in alert_types
        assert len(alerts) >= 2


# =============================================================================
# trend_forecasting.py — _compute_risk_projection branches
# =============================================================================

class TestComputeRiskProjectionBranches:
    """Cover more branches in _compute_risk_projection."""

    def test_hr_increasing_adds_risk(self):
        """HR increasing > 0.5 adds risk."""
        from app.services.trend_forecasting import _compute_risk_projection

        trends = {
            "heart_rate": {"slope_per_day": 1.0, "direction": "increasing"},
            "spo2": {"slope_per_day": 0.0, "direction": "stable"},
        }

        result = _compute_risk_projection(trends)
        assert isinstance(result, dict)
        assert "risk_direction" in result
        assert result["risk_score_delta"] > 0

    def test_spo2_decreasing_adds_risk(self):
        """SpO2 decreasing < -0.1 adds risk."""
        from app.services.trend_forecasting import _compute_risk_projection

        trends = {
            "heart_rate": {"slope_per_day": 0.0, "direction": "stable"},
            "spo2": {"slope_per_day": -0.5, "direction": "decreasing"},
        }

        result = _compute_risk_projection(trends)
        assert isinstance(result, dict)
        assert result["risk_score_delta"] > 0

    def test_hr_decreasing_improving(self):
        """HR decreasing < -0.5 → improving."""
        from app.services.trend_forecasting import _compute_risk_projection

        trends = {
            "heart_rate": {"slope_per_day": -1.0, "direction": "decreasing"},
            "spo2": {"slope_per_day": 0.1, "direction": "stable"},
        }

        result = _compute_risk_projection(trends)
        assert isinstance(result, dict)
        assert result["risk_score_delta"] < 0


# =============================================================================
# services/nl_builders.py — build_alert_explanation_text additional branch
# =============================================================================

class TestAlertExplanationSlowDown:
    """Cover SLOW_DOWN action."""

    def test_slow_down_action(self):
        """SLOW_DOWN recommended action."""
        from app.services.nl_builders import build_alert_explanation_text
        from datetime import datetime, timezone

        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE",
            severity_level="LOW",
            alert_time=datetime.now(timezone.utc),
            during_activity=True,
            activity_type="WALKING",
            heart_rate=150,
            spo2=97,
            recommended_action="SLOW_DOWN",
        )

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# nutrition.py — exception branches
# =============================================================================

class TestNutritionExceptionBranches:
    """Cover nutrition exception branches via dependency overrides."""

    def test_create_nutrition_commit_error_returns_400(self):
        """Commit error returns 400 in create_nutrition_entry."""
        from app.api.auth import get_current_user
        from app.models.user import User, UserRole

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("DB error")
        mock_db.rollback = MagicMock()

        user = User(
            user_id=1,
            email="nutr_ex@example.com",
            full_name="Nutr Ex",
            role=UserRole.PATIENT,
            is_active=True,
        )

        def override_get_db():
            yield mock_db

        def override_current_user():
            return user

        fastapi_app.dependency_overrides[get_db] = override_get_db
        fastapi_app.dependency_overrides[get_current_user] = override_current_user
        try:
            response = client.post(
                "/api/v1/nutrition",
                json={"meal_type": "breakfast", "calories": 450},
            )
        finally:
            fastapi_app.dependency_overrides.pop(get_db, None)
            fastapi_app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 400
        assert "Failed to create" in response.json()["detail"]

    def test_get_recent_nutrition_query_error_returns_500(self):
        """Query error returns 500 in get_recent_nutrition_entries."""
        from app.api.auth import get_current_user
        from app.models.user import User, UserRole

        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")

        user = User(
            user_id=2,
            email="nutr_ex2@example.com",
            full_name="Nutr Ex2",
            role=UserRole.PATIENT,
            is_active=True,
        )

        def override_get_db():
            yield mock_db

        def override_current_user():
            return user

        fastapi_app.dependency_overrides[get_db] = override_get_db
        fastapi_app.dependency_overrides[get_current_user] = override_current_user
        try:
            response = client.get("/api/v1/nutrition/recent")
        finally:
            fastapi_app.dependency_overrides.pop(get_db, None)
            fastapi_app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 500
        assert "Failed to retrieve" in response.json()["detail"]

    def test_delete_nutrition_delete_error_returns_500(self):
        """Delete error returns 500 in delete_nutrition_entry."""
        from app.api.auth import get_current_user
        from app.models.user import User, UserRole

        entry = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = entry
        mock_db.delete.side_effect = Exception("DB error")
        mock_db.rollback = MagicMock()

        user = User(
            user_id=3,
            email="nutr_ex3@example.com",
            full_name="Nutr Ex3",
            role=UserRole.PATIENT,
            is_active=True,
        )

        def override_get_db():
            yield mock_db

        def override_current_user():
            return user

        fastapi_app.dependency_overrides[get_db] = override_get_db
        fastapi_app.dependency_overrides[get_current_user] = override_current_user
        try:
            response = client.delete("/api/v1/nutrition/1")
        finally:
            fastapi_app.dependency_overrides.pop(get_db, None)
            fastapi_app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 500
        assert "Failed to delete" in response.json()["detail"]


# =============================================================================
# vital_signs.py — API-level SpO2 validation
# =============================================================================

class TestVitalSignsSpO2APIValidation:
    """Cover API-level SpO2 guard in submit_vitals."""

    def test_submit_vitals_spo2_below_70_returns_400(self, db_session):
        """SpO2=50 should trigger API-level 400."""
        user = make_user(db_session, "spo2_low_api@example.com", "SpO2 Low", "patient")
        token = get_token(client, "spo2_low_api@example.com")

        response = client.post(
            "/api/v1/vitals",
            json={"heart_rate": 80, "spo2": 50},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "70-100" in response.json()["detail"]

    def test_submit_vitals_spo2_65_returns_400(self, db_session):
        """SpO2=65 should trigger API-level 400."""
        user = make_user(db_session, "spo2_low_api2@example.com", "SpO2 Low2", "patient")
        token = get_token(client, "spo2_low_api2@example.com")

        response = client.post(
            "/api/v1/vitals",
            json={"heart_rate": 80, "spo2": 65},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400

    def test_submit_vitals_heart_rate_validation_direct_call(self, db_session):
        """Direct call with invalid heart_rate bypassing Pydantic to cover line 288."""
        from app.api.vital_signs import submit_vitals
        from app.schemas.vital_signs import VitalSignCreate
        from fastapi import BackgroundTasks, HTTPException
        import asyncio

        user = make_user(db_session, f"hr_validation_{uuid.uuid4().hex[:8]}@example.com", "HR Test", "patient")

        # Bypass Pydantic validation with model_construct
        invalid_vital = VitalSignCreate.model_construct(
            heart_rate=20,  # Below 30 threshold
            spo2=None,
            blood_pressure_systolic=None,
            blood_pressure_diastolic=None,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(HTTPException) as exc_info:
                loop.run_until_complete(
                    submit_vitals(
                        vital_data=invalid_vital,
                        background_tasks=BackgroundTasks(),
                        current_user=user,
                        db=db_session,
                    )
                )
            assert exc_info.value.status_code == 400
            assert "30-250" in exc_info.value.detail
        finally:
            loop.close()


# =============================================================================
# schemas/user.py — UserUpdate gender, PasswordResetConfirm no digit
# =============================================================================

class TestUserSchemaValidationEdges:
    """Cover UserUpdate gender and PasswordResetConfirm digit check."""

    def test_userupdate_invalid_gender_raises_validation_error(self):
        """Invalid gender in UserUpdate raises ValidationError."""
        from app.schemas.user import UserUpdate

        with pytest.raises(ValidationError):
            UserUpdate(gender="martian")

    def test_passwordresetconfirm_no_digit_raises_validation_error(self):
        """Missing digit in password raises ValidationError."""
        from app.schemas.user import PasswordResetConfirm

        with pytest.raises(ValidationError, match="digit"):
            PasswordResetConfirm(token="sometoken", new_password="NoDigitsHere")

    def test_passwordresetconfirm_no_digit_direct_validator(self):
        """Direct validator call hits digit check line."""
        from app.schemas.user import PasswordResetConfirm

        with pytest.raises(ValueError):
            PasswordResetConfirm.validate_password_strength("NoDigitsHere")


# =============================================================================
# schemas/vital_signs.py — validator lines 59, 66
# =============================================================================

class TestVitalSignsSchemaValidatorLines:
    """Cover explicit validator lines for blood pressure and SpO2."""

    def test_negative_blood_pressure_systolic_raises(self):
        """Validator raises on negative blood pressure."""
        from app.schemas.vital_signs import VitalSignBase

        with pytest.raises(ValueError):
            VitalSignBase.validate_blood_pressure(-5)

    def test_zero_blood_pressure_diastolic_raises(self):
        """Validator raises on zero blood pressure."""
        from app.schemas.vital_signs import VitalSignBase

        with pytest.raises(ValueError):
            VitalSignBase.validate_blood_pressure(0)

    def test_negative_spo2_raises(self):
        """Validator raises on negative SpO2."""
        from app.schemas.vital_signs import VitalSignBase

        with pytest.raises(ValueError):
            VitalSignBase.validate_spo2(-1)


# =============================================================================
# trend_forecasting.py — spo2 series branch, parse non-string
# =============================================================================

class TestTrendForecastingBranches:
    """Cover spo2 series branch and _parse_timestamp fallback."""

    def test_spo2_series_branch_executed(self):
        """>=7 spo2 readings should populate spo2 trends."""
        from app.services.trend_forecasting import forecast_trends

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        readings = [
            {
                "heart_rate": 75 + i,
                "spo2": 97.0 - i * 0.1,
                "timestamp": (base + timedelta(days=i)).isoformat(),
            }
            for i in range(10)
        ]

        result = forecast_trends(readings, forecast_days=7)

        assert result["status"] == "ok"
        assert "spo2" in result["trends"]

    def test_parse_timestamp_integer_returns_none(self):
        """Non-string/non-datetime returns None."""
        from app.services.trend_forecasting import _parse_timestamp

        assert _parse_timestamp(99999) is None

    def test_parse_timestamp_list_returns_none(self):
        """List timestamp returns None."""
        from app.services.trend_forecasting import _parse_timestamp

        assert _parse_timestamp([2026, 1, 1]) is None


# =============================================================================
# activity.py — duration auto-calculation line 141
# =============================================================================

class TestActivityDurationAutoCalc:
    """Cover duration auto-calculation in end_activity_session."""

    def test_end_activity_without_duration_auto_calculates(self, db_session):
        """Ending a session without duration calculates it from timestamps."""
        user = make_user(db_session, "act_dur@example.com", "Act Dur", "patient")
        token = get_token(client, "act_dur@example.com")

        start_time = (datetime.now() - timedelta(minutes=45)).isoformat()
        start_resp = client.post(
            "/api/v1/activities/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"activity_type": "walking", "start_time": start_time},
        )

        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        end_resp = client.post(
            f"/api/v1/activities/end/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"end_time": datetime.now().isoformat()},
        )

        assert end_resp.status_code == 200
        assert end_resp.json()["duration_minutes"] is not None
        assert end_resp.json()["duration_minutes"] >= 1


# =============================================================================
# auth.py — check_clinician_phi_access SHARING_OFF
# =============================================================================

class TestClinicianPhiAccessDenied:
    """Cover SHARING_OFF 403 in check_clinician_phi_access."""

    def test_sharing_off_blocks_clinician_vitals_access(self, db_session):
        """Clinician cannot access patient with SHARING_OFF."""
        clinician = make_user(db_session, "phi_doc@example.com", "Phi Doc", "clinician")
        patient = make_user(db_session, "phi_pat@example.com", "Phi Pat", "patient")
        patient.share_state = "SHARING_OFF"
        db_session.commit()

        token = get_token(client, "phi_doc@example.com")
        response = client.get(
            f"/api/v1/vitals/user/{patient.user_id}/latest",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


# =============================================================================
# messages.py — other user not found
# =============================================================================

class TestMessageThreadNotFound:
    """Cover get_message_thread other_user not found branch."""

    def test_thread_with_nonexistent_user_returns_404(self, db_session):
        """Nonexistent other user returns 404."""
        user = make_user(db_session, "msg_thr@example.com", "Msg Thr", "patient")
        token = get_token(client, "msg_thr@example.com")

        response = client.get(
            "/api/v1/messages/thread/999999",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# =============================================================================
# predict.py — patient latest recommendation not found
# =============================================================================

class TestPatientRecommendationNotFound:
    """Cover latest recommendation not found branch."""

    def test_no_recommendations_returns_404(self, db_session):
        """No recommendations for patient returns 404."""
        clinician = make_user(db_session, "rec_doc@example.com", "Rec Doc", "clinician")
        patient = make_user(db_session, "rec_pat@example.com", "Rec Pat", "patient")
        db_session.commit()

        token = get_token(client, "rec_doc@example.com")
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/recommendations/latest",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "No recommendations" in response.json()["detail"]


# =============================================================================
# user.py — clinician cannot access other clinician
# =============================================================================

class TestUserAccessControlClinician:
    """Cover can_access_user False branch for clinician -> clinician."""

    def test_clinician_cannot_access_other_clinician_returns_403(self, db_session):
        """Clinician cannot access another clinician."""
        clinician_a = make_user(db_session, "clin_a@example.com", "Clin A", "clinician")
        clinician_b = make_user(db_session, "clin_b@example.com", "Clin B", "clinician")
        db_session.commit()

        token = get_token(client, "clin_a@example.com")
        response = client.get(
            f"/api/v1/users/{clinician_b.user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


# =============================================================================
# database.py — PostgreSQL engine branch
# =============================================================================

class TestDatabasePostgresqlBranch:
    """Cover PostgreSQL engine creation branch."""

    def test_postgresql_else_branch_covered(self):
        """Reload app.database with PostgreSQL settings to hit else branch."""
        import app.config as config_module
        import app.database as db_module

        mock_engine = MagicMock()
        original_settings = config_module.settings

        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+psycopg://user:pass@localhost/adaptiv_test"
        mock_settings.debug = False

        with patch.object(config_module, "settings", mock_settings), \
            patch("sqlalchemy.create_engine", return_value=mock_engine) as mock_ce, \
            patch("sqlalchemy.event.listens_for", return_value=lambda f: f):
            importlib.reload(db_module)
            assert mock_ce.called

        with patch.object(config_module, "settings", original_settings):
            importlib.reload(db_module)


# =============================================================================
# main.py — lifespan and middleware branches
# =============================================================================

class TestMainLifespanAndMiddleware:
    """Cover lifespan error paths and middleware exception handler."""

    def test_init_db_exception_propagates(self):
        """init_db exception is re-raised in lifespan."""
        from app.main import lifespan, app as app_instance

        async def run():
            async with lifespan(app_instance):
                pass

        with patch("app.main.init_db", side_effect=RuntimeError("init failed")):
            with pytest.raises(RuntimeError, match="init failed"):
                asyncio.run(run())

    def test_check_db_connection_false_raises_runtime(self):
        """check_db_connection False raises RuntimeError."""
        from app.main import lifespan, app as app_instance

        async def run():
            async with lifespan(app_instance):
                pass

        with patch("app.main.init_db"), \
            patch("app.main.check_db_connection", return_value=False):
            with pytest.raises(RuntimeError, match="Cannot connect"):
                asyncio.run(run())

    def test_ml_load_exception_is_caught_startup_succeeds(self):
        """ML load exception is caught and does not raise."""
        from app.main import lifespan, app as app_instance

        async def run():
            async with lifespan(app_instance):
                pass

        with patch("app.main.init_db"), \
            patch("app.main.check_db_connection", return_value=True), \
            patch("app.main.load_ml_model", side_effect=Exception("Model missing")):
            asyncio.run(run())

    def test_middleware_exception_branch_executes(self):
        """Middleware logs and re-raises on exception."""
        from app.main import app as app_instance

        @app_instance.get("/test-raise-internal")
        async def raise_internal():
            raise RuntimeError("Deliberate test error")

        error_client = TestClient(app_instance, raise_server_exceptions=False)
        response = error_client.get("/test-raise-internal")

        assert response.status_code == 500

        app_instance.router.routes[:] = [
            r for r in app_instance.router.routes
            if not (hasattr(r, "path") and r.path == "/test-raise-internal")
        ]


# =============================================================================
# baseline_optimization.py — outlier fallback
# =============================================================================

class TestBaselineOptimizationOutlierFallback:
    """Cover outlier fallback when filtered < 3."""

    def test_extreme_outliers_trigger_fallback_on_line_74(self):
        """Outliers cause fallback to all values."""
        from app.services.baseline_optimization import compute_optimized_baseline

        readings = [
            {"heart_rate": 70},
            {"heart_rate": 71},
            {"heart_rate": 110},
            {"heart_rate": 110},
            {"heart_rate": 110},
        ]

        with patch("app.services.baseline_optimization._std", return_value=1.0):
            result = compute_optimized_baseline(readings, current_baseline=72)

        assert result["status"] == "ok"
        assert result["readings_used"] >= 3


# =============================================================================
# encryption.py — key length validation
# =============================================================================

class TestEncryptionKeyValidation:
    """Cover wrong-length key errors in EncryptionService."""

    def test_16_byte_key_raises_value_error(self):
        """16-byte key should raise ValueError."""
        from app.services.encryption import EncryptionService

        short_key_b64 = base64.b64encode(b"A" * 16).decode()
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService(key_b64=short_key_b64)

    def test_64_byte_key_raises_value_error(self):
        """64-byte key should raise ValueError."""
        from app.services.encryption import EncryptionService

        long_key_b64 = base64.b64encode(b"B" * 64).decode()
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService(key_b64=long_key_b64)

    def test_32_byte_key_passes_validation(self):
        """32-byte key should pass validation."""
        from app.services.encryption import EncryptionService

        valid_key_b64 = base64.b64encode(b"C" * 32).decode()
        service = EncryptionService(key_b64=valid_key_b64)
        assert service is not None

    def test_missing_key_raises_value_error(self):
        """No key provided and no settings key should raise ValueError (line 48)."""
        from app.services.encryption import EncryptionService
        from app.config import settings

        # Temporarily clear the settings key
        original_key = getattr(settings, "phi_encryption_key", None)
        try:
            settings.phi_encryption_key = None
            with pytest.raises(ValueError, match="PHI_ENCRYPTION_KEY is missing"):
                EncryptionService()
        finally:
            settings.phi_encryption_key = original_key


# =============================================================================
# auth.py — user not found in get_current_user
# =============================================================================

class TestAuthUserNotFound:
    """Cover get_current_user user not found branch."""

    def test_token_user_not_found_returns_401(self, db_session):
        """Access token for non-existent user returns 401."""
        from app.services.auth_service import AuthService
        from app.database import get_db

        token = AuthService.create_access_token({"sub": "999999"})

        def override_get_db():
            yield db_session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        try:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
        finally:
            fastapi_app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]


# =============================================================================
# predict.py — latest risk assessment not found
# =============================================================================

class TestLatestRiskAssessmentNotFound:
    """Cover no risk assessments found branch."""

    def test_no_risk_assessments_returns_404(self, db_session):
        """Clinician request with no risk assessments returns 404."""
        clinician = make_user(
            db_session,
            f"ra_doc_{uuid.uuid4().hex[:8]}@example.com",
            "RA Doc",
            "clinician"
        )
        patient = make_user(
            db_session,
            f"ra_pat_{uuid.uuid4().hex[:8]}@example.com",
            "RA Pat",
            "patient"
        )
        patient.share_state = "SHARING_ON"
        db_session.commit()

        token = get_token(client, clinician.email)
        response = client.get(
            f"/api/v1/patients/{patient.user_id}/risk-assessments/latest",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "No risk assessments" in response.json()["detail"]

    def test_no_risk_assessments_direct_call(self, db_session):
        """Direct call hits no risk assessments branch."""
        from fastapi import HTTPException
        from app.api.predict import get_patient_latest_risk_assessment
        import asyncio

        clinician = make_user(
            db_session,
            f"ra_doc_direct_{uuid.uuid4().hex[:8]}@example.com",
            "RA Doc D",
            "clinician"
        )
        patient = make_user(
            db_session,
            f"ra_pat_direct_{uuid.uuid4().hex[:8]}@example.com",
            "RA Pat D",
            "patient"
        )
        patient.share_state = "SHARING_ON"
        db_session.commit()

        # Ensure no risk assessments exist for this patient
        from app.models.risk_assessment import RiskAssessment
        existing_ra = db_session.query(RiskAssessment).filter(
            RiskAssessment.user_id == patient.user_id
        ).all()
        assert len(existing_ra) == 0, "Patient should have no risk assessments"

        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await get_patient_latest_risk_assessment(
                    user_id=patient.user_id,
                    current_user=clinician,
                    db=db_session
                )
            assert exc_info.value.status_code == 404
            assert "No risk assessments" in exc_info.value.detail

        asyncio.run(run_test())

    def test_patient_user_not_found_line_807(self, db_session):
        """Non-existent patient user_id raises 404 (line 807)."""
        from fastapi import HTTPException
        from app.api.predict import get_patient_latest_risk_assessment
        import asyncio

        clinician = make_user(
            db_session,
            f"ra_doc_notfound_{uuid.uuid4().hex[:8]}@example.com",
            "RA Doc NF",
            "clinician"
        )

        # Use a user_id that doesn't exist
        non_existent_user_id = 999999

        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await get_patient_latest_risk_assessment(
                    user_id=non_existent_user_id,
                    current_user=clinician,
                    db=db_session
                )
            assert exc_info.value.status_code == 404
            assert "User not found" in exc_info.value.detail

        asyncio.run(run_test())


# =============================================================================
# vital_signs.py — missing lines 288, 366, 542, 570, 607
# =============================================================================

class TestVitalSignsCoverageGaps:
    """Cover vital_signs remaining lines."""

    def test_spo2_below_70_hits_api_guard(self, db_session):
        """SpO2 below 70 should hit API guard 400."""
        user = make_user(db_session, "spo2_guard@example.com", "SpO2 Guard", "patient")
        token = get_token(client, user.email)

        response = client.post(
            "/api/v1/vitals",
            json={"heart_rate": 80, "spo2": 50},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "70-100" in response.json()["detail"]

    def test_spo2_guard_direct_call(self, db_session):
        """Directly call submit_vitals to hit SpO2 guard line."""
        from fastapi import BackgroundTasks, HTTPException
        from app.api.vital_signs import submit_vitals
        from app.schemas.vital_signs import VitalSignCreate

        user = make_user(db_session, f"spo2_direct_{uuid.uuid4().hex[:8]}@example.com", "SpO2 D", "patient")
        vital_data = VitalSignCreate(heart_rate=80, spo2=50)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                submit_vitals(
                    vital_data=vital_data,
                    background_tasks=BackgroundTasks(),
                    current_user=user,
                    db=db_session
                )
            )

        assert exc_info.value.status_code == 400

    def test_vitals_batch_records_created_increments(self, db_session):
        """Batch vitals should create at least one record."""
        user = make_user(db_session, "batch_user@example.com", "Batch User", "patient")
        token = get_token(client, user.email)

        response = client.post(
            "/api/v1/vitals/batch",
            json={
                "vitals": [
                    {"heart_rate": 75, "spo2": 98, "blood_pressure_systolic": 120, "blood_pressure_diastolic": 80}
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["records_created"] == 1

    def test_vitals_batch_skips_invalid_heart_rate(self, db_session):
        """Invalid heart rate in batch is skipped (covered via model_construct)."""
        from app.api.vital_signs import submit_vitals_batch
        from app.schemas.vital_signs import VitalSignCreate, VitalSignBatchCreate
        from fastapi import BackgroundTasks
        import asyncio

        user = make_user(db_session, f"batch_skip_{uuid.uuid4().hex[:8]}@example.com", "Batch Skip", "patient")

        # heart_rate=20 fails schema (ge=30) so we bypass with model_construct
        invalid_vital = VitalSignCreate.model_construct(
            heart_rate=20,
            spo2=None,
            blood_pressure_systolic=None,
            blood_pressure_diastolic=None,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )
        batch = VitalSignBatchCreate.model_construct(vitals=[invalid_vital])

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                submit_vitals_batch(
                    batch_data=batch,
                    background_tasks=BackgroundTasks(),
                    current_user=user,
                    db=db_session,
                )
            )
        finally:
            loop.close()

        assert result["records_created"] == 0

    def test_clinician_latest_vitals_not_found(self, db_session):
        """Clinician latest vitals for patient with none returns 404."""
        clinician = make_user(db_session, "vit_doc@example.com", "Vit Doc", "clinician")
        patient = make_user(db_session, "vit_pat@example.com", "Vit Pat", "patient")
        patient.share_state = "SHARING_ON"
        db_session.commit()

        token = get_token(client, "vit_doc@example.com")
        response = client.get(
            f"/api/v1/vitals/user/{patient.user_id}/latest",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "No vital signs" in response.json()["detail"]

    def test_vitals_summary_user_not_found(self, db_session):
        """Summary endpoint with nonexistent user returns 404."""
        clinician = make_user(db_session, "sum_doc@example.com", "Sum Doc", "clinician")
        token = get_token(client, "sum_doc@example.com")

        response = client.get(
            "/api/v1/vitals/user/999999/summary",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_vitals_history_user_not_found(self, db_session):
        """History endpoint with nonexistent user returns 404."""
        clinician = make_user(db_session, "hist_doc@example.com", "Hist Doc", "clinician")
        token = get_token(client, "hist_doc@example.com")

        response = client.get(
            "/api/v1/vitals/user/999999/history",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# =============================================================================
# schemas/user.py — UserCreate password digit check
# =============================================================================

class TestUserCreatePasswordMissingDigit:
    """Cover UserCreate missing digit validation branch."""

    def test_usercreate_password_missing_digit_raises(self):
        """Password without digit raises ValidationError."""
        from app.schemas.user import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                email="nodigit@example.com",
                name="No Digit",
                password="NoDigitsHere",
            )

    def test_usercreate_missing_digit_direct_validator(self):
        """Direct validator call hits missing digit line."""
        from app.schemas.user import UserCreate

        with pytest.raises(ValueError):
            UserCreate.validate_password_strength("NoDigitsHere")


# =============================================================================
# ml_prediction.py — get_ml_service ensure_model_loaded line
# =============================================================================

class TestGetMlService:
    """Cover ensure_model_loaded call in get_ml_service."""

    def test_get_ml_service_calls_ensure_model_loaded(self):
        """Patch ensure_model_loaded to avoid loading real model."""
        from app.services import ml_prediction

        with patch("app.services.ml_prediction.ensure_model_loaded"):
            service = ml_prediction.get_ml_service()

        assert service is not None

    def test_ml_service_predict_risk_method(self):
        """Call MLPredictionService.predict_risk to cover line 283."""
        from app.services.ml_prediction import MLPredictionService, predict_risk

        with patch("app.services.ml_prediction.predict_risk") as mock_predict:
            mock_predict.return_value = {"risk_score": 0.5}
            service = MLPredictionService()
            result = service.predict_risk(age=50, baseline_hr=70, max_safe_hr=150)

        assert result == {"risk_score": 0.5}
        mock_predict.assert_called_once()


# =============================================================================
# trend_forecasting.py — ensure spo2 branch executes
# =============================================================================

class TestTrendForecastingSpo2Branch:
    """Cover spo2 trends branch."""

    def test_spo2_branch_executes(self):
        """All readings with spo2 should populate spo2 trend."""
        from app.services.trend_forecasting import forecast_trends

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        readings = [
            {
                "heart_rate": 72 + i,
                "spo2": 98.0 - (i * 0.1),
                "timestamp": (base + timedelta(days=i)).isoformat(),
            }
            for i in range(10)
        ]

        result = forecast_trends(readings, forecast_days=7)

        assert result["status"] == "ok"
        assert "spo2" in result["trends"]

    def test_spo2_none_branch(self):
        """Readings with spo2=None should skip spo2 series append."""
        from app.services.trend_forecasting import forecast_trends

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        readings = [
            {
                "heart_rate": 72 + i,
                "spo2": None,  # Explicitly None
                "timestamp": (base + timedelta(days=i)).isoformat(),
            }
            for i in range(10)
        ]

        result = forecast_trends(readings, forecast_days=7)

        assert result["status"] == "ok"
        # spo2 was None in all readings, so no spo2 trend
        assert "spo2" not in result["trends"]

    def test_invalid_timestamp_hits_else_branch(self):
        """Invalid timestamp forces else branch (line 55: day_offset = 0.0)."""
        from app.services.trend_forecasting import forecast_trends

        # Provide readings with unparseable timestamps
        readings = [
            {
                "heart_rate": 72 + i,
                "spo2": 98.0,
                "timestamp": "invalid-timestamp-format",  # Will fail parsing
            }
            for i in range(10)
        ]

        result = forecast_trends(readings, forecast_days=7)

        assert result["status"] == "ok"
        # Even with invalid timestamps, processing continues with day_offset=0.0


# =============================================================================
# main.py — load_ml_model False + TrustedHostMiddleware branch
# =============================================================================

class TestMainAdditionalCoverage:
    """Cover ML load False warning and trusted host middleware block."""

    def test_load_ml_model_returns_false_logs_warning(self):
        """load_ml_model returning False hits warning branch."""
        from app.main import lifespan, app as app_instance

        async def run():
            async with lifespan(app_instance):
                pass

        with patch("app.main.init_db"), \
            patch("app.main.check_db_connection", return_value=True), \
            patch("app.main.load_ml_model", return_value=False):
            asyncio.run(run())

    def test_trusted_host_middleware_enabled_when_not_debug(self):
        """Reload app.main with debug False to execute TrustedHostMiddleware block."""
        import app.config as config_module
        import app.main as main_module

        original_debug = config_module.settings.debug

        try:
            config_module.settings.debug = False
            reloaded = importlib.reload(main_module)
            middleware_names = [m.cls.__name__ for m in reloaded.app.user_middleware]
            assert "TrustedHostMiddleware" in middleware_names
        finally:
            config_module.settings.debug = original_debug
            importlib.reload(main_module)

