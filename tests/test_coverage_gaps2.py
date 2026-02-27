"""
Second-pass coverage gap tests.

Targets remaining 126 missing lines across these files:
- app/api/nutrition.py        (78% → 100%) - 11 missing
- app/api/consent.py          (91% → 100%) - 9 missing
- app/services/nl_builders.py (90% → 100%) - 12 missing
- app/services/ml_prediction.py (93% → 100%) - 7 missing
- app/services/retraining_pipeline.py (88% → 100%) - 8 missing
- app/services/recommendation_ranking.py (92% → 100%) - 2 missing
- app/services/explainability.py (95% → 100%) - 3 missing
- app/services/baseline_optimization.py (94% → 100%) - 2 missing
- app/services/anomaly_detection.py (98% → 100%) - 1 missing

Run with:
    pytest tests/test_coverage_gaps2.py -v
"""

from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token, make_alert


client = TestClient(fastapi_app)


# =============================================================================
# nutrition.py GAP COVERAGE (78% → 100%)
# Missing: create (try/except path), get_recent (try/except path),
#          delete (not_found path + try/except delete path)
# =============================================================================

class TestNutritionCreateEntry:
    """Test POST /api/v1/nutrition endpoint."""

    def test_create_basic_nutrition_entry(self, db_session):
        """Create a nutrition entry - happy path (covers main code path)."""
        user = make_user(db_session, "nut_create1@example.com", "Nut Create1", "patient")
        token = get_token(client, "nut_create1@example.com")

        response = client.post(
            "/api/v1/nutrition",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "meal_type": "breakfast",
                "description": "Oatmeal with banana",
                "calories": 350,
                "protein_grams": 12,
                "carbs_grams": 65,
                "fat_grams": 7
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meal_type"] == "breakfast"
        assert data["calories"] == 350
        assert data["protein_grams"] == 12
        assert data["user_id"] == user.user_id

    def test_create_nutrition_entry_minimal(self, db_session):
        """Create with only required fields (calories, meal_type)."""
        user = make_user(db_session, "nut_create2@example.com", "Nut Create2", "patient")
        token = get_token(client, "nut_create2@example.com")

        response = client.post(
            "/api/v1/nutrition",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "meal_type": "lunch",
                "calories": 500
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meal_type"] == "lunch"
        assert data["calories"] == 500

    def test_create_all_meal_types(self, db_session):
        """Test each valid meal type."""
        user = make_user(db_session, "nut_create3@example.com", "Nut Create3", "patient")
        token = get_token(client, "nut_create3@example.com")

        for meal_type in ["breakfast", "lunch", "dinner", "snack", "other"]:
            response = client.post(
                "/api/v1/nutrition",
                headers={"Authorization": f"Bearer {token}"},
                json={"meal_type": meal_type, "calories": 300}
            )
            assert response.status_code == 201

    def test_create_invalid_meal_type_returns_422(self, db_session):
        """Invalid meal_type returns 422 validation error."""
        user = make_user(db_session, "nut_create4@example.com", "Nut Create4", "patient")
        token = get_token(client, "nut_create4@example.com")

        response = client.post(
            "/api/v1/nutrition",
            headers={"Authorization": f"Bearer {token}"},
            json={"meal_type": "elevenses", "calories": 300}
        )

        assert response.status_code == 422

    def test_create_no_auth_returns_401(self, db_session):
        """No auth returns 401."""
        response = client.post(
            "/api/v1/nutrition",
            json={"meal_type": "lunch", "calories": 500}
        )
        assert response.status_code == 401


class TestNutritionGetRecentEntries:
    """Test GET /api/v1/nutrition/recent endpoint."""

    def test_get_recent_entries_empty(self, db_session):
        """User with no entries returns empty list."""
        user = make_user(db_session, "nut_get1@example.com", "Nut Get1", "patient")
        token = get_token(client, "nut_get1@example.com")

        response = client.get(
            "/api/v1/nutrition/recent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["entries"] == []

    def test_get_recent_entries_with_data(self, db_session):
        """Returns created entries ordered by most recent first."""
        user = make_user(db_session, "nut_get2@example.com", "Nut Get2", "patient")
        token = get_token(client, "nut_get2@example.com")

        # Create 3 entries
        for i in range(3):
            client.post(
                "/api/v1/nutrition",
                headers={"Authorization": f"Bearer {token}"},
                json={"meal_type": "snack", "calories": 100 + i * 50}
            )

        response = client.get(
            "/api/v1/nutrition/recent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["entries"]) == 3

    def test_get_recent_entries_limit_param(self, db_session):
        """Limit parameter restricts number of results returned."""
        user = make_user(db_session, "nut_get3@example.com", "Nut Get3", "patient")
        token = get_token(client, "nut_get3@example.com")

        # Create 5 entries
        for i in range(5):
            client.post(
                "/api/v1/nutrition",
                headers={"Authorization": f"Bearer {token}"},
                json={"meal_type": "snack", "calories": 200}
            )

        response = client.get(
            "/api/v1/nutrition/recent?limit=2",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["total_count"] == 5
        assert data["limit"] == 2

    def test_get_recent_no_auth_returns_401(self, db_session):
        """No auth returns 401."""
        response = client.get("/api/v1/nutrition/recent")
        assert response.status_code == 401


class TestNutritionDeleteEntry:
    """Test DELETE /api/v1/nutrition/{entry_id} endpoint."""

    def test_delete_own_entry_returns_204(self, db_session):
        """Delete own entry returns 204 No Content."""
        user = make_user(db_session, "nut_del1@example.com", "Nut Del1", "patient")
        token = get_token(client, "nut_del1@example.com")

        # Create an entry
        create_resp = client.post(
            "/api/v1/nutrition",
            headers={"Authorization": f"Bearer {token}"},
            json={"meal_type": "dinner", "calories": 600}
        )
        entry_id = create_resp.json()["entry_id"]

        # Delete it
        response = client.delete(
            f"/api/v1/nutrition/{entry_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

    def test_delete_nonexistent_entry_returns_404(self, db_session):
        """Delete non-existent entry returns 404."""
        user = make_user(db_session, "nut_del2@example.com", "Nut Del2", "patient")
        token = get_token(client, "nut_del2@example.com")

        response = client.delete(
            "/api/v1/nutrition/999999",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_delete_other_user_entry_returns_404(self, db_session):
        """Cannot delete another user's entry (returns 404)."""
        user_a = make_user(db_session, "nut_del3a@example.com", "Nut Del3A", "patient")
        user_b = make_user(db_session, "nut_del3b@example.com", "Nut Del3B", "patient")

        token_a = get_token(client, "nut_del3a@example.com")
        token_b = get_token(client, "nut_del3b@example.com")

        # User A creates an entry
        create_resp = client.post(
            "/api/v1/nutrition",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"meal_type": "lunch", "calories": 400}
        )
        entry_id = create_resp.json()["entry_id"]

        # User B tries to delete it
        response = client.delete(
            f"/api/v1/nutrition/{entry_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )

        assert response.status_code == 404

    def test_delete_no_auth_returns_401(self, db_session):
        """No auth returns 401."""
        response = client.delete("/api/v1/nutrition/1")
        assert response.status_code == 401


# =============================================================================
# consent.py GAP COVERAGE (91% → 100%)
# Missing: request_sharing_disable (SHARING_OFF + SHARING_DISABLE_REQUESTED branches)
#          enable_sharing (SHARING_ON + SHARING_DISABLE_REQUESTED branches)
#          list_pending_requests (non-CLINICIAN returns 403)
#          review_consent_request branches (invalid decision, patient not found,
#          not-pending state, reject path with reason)
# =============================================================================

class TestConsentDisable:
    """Test POST /api/v1/consent/disable endpoint."""

    def test_patient_requests_disable_when_sharing_on(self, db_session):
        """Happy path: patient requests disable when sharing is ON."""
        user = make_user(db_session, "consent_dis1@example.com", "Consent Dis1", "patient")
        token = get_token(client, "consent_dis1@example.com")

        response = client.post(
            "/api/v1/consent/disable",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Privacy concerns"}
        )

        assert response.status_code == 200
        assert "submitted" in response.json()["message"].lower()

    def test_patient_disable_when_already_disabled_returns_400(self, db_session):
        """Sharing already disabled returns 400."""
        user = make_user(db_session, "consent_dis2@example.com", "Consent Dis2", "patient")
        user.share_state = "SHARING_OFF"
        db_session.commit()

        token = get_token(client, "consent_dis2@example.com")
        response = client.post(
            "/api/v1/consent/disable",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

        assert response.status_code == 400
        assert "already disabled" in response.json()["detail"].lower()

    def test_patient_disable_when_request_pending_returns_400(self, db_session):
        """Already a pending request returns 400."""
        user = make_user(db_session, "consent_dis3@example.com", "Consent Dis3", "patient")
        user.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_dis3@example.com")
        response = client.post(
            "/api/v1/consent/disable",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    def test_clinician_cannot_disable_sharing_returns_403(self, db_session):
        """Clinician (non-patient) trying to disable sharing returns 403."""
        doctor = make_user(db_session, "consent_dis4@example.com", "Consent Dis4", "clinician")
        token = get_token(client, "consent_dis4@example.com")

        response = client.post(
            "/api/v1/consent/disable",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

        assert response.status_code == 403


class TestConsentEnable:
    """Test POST /api/v1/consent/enable endpoint."""

    def test_patient_enable_when_sharing_off(self, db_session):
        """Happy path: patient re-enables from SHARING_OFF state."""
        user = make_user(db_session, "consent_en1@example.com", "Consent En1", "patient")
        user.share_state = "SHARING_OFF"
        db_session.commit()

        token = get_token(client, "consent_en1@example.com")
        response = client.post(
            "/api/v1/consent/enable",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "re-enabled" in response.json()["message"].lower()

    def test_patient_enable_when_already_on_returns_400(self, db_session):
        """Sharing already enabled returns 400."""
        user = make_user(db_session, "consent_en2@example.com", "Consent En2", "patient")
        # Default share_state is None → treated as SHARING_ON
        db_session.commit()

        token = get_token(client, "consent_en2@example.com")
        response = client.post(
            "/api/v1/consent/enable",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "already enabled" in response.json()["detail"].lower()

    def test_patient_enable_when_request_pending_returns_400(self, db_session):
        """Cannot re-enable while disable request is pending."""
        user = make_user(db_session, "consent_en3@example.com", "Consent En3", "patient")
        user.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_en3@example.com")
        response = client.post(
            "/api/v1/consent/enable",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    def test_clinician_cannot_enable_returns_403(self, db_session):
        """Non-patient role returns 403."""
        doctor = make_user(db_session, "consent_en4@example.com", "Consent En4", "clinician")
        token = get_token(client, "consent_en4@example.com")

        response = client.post(
            "/api/v1/consent/enable",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403


class TestConsentListPending:
    """Test GET /api/v1/consent/pending endpoint."""

    def test_clinician_gets_pending_list(self, db_session):
        """Clinician gets pending requests list."""
        doctor = make_user(db_session, "consent_list1@example.com", "Consent List1", "clinician")
        patient = make_user(db_session, "consent_list1_pat@example.com", "Consent Pat1", "patient")
        patient.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_list1@example.com")
        response = client.get(
            "/api/v1/consent/pending",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "pending_requests" in data

    def test_patient_cannot_list_pending_returns_403(self, db_session):
        """Patient role returns 403 (covers list_pending_requests 403 branch)."""
        patient = make_user(db_session, "consent_list2@example.com", "Consent List2", "patient")
        token = get_token(client, "consent_list2@example.com")

        response = client.get(
            "/api/v1/consent/pending",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403


class TestConsentReview:
    """Test POST /api/v1/consent/{patient_id}/review endpoint."""

    def test_clinician_approves_consent_request(self, db_session):
        """Clinician approves consent → SHARING_OFF."""
        doctor = make_user(db_session, "consent_rev1@example.com", "Consent Rev1", "clinician")
        patient = make_user(db_session, "consent_rev1_pat@example.com", "Consent Rev1 Pat", "patient")
        patient.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_rev1@example.com")
        response = client.post(
            f"/api/v1/consent/{patient.user_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approve"}
        )

        assert response.status_code == 200
        assert "approved" in response.json()["message"].lower()

    def test_clinician_rejects_consent_request(self, db_session):
        """Clinician rejects consent → SHARING_ON (covers reject path with reason)."""
        doctor = make_user(db_session, "consent_rev2@example.com", "Consent Rev2", "clinician")
        patient = make_user(db_session, "consent_rev2_pat@example.com", "Consent Rev2 Pat", "patient")
        patient.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_rev2@example.com")
        response = client.post(
            f"/api/v1/consent/{patient.user_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "reject", "reason": "Clinical necessity"}
        )

        assert response.status_code == 200
        assert "rejected" in response.json()["message"].lower()

    def test_invalid_decision_returns_400(self, db_session):
        """Decision other than approve/reject returns 400."""
        doctor = make_user(db_session, "consent_rev3@example.com", "Consent Rev3", "clinician")
        patient = make_user(db_session, "consent_rev3_pat@example.com", "Consent Rev3 Pat", "patient")
        patient.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_rev3@example.com")
        response = client.post(
            f"/api/v1/consent/{patient.user_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "maybe"}
        )

        assert response.status_code == 400

    def test_patient_not_found_returns_404(self, db_session):
        """Non-existent patient ID returns 404."""
        doctor = make_user(db_session, "consent_rev4@example.com", "Consent Rev4", "clinician")
        token = get_token(client, "consent_rev4@example.com")

        response = client.post(
            "/api/v1/consent/999999/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approve"}
        )

        assert response.status_code == 404

    def test_no_pending_request_returns_400(self, db_session):
        """Patient has no pending request returns 400."""
        doctor = make_user(db_session, "consent_rev5@example.com", "Consent Rev5", "clinician")
        patient = make_user(db_session, "consent_rev5_pat@example.com", "Consent Rev5 Pat", "patient")
        # Default state (SHARING_ON), no pending request
        db_session.commit()

        token = get_token(client, "consent_rev5@example.com")
        response = client.post(
            f"/api/v1/consent/{patient.user_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approve"}
        )

        assert response.status_code == 400
        assert "no pending" in response.json()["detail"].lower()

    def test_patient_cannot_review_returns_403(self, db_session):
        """Patient role cannot review requests."""
        patient_a = make_user(db_session, "consent_rev6a@example.com", "Consent Rev6A", "patient")
        patient_b = make_user(db_session, "consent_rev6b@example.com", "Consent Rev6B", "patient")
        patient_b.share_state = "SHARING_DISABLE_REQUESTED"
        db_session.commit()

        token = get_token(client, "consent_rev6a@example.com")
        response = client.post(
            f"/api/v1/consent/{patient_b.user_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approve"}
        )

        assert response.status_code == 403


# =============================================================================
# nl_builders.py GAP COVERAGE - EXHAUSTIVE (90% → 100%)
# Strategy: test ALL branches in every function
# =============================================================================

class TestBuildRiskSummaryTextAllBranches:
    """Exhaustive tests for all branches in build_risk_summary_text."""

    def test_low_risk_no_alerts_safe(self):
        """LOW risk, 0 alerts, SAFE safety - covers LOW opener, 0 alert_count, SAFE safety."""
        from app.services.nl_builders import build_risk_summary_text
        result = build_risk_summary_text(
            risk_level="LOW", risk_score=0.1, time_window_hours=24,
            avg_heart_rate=70, max_heart_rate=90, avg_spo2=98,
            alert_count=0, safety_status="SAFE"
        )
        assert "stable" in result.lower()
        assert "no alerts" in result.lower()
        assert "light to moderate" in result.lower()

    def test_moderate_risk_one_alert_caution(self):
        """MODERATE risk, 1 alert, CAUTION - covers MODERATE opener, 1 alert, CAUTION."""
        from app.services.nl_builders import build_risk_summary_text
        result = build_risk_summary_text(
            risk_level="MODERATE", risk_score=0.55, time_window_hours=12,
            avg_heart_rate=85, max_heart_rate=120, avg_spo2=96,
            alert_count=1, safety_status="CAUTION"
        )
        assert "variation" in result.lower() or "monitoring" in result.lower()
        assert "one alert" in result.lower()
        assert "easy" in result.lower() or "light activities" in result.lower()

    def test_high_risk_many_alerts_unsafe(self):
        """HIGH risk, 3 alerts, UNSAFE - covers HIGH opener, many alerts, UNSAFE safety."""
        from app.services.nl_builders import build_risk_summary_text
        result = build_risk_summary_text(
            risk_level="HIGH", risk_score=0.85, time_window_hours=6,
            avg_heart_rate=100, max_heart_rate=150, avg_spo2=93,
            alert_count=3, safety_status="UNSAFE"
        )
        assert "concerning" in result.lower()
        assert "3 alerts" in result.lower()
        assert "rest" in result.lower() or "avoid" in result.lower()


class TestBuildTodaysWorkoutTextAllBranches:
    """Exhaustive tests for all branches in build_todays_workout_text."""

    def test_light_walking_low_risk(self):
        """LIGHT intensity + WALKING + LOW risk."""
        from app.services.nl_builders import build_todays_workout_text
        result = build_todays_workout_text(
            activity_type="WALKING", intensity_level="LIGHT",
            duration_minutes=20, target_hr_min=90, target_hr_max=110,
            risk_level="LOW"
        )
        assert "comfortable" in result.lower() or "easy pace" in result.lower()
        assert "discomfort" in result.lower() or "enjoy" in result.lower()

    def test_moderate_cycling_low_risk(self):
        """MODERATE intensity + CYCLING + LOW risk - covers MODERATE pace branch."""
        from app.services.nl_builders import build_todays_workout_text
        result = build_todays_workout_text(
            activity_type="CYCLING", intensity_level="MODERATE",
            duration_minutes=25, target_hr_min=110, target_hr_max=135,
            risk_level="LOW"
        )
        assert "steady" in result.lower() or "moderate" in result.lower()

    def test_vigorous_other_high_risk(self):
        """VIGOROUS intensity + OTHER + HIGH risk - covers VIGOROUS and HIGH safety."""
        from app.services.nl_builders import build_todays_workout_text
        result = build_todays_workout_text(
            activity_type="OTHER", intensity_level="VIGOROUS",
            duration_minutes=15, target_hr_min=130, target_hr_max=160,
            risk_level="HIGH"
        )
        assert "brisk" in result.lower() or "challenging" in result.lower()
        assert "stop immediately" in result.lower() or "care team" in result.lower()

    def test_light_walking_moderate_risk(self):
        """LIGHT + WALKING + MODERATE risk - covers MODERATE safety cue."""
        from app.services.nl_builders import build_todays_workout_text
        result = build_todays_workout_text(
            activity_type="WALKING", intensity_level="LIGHT",
            duration_minutes=20, target_hr_min=90, target_hr_max=110,
            risk_level="MODERATE"
        )
        assert "monitor" in result.lower() or "chest pain" in result.lower()


class TestBuildAlertExplanationTextAllBranches:
    """Exhaustive tests for all branches in build_alert_explanation_text."""

    def test_high_heart_rate_during_activity(self):
        """HIGH_HEART_RATE + during_activity=True + SLOW_DOWN action."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="MEDIUM",
            alert_time=datetime(2026, 1, 15, 10, 0),
            during_activity=True, activity_type="running",
            heart_rate=175, spo2=None, recommended_action="SLOW_DOWN"
        )
        assert "running" in result.lower()
        assert "slow down" in result.lower() or "ease up" in result.lower()

    def test_high_heart_rate_at_rest(self):
        """HIGH_HEART_RATE + during_activity=False (at rest)."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 14, 30),
            during_activity=False, activity_type=None,
            heart_rate=145, spo2=None, recommended_action="CONTACT_DOCTOR"
        )
        assert "at rest" in result.lower()
        assert "contact" in result.lower() or "care team" in result.lower()

    def test_low_oxygen_alert(self):
        """LOW_OXYGEN alert type + STOP_AND_REST action."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="LOW_OXYGEN", severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 9, 0),
            during_activity=False, activity_type=None,
            heart_rate=None, spo2=88, recommended_action="STOP_AND_REST"
        )
        assert "oxygen" in result.lower() or "88" in result
        assert "stop" in result.lower() or "rest" in result.lower()

    def test_other_alert_type_fallback(self):
        """OTHER alert type - fallback trigger text."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="OTHER", severity_level="LOW",
            alert_time=datetime(2026, 1, 15, 7, 0),
            during_activity=False, activity_type=None,
            heart_rate=None, spo2=None, recommended_action="CONTINUE"
        )
        assert "unusual reading" in result.lower()
        assert "continue" in result.lower() or "current activity" in result.lower()

    def test_low_severity_level(self):
        """LOW severity_level text branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="LOW",
            alert_time=datetime(2026, 1, 15, 8, 0),
            during_activity=True, activity_type="walking",
            heart_rate=130, spo2=None, recommended_action="CONTINUE"
        )
        assert "minor concern" in result.lower() or "harder than usual" in result.lower()

    def test_medium_severity_level(self):
        """MEDIUM severity_level text branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="LOW_OXYGEN", severity_level="MEDIUM",
            alert_time=datetime(2026, 1, 15, 11, 0),
            during_activity=False, activity_type=None,
            heart_rate=None, spo2=92, recommended_action="STOP_AND_REST"
        )
        assert "attention" in result.lower()

    def test_high_severity_level(self):
        """HIGH severity_level text branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 16, 45),
            during_activity=True, activity_type="running",
            heart_rate=195, spo2=None, recommended_action="EMERGENCY"
        )
        assert "significant" in result.lower() or "immediate" in result.lower()
        assert "emergency" in result.lower() or "911" in result.lower()

    def test_stop_and_rest_action(self):
        """STOP_AND_REST recommended action branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="LOW_OXYGEN", severity_level="MEDIUM",
            alert_time=datetime(2026, 1, 15, 13, 0),
            during_activity=True, activity_type="cycling",
            heart_rate=None, spo2=90, recommended_action="STOP_AND_REST"
        )
        assert "stop" in result.lower() and "rest" in result.lower()

    def test_contact_doctor_action(self):
        """CONTACT_DOCTOR recommended action branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 15, 0),
            during_activity=False, activity_type=None,
            heart_rate=160, spo2=None, recommended_action="CONTACT_DOCTOR"
        )
        assert "care team" in result.lower() or "contact" in result.lower()

    def test_continue_action(self):
        """CONTINUE recommended action branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="OTHER", severity_level="LOW",
            alert_time=datetime(2026, 1, 15, 6, 0),
            during_activity=False, activity_type=None,
            heart_rate=None, spo2=None, recommended_action="CONTINUE"
        )
        assert "continue" in result.lower()

    def test_emergency_action(self):
        """EMERGENCY recommended action branch."""
        from app.services.nl_builders import build_alert_explanation_text
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE", severity_level="HIGH",
            alert_time=datetime(2026, 1, 15, 20, 0),
            during_activity=True, activity_type="cycling",
            heart_rate=200, spo2=None, recommended_action="EMERGENCY"
        )
        assert "emergency" in result.lower() or "911" in result.lower()


# =============================================================================
# ml_prediction.py GAP COVERAGE - CAREFUL ISOLATION (93% → 100%)
# =============================================================================

class TestMlPredictionLoadModelTimeout:
    """Load ML model with timeout - careful state management."""

    def test_load_returns_false_on_thread_timeout(self):
        """Thread is_alive=True after join → return False."""
        from app.services import ml_prediction

        # Save original state
        orig_attempted = ml_prediction._model_load_attempted
        orig_model = ml_prediction.model

        try:
            mock_thread = Mock()
            mock_thread.is_alive.return_value = True

            with patch("app.services.ml_prediction.threading.Thread", return_value=mock_thread):
                result = ml_prediction.load_ml_model(timeout=0)

            assert result is False
        finally:
            ml_prediction._model_load_attempted = orig_attempted
            ml_prediction.model = orig_model

    def test_load_returns_false_when_inner_sets_ok_false(self):
        """File not found inside thread → ok=False → return False (line 117)."""
        from app.services import ml_prediction

        orig_attempted = ml_prediction._model_load_attempted
        orig_model = ml_prediction.model

        try:
            with patch("app.services.ml_prediction.joblib.load", side_effect=FileNotFoundError()):
                result = ml_prediction.load_ml_model(timeout=10)

            assert result is False
        finally:
            ml_prediction._model_load_attempted = orig_attempted
            ml_prediction.model = orig_model


class TestMlPredictionEnsureModelLoaded:
    """ensure_model_loaded branch coverage."""

    def test_returns_true_when_already_loaded(self):
        """Line 128: early return True when is_model_loaded() is True."""
        from app.services import ml_prediction

        with patch.object(ml_prediction, "is_model_loaded", return_value=True):
            result = ml_prediction.ensure_model_loaded()

        assert result is True

    def test_returns_true_when_loaded_inside_lock(self):
        """Line 132: returns True from inside lock when model loaded by other thread."""
        from app.services import ml_prediction

        orig_attempted = ml_prediction._model_load_attempted

        try:
            # First call (outer) returns False, second call (inside lock) returns True
            call_count = [0]
            def is_loaded_side_effect():
                call_count[0] += 1
                return call_count[0] >= 2  # False first, True second+

            with patch.object(ml_prediction, "is_model_loaded", side_effect=is_loaded_side_effect):
                ml_prediction._model_load_attempted = False
                result = ml_prediction.ensure_model_loaded()

            assert result is True
        finally:
            ml_prediction._model_load_attempted = orig_attempted


class TestMlPredictionRiskLevels:
    """predict_risk branch coverage for all risk levels."""

    def _setup_mocks(self, ml_prediction, prob_high):
        """Helper: set up module globals with mock model returning given probability."""
        import numpy as np

        mock_model = Mock()
        mock_model.predict.return_value = np.array([0])
        mock_model.predict_proba.return_value = np.array([[1 - prob_high, prob_high]])

        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.array([[1.0] * 17])

        feature_columns = [
            "age", "baseline_hr", "max_safe_hr", "avg_heart_rate",
            "peak_heart_rate", "min_heart_rate", "avg_spo2",
            "duration_minutes", "recovery_time_minutes", "hr_pct_of_max",
            "hr_elevation", "hr_range", "duration_intensity",
            "recovery_efficiency", "spo2_deviation", "age_risk_factor",
            "activity_intensity"
        ]

        orig = (ml_prediction.model, ml_prediction.scaler, ml_prediction.feature_columns)
        ml_prediction.model = mock_model
        ml_prediction.scaler = mock_scaler
        ml_prediction.feature_columns = feature_columns
        return orig

    def _restore(self, ml_prediction, orig):
        ml_prediction.model, ml_prediction.scaler, ml_prediction.feature_columns = orig

    def test_moderate_risk_score_between_50_and_80(self):
        """Lines 247-248: risk_score 0.50-0.79 → risk_level='moderate'."""
        from app.services import ml_prediction

        orig = self._setup_mocks(ml_prediction, prob_high=0.65)
        try:
            result = ml_prediction.predict_risk(
                age=45, baseline_hr=70, max_safe_hr=175,
                avg_heart_rate=110, peak_heart_rate=140, min_heart_rate=65,
                avg_spo2=97, duration_minutes=30, recovery_time_minutes=5
            )
            assert result["risk_level"] == "moderate"
            assert 0.50 <= result["risk_score"] < 0.80
            assert "Reduce intensity" in result["recommendation"]
        finally:
            self._restore(ml_prediction, orig)

    def test_high_risk_score_above_80(self):
        """risk_score >= 0.80 → risk_level='high'."""
        from app.services import ml_prediction

        orig = self._setup_mocks(ml_prediction, prob_high=0.90)
        try:
            result = ml_prediction.predict_risk(
                age=65, baseline_hr=72, max_safe_hr=155,
                avg_heart_rate=145, peak_heart_rate=170, min_heart_rate=70,
                avg_spo2=93, duration_minutes=45, recovery_time_minutes=15
            )
            assert result["risk_level"] == "high"
            assert result["risk_score"] >= 0.80
            assert "STOP" in result["recommendation"]
        finally:
            self._restore(ml_prediction, orig)

    def test_low_risk_score_below_50(self):
        """risk_score < 0.50 → risk_level='low'."""
        from app.services import ml_prediction

        orig = self._setup_mocks(ml_prediction, prob_high=0.20)
        try:
            result = ml_prediction.predict_risk(
                age=30, baseline_hr=68, max_safe_hr=185,
                avg_heart_rate=85, peak_heart_rate=110, min_heart_rate=62,
                avg_spo2=99, duration_minutes=20, recovery_time_minutes=3
            )
            assert result["risk_level"] == "low"
            assert result["risk_score"] < 0.50
            assert "Safe to continue" in result["recommendation"]
        finally:
            self._restore(ml_prediction, orig)


# =============================================================================
# retraining_pipeline.py GAP COVERAGE (88% → 100%)
# Missing: evaluate_retraining_readiness (invalid date branch + both conditions met)
#          get_retraining_status (model_path.exists() path + metadata exists path)
#          save_retraining_metadata (file write error path)
#          prepare_training_data (no_valid_data path)
# =============================================================================

class TestRetrainingPipelineGaps:
    """Cover remaining gaps in retraining_pipeline.py."""

    def test_evaluate_readiness_invalid_date_parses_gracefully(self):
        """Covers the ValueError branch when last_retrain_date is invalid."""
        from app.services.retraining_pipeline import evaluate_retraining_readiness

        result = evaluate_retraining_readiness(
            new_records_count=200,
            last_retrain_date="not-a-valid-date",
            min_records=100
        )

        # Should still return without crashing
        assert "ready" in result
        assert any("parse" in r.lower() for r in result["reasons"])

    def test_evaluate_readiness_both_conditions_met(self):
        """All conditions met → reasons says 'all conditions'."""
        from app.services.retraining_pipeline import evaluate_retraining_readiness

        # Enough records, last retrain was 30 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        result = evaluate_retraining_readiness(
            new_records_count=200,
            last_retrain_date=old_date,
            min_records=100,
            min_days_since_last=7
        )

        assert result["ready"] is True
        assert any("all conditions" in r.lower() for r in result["reasons"])

    def test_evaluate_readiness_recent_retrain_not_ready(self):
        """Recent retrain (< 7 days) → not ready."""
        from app.services.retraining_pipeline import evaluate_retraining_readiness

        recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        result = evaluate_retraining_readiness(
            new_records_count=200,
            last_retrain_date=recent_date,
            min_records=100,
            min_days_since_last=7
        )

        assert result["ready"] is False

    def test_prepare_training_data_no_valid_records(self):
        """All records missing required fields → no_valid_data status."""
        from app.services.retraining_pipeline import prepare_training_data

        records = [
            {"heart_rate": 70},          # missing spo2 and risk_label
            {"spo2": 97},                 # missing heart_rate and risk_label
            {"risk_label": 0},            # missing heart_rate and spo2
        ]

        result = prepare_training_data(records)
        assert result["status"] == "no_valid_data"
        assert result["valid_records"] == 0
        assert result["skipped_records"] == 3

    def test_save_retraining_metadata_handles_write_error(self):
        """Write error is caught and returned in metadata dict."""
        from app.services.retraining_pipeline import save_retraining_metadata

        with patch("builtins.open", side_effect=PermissionError("Read only filesystem")):
            result = save_retraining_metadata(
                version="2.0",
                accuracy=0.95,
                records_used=500,
                notes="Test run"
            )

        assert "save_error" in result
        assert result["version"] == "2.0"

    def test_get_retraining_status_returns_dict_with_model_dir(self):
        """get_retraining_status returns expected keys."""
        from app.services.retraining_pipeline import get_retraining_status

        result = get_retraining_status()

        assert "model_dir" in result
        assert "model_exists" in result
        assert "metadata" in result


# =============================================================================
# recommendation_ranking.py GAP COVERAGE (92% → 100%)
# Missing: critical/high → mapped to "high" level branch,
#          level not in known levels → default "low" branch
# =============================================================================

class TestRecommendationRankingEdgeCases:
    """Cover remaining branches in recommendation_ranking.py."""

    def test_critical_risk_level_maps_to_high(self):
        """'critical' risk_level maps to 'high' recommendations."""
        from app.services.recommendation_ranking import get_ranked_recommendation

        result = get_ranked_recommendation(user_id=1, risk_level="critical")

        assert result["risk_level"] == "high"
        assert result["recommendation"]["intensity_level"] == "low"

    def test_high_risk_level_maps_to_high(self):
        """'high' risk_level correctly maps to high variant."""
        from app.services.recommendation_ranking import get_ranked_recommendation

        result = get_ranked_recommendation(user_id=1, risk_level="high")

        assert result["risk_level"] == "high"

    def test_unknown_risk_level_defaults_to_low(self):
        """Unknown risk_level (not moderate/low) defaults to 'low'."""
        from app.services.recommendation_ranking import get_ranked_recommendation

        result = get_ranked_recommendation(user_id=1, risk_level="unknown_level")

        assert result["risk_level"] == "low"


# =============================================================================
# explainability.py GAP COVERAGE (95% → 100%)
# Missing: explain_prediction when no top features (empty plain_explanation)
#          _estimate_contributions when typical=0
#          _generate_feature_explanation neutral direction
# =============================================================================

class TestExplainabilityGaps:
    """Cover remaining branches in explainability.py."""

    def test_explain_prediction_with_empty_features(self):
        """explain_prediction with no features_used → plain_explanation falls back."""
        from app.services.explainability import explain_prediction

        result = explain_prediction(
            prediction_result={
                "risk_score": 0.45,
                "risk_level": "low",
                "features_used": {}
            },
            feature_columns=[],
            model=None
        )

        assert "plain_explanation" in result
        assert "0.45" in result["plain_explanation"]

    def test_estimate_contributions_when_typical_is_zero(self):
        """_estimate_contributions: typical=0 → deviation=0 (no division by zero)."""
        from app.services.explainability import _estimate_contributions

        # 'hr_elevation' typical is 18, but if we use a feature not in _TYPICAL_VALUES
        # with value=0, typical defaults to value=0
        features = {"unknown_feature_xyz": 0.0}
        result = _estimate_contributions(
            features=features,
            feature_columns=["unknown_feature_xyz"],
            global_importances={}
        )

        assert "unknown_feature_xyz" in result
        assert result["unknown_feature_xyz"]["deviation"] == 0.0

    def test_estimate_contributions_neutral_direction(self):
        """_estimate_contributions: value == typical → contribution=0 → neutral direction."""
        from app.services.explainability import _estimate_contributions

        # age typical=55, if value=55 then deviation=0 → contribution=0 → neutral
        features = {"age": 55.0}
        result = _estimate_contributions(
            features=features,
            feature_columns=["age"],
            global_importances={"age": 0.5}
        )

        assert result["age"]["direction"] == "neutral"
        assert result["age"]["contribution"] == 0.0


# =============================================================================
# baseline_optimization.py GAP COVERAGE (94% → 100%)
# Missing: _std function when n=0/1, compute when no adjustment needed (edge)
# =============================================================================

class TestBaselineOptimizationGaps:
    """Cover remaining _std and compute branches."""

    def test_std_with_single_element_list(self):
        """_std with single element → std=0 (avoids division by zero)."""
        from app.services.baseline_optimization import _std

        result = _std([70])
        assert result == 0.0

    def test_compute_with_small_dataset_still_works(self):
        """5 valid readings with different baseline → still computes."""
        from app.services.baseline_optimization import compute_optimized_baseline

        readings = [{"heart_rate": hr} for hr in [65, 66, 67, 68, 69]]
        result = compute_optimized_baseline(readings, current_baseline=80)

        assert result["status"] == "ok"
        assert result["new_baseline"] < 80


# =============================================================================
# anomaly_detection.py GAP COVERAGE (98% → 100%)
# Missing: _std function with single element (similar to baseline_optimization)
# =============================================================================

class TestAnomalyDetectionStd:
    """Cover _std edge case in anomaly_detection.py."""

    def test_std_with_single_value_returns_zero(self):
        """_std with one element should return 0 without error."""
        from app.services.anomaly_detection import _std

        result = _std([75])
        assert result == 0.0
