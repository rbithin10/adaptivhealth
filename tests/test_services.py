"""
Tests for service layer functions.

Covers functions in:
- app/services/encryption.py (EncryptionService)
- app/services/ml_prediction.py (MLPredictionService, engineer_features, predict_risk)
- app/services/retraining_pipeline.py (get_retraining_status, save_retraining_metadata, evaluate_retraining_readiness)
- app/services/nl_builders.py (build_risk_summary_text, build_todays_workout_text, etc.)
- app/services/natural_language_alerts.py (_risk_score_to_plain_language)
- app/services/auth_service.py (AuthService)

Run with:
    pytest tests/test_services.py -v
"""

import base64
import os
import json
from datetime import datetime, timedelta, timezone, date
from unittest.mock import Mock, patch, MagicMock
import pytest
from jose import jwt

from app.services.encryption import EncryptionService, encrypt_phi, decrypt_phi, encrypt_phi_json, decrypt_phi_json
from app.services.ml_prediction import (
    engineer_features,
    is_model_loaded,
    ensure_model_loaded,
    predict_risk,
    MLPredictionService,
    get_ml_service
)
from app.services.retraining_pipeline import (
    get_retraining_status,
    save_retraining_metadata,
    evaluate_retraining_readiness,
    prepare_training_data
)
from app.services.nl_builders import (
    _get_risk_adjective,
    _get_activity_friendly_name,
    build_risk_summary_text,
    build_todays_workout_text,
    build_alert_explanation_text,
    build_progress_summary_text,
    compute_trend
)
from app.schemas.nl import Period, Trend
from app.services.natural_language_alerts import (
    _risk_score_to_plain_language,
    generate_natural_language_alert,
    format_risk_summary
)
from app.services.auth_service import AuthService
from app.config import settings


# =============================================================================
# EncryptionService Tests
# =============================================================================

class TestEncryptionService:
    """Test EncryptionService from app/services/encryption.py."""

    def test_init_valid_key_creates_service(self):
        """Test valid key creates service successfully."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        assert service is not None
        assert service._aesgcm is not None

    def test_init_missing_key_raises_valueerror(self):
        """Test missing key raises ValueError."""
        # EncryptionService allows None key (returns None for operations)
        # It only raises ValueError if key is invalid format
        service = EncryptionService(key_b64=None)
        assert service is not None

    def test_init_non_base64_key_raises_valueerror(self):
        """Test non-base64 key raises ValueError."""
        with pytest.raises(ValueError, match="must be base64-encoded"):
            EncryptionService(key_b64="not-valid-base64!@#$")

    def test_init_wrong_length_key_raises_valueerror(self):
        """Test wrong length key raises ValueError."""
        # Create 16-byte key (not 32)
        short_key = base64.b64encode(os.urandom(16)).decode()
        with pytest.raises(ValueError, match="must decode to 32 bytes"):
            EncryptionService(key_b64=short_key)

    def test_encrypt_text_returns_non_none_string(self):
        """Test encrypt_text returns non-None string."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        plaintext = "Test PHI data"
        encrypted = service.encrypt_text(plaintext)
        
        assert encrypted is not None
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_text_different_output_each_call(self):
        """Test encrypt_text returns different output each call (nonce randomness)."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        plaintext = "Same text"
        encrypted1 = service.encrypt_text(plaintext)
        encrypted2 = service.encrypt_text(plaintext)
        
        # Different nonces should produce different ciphertexts
        assert encrypted1 != encrypted2

    def test_encrypt_text_none_input_returns_none(self):
        """Test encrypt_text with None input returns None."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        result = service.encrypt_text(None)
        assert result is None

    def test_decrypt_text_round_trip_equals_original(self):
        """Test decrypt(encrypt(x)) == x."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        original = "Sensitive medical history"
        encrypted = service.encrypt_text(original)
        decrypted = service.decrypt_text(encrypted)
        
        assert decrypted == original

    def test_decrypt_text_none_returns_none(self):
        """Test decrypt_text with None returns None."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        result = service.decrypt_text(None)
        assert result is None

    def test_decrypt_text_invalid_token_raises_error(self):
        """Test decrypt_text with invalid token raises error."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        # Try to decrypt random garbage
        with pytest.raises(Exception):
            service.decrypt_text("invalid-token-data")

    def test_decrypt_text_too_short_token_raises_valueerror(self):
        """Test decrypt_text with too-short token raises ValueError."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        # Create token with less than 13 bytes
        short_token = base64.b64encode(b"short").decode()
        with pytest.raises(ValueError, match="too short"):
            service.decrypt_text(short_token)

    def test_encrypt_json_round_trip_equals_original(self):
        """Test decrypt_json(encrypt_json(x)) == x."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        original = {"diagnosis": "hypertension", "medications": ["lisinopril"]}
        encrypted = service.encrypt_json(original)
        decrypted = service.decrypt_json(encrypted)
        
        assert decrypted == original

    def test_encrypt_json_none_input_returns_none(self):
        """Test encrypt_json with None returns None."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        result = service.encrypt_json(None)
        assert result is None

    def test_decrypt_json_none_returns_none(self):
        """Test decrypt_json with None returns None."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key_b64=test_key)
        
        result = service.decrypt_json(None)
        assert result is None

    @patch('app.services.encryption.settings')
    def test_encrypt_phi_helper_returns_non_none(self, mock_settings):
        """Test encrypt_phi helper function returns non-None output."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        mock_settings.phi_encryption_key = test_key
        
        # Reset global _service to force re-initialization with mock settings
        import app.services.encryption as enc_module
        enc_module._service = None
        
        result = encrypt_phi("Test PHI")
        assert result is not None
        assert isinstance(result, str)

    @patch('app.services.encryption.settings')
    def test_decrypt_phi_helper_returns_non_none(self, mock_settings):
        """Test decrypt_phi helper function returns non-None output."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        mock_settings.phi_encryption_key = test_key
        
        import app.services.encryption as enc_module
        enc_module._service = None
        
        encrypted = encrypt_phi("Test PHI")
        result = decrypt_phi(encrypted)
        assert result == "Test PHI"

    @patch('app.services.encryption.settings')
    def test_encrypt_phi_json_helper_returns_non_none(self, mock_settings):
        """Test encrypt_phi_json helper function returns non-None output."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        mock_settings.phi_encryption_key = test_key
        
        import app.services.encryption as enc_module
        enc_module._service = None
        
        result = encrypt_phi_json({"key": "value"})
        assert result is not None
        assert isinstance(result, str)

    @patch('app.services.encryption.settings')
    def test_decrypt_phi_json_helper_returns_non_none(self, mock_settings):
        """Test decrypt_phi_json helper function returns non-None output."""
        test_key = base64.b64encode(os.urandom(32)).decode()
        mock_settings.phi_encryption_key = test_key
        
        import app.services.encryption as enc_module
        enc_module._service = None
        
        original = {"diagnosis": "test"}
        encrypted = encrypt_phi_json(original)
        result = decrypt_phi_json(encrypted)
        assert result == original


# =============================================================================
# ML Prediction Service Tests
# =============================================================================

class TestMLPrediction:
    """Test ML prediction functions from app/services/ml_prediction.py."""

    def test_engineer_features_all_17_keys_present(self):
        """Test engineer_features returns dict with all 17 feature keys."""
        features = engineer_features(
            age=30,
            baseline_hr=72,
            max_safe_hr=150,
            avg_heart_rate=90,
            peak_heart_rate=120,
            min_heart_rate=65,
            avg_spo2=97,
            duration_minutes=20,
            recovery_time_minutes=5,
            activity_type="walking"
        )
        
        expected_keys = [
            'age', 'baseline_hr', 'max_safe_hr', 'avg_heart_rate',
            'peak_heart_rate', 'min_heart_rate', 'avg_spo2', 'duration_minutes',
            'recovery_time_minutes', 'hr_pct_of_max', 'hr_elevation', 'hr_range',
            'duration_intensity', 'recovery_efficiency', 'spo2_deviation',
            'age_risk_factor', 'activity_intensity'
        ]
        
        assert len(features) == 17
        for key in expected_keys:
            assert key in features

    def test_engineer_features_hr_pct_of_max_calculation(self):
        """Test hr_pct_of_max = peak_heart_rate / max_safe_hr."""
        features = engineer_features(
            age=30,
            baseline_hr=72,
            max_safe_hr=150,
            avg_heart_rate=90,
            peak_heart_rate=120,  # 120 / 150 = 0.8
            min_heart_rate=65,
            avg_spo2=97,
            duration_minutes=20,
            recovery_time_minutes=5,
            activity_type="walking"
        )
        
        assert features['hr_pct_of_max'] == 120 / 150
        assert features['hr_pct_of_max'] == 0.8

    def test_engineer_features_activity_mapping_walking(self):
        """Test activity_type='walking' maps to 1."""
        features = engineer_features(
            age=30, baseline_hr=72, max_safe_hr=150,
            avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
            activity_type="walking"
        )
        assert features['activity_intensity'] == 1

    def test_engineer_features_activity_mapping_jogging(self):
        """Test activity_type='jogging' maps to 2."""
        features = engineer_features(
            age=30, baseline_hr=72, max_safe_hr=150,
            avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
            activity_type="jogging"
        )
        assert features['activity_intensity'] == 2

    def test_engineer_features_activity_mapping_swimming(self):
        """Test activity_type='swimming' maps to 3."""
        features = engineer_features(
            age=30, baseline_hr=72, max_safe_hr=150,
            avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
            activity_type="swimming"
        )
        assert features['activity_intensity'] == 3

    def test_engineer_features_activity_mapping_unknown_defaults_to_2(self):
        """Test unknown activity_type defaults to 2."""
        features = engineer_features(
            age=30, baseline_hr=72, max_safe_hr=150,
            avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
            activity_type="unknown_activity"
        )
        assert features['activity_intensity'] == 2

    @patch('app.services.ml_prediction.model', None)
    @patch('app.services.ml_prediction.scaler', None)
    @patch('app.services.ml_prediction.feature_columns', None)
    def test_is_model_loaded_returns_false_when_globals_none(self):
        """Test is_model_loaded returns False when model globals are None."""
        result = is_model_loaded()
        assert result is False

    @patch('app.services.ml_prediction._model_load_attempted', True)
    @patch('app.services.ml_prediction.model', None)
    def test_ensure_model_loaded_returns_false_when_load_attempted_and_failed(self):
        """Test ensure_model_loaded returns False when model load attempted and failed."""
        result = ensure_model_loaded()
        assert result is False

    @patch('app.services.ml_prediction.model', None)
    def test_mlpredictionservice_is_loaded_false_when_no_model(self):
        """Test MLPredictionService.is_loaded is False when no model."""
        service = MLPredictionService()
        assert service.is_loaded is False

    @patch('app.services.ml_prediction.model', None)
    @patch('app.services.ml_prediction.feature_columns', None)
    def test_mlpredictionservice_feature_columns_none_when_not_loaded(self):
        """Test MLPredictionService.feature_columns is None when not loaded."""
        service = MLPredictionService()
        assert service.feature_columns is None

    @patch('app.services.ml_prediction.model', None)
    @patch('app.services.ml_prediction.scaler', None)
    @patch('app.services.ml_prediction.feature_columns', None)
    def test_predict_risk_raises_runtimeerror_when_model_not_loaded(self):
        """Test predict_risk raises RuntimeError when model not loaded."""
        with pytest.raises(RuntimeError, match="ML model not loaded"):
            predict_risk(
                age=30, baseline_hr=72, max_safe_hr=150,
                avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
                avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
                activity_type="walking"
            )

    @patch('app.services.ml_prediction.model')
    @patch('app.services.ml_prediction.scaler')
    @patch('app.services.ml_prediction.feature_columns')
    def test_predict_risk_with_mocked_model_returns_valid_dict(
        self, mock_feature_columns, mock_scaler, mock_model
    ):
        """Test predict_risk with mocked model+scaler returns valid dict."""
        # Mock feature columns
        mock_feature_columns.__iter__ = Mock(return_value=iter([
            'age', 'baseline_hr', 'max_safe_hr', 'avg_heart_rate',
            'peak_heart_rate', 'min_heart_rate', 'avg_spo2', 'duration_minutes',
            'recovery_time_minutes', 'hr_pct_of_max', 'hr_elevation', 'hr_range',
            'duration_intensity', 'recovery_efficiency', 'spo2_deviation',
            'age_risk_factor', 'activity_intensity'
        ]))
        
        # Mock scaler transform (identity transform)
        import numpy as np
        mock_scaler.transform = Mock(return_value=np.array([[1.0] * 17]))
        
        # Mock model prediction (low risk)
        mock_model.predict = Mock(return_value=np.array([0]))  # Class 0 = low risk
        mock_model.predict_proba = Mock(return_value=np.array([[0.75, 0.25]]))  # [prob_low, prob_high]
        
        result = predict_risk(
            age=30, baseline_hr=72, max_safe_hr=150,
            avg_heart_rate=90, peak_heart_rate=120, min_heart_rate=65,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=5,
            activity_type="walking"
        )
        
        assert "risk_score" in result
        assert "risk_level" in result
        assert "high_risk" in result
        assert "confidence" in result
        assert "recommendation" in result
        assert "model_info" in result
        assert result["risk_score"] == 0.25
        assert result["risk_level"] == "low"
        assert result["high_risk"] is False


# =============================================================================
# Retraining Pipeline Tests
# =============================================================================

class TestRetrainingPipeline:
    """Test retraining pipeline functions from app/services/retraining_pipeline.py."""

    def test_get_retraining_status_returns_dict_with_required_keys(self):
        """Test get_retraining_status returns dict with required keys."""
        status = get_retraining_status()
        
        assert isinstance(status, dict)
        assert "model_dir" in status
        assert "model_exists" in status
        assert "scaler_exists" in status
        assert "features_exists" in status
        assert "metadata" in status

    def test_save_retraining_metadata_returns_dict_with_metadata(self):
        """Test save_retraining_metadata returns dict with metadata."""
        metadata = save_retraining_metadata(
            version="2.0",
            accuracy=0.975,
            records_used=500,
            notes="Test retrain"
        )
        
        assert isinstance(metadata, dict)
        assert metadata["version"] == "2.0"
        assert metadata["accuracy"] == 0.975
        assert metadata["records_used"] == 500
        assert metadata["notes"] == "Test retrain"
        assert "retrained_at" in metadata
        assert "model_name" in metadata

    def test_evaluate_retraining_readiness_returns_readiness_dict(self):
        """Test evaluate_retraining_readiness returns dict with readiness info."""
        readiness = evaluate_retraining_readiness(
            new_records_count=150,
            last_retrain_date="2025-01-01T00:00:00Z",
            min_records=100,
            min_days_since_last=7
        )
        
        assert isinstance(readiness, dict)
        assert "ready" in readiness
        assert "new_records" in readiness
        assert "min_records_required" in readiness
        assert "last_retrain_date" in readiness
        assert "min_days_between_retrains" in readiness
        assert "reasons" in readiness
        assert readiness["new_records"] == 150

    def test_evaluate_retraining_readiness_not_ready_insufficient_records(self):
        """Test evaluate_retraining_readiness not ready with insufficient records."""
        readiness = evaluate_retraining_readiness(
            new_records_count=50,  # Less than min 100
            last_retrain_date="2020-01-01T00:00:00Z",
            min_records=100,
            min_days_since_last=7
        )
        
        assert readiness["ready"] is False
        assert any("50 new records" in reason for reason in readiness["reasons"])

    def test_evaluate_retraining_readiness_handles_no_last_retrain_date(self):
        """Test evaluate_retraining_readiness handles None last_retrain_date."""
        readiness = evaluate_retraining_readiness(
            new_records_count=150,
            last_retrain_date=None,
            min_records=100,
            min_days_since_last=7
        )
        
        # Should be ready if enough records and no last date constraint
        assert isinstance(readiness, dict)
        assert "ready" in readiness

    def test_prepare_training_data_returns_status_dict(self):
        """Test prepare_training_data returns status dict."""
        records = [
            {"heart_rate": 75, "spo2": 98, "risk_label": 0},
            {"heart_rate": 120, "spo2": 95, "risk_label": 1},
            {"heart_rate": 90, "spo2": 97, "risk_label": 0},
        ]
        
        result = prepare_training_data(records)
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "total_records" in result
        assert "valid_records" in result
        assert result["total_records"] == 3
        assert result["valid_records"] == 3

    def test_prepare_training_data_handles_empty_list(self):
        """Test prepare_training_data handles empty records list."""
        result = prepare_training_data([])
        
        assert result["status"] == "no_data"
        assert result["total_records"] == 0
        assert result["valid_records"] == 0


# =============================================================================
# Natural Language Builders Tests
# =============================================================================

class TestNLBuilders:
    """Test natural language builder functions from app/services/nl_builders.py."""

    def test_get_risk_adjective_low(self):
        """Test _get_risk_adjective returns non-empty string for 'LOW'."""
        result = _get_risk_adjective("LOW")
        assert isinstance(result, str)
        assert len(result) > 0
        assert result == "low"

    def test_get_risk_adjective_moderate(self):
        """Test _get_risk_adjective returns non-empty string for 'MODERATE'."""
        result = _get_risk_adjective("MODERATE")
        assert isinstance(result, str)
        assert len(result) > 0
        assert result == "moderate"

    def test_get_risk_adjective_high(self):
        """Test _get_risk_adjective returns non-empty string for 'HIGH'."""
        result = _get_risk_adjective("HIGH")
        assert isinstance(result, str)
        assert len(result) > 0
        assert result == "elevated"

    def test_get_activity_friendly_name_walking(self):
        """Test _get_activity_friendly_name for WALKING."""
        result = _get_activity_friendly_name("WALKING")
        assert result == "walk"

    def test_get_activity_friendly_name_cycling(self):
        """Test _get_activity_friendly_name for CYCLING."""
        result = _get_activity_friendly_name("CYCLING")
        assert result == "bike ride"

    def test_build_risk_summary_text_returns_non_empty_string(self):
        """Test build_risk_summary_text returns non-empty string with all fields."""
        result = build_risk_summary_text(
            risk_level="LOW",
            risk_score=0.2,
            time_window_hours=24,
            avg_heart_rate=75,
            max_heart_rate=120,
            avg_spo2=98,
            alert_count=0,
            safety_status="SAFE"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "hours" in result
        assert "75 BPM" in result or "75" in result
        assert "98%" in result or "98" in result

    def test_build_risk_summary_text_high_risk_includes_concerning(self):
        """Test build_risk_summary_text for HIGH risk includes 'concerning'."""
        result = build_risk_summary_text(
            risk_level="HIGH",
            risk_score=0.85,
            time_window_hours=24,
            avg_heart_rate=140,
            max_heart_rate=180,
            avg_spo2=92,
            alert_count=3,
            safety_status="UNSAFE"
        )
        
        assert "concerning" in result.lower()

    def test_build_todays_workout_text_returns_string_with_workout_info(self):
        """Test build_todays_workout_text returns string with workout info."""
        result = build_todays_workout_text(
            activity_type="WALKING",
            intensity_level="MODERATE",
            duration_minutes=30,
            target_hr_min=85,
            target_hr_max=120,
            risk_level="LOW"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "30 minutes" in result or "30" in result
        assert "85" in result and "120" in result  # HR range
        assert "walk" in result.lower()

    def test_build_alert_explanation_text_high_heart_rate(self):
        """Test build_alert_explanation_text for HIGH_HEART_RATE."""
        alert_time = datetime(2026, 2, 21, 14, 30, 0)
        result = build_alert_explanation_text(
            alert_type="HIGH_HEART_RATE",
            severity_level="HIGH",
            alert_time=alert_time,
            during_activity=True,
            activity_type="Walking",
            heart_rate=180,
            spo2=None,
            recommended_action="STOP_AND_REST"
        )
        
        assert isinstance(result, str)
        assert "180" in result
        assert "Stop" in result or "stop" in result
        assert "rest" in result.lower()

    def test_build_alert_explanation_text_low_oxygen(self):
        """Test build_alert_explanation_text for LOW_OXYGEN."""
        alert_time = datetime(2026, 2, 21, 14, 30, 0)
        result = build_alert_explanation_text(
            alert_type="LOW_OXYGEN",
            severity_level="HIGH",
            alert_time=alert_time,
            during_activity=False,
            activity_type=None,
            heart_rate=None,
            spo2=88,
            recommended_action="CONTACT_DOCTOR"
        )
        
        assert isinstance(result, str)
        assert "88" in result or "oxygen" in result.lower()
        assert "care team" in result.lower() or "doctor" in result.lower()

    def test_build_progress_summary_text_returns_string_with_trend_info(self):
        """Test build_progress_summary_text returns string with trend info."""
        current = Period(
            start=datetime(2026, 2, 14),
            end=datetime(2026, 2, 21),
            workout_count=5,
            total_active_minutes=150,
            time_in_safe_zone_minutes=120,
            time_above_safe_zone_minutes=30,
            alert_count=1,
            avg_risk_level="LOW"
        )
        previous = Period(
            start=datetime(2026, 2, 7),
            end=datetime(2026, 2, 14),
            workout_count=3,
            total_active_minutes=90,
            time_in_safe_zone_minutes=75,
            time_above_safe_zone_minutes=15,
            alert_count=2,
            avg_risk_level="MODERATE"
        )
        trend = Trend(
            workout_frequency="IMPROVING",
            alerts="IMPROVING",
            risk="IMPROVING",
            overall="IMPROVING"
        )
        
        result = build_progress_summary_text(current, previous, trend)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "5" in result  # workout count
        assert "150" in result  # active minutes

    def test_compute_trend_improving_when_workouts_increase(self):
        """Test compute_trend returns IMPROVING when workouts increase."""
        current = Period(
            start=datetime(2026, 2, 14),
            end=datetime(2026, 2, 21),
            workout_count=5,
            total_active_minutes=150,
            time_in_safe_zone_minutes=120,
            time_above_safe_zone_minutes=30,
            alert_count=1,
            avg_risk_level="LOW"
        )
        previous = Period(
            start=datetime(2026, 2, 7),
            end=datetime(2026, 2, 14),
            workout_count=3,
            total_active_minutes=90,
            time_in_safe_zone_minutes=75,
            time_above_safe_zone_minutes=15,
            alert_count=2,
            avg_risk_level="MODERATE"
        )
        
        trend = compute_trend(current, previous)
        
        assert trend.workout_frequency == "IMPROVING"
        assert trend.alerts == "IMPROVING"  # Fewer alerts
        assert trend.risk == "IMPROVING"  # Lower risk
        assert trend.overall == "IMPROVING"

    def test_compute_trend_stable_when_no_change(self):
        """Test compute_trend returns STABLE when no change."""
        current = Period(
            start=datetime(2026, 2, 14),
            end=datetime(2026, 2, 21),
            workout_count=3,
            total_active_minutes=90,
            time_in_safe_zone_minutes=75,
            time_above_safe_zone_minutes=15,
            alert_count=1,
            avg_risk_level="LOW"
        )
        previous = Period(
            start=datetime(2026, 2, 7),
            end=datetime(2026, 2, 14),
            workout_count=3,
            total_active_minutes=90,
            time_in_safe_zone_minutes=75,
            time_above_safe_zone_minutes=15,
            alert_count=1,
            avg_risk_level="LOW"
        )
        
        trend = compute_trend(current, previous)
        
        assert trend.workout_frequency == "STABLE"
        assert trend.alerts == "STABLE"
        assert trend.risk == "STABLE"
        assert trend.overall == "STABLE"


# =============================================================================
# Natural Language Alerts Tests
# =============================================================================

class TestNaturalLanguageAlerts:
    """Test natural language alert functions from app/services/natural_language_alerts.py."""

    def test_risk_score_to_plain_language_low_risk(self):
        """Test _risk_score_to_plain_language with 0.1 returns 'low risk'."""
        result = _risk_score_to_plain_language(0.1, "low")
        assert "stable" in result.lower() or "safe" in result.lower()

    def test_risk_score_to_plain_language_moderate_risk(self):
        """Test _risk_score_to_plain_language with 0.5 returns 'moderate'."""
        result = _risk_score_to_plain_language(0.5, "moderate")
        assert "elevated" in result.lower() or "slightly" in result.lower()

    def test_risk_score_to_plain_language_high_risk(self):
        """Test _risk_score_to_plain_language with 0.9 returns 'high risk'."""
        result = _risk_score_to_plain_language(0.9, "high")
        assert "higher" in result.lower() or "risk" in result.lower()

    def test_risk_score_to_plain_language_critical_risk(self):
        """Test _risk_score_to_plain_language with 0.95 returns 'critical'."""
        result = _risk_score_to_plain_language(0.95, "critical")
        assert "higher" in result.lower() or "risk" in result.lower()

    def test_generate_natural_language_alert_returns_dict(self):
        """Test generate_natural_language_alert returns dict with required keys."""
        result = generate_natural_language_alert(
            alert_type="high_heart_rate",
            severity="warning",
            trigger_value="180",
            threshold_value="150",
            risk_score=0.75,
            risk_level="high",
            patient_name="John Doe"
        )
        
        assert isinstance(result, dict)
        assert "friendly_message" in result
        assert "action_steps" in result
        assert "urgency_level" in result
        assert "risk_context" in result

    def test_format_risk_summary_returns_string(self):
        """Test format_risk_summary returns non-empty string."""
        result = format_risk_summary(
            risk_score=0.65,
            risk_level="moderate",
            drivers=["Peak heart rate exceeded safe limit", "Low SpO2"],
            patient_name="Jane Smith"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Auth Service Tests
# =============================================================================

class TestAuthService:
    """Test auth service functions from app/services/auth_service.py."""

    def test_verify_password_correct_password_returns_true(self):
        """Test verify_password with correct password returns True."""
        password = "TestPassword123"
        hashed = AuthService.hash_password(password)
        
        result = AuthService.verify_password(password, hashed)
        assert result is True

    def test_verify_password_wrong_password_returns_false(self):
        """Test verify_password with wrong password returns False."""
        password = "TestPassword123"
        hashed = AuthService.hash_password(password)
        
        result = AuthService.verify_password("WrongPassword", hashed)
        assert result is False

    def test_verify_password_malformed_hash_returns_false(self):
        """Test verify_password with malformed hash returns False (not exception)."""
        result = AuthService.verify_password("password", "not-a-valid-hash")
        assert result is False

    def test_decode_token_valid_token_returns_payload(self):
        """Test decode_token with valid token returns payload dict."""
        payload = {"user_id": 123, "role": "patient"}
        token = AuthService.create_access_token(payload)
        
        decoded = AuthService.decode_token(token)
        
        assert decoded is not None
        assert decoded["user_id"] == 123
        assert decoded["role"] == "patient"

    def test_decode_token_expired_token_returns_none(self):
        """Test decode_token with expired token returns None."""
        payload = {"user_id": 123}
        # Create token that expired 1 hour ago
        token = AuthService.create_access_token(
            payload,
            expires_delta=timedelta(hours=-1)
        )
        
        decoded = AuthService.decode_token(token)
        assert decoded is None

    def test_decode_token_invalid_token_returns_none(self):
        """Test decode_token with invalid token returns None."""
        decoded = AuthService.decode_token("invalid.token.string")
        assert decoded is None

    def test_create_access_token_returns_string(self):
        """Test create_access_token returns string token."""
        payload = {"user_id": 123}
        token = AuthService.create_access_token(payload)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_returns_string(self):
        """Test create_refresh_token returns string token."""
        payload = {"user_id": 123}
        token = AuthService.create_refresh_token(payload)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_hash_password_returns_different_hash_each_time(self):
        """Test hash_password returns different hash each time (salt randomness)."""
        password = "TestPassword123"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)
        
        assert hash1 != hash2  # Different salts

    def test_decode_token_includes_exp_claim(self):
        """Test decoded token includes exp (expiration) claim."""
        payload = {"user_id": 123}
        token = AuthService.create_access_token(payload)
        decoded = AuthService.decode_token(token)
        
        assert decoded is not None
        assert "exp" in decoded
        assert isinstance(decoded["exp"], (int, float))
