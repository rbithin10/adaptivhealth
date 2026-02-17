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
#   - load_ml_model().................. Line 42  (Load model files on startup)
#   - is_model_loaded()................ Line 82  (Check model state)
#   - engineer_features().............. Line 88  (Calculate derived features)
#   - predict_risk()................... Line 145 (Core prediction function)
#
# CLASS
#   - MLPredictionService.............. Line 218 (Wrapper for DI)
#   - get_ml_service()................. Line 229 (Singleton factory)
#
# BUSINESS CONTEXT:
# - Random Forest model predicts cardiac risk 0.0-1.0
# - Uses 17 engineered features (HR ratios, reserves, zones)
# - Loaded once at startup, shared across all requests
# =============================================================================
"""

import json
import logging
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
_model_load_attempted = False
_model_load_lock = threading.Lock()


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


def load_ml_model(timeout: int = 15) -> bool:
    """
    Load the model files from disk on app startup with a timeout.

    Uses a background thread so that a hanging joblib.load()
    (e.g. version mismatch) does not block server startup forever.

    Args:
        timeout: Maximum seconds to wait for model loading (default 15).

    Returns:
        True if successful, False on any error or timeout.
    """
    global model, scaler, feature_columns, _model_load_attempted

    _model_load_attempted = True

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
        return True

    return False


def ensure_model_loaded() -> bool:
    """
    Ensure the ML model is loaded, attempting once if needed.

    Returns:
        True if model is loaded, False otherwise.
    """
    if is_model_loaded():
        return True

    with _model_load_lock:
        if is_model_loaded():
            return True
        if _model_load_attempted:
            return False
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
