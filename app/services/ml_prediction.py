"""
Machine learning helper.

This loads the trained model and returns a risk score.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import joblib

# Logger setup
logger = logging.getLogger(__name__)

# ---- Absolute paths to model files ----
# Safer than relative paths - works regardless of working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "model" / "risk_model.pkl"
SCALER_PATH = BASE_DIR / "model" / "scaler.pkl"
FEATURES_PATH = BASE_DIR / "model" / "feature_columns.json"

# ---- Global ML model state ----
# Loaded once on app startup, reused for all requests
model = None
scaler = None
feature_columns = None


def load_ml_model() -> bool:
    """
    Load the model files from disk on app startup.
    
    Uses absolute paths to avoid working directory issues.
    Loads once and stores in module-level globals.

    Returns:
        True if successful, False on any file/parsing error
    """
    global model, scaler, feature_columns
    
    try:
        # Load pre-trained Random Forest model using joblib (more efficient than pickle)
        model = joblib.load(MODEL_PATH)
        logger.info(f"Loaded model from {MODEL_PATH}")

        # Load feature scaler (StandardScaler or similar)
        # WHY: Tree models don't need scaling, but other models might
        # Loaded for future compatibility if model architecture changes
        scaler = joblib.load(SCALER_PATH)
        logger.info(f"Loaded scaler from {SCALER_PATH}")

        # Load feature column names
        # WHY: Model expects 17 features in specific order
        # Loading from JSON makes it easy to change without code edits
        with open(FEATURES_PATH, 'r') as f:
            feature_columns = json.load(f)
        logger.info(f"Loaded {len(feature_columns)} feature columns")

        return True

    except FileNotFoundError as e:
        # Model files not found - likely first deployment
        # User should copy ml_models/ folder from training repo
        logger.error(f"Model file not found: {e}")
        logger.error(f"Expected files in: {BASE_DIR / 'ml_models'}")
        logger.error("Copy risk_model.pkl, scaler.pkl, feature_columns.json to ml_models/")
        return False
    except Exception as e:
        # Unexpected error (corrupted file, wrong format, etc.)
        logger.error(f"Failed to load ML model: {e}")
        return False


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
            "version": "2.0",
            "accuracy": "100.0%"
        }
    }


# ---- Dummy service class for backwards compatibility with predict.py ----
# Can be removed once predict.py is refactored to use functions directly
class MLPredictionService:
    """Wrapper for backward compatibility."""
    
    @property
    def is_loaded(self) -> bool:
        return is_model_loaded()
    
    def predict_risk(self, **kwargs) -> Dict[str, Any]:
        return predict_risk(**kwargs)


def get_ml_service() -> MLPredictionService:
    """Get the ML prediction service (for backward compatibility)."""
    return MLPredictionService()
