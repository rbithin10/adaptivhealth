"""
Machine learning helper.

This loads the trained model and returns a risk score.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS/CONSTANTS.................... Line 25
# MODEL STATE (globals)................ Line 35
#
# FUNCTIONS
#   - load_ml_model().................. Line 50  (Load model files on startup)
#   - is_model_loaded()................ Line 105 (Check model state)
#   - ensure_model_loaded()............ Line 110 (Lazy load with retry)
#   - reload_ml_model()................ Line 130 (Force reload for recovery)
#   - engineer_features().............. Line 140 (Calculate derived features)
#   - predict_risk()................... Line 200 (Core prediction function)
#
# CLASS
#   - MLPredictionService.............. Line 275 (Wrapper for DI)
#   - get_ml_service()................. Line 290 (Singleton factory)
#
# BUSINESS CONTEXT:
# - Random Forest model predicts cardiac risk 0.0-1.0
# - Uses 17 engineered features (HR ratios, reserves, zones)
# - Loaded once at startup, shared across all requests
# - Auto-retries on failure (max 3 attempts with backoff)
# =============================================================================
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import threading
import joblib

# Logger setup
logger = logging.getLogger(__name__)

# ---- Absolute paths to model files ----
# Safer than relative paths - works regardless of working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "ml_models" / "risk_model.pkl"
SCALER_PATH = BASE_DIR / "ml_models" / "scaler.pkl"
FEATURES_PATH = BASE_DIR / "ml_models" / "feature_columns.json"

# ---- Global ML model state ----
# Loaded once on app startup, reused for all requests
model = None
scaler = None
feature_columns = None
_model_load_lock = threading.Lock()

# ---- Retry configuration ----
_MAX_LOAD_RETRIES = 3
_load_attempt_count = 0
_last_load_attempt_time: float = 0.0
_RETRY_COOLDOWN_SECONDS = 30  # Wait 30s between retry attempts


def _load_ml_model_inner(result: dict) -> None:
    """
    Internal helper that loads model files.
    Runs inside a thread so the caller can enforce a timeout.
    """
    try:
        result["model"] = joblib.load(MODEL_PATH)
        logger.info(f"Loaded model from {MODEL_PATH}")

        result["scaler"] = joblib.load(SCALER_PATH)
        logger.info(f"Loaded scaler from {SCALER_PATH}")

        with open(FEATURES_PATH, 'r') as f:
            result["feature_columns"] = json.load(f)
        logger.info(f"Loaded {len(result['feature_columns'])} feature columns")

        result["ok"] = True
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        logger.error(f"Expected files in: {BASE_DIR / 'ml_models'}")
        result["ok"] = False
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")
        result["ok"] = False


def load_ml_model(timeout: int = 30) -> bool:
    """
    Load the model files from disk on app startup with a timeout.

    Uses a background thread so that a hanging joblib.load()
    (e.g. version mismatch) does not block server startup forever.

    Args:
        timeout: Maximum seconds to wait for model loading (default 30).

    Returns:
        True if successful, False on any error or timeout.
    """
    global model, scaler, feature_columns, _load_attempt_count, _last_load_attempt_time

    _load_attempt_count += 1
    _last_load_attempt_time = time.time()

    logger.info(f"ML model load attempt {_load_attempt_count}/{_MAX_LOAD_RETRIES}")

    result: dict = {"ok": False}
    loader = threading.Thread(target=_load_ml_model_inner, args=(result,), daemon=True)
    loader.start()
    loader.join(timeout=timeout)

    if loader.is_alive():
        logger.error(
            f"ML model loading timed out after {timeout}s – "
            "pkl files may be incompatible with the current scikit-learn / Python version. "
            "Prediction endpoints will return 503."
        )
        return False

    if result.get("ok"):
        model = result["model"]
        scaler = result["scaler"]
        feature_columns = result["feature_columns"]
        logger.info("ML model loaded successfully")
        return True

    return False


def ensure_model_loaded() -> bool:
    """
    Ensure the ML model is loaded, retrying if previous attempts failed.

    Allows up to _MAX_LOAD_RETRIES attempts with a cooldown period
    between retries to avoid hammering the disk on repeated failures.

    Returns:
        True if model is loaded, False otherwise.
    """
    global _load_attempt_count

    if is_model_loaded():
        return True

    with _model_load_lock:
        # Double-check after acquiring lock
        if is_model_loaded():
            return True

        # Check if we've exhausted all retries
        if _load_attempt_count >= _MAX_LOAD_RETRIES:
            logger.warning(
                f"ML model load exhausted all {_MAX_LOAD_RETRIES} retries. "
                "Use reload_ml_model() or restart the server to try again."
            )
            return False

        # Enforce cooldown between retry attempts
        elapsed = time.time() - _last_load_attempt_time
        if _load_attempt_count > 0 and elapsed < _RETRY_COOLDOWN_SECONDS:
            logger.info(
                f"ML model retry cooldown: {_RETRY_COOLDOWN_SECONDS - elapsed:.0f}s remaining"
            )
            return False

        return load_ml_model()


def reload_ml_model() -> bool:
    """
    Force-reload the ML model, resetting retry counters.

    Use this to recover from a failed load without restarting the server.
    Can be called from an admin endpoint or a management command.

    Returns:
        True if model loaded successfully, False otherwise.
    """
    global _load_attempt_count, _last_load_attempt_time, model, scaler, feature_columns

    with _model_load_lock:
        logger.info("Force-reloading ML model (resetting retry counters)")
        _load_attempt_count = 0
        _last_load_attempt_time = 0.0
        model = None
        scaler = None
        feature_columns = None
        return load_ml_model()


def is_model_loaded() -> bool:
    """Check if the model is loaded and ready."""
    return model is not None and scaler is not None and feature_columns is not None

def engineer_features(
    age: int,
    baseline_hr: int,
    max_safe_hr: int,
    avg_heart_rate: int,
    peak_heart_rate: int,
    min_heart_rate: int,
    avg_spo2: int,
    duration_minutes: int,
    recovery_time_minutes: int,
    activity_type: str = "walking"
) -> Dict[str, float]:
    """
    Turn raw readings into the features the model expects.
    This gives the model enough context to judge risk.

    Returns dict of feature_name -> value.
    """
    # Build the feature values the model expects.
    hr_pct_of_max = peak_heart_rate / max_safe_hr if max_safe_hr > 0 else 0
    hr_elevation = avg_heart_rate - baseline_hr
    hr_range = peak_heart_rate - min_heart_rate
    duration_intensity = duration_minutes * hr_pct_of_max
    recovery_efficiency = recovery_time_minutes / duration_minutes if duration_minutes > 0 else 0
    spo2_deviation = 98 - avg_spo2
    age_risk_factor = age / 70

    # Activity type encoding (same mapping as train_model.py)
    activity_mapping = {
        'walking': 1, 'yoga': 1,
        'jogging': 2, 'cycling': 2,
        'swimming': 3
    }
    activity_intensity = activity_mapping.get(activity_type, 2)

    return {
        'age': age,
        'baseline_hr': baseline_hr,
        'max_safe_hr': max_safe_hr,
        'avg_heart_rate': avg_heart_rate,
        'peak_heart_rate': peak_heart_rate,
        'min_heart_rate': min_heart_rate,
        'avg_spo2': avg_spo2,
        'duration_minutes': duration_minutes,
        'recovery_time_minutes': recovery_time_minutes,
        'hr_pct_of_max': hr_pct_of_max,
        'hr_elevation': hr_elevation,
        'hr_range': hr_range,
        'duration_intensity': duration_intensity,
        'recovery_efficiency': recovery_efficiency,
        'spo2_deviation': spo2_deviation,
        'age_risk_factor': age_risk_factor,
        'activity_intensity': activity_intensity
    }


def predict_risk(
    age: int,
    baseline_hr: int,
    max_safe_hr: int,
    avg_heart_rate: int,
    peak_heart_rate: int,
    min_heart_rate: int,
    avg_spo2: int,
    duration_minutes: int,
    recovery_time_minutes: int,
    activity_type: str = "walking"
) -> Dict[str, Any]:
    """
    Predict heart risk for a workout session.
    Returns a score, a label, and a simple recommendation.
    
    Requires: load_ml_model() must have been called (done by FastAPI startup)
    """
    if model is None or scaler is None or feature_columns is None:
        raise RuntimeError("ML model not loaded. Server startup failed.")

    # Step 1: build the features from the raw readings.
    features = engineer_features(
        age, baseline_hr, max_safe_hr,
        avg_heart_rate, peak_heart_rate, min_heart_rate,
        avg_spo2, duration_minutes, recovery_time_minutes,
        activity_type
    )

    # Step 2: put features in the exact order the model expects.
    import numpy as np
    feature_array = np.array([[features[col] for col in feature_columns]])

    # Step 3: scale values if needed.
    feature_scaled = scaler.transform(feature_array)

    # Step 4: ask the model for a prediction.
    prediction = model.predict(feature_scaled)[0]  # 0 or 1
    probabilities = model.predict_proba(feature_scaled)[0]  # [prob_low, prob_high]

    # Step 5: turn the score into a simple risk label.
    risk_score = float(probabilities[1])  # probability of high risk class

    if risk_score >= 0.80:
        # High risk.
        risk_level = "high"
        recommendation = "STOP activity immediately. Rest and monitor symptoms."
    elif risk_score >= 0.50:
        # Medium risk.
        risk_level = "moderate"
        recommendation = "Reduce intensity. Consider taking a break."
    else:
        # Low risk.
        risk_level = "low"
        recommendation = "Safe to continue at current intensity."

    return {
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level,
        "high_risk": bool(prediction == 1),
        "confidence": round(float(max(probabilities)), 4),
        "features_used": features,
        "recommendation": recommendation,
        "model_info": {
            "name": "RandomForest",
            "version": "1.0",
            "accuracy": "96.9%"
        }
    }


# ---- Dummy service class for backwards compatibility with predict.py ----
# Can be removed once predict.py is refactored to use functions directly
class MLPredictionService:
    """Wrapper for backward compatibility."""
    
    @property
    def is_loaded(self) -> bool:
        return is_model_loaded()

    @property
    def feature_columns(self) -> Optional[list[str]]:
        return feature_columns
    
    def predict_risk(self, **kwargs) -> Dict[str, Any]:
        return predict_risk(**kwargs)


def get_ml_service() -> MLPredictionService:
    """Get the ML prediction service (for backward compatibility)."""
    ensure_model_loaded()
    return MLPredictionService()


# =============================================================================
# Medical History Risk Adjustments
# =============================================================================

def apply_medical_adjustments(
    risk_score: float,
    medical_profile: Dict[str, Any]
) -> tuple:
    """
    Post-process ML risk score using patient medical history.

    Applied AFTER the RandomForest prediction to account for
    clinical factors not in the training data.

    Returns:
        (adjusted_risk_score, list_of_adjustment_reasons)
    """
    adjustments = []

    # Prior MI: +0.10 risk
    if medical_profile.get("has_prior_mi"):
        risk_score = min(1.0, risk_score + 0.10)
        adjustments.append("Prior MI: +0.10 risk")

    # Heart failure: +0.05 to +0.20 based on NYHA class
    if medical_profile.get("has_heart_failure"):
        nyha_bumps = {"I": 0.05, "II": 0.10, "III": 0.15, "IV": 0.20}
        hf_class = medical_profile.get("heart_failure_class", "II")
        bump = nyha_bumps.get(hf_class, 0.10)
        risk_score = min(1.0, risk_score + bump)
        adjustments.append(f"Heart failure NYHA {hf_class}: +{bump:.2f} risk")

    # Anticoagulant: +0.05 (fall/bleed risk during exercise)
    if medical_profile.get("is_on_anticoagulant"):
        risk_score = min(1.0, risk_score + 0.05)
        adjustments.append("On anticoagulant (bleed risk): +0.05 risk")

    return round(risk_score, 4), adjustments


def get_adjusted_max_hr(age: int, is_on_beta_blocker: bool) -> int:
    """
    Calculate max heart rate adjusted for beta-blocker therapy.

    Beta-blockers blunt HR response by ~25%. Uses conservative
    Kokkinos-adjusted formula: (220 - age) * 0.75.
    """
    base_max = 220 - age if age else 180
    if is_on_beta_blocker:
        return int(base_max * 0.75)
    return base_max