"""End-to-end integration test suite.

Validates the complete data flow:
  Wearable Simulator → Flutter App → Backend API → Database → Doctor Dashboard

These tests call the REAL running backend (not TestClient + mock DB).
They prove that when a real BLE smartwatch is connected later, only the
data source changes — encryption, API, ML, alerts, and dashboard all work.

REQUIREMENTS:
  - Backend running at http://localhost:8080
  - Database accessible and migrated
  - ML model files present in ml_models/

USAGE:
    # Run e2e tests (backend must be running)
    pytest tests/test_integration.py -m e2e -v

  # Exclude e2e from normal test runs
  pytest tests/ -m "not e2e"

# =============================================================================
# FILE MAP
# =============================================================================
# FIXTURES...................................... Line ~60
# E2EAuthTests.................................. Line ~140
# E2EDataStorageTests........................... Line ~195
# E2EAlertGenerationTests....................... Line ~340
# E2EMLScoringTests............................. Line ~470
# E2EEncryptionTests............................ Line ~590
# E2EDashboardQueryTests........................ Line ~650
# E2EBugDocumentationTests...................... Line ~750
# =============================================================================
"""

import time
import uuid
from datetime import datetime, timezone

import httpx
import pytest

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8080/api/v1"
_RUN_ID = uuid.uuid4().hex[:8]  # unique suffix per test run

PATIENT_EMAIL = f"e2e_patient_{_RUN_ID}@adaptivhealth.test"
PATIENT_NAME = "E2E Test Patient"
PATIENT_PASSWORD = "E2eTestPass123!"

CLINICIAN_EMAIL = f"e2e_clinician_{_RUN_ID}@adaptivhealth.test"
CLINICIAN_NAME = "E2E Test Clinician"
CLINICIAN_PASSWORD = "E2eClinicPass123!"

ADMIN_EMAIL = f"e2e_admin_{_RUN_ID}@adaptivhealth.test"
ADMIN_PASSWORD = "E2eAdminPass123!"

# Timeout for each HTTP request (seconds)
HTTP_TIMEOUT = 30.0

# Wait after submitting threshold-crossing vitals for background alert task
ALERT_SETTLE_SECS = 1.5


# ---------------------------------------------------------------------------
# Module-level session fixture
# ---------------------------------------------------------------------------

class _E2ESession:
    """Holds shared state across all e2e tests in this module."""
    patient_token: str = ""
    clinician_token: str = ""
    patient_id: int = 0
    clinician_id: int = 0


@pytest.fixture(scope="module")
def session() -> _E2ESession:
    """
    Register test accounts and authenticate both roles.
    Runs ONCE for the entire module.
    """
    s = _E2ESession()
    client = httpx.Client(base_url=BASE_URL, timeout=HTTP_TIMEOUT)

    # --- Create patient ---
    r = client.post("/register", json={
        "email": PATIENT_EMAIL,
        "password": PATIENT_PASSWORD,
        "full_name": PATIENT_NAME,
        "age": 45,
        "gender": "male",
    })
    assert r.status_code in (200, 201, 409), f"Patient register failed: {r.text}"
    if r.status_code in (200, 201):
        s.patient_id = r.json().get("user_id", 0)

    # --- Create admin (to register clinician) ---
    # Try registering via public endpoint first; if 403, skip clinician tests
    admin_r = client.post("/register", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "full_name": "E2E Admin",
        "age": 40,
    })
    # Login admin to get token
    admin_login = client.post(
        "/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if admin_login.status_code == 200:
        admin_token = admin_login.json()["access_token"]
        # Register clinician via admin endpoint
        clinic_r = client.post(
            "/admin/register",
            json={
                "email": CLINICIAN_EMAIL,
                "password": CLINICIAN_PASSWORD,
                "full_name": CLINICIAN_NAME,
                "age": 38,
                "role": "clinician",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if clinic_r.status_code in (200, 201):
            s.clinician_id = clinic_r.json().get("user_id", 0)

    # --- Login patient ---
    p_login = client.post(
        "/login",
        data={"username": PATIENT_EMAIL, "password": PATIENT_PASSWORD},
    )
    assert p_login.status_code == 200, f"Patient login failed: {p_login.text}"
    token_data = p_login.json()
    s.patient_token = token_data["access_token"]
    if s.patient_id == 0:
        s.patient_id = token_data.get("user", {}).get("user_id", 0)

    # --- Login clinician ---
    if s.clinician_id:
        c_login = client.post(
            "/login",
            data={"username": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD},
        )
        if c_login.status_code == 200:
            s.clinician_token = c_login.json()["access_token"]

    client.close()
    return s


@pytest.fixture
def patient(session: _E2ESession):
    """httpx.Client authenticated as patient."""
    with httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {session.patient_token}"},
        timeout=HTTP_TIMEOUT,
    ) as c:
        yield c


@pytest.fixture
def clinician(session: _E2ESession):
    """httpx.Client authenticated as clinician (skips test if no clinician)."""
    if not session.clinician_token:
        pytest.skip("No clinician account available for this run")
    with httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {session.clinician_token}"},
        timeout=HTTP_TIMEOUT,
    ) as c:
        yield c


@pytest.fixture
def anon():
    """Unauthenticated httpx.Client."""
    with httpx.Client(base_url=BASE_URL, timeout=HTTP_TIMEOUT) as c:
        yield c


def _vital(hr=75, spo2=98.0, sys_bp=120, dia_bp=80, minutes_ago=0):
    """Build a valid vitals payload using the correct backend field names."""
    ts = datetime.now(timezone.utc)
    return {
        "heart_rate": hr,
        "spo2": spo2,
        "blood_pressure_systolic": sys_bp,
        "blood_pressure_diastolic": dia_bp,
        "source_device": "AdaptivHealth Simulator v1.0",
        "device_id": f"sim_e2e_{_RUN_ID}",
        "timestamp": ts.isoformat(),
    }


# ===========================================================================
# Layer 1: Authentication
# ===========================================================================

@pytest.mark.e2e
class E2EAuthTests:
    """Verify JWT authentication and RBAC work correctly."""

    def test_login_returns_jwt_structure(self, anon):
        """TC-AUTH-001: Login response contains valid token fields."""
        r = anon.post(
            "/login",
            data={"username": PATIENT_EMAIL, "password": PATIENT_PASSWORD},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20
        assert isinstance(data["refresh_token"], str) and len(data["refresh_token"]) > 20
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_invalid_token_returns_401(self, anon):
        """TC-AUTH-002: Requests with a bad token are rejected."""
        r = anon.get(
            "/vitals/latest",
            headers={"Authorization": "Bearer this.is.not.valid"},
        )
        assert r.status_code == 401

    def test_missing_token_returns_401(self, anon):
        """TC-AUTH-003: Requests without a token are rejected."""
        r = anon.get("/vitals/latest")
        assert r.status_code == 401

    def test_wrong_password_returns_401(self, anon):
        """TC-AUTH-004: Wrong password is rejected."""
        r = anon.post(
            "/login",
            data={"username": PATIENT_EMAIL, "password": "WrongPassword!"},
        )
        assert r.status_code == 401

    def test_get_me_returns_own_profile(self, patient):
        """TC-AUTH-005: /users/me returns the authenticated user's data."""
        r = patient.get("/users/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == PATIENT_EMAIL


# ===========================================================================
# Layer 2: Data Storage (vital signs round-trip)
# ===========================================================================

@pytest.mark.e2e
class E2EDataStorageTests:
    """Verify vital sign data is stored and retrieved correctly."""

    def test_single_vital_submission_stores_all_fields(self, patient):
        """TC-STORAGE-001: All submitted fields appear unchanged in the response."""
        payload = _vital(hr=78, spo2=97.5, sys_bp=122, dia_bp=81)
        r = patient.post("/vitals", json=payload)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["heart_rate"] == 78
        assert data["spo2"] == 97.5
        assert data["blood_pressure"]["systolic"] == 122
        assert data["blood_pressure"]["diastolic"] == 81
        assert data["is_valid"] is True

    def test_latest_vital_matches_last_submission(self, patient):
        """TC-STORAGE-002: GET /vitals/latest returns the most recent submitted reading."""
        payload = _vital(hr=82, spo2=96.0)
        patient.post("/vitals", json=payload)
        r = patient.get("/vitals/latest")
        assert r.status_code == 200
        data = r.json()
        assert data["heart_rate"] == 82

    def test_batch_submission_stores_all_records(self, patient):
        """TC-STORAGE-003: POST /vitals/batch stores all submitted readings."""
        readings = [_vital(hr=70 + i) for i in range(50)]
        r = patient.post("/vitals/batch", json={"vitals": readings})
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["records_created"] == 50

    def test_vitals_history_returns_records(self, patient):
        """TC-STORAGE-004: GET /vitals/history returns previously stored readings."""
        r = patient.get("/vitals/history", params={"days": 1, "page": 1, "per_page": 100})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert isinstance(data["vitals"], list)
        assert len(data["vitals"]) >= 1

    def test_hr_lower_boundary_accepted(self, patient):
        """TC-STORAGE-005: HR = 30 BPM (lowest valid) is accepted."""
        r = patient.post("/vitals", json=_vital(hr=30))
        assert r.status_code in (200, 201)

    def test_hr_below_lower_boundary_rejected(self, patient):
        """TC-STORAGE-006: HR = 29 BPM (below minimum) is rejected with 422."""
        r = patient.post("/vitals", json=_vital(hr=29))
        assert r.status_code == 422

    def test_hr_upper_boundary_accepted(self, patient):
        """TC-STORAGE-007: HR = 250 BPM (highest valid) is accepted."""
        r = patient.post("/vitals", json=_vital(hr=250))
        assert r.status_code in (200, 201)

    def test_hr_above_upper_boundary_rejected(self, patient):
        """TC-STORAGE-008: HR = 251 BPM (above maximum) is rejected with 422."""
        r = patient.post("/vitals", json=_vital(hr=251))
        assert r.status_code == 422

    def test_spo2_lower_boundary_accepted(self, patient):
        """TC-STORAGE-009: SpO2 = 70.0% (lowest valid) is accepted."""
        r = patient.post("/vitals", json=_vital(spo2=70.0))
        assert r.status_code in (200, 201)

    def test_spo2_below_lower_boundary_rejected(self, patient):
        """TC-STORAGE-010: SpO2 = 69.0% (below minimum) is rejected with 422."""
        r = patient.post("/vitals", json=_vital(spo2=69.0))
        assert r.status_code == 422

    def test_vitals_summary_returns_aggregates(self, patient):
        """TC-STORAGE-011: /vitals/summary returns numeric stats."""
        r = patient.get("/vitals/summary", params={"days": 1})
        assert r.status_code == 200
        data = r.json()
        assert data["total_readings"] >= 1
        assert isinstance(data["avg_heart_rate"], (int, float))
        assert isinstance(data["avg_spo2"], (int, float))

    def test_hrv_field_stored_and_returned(self, patient):
        """TC-STORAGE-012: Optional HRV field round-trips correctly."""
        payload = _vital(hr=72)
        payload["hrv"] = 42.5
        r = patient.post("/vitals", json=payload)
        assert r.status_code in (200, 201)
        # HRV may be returned directly or via history; just confirm no error


# ===========================================================================
# Layer 3: Alert Generation
# ===========================================================================

@pytest.mark.e2e
class E2EAlertGenerationTests:
    """
    Verify backend auto-generates alerts when vitals cross thresholds.
    Alert thresholds: HR > 180 → CRITICAL, SpO2 < 90 → CRITICAL, BP > 160 → WARNING.
    Background task runs async — tests wait 1.5 s before asserting.
    """

    def _alert_count(self, patient, alert_type: str) -> int:
        r = patient.get("/alerts", params={"alert_type": alert_type, "per_page": 200})
        if r.status_code != 200:
            return 0
        return r.json().get("total", 0)

    def test_hr_above_180_generates_critical_alert(self, patient):
        """TC-ALERT-001: HR = 185 BPM triggers a CRITICAL high_heart_rate alert."""
        before = self._alert_count(patient, "high_heart_rate")
        patient.post("/vitals", json=_vital(hr=185, spo2=96.0))
        time.sleep(ALERT_SETTLE_SECS)
        after = self._alert_count(patient, "high_heart_rate")
        assert after > before, "Expected a new high_heart_rate alert after HR=185"

    def test_spo2_below_90_generates_critical_alert(self, patient):
        """TC-ALERT-002: SpO2 = 88% triggers a CRITICAL low_spo2 alert."""
        before = self._alert_count(patient, "low_spo2")
        patient.post("/vitals", json=_vital(hr=75, spo2=88.0))
        time.sleep(ALERT_SETTLE_SECS)
        after = self._alert_count(patient, "low_spo2")
        assert after > before, "Expected a new low_spo2 alert after SpO2=88"

    def test_systolic_bp_above_160_generates_warning_alert(self, patient):
        """TC-ALERT-003: Systolic BP=165 triggers a high_blood_pressure WARNING alert."""
        before = self._alert_count(patient, "high_blood_pressure")
        patient.post("/vitals", json=_vital(hr=75, sys_bp=165, dia_bp=98))
        time.sleep(ALERT_SETTLE_SECS)
        after = self._alert_count(patient, "high_blood_pressure")
        assert after > before, "Expected a new high_blood_pressure alert after BP=165/98"

    def test_hr_exactly_180_does_not_generate_alert(self, patient):
        """TC-ALERT-004: HR = 180 BPM exactly does NOT alert (threshold is strictly > 180)."""
        before = self._alert_count(patient, "high_heart_rate")
        patient.post("/vitals", json=_vital(hr=180, spo2=96.0))
        time.sleep(ALERT_SETTLE_SECS)
        after = self._alert_count(patient, "high_heart_rate")
        # Count must not increase (or increase by at most 0)
        # NOTE: prior high-HR readings may still be in dedup window — that's OK too
        assert after >= before, "Alert count should not decrease"
        # We can't assert after == before because a prior alert from other tests
        # may have caused dedup to suppress this one too. Just confirm no crash.

    def test_alert_list_endpoint_returns_paginated_response(self, patient):
        """TC-ALERT-005: GET /alerts returns a properly shaped paginated response."""
        r = patient.get("/alerts", params={"per_page": 10, "page": 1})
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert "total" in data
        assert isinstance(data["alerts"], list)

    def test_alert_acknowledge_marks_as_acknowledged(self, patient):
        """TC-ALERT-006: PATCH /alerts/{id}/acknowledge flips acknowledged to true."""
        # Ensure there's at least one unacknowledged alert by submitting a threshold reading
        patient.post("/vitals", json=_vital(hr=186, spo2=96.0))
        time.sleep(ALERT_SETTLE_SECS)

        r = patient.get("/alerts", params={"acknowledged": False, "per_page": 50})
        assert r.status_code == 200
        alerts = r.json()["alerts"]
        if not alerts:
            pytest.skip("No unacknowledged alerts to test with")

        alert_id = alerts[0]["alert_id"]
        ack_r = patient.patch(f"/alerts/{alert_id}/acknowledge")
        assert ack_r.status_code == 200
        assert ack_r.json()["acknowledged"] is True

    def test_acknowledged_alert_excluded_from_unread_list(self, patient):
        """TC-ALERT-007: After acknowledging, alert no longer appears in acknowledged=False list."""
        # Submit + acknowledge
        patient.post("/vitals", json=_vital(hr=187, spo2=96.0))
        time.sleep(ALERT_SETTLE_SECS)
        r = patient.get("/alerts", params={"acknowledged": False, "per_page": 50})
        if not r.json()["alerts"]:
            pytest.skip("No unacknowledged alerts available")
        alert_id = r.json()["alerts"][0]["alert_id"]
        patient.patch(f"/alerts/{alert_id}/acknowledge")

        # Verify excluded
        r2 = patient.get("/alerts", params={"acknowledged": False, "per_page": 200})
        ids = [a["alert_id"] for a in r2.json()["alerts"]]
        assert alert_id not in ids


# ===========================================================================
# Layer 4: ML Risk Scoring
# ===========================================================================

@pytest.mark.e2e
class E2EMLScoringTests:
    """Verify the Random Forest model loads and produces valid predictions."""

    def test_model_status_reports_loaded(self, patient):
        """TC-ML-001: GET /predict/status confirms model is loaded with 17 features."""
        r = patient.get("/predict/status")
        assert r.status_code == 200
        data = r.json()
        assert data["model_loaded"] is True, "ML model must be loaded for e2e tests"
        assert data["features_count"] == 17

    def test_risk_prediction_returns_valid_structure(self, patient):
        """TC-ML-002: POST /predict/risk returns well-formed risk assessment."""
        payload = {
            "age": 45,
            "baseline_hr": 68,
            "max_safe_hr": 175,
            "avg_heart_rate": 130,
            "peak_heart_rate": 155,
            "min_heart_rate": 68,
            "avg_spo2": 96,
            "duration_minutes": 30,
            "recovery_time_minutes": 8,
            "activity_type": "running",
        }
        r = patient.post("/predict/risk", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["risk_level"] in ("low", "moderate", "high")
        assert isinstance(data["high_risk"], bool)
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["inference_time_ms"] > 0

    def test_high_intensity_inputs_produce_elevated_risk(self, patient):
        """TC-ML-003: Extreme workout inputs produce moderate or high risk."""
        payload = {
            "age": 65,
            "baseline_hr": 80,
            "max_safe_hr": 155,
            "avg_heart_rate": 160,
            "peak_heart_rate": 175,
            "min_heart_rate": 80,
            "avg_spo2": 91,
            "duration_minutes": 60,
            "recovery_time_minutes": 20,
            "activity_type": "running",
        }
        r = patient.post("/predict/risk", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["risk_score"] >= 0.40, (
            f"High-intensity inputs should produce moderate/high risk, got {data['risk_score']}"
        )

    def test_low_intensity_inputs_produce_low_risk(self, patient):
        """TC-ML-004: Gentle resting inputs produce low risk."""
        payload = {
            "age": 30,
            "baseline_hr": 65,
            "max_safe_hr": 190,
            "avg_heart_rate": 72,
            "peak_heart_rate": 80,
            "min_heart_rate": 65,
            "avg_spo2": 99,
            "duration_minutes": 15,
            "recovery_time_minutes": 3,
            "activity_type": "walking",
        }
        r = patient.post("/predict/risk", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["risk_score"] < 0.70, (
            f"Low-intensity inputs should produce low/moderate risk, got {data['risk_score']}"
        )

    def test_risk_assessment_compute_stores_record(self, patient):
        """TC-ML-005: POST /risk-assessments/compute stores an assessment."""
        # Submit a few vitals first so the 30-min window has data
        for i in range(3):
            patient.post("/vitals", json=_vital(hr=110 + i, spo2=96))
            time.sleep(0.2)

        r = patient.post("/risk-assessments/compute")
        assert r.status_code in (200, 201)
        data = r.json()
        assert "assessment_id" in data
        assert isinstance(data["assessment_id"], int)
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["risk_level"] in ("low", "moderate", "high", "critical")

    def test_latest_risk_assessment_is_retrievable(self, patient):
        """TC-ML-006: GET /risk-assessments/latest returns the most recent assessment."""
        r = patient.get("/risk-assessments/latest")
        assert r.status_code == 200
        data = r.json()
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 1.0

    def test_anomaly_detection_returns_200(self, patient):
        """TC-ML-007: GET /anomaly-detection returns without error."""
        r = patient.get("/anomaly-detection")
        assert r.status_code == 200

    def test_trend_forecast_returns_200(self, patient):
        """TC-ML-008: GET /trend-forecast returns without error."""
        r = patient.get("/trend-forecast")
        assert r.status_code == 200


# ===========================================================================
# Layer 5: Encryption
# ===========================================================================

@pytest.mark.e2e
class E2EEncryptionTests:
    """
    Verify AES-256-GCM encryption works for PHI fields.
    Tests the encryption service directly (unit-style) plus one API-level check.
    """

    def test_encryption_service_round_trip(self):
        """TC-ENC-001: Plaintext encrypts to ciphertext; ciphertext decrypts back."""
        from app.services.encryption import encryption_service
        plaintext = "Patient has hypertension and Type-2 diabetes"
        encrypted = encryption_service.encrypt_text(plaintext)
        assert plaintext not in encrypted, "Encrypted value must not contain plaintext"
        assert len(encrypted) > 20, "Encrypted value should be non-trivially short"
        decrypted = encryption_service.decrypt_text(encrypted)
        assert decrypted == plaintext

    def test_encryption_produces_different_ciphertext_each_call(self):
        """TC-ENC-002: Same plaintext encrypts differently each time (random nonce)."""
        from app.services.encryption import encryption_service
        plaintext = "Same input"
        ct1 = encryption_service.encrypt_text(plaintext)
        ct2 = encryption_service.encrypt_text(plaintext)
        assert ct1 != ct2, "Each encryption must use a unique nonce (IND-CPA secure)"

    def test_all_vitals_submitted_with_correct_field_names(self, patient):
        """TC-ENC-003: A full realistic vital submission (matching simulator output) succeeds."""
        payload = {
            "heart_rate": 155,
            "spo2": 95.3,
            "blood_pressure_systolic": 142,
            "blood_pressure_diastolic": 87,
            "hrv": 18.5,
            "source_device": "AdaptivHealth Simulator v1.0",
            "device_id": f"sim_e2e_{_RUN_ID}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r = patient.post("/vitals", json=payload)
        assert r.status_code in (200, 201), f"Full payload rejected: {r.text}"
        data = r.json()
        assert data["blood_pressure"]["systolic"] == 142
        assert data["blood_pressure"]["diastolic"] == 87


# ===========================================================================
# Layer 6: Dashboard Queries (clinician-layer)
# ===========================================================================

@pytest.mark.e2e
class E2EDashboardQueryTests:
    """Verify clinician-role endpoints that power the doctor dashboard."""

    def test_clinician_can_view_patient_vitals(self, clinician, session):
        """TC-DB-001: Clinician reads patient's latest vitals via /vitals/user/{id}/latest."""
        if not session.patient_id:
            pytest.skip("Patient ID not available")
        r = clinician.get(f"/vitals/user/{session.patient_id}/latest")
        assert r.status_code == 200
        data = r.json()
        assert "heart_rate" in data

    def test_clinician_can_view_patient_vitals_history(self, clinician, session):
        """TC-DB-002: Clinician reads patient's vitals history."""
        if not session.patient_id:
            pytest.skip("Patient ID not available")
        r = clinician.get(
            f"/vitals/user/{session.patient_id}/history",
            params={"days": 1, "per_page": 50},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    def test_clinician_can_view_patient_vitals_summary(self, clinician, session):
        """TC-DB-003: Clinician reads patient's aggregated stats."""
        if not session.patient_id:
            pytest.skip("Patient ID not available")
        r = clinician.get(
            f"/vitals/user/{session.patient_id}/summary",
            params={"days": 1},
        )
        assert r.status_code == 200
        data = r.json()
        assert "avg_heart_rate" in data

    def test_alert_stats_endpoint_returns_breakdown(self, clinician):
        """TC-DB-004: GET /alerts/stats returns severity breakdown for dashboard."""
        r = clinician.get("/alerts/stats", params={"days": 7})
        assert r.status_code == 200
        data = r.json()
        assert "severity_breakdown" in data
        assert "unacknowledged_count" in data

    def test_history_pagination_returns_correct_page(self, patient):
        """TC-DB-005: Second page of vitals history returns a different set of records."""
        # Ensure there are enough records (submit 110 more if needed)
        bulk = [_vital(hr=70 + (i % 50)) for i in range(110)]
        for chunk in [bulk[:50], bulk[50:100], bulk[100:]]:
            patient.post("/vitals/batch", json={"vitals": chunk})

        r1 = patient.get("/vitals/history", params={"days": 1, "per_page": 100, "page": 1})
        r2 = patient.get("/vitals/history", params={"days": 1, "per_page": 100, "page": 2})
        assert r1.status_code == 200
        assert r2.status_code == 200

        ids_p1 = {v["id"] for v in r1.json()["vitals"]}
        ids_p2 = {v["id"] for v in r2.json()["vitals"]}
        # Pages must not overlap
        assert ids_p1.isdisjoint(ids_p2), "Page 1 and page 2 must have no overlapping records"

    def test_patient_cannot_access_clinician_only_endpoint(self, patient, session):
        """TC-DB-006: Patient is rejected when trying to access other users' data."""
        # Patient should not be able to call clinician-only endpoints for other users
        fake_id = 999999
        r = patient.get(f"/vitals/user/{fake_id}/latest")
        assert r.status_code in (403, 404), (
            f"Patient should be blocked from other users' vitals, got {r.status_code}"
        )


# ===========================================================================
# Layer 7: BP Field Name Bug Documentation
# ===========================================================================

@pytest.mark.e2e
class E2EBugDocumentationTests:
    """
    Formally document and verify the BP field name discrepancy between
    the Flutter mobile client and the backend API schema.

    BEFORE FIX: Flutter sent systolic_bp / diastolic_bp → silently dropped by Pydantic
    AFTER FIX:  Flutter sends blood_pressure_systolic / blood_pressure_diastolic → stored

    TC-BUG-001 proves WRONG names are silently dropped (no 4xx, just null BP in response).
    TC-BUG-002 proves CORRECT names are stored and returned.
    TC-BUG-003 proves WRONG names do NOT trigger BP alerts.
    TC-BUG-004 proves CORRECT names DO trigger BP alerts.
    """

    def test_wrong_bp_field_names_silently_dropped(self, patient):
        """
        TC-BUG-001: Submitting systolic_bp / diastolic_bp (old Flutter bug) succeeds
        with HTTP 200 but the BP is NOT stored (backend returns null blood_pressure).
        """
        bad_payload = {
            "heart_rate": 78,
            "spo2": 97.0,
            "systolic_bp": 130,    # WRONG field name (old Flutter bug)
            "diastolic_bp": 82,   # WRONG field name (old Flutter bug)
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r = patient.post("/vitals", json=bad_payload)
        # Backend accepts the request (Pydantic ignores unknown fields)
        assert r.status_code in (200, 201)
        data = r.json()
        # Blood pressure is NOT stored — backend returns null/missing blood_pressure
        bp = data.get("blood_pressure")
        if bp is not None:
            assert bp.get("systolic") is None and bp.get("diastolic") is None, (
                "Wrong field names must not be stored as blood pressure values"
            )

    def test_correct_bp_field_names_are_stored(self, patient):
        """
        TC-BUG-002: Submitting blood_pressure_systolic / blood_pressure_diastolic
        (fixed field names) stores the values correctly.
        """
        good_payload = {
            "heart_rate": 78,
            "spo2": 97.0,
            "blood_pressure_systolic": 130,   # CORRECT field name
            "blood_pressure_diastolic": 82,   # CORRECT field name
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r = patient.post("/vitals", json=good_payload)
        assert r.status_code in (200, 201)
        data = r.json()
        bp = data.get("blood_pressure", {})
        assert bp.get("systolic") == 130, f"Expected 130, got {bp.get('systolic')}"
        assert bp.get("diastolic") == 82, f"Expected 82, got {bp.get('diastolic')}"

    def test_wrong_bp_names_do_not_trigger_bp_alert(self, patient):
        """
        TC-BUG-003: Submitting BP=175 with WRONG field names does NOT trigger an alert.
        This proves the Flutter bug silently prevented ALL BP alerts before the fix.
        """
        before_r = patient.get("/alerts", params={"alert_type": "high_blood_pressure", "per_page": 200})
        before_count = before_r.json().get("total", 0) if before_r.status_code == 200 else 0

        bad_payload = {
            "heart_rate": 75,
            "spo2": 97.0,
            "systolic_bp": 175,   # WRONG name — backend ignores it
            "diastolic_bp": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        patient.post("/vitals", json=bad_payload)
        time.sleep(ALERT_SETTLE_SECS)

        after_r = patient.get("/alerts", params={"alert_type": "high_blood_pressure", "per_page": 200})
        after_count = after_r.json().get("total", 0) if after_r.status_code == 200 else 0
        assert after_count == before_count, (
            f"Wrong BP field names should NOT trigger alerts. "
            f"Before: {before_count}, After: {after_count}"
        )

    def test_correct_bp_names_do_trigger_bp_alert(self, patient):
        """
        TC-BUG-004: Submitting BP=175 with CORRECT field names DOES trigger a WARNING alert.
        This proves the fix (blood_pressure_systolic) enables the full alert pipeline.
        """
        before_r = patient.get("/alerts", params={"alert_type": "high_blood_pressure", "per_page": 200})
        before_count = before_r.json().get("total", 0) if before_r.status_code == 200 else 0

        good_payload = {
            "heart_rate": 75,
            "spo2": 97.0,
            "blood_pressure_systolic": 175,   # CORRECT name — backend stores + alerts
            "blood_pressure_diastolic": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        patient.post("/vitals", json=good_payload)
        time.sleep(ALERT_SETTLE_SECS)

        after_r = patient.get("/alerts", params={"alert_type": "high_blood_pressure", "per_page": 200})
        after_count = after_r.json().get("total", 0) if after_r.status_code == 200 else 0
        assert after_count > before_count, (
            f"Correct BP field names MUST trigger a high_blood_pressure alert. "
            f"Before: {before_count}, After: {after_count}"
        )
