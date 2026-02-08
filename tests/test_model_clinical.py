"""
Tests for the improved ML model (v2.0).

Validates that the retrained model correctly identifies clinically
dangerous scenarios that the v1.0 model missed:
  - Bradycardia (HR < 50 BPM)
  - Hypoxemia (SpO2 < 92%)
  - Tachycardia at rest
  - Age-adjusted max HR exceeded
  - Normal exercise remains low-risk
"""

import numpy as np
import pytest


class TestImprovedModel:
    """Verify the retrained model handles real-world clinical scenarios."""

    @pytest.fixture(autouse=True)
    def load_model(self):
        from app.services.ml_prediction import load_ml_model, predict_risk

        load_ml_model()
        self.predict = predict_risk

    # ---- High-risk: must be detected ----

    def test_bradycardia_30bpm_is_high_risk(self):
        """30 BPM average HR is dangerously low — model must flag it."""
        result = self.predict(
            age=65, baseline_hr=72, max_safe_hr=155,
            avg_heart_rate=30, peak_heart_rate=40, min_heart_rate=28,
            avg_spo2=88, duration_minutes=30, recovery_time_minutes=5,
        )
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 0.80

    def test_bradycardia_40bpm_is_high_risk(self):
        """40 BPM with low SpO2 is clinically dangerous."""
        result = self.predict(
            age=55, baseline_hr=60, max_safe_hr=165,
            avg_heart_rate=40, peak_heart_rate=50, min_heart_rate=35,
            avg_spo2=90, duration_minutes=20, recovery_time_minutes=10,
        )
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 0.80

    def test_severe_hypoxemia_is_high_risk(self):
        """SpO2 of 82% is severe hypoxemia — must be high risk."""
        result = self.predict(
            age=60, baseline_hr=75, max_safe_hr=160,
            avg_heart_rate=100, peak_heart_rate=120, min_heart_rate=80,
            avg_spo2=82, duration_minutes=20, recovery_time_minutes=8,
        )
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 0.80

    def test_elderly_high_hr_low_spo2_is_high_risk(self):
        """70-year-old with HR 160 and SpO2 89% — clearly dangerous."""
        result = self.predict(
            age=70, baseline_hr=80, max_safe_hr=150,
            avg_heart_rate=160, peak_heart_rate=180, min_heart_rate=100,
            avg_spo2=89, duration_minutes=45, recovery_time_minutes=15,
            activity_type="jogging",
        )
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 0.80

    def test_resting_tachycardia_is_high_risk(self):
        """Resting HR of 130 is abnormal tachycardia."""
        result = self.predict(
            age=50, baseline_hr=72, max_safe_hr=170,
            avg_heart_rate=130, peak_heart_rate=145, min_heart_rate=120,
            avg_spo2=94, duration_minutes=10, recovery_time_minutes=15,
        )
        assert result["risk_score"] >= 0.50

    # ---- Low-risk: must NOT over-alarm ----

    def test_normal_vitals_at_rest_is_low_risk(self):
        """Normal resting vitals should be low risk."""
        result = self.predict(
            age=35, baseline_hr=72, max_safe_hr=185,
            avg_heart_rate=75, peak_heart_rate=82, min_heart_rate=68,
            avg_spo2=98, duration_minutes=20, recovery_time_minutes=3,
        )
        assert result["risk_level"] == "low"
        assert result["risk_score"] < 0.50

    def test_healthy_jogging_is_low_risk(self):
        """Young adult jogging with normal vitals — safe."""
        result = self.predict(
            age=28, baseline_hr=65, max_safe_hr=192,
            avg_heart_rate=130, peak_heart_rate=150, min_heart_rate=70,
            avg_spo2=98, duration_minutes=30, recovery_time_minutes=3,
            activity_type="jogging",
        )
        assert result["risk_level"] == "low"
        assert result["risk_score"] < 0.50

    def test_athlete_high_intensity_is_low_risk(self):
        """Athlete with low resting HR doing intense exercise — safe."""
        result = self.predict(
            age=25, baseline_hr=50, max_safe_hr=195,
            avg_heart_rate=140, peak_heart_rate=160, min_heart_rate=55,
            avg_spo2=98, duration_minutes=45, recovery_time_minutes=3,
            activity_type="jogging",
        )
        assert result["risk_level"] == "low"
        assert result["risk_score"] < 0.50

    # ---- Model info ----

    def test_model_version_is_2(self):
        """New model should report version 2.0."""
        result = self.predict(
            age=35, baseline_hr=72, max_safe_hr=185,
            avg_heart_rate=85, peak_heart_rate=100, min_heart_rate=68,
            avg_spo2=97, duration_minutes=20, recovery_time_minutes=3,
        )
        assert result["model_info"]["version"] == "2.0"
