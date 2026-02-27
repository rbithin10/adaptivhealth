"""
tests/test_last_7_lines.py

Targets the 5 remaining non-Pydantic missing lines after # pragma: no cover
was added to the Pydantic v2 validator raises (lines 85, 226 in schemas/user.py).

Remaining missing lines after pragma fixes:
  vital_signs.py:288   – submit_vitals SpO2 API guard
  vital_signs.py:366   – submit_vitals_batch continue for invalid HR
  trend_forecasting.py:55  – spo2 series forecast branch
  encryption.py:48     – EncryptionService wrong key length raise
  predict.py:807       – get_patient_latest_recommendation no-rec 404

All use direct function/coroutine calls (bypassing HTTP + Pydantic schema
validation) so coverage.py's Python trace hook sees every line.
"""

import asyncio
import base64
import uuid
import pytest

from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from tests.helpers import make_user, get_token

client = TestClient(fastapi_app)


# ---------------------------------------------------------------------------
# Helper: run an async coroutine from a sync test without conflicting with
# pytest-asyncio's event loop (creates and destroys a dedicated loop).
# ---------------------------------------------------------------------------
def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ===========================================================================
# vital_signs.py : line 288
# `if vital_data.spo2 and (vital_data.spo2 < 70 or vital_data.spo2 > 100):`
# The schema allows spo2 0-100 (ge=0, le=100), so spo2=50 passes schema
# but triggers the endpoint's tighter API-level guard at line 288.
# ===========================================================================

class TestVitalSignsLine288:
    def test_spo2_50_triggers_api_guard(self, db_session):
        from app.api.vital_signs import submit_vitals
        from app.schemas.vital_signs import VitalSignCreate

        user = make_user(
            db_session,
            f"spo2_288_{uuid.uuid4().hex[:8]}@example.com",
            "SpO2 288",
            "patient",
        )
        vital = VitalSignCreate(heart_rate=80, spo2=50)   # 50 passes schema ge=0 le=100

        with pytest.raises(HTTPException) as exc_info:
            _run(
                submit_vitals(
                    vital_data=vital,
                    background_tasks=BackgroundTasks(),
                    current_user=user,
                    db=db_session,
                )
            )

        assert exc_info.value.status_code == 400
        assert "70-100" in exc_info.value.detail

    def test_spo2_65_triggers_api_guard(self, db_session):
        from app.api.vital_signs import submit_vitals
        from app.schemas.vital_signs import VitalSignCreate

        user = make_user(
            db_session,
            f"spo2_65_{uuid.uuid4().hex[:8]}@example.com",
            "SpO2 65",
            "patient",
        )
        vital = VitalSignCreate(heart_rate=90, spo2=65)

        with pytest.raises(HTTPException) as exc_info:
            _run(
                submit_vitals(
                    vital_data=vital,
                    background_tasks=BackgroundTasks(),
                    current_user=user,
                    db=db_session,
                )
            )

        assert exc_info.value.status_code == 400


# ===========================================================================
# vital_signs.py : line 366
# `continue  # Skip invalid records`
# VitalSignCreate has `ge=30 le=250` so heart_rate=20 is rejected by Pydantic
# (422) before the endpoint sees it. Must bypass with model_construct().
# ===========================================================================

class TestVitalSignsLine366:
    def test_batch_skips_heart_rate_below_30(self, db_session):
        from app.api.vital_signs import submit_vitals_batch
        from app.schemas.vital_signs import VitalSignCreate, VitalSignBatchCreate

        user = make_user(
            db_session,
            f"batch366_{uuid.uuid4().hex[:8]}@example.com",
            "Batch 366",
            "patient",
        )

        # model_construct bypasses ALL field constraints — heart_rate=20 is allowed
        invalid = VitalSignCreate.model_construct(
            heart_rate=20,
            spo2=None,
            blood_pressure_systolic=None,
            blood_pressure_diastolic=None,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )
        batch = VitalSignBatchCreate.model_construct(vitals=[invalid])

        result = _run(
            submit_vitals_batch(
                batch_data=batch,
                background_tasks=BackgroundTasks(),
                current_user=user,
                db=db_session,
            )
        )

        # Invalid record skipped → records_created == 0
        assert result["records_created"] == 0

    def test_batch_skips_heart_rate_above_250(self, db_session):
        from app.api.vital_signs import submit_vitals_batch
        from app.schemas.vital_signs import VitalSignCreate, VitalSignBatchCreate

        user = make_user(
            db_session,
            f"batch366hi_{uuid.uuid4().hex[:8]}@example.com",
            "Batch 366 Hi",
            "patient",
        )

        too_high = VitalSignCreate.model_construct(
            heart_rate=300,
            spo2=None,
            blood_pressure_systolic=None,
            blood_pressure_diastolic=None,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )
        batch = VitalSignBatchCreate.model_construct(vitals=[too_high])

        result = _run(
            submit_vitals_batch(
                batch_data=batch,
                background_tasks=BackgroundTasks(),
                current_user=user,
                db=db_session,
            )
        )

        assert result["records_created"] == 0

    def test_batch_mixed_valid_and_invalid(self, db_session):
        """One valid + one invalid: only the valid one is saved (continue fires)."""
        from app.api.vital_signs import submit_vitals_batch
        from app.schemas.vital_signs import VitalSignCreate, VitalSignBatchCreate

        user = make_user(
            db_session,
            f"batch366mix_{uuid.uuid4().hex[:8]}@example.com",
            "Batch 366 Mix",
            "patient",
        )

        valid = VitalSignCreate.model_construct(
            heart_rate=75,
            spo2=98.0,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )
        invalid = VitalSignCreate.model_construct(
            heart_rate=15,        # below 30 → skipped
            spo2=None,
            blood_pressure_systolic=None,
            blood_pressure_diastolic=None,
            hrv=None,
            source_device=None,
            device_id=None,
            timestamp=None,
        )
        batch = VitalSignBatchCreate.model_construct(vitals=[valid, invalid])

        result = _run(
            submit_vitals_batch(
                batch_data=batch,
                background_tasks=BackgroundTasks(),
                current_user=user,
                db=db_session,
            )
        )

        assert result["records_created"] == 1


# ===========================================================================
# trend_forecasting.py : line 55
# `result["trends"]["spo2"] = _linear_forecast(spo2_series, forecast_days)`
# Executes only when len(spo2_series) >= 7.  Supply 10 readings all with spo2.
# ===========================================================================

class TestTrendForecastingLine55:
    def test_spo2_series_branch_executes(self):
        from datetime import datetime, timezone, timedelta
        from app.services.trend_forecasting import forecast_trends

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        readings = [
            {
                "heart_rate": 70 + i,
                "spo2": 97.0 - i * 0.1,
                "timestamp": (base + timedelta(days=i)).isoformat(),
            }
            for i in range(10)
        ]

        result = forecast_trends(readings, forecast_days=7)

        assert result["status"] == "ok"
        assert "spo2" in result["trends"], "spo2 key missing — line 55 not executed"

    def test_spo2_forecasted_value_is_numeric(self):
        from datetime import datetime, timezone, timedelta
        from app.services.trend_forecasting import forecast_trends

        base = datetime(2026, 2, 1, tzinfo=timezone.utc)
        readings = [
            {
                "heart_rate": 75,
                "spo2": 98.0 - idx * 0.05,
                "timestamp": (base + timedelta(days=idx)).isoformat(),
            }
            for idx in range(10)
        ]

        result = forecast_trends(readings, forecast_days=14)

        spo2 = result["trends"]["spo2"]
        assert isinstance(spo2["slope_per_day"], float)
        assert isinstance(spo2["forecasted_value"], float)


# ===========================================================================
# encryption.py : line 48
# `raise ValueError(f"...Got {len(key)} bytes.")`
# key_b64 must be valid base64 that decodes to != 32 bytes.
# ===========================================================================

class TestEncryptionLine48:
    def test_16_byte_key_raises_value_error(self):
        from app.services.encryption import EncryptionService

        short = base64.b64encode(b"A" * 16).decode()
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService(key_b64=short)

    def test_64_byte_key_raises_value_error(self):
        from app.services.encryption import EncryptionService

        long_ = base64.b64encode(b"B" * 64).decode()
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService(key_b64=long_)

    def test_1_byte_key_raises_value_error(self):
        from app.services.encryption import EncryptionService

        tiny = base64.b64encode(b"X").decode()
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService(key_b64=tiny)

    def test_32_byte_key_succeeds(self):
        """Sanity: exactly 32 bytes must NOT raise."""
        from app.services.encryption import EncryptionService

        ok = base64.b64encode(b"K" * 32).decode()
        svc = EncryptionService(key_b64=ok)
        assert svc is not None


# ===========================================================================
# predict.py : line 807
# `raise HTTPException(status_code=404, detail="No recommendations found")`
# inside get_patient_latest_recommendation — patient has no ExerciseRecommendation.
# ===========================================================================

class TestPredictLine807:
    def test_no_recommendation_raises_404_direct(self, db_session):
        from app.api.predict import get_patient_latest_recommendation

        clinician = make_user(
            db_session,
            f"rec807_doc_{uuid.uuid4().hex[:8]}@example.com",
            "Rec807 Doc",
            "clinician",
        )
        patient = make_user(
            db_session,
            f"rec807_pat_{uuid.uuid4().hex[:8]}@example.com",
            "Rec807 Pat",
            "patient",
        )
        patient.share_state = "SHARING_ON"
        db_session.commit()

        # No ExerciseRecommendation rows for this patient → line 807 fires
        with pytest.raises(HTTPException) as exc_info:
            _run(
                get_patient_latest_recommendation(
                    user_id=patient.user_id,
                    current_user=clinician,
                    db=db_session,
                )
            )

        assert exc_info.value.status_code == 404
        assert "No recommendations found" in exc_info.value.detail

    def test_no_recommendation_via_http(self, db_session):
        """Belt-and-suspenders: also call via TestClient."""
        clinician = make_user(
            db_session,
            f"rec807_api_doc_{uuid.uuid4().hex[:8]}@example.com",
            "Rec807 API Doc",
            "clinician",
        )
        patient = make_user(
            db_session,
            f"rec807_api_pat_{uuid.uuid4().hex[:8]}@example.com",
            "Rec807 API Pat",
            "patient",
        )
        patient.share_state = "SHARING_ON"
        db_session.commit()

        token = get_token(client, clinician.email)
        resp = client.get(
            f"/api/v1/patients/{patient.user_id}/recommendations/latest",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404
        assert "No recommendations" in resp.json()["detail"]
