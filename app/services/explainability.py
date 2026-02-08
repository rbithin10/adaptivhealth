"""
Explainability service.

Provides SHAP-like feature importance explanations for ML predictions.
Uses tree-based feature importance from the Random Forest model
and per-prediction contribution analysis.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def compute_feature_importance(
    features_used: Dict[str, float],
    feature_columns: List[str],
    model=None,
) -> Dict[str, Any]:
    """
    Compute feature importance for a single prediction.
    """
    global_importances: Dict[str, float] = {}
    if model is not None and hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        for i, col in enumerate(feature_columns):
            if i < len(importances):
                global_importances[col] = round(float(importances[i]), 4)

    contributions = _estimate_contributions(features_used, feature_columns, global_importances)

    sorted_contributions = sorted(
        contributions.items(),
        key=lambda x: abs(x[1]["contribution"]),
        reverse=True,
    )

    top_features = []
    for feat_name, info in sorted_contributions[:5]:
        top_features.append(
            {
                "feature": feat_name,
                "value": info["value"],
                "contribution": info["contribution"],
                "direction": info["direction"],
                "explanation": info["explanation"],
                "global_importance": global_importances.get(feat_name, 0.0),
            }
        )

    return {
        "top_features": top_features,
        "global_importances": global_importances,
        "feature_count": len(feature_columns),
        "method": "tree_importance_with_deviation_analysis",
    }


def explain_prediction(
    prediction_result: Dict[str, Any],
    feature_columns: List[str],
    model=None,
) -> Dict[str, Any]:
    """
    Generate a full explanation for a prediction result.
    """
    features_used = prediction_result.get("features_used", {})
    risk_score = prediction_result.get("risk_score", 0.0)
    risk_level = prediction_result.get("risk_level", "unknown")

    importance = compute_feature_importance(features_used, feature_columns, model)

    explanation_parts = []
    for feat in importance["top_features"][:3]:
        explanation_parts.append(
            f"{_feature_to_readable(feat['feature'])} "
            f"({'pushed risk up' if feat['direction'] == 'increasing' else 'kept risk lower'})"
        )

    if explanation_parts:
        plain_explanation = (
            f"Your risk score is {risk_score:.2f} ({risk_level}). "
            f"The main factors: {'; '.join(explanation_parts)}."
        )
    else:
        plain_explanation = f"Your risk score is {risk_score:.2f} ({risk_level})."

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "feature_importance": importance,
        "plain_explanation": plain_explanation,
    }


_TYPICAL_VALUES = {
    "age": 55,
    "baseline_hr": 72,
    "max_safe_hr": 165,
    "avg_heart_rate": 90,
    "peak_heart_rate": 120,
    "min_heart_rate": 65,
    "avg_spo2": 97,
    "duration_minutes": 20,
    "recovery_time_minutes": 5,
    "hr_pct_of_max": 0.72,
    "hr_elevation": 18,
    "hr_range": 55,
    "duration_intensity": 14.4,
    "recovery_efficiency": 0.25,
    "spo2_deviation": 1,
    "age_risk_factor": 0.79,
    "activity_intensity": 2,
}

_FEATURE_NAMES = {
    "age": "Age",
    "baseline_hr": "Resting heart rate",
    "max_safe_hr": "Maximum safe heart rate",
    "avg_heart_rate": "Average heart rate",
    "peak_heart_rate": "Peak heart rate",
    "min_heart_rate": "Minimum heart rate",
    "avg_spo2": "Blood oxygen (SpO2)",
    "duration_minutes": "Session duration",
    "recovery_time_minutes": "Recovery time",
    "hr_pct_of_max": "Heart rate percent of maximum",
    "hr_elevation": "Heart rate elevation from baseline",
    "hr_range": "Heart rate range",
    "duration_intensity": "Duration intensity",
    "recovery_efficiency": "Recovery efficiency",
    "spo2_deviation": "SpO2 deviation from normal",
    "age_risk_factor": "Age-based risk factor",
    "activity_intensity": "Activity intensity level",
}


def _estimate_contributions(
    features: Dict[str, float],
    feature_columns: List[str],
    global_importances: Dict[str, float],
) -> Dict[str, Dict[str, Any]]:
    """Estimate per-feature contribution based on deviation and global importance."""
    contributions: Dict[str, Dict[str, Any]] = {}

    for col in feature_columns:
        value = features.get(col, 0.0)
        typical = _TYPICAL_VALUES.get(col, value)
        global_imp = global_importances.get(col, 1.0 / max(1, len(feature_columns)))

        if typical != 0:
            deviation = (value - typical) / abs(typical)
        else:
            deviation = 0.0

        contribution = round(global_imp * deviation, 4)

        if contribution > 0:
            direction = "increasing"
        elif contribution < 0:
            direction = "decreasing"
        else:
            direction = "neutral"

        contributions[col] = {
            "value": round(float(value), 4) if isinstance(value, float) else value,
            "typical_value": typical,
            "deviation": round(deviation, 4),
            "contribution": contribution,
            "direction": direction,
            "explanation": _generate_feature_explanation(col, value, typical, direction),
        }

    return contributions


def _generate_feature_explanation(feature: str, value: float, typical: float, direction: str) -> str:
    name = _feature_to_readable(feature)
    if direction == "increasing":
        return f"{name} is higher than typical."
    if direction == "decreasing":
        return f"{name} is lower than typical."
    return f"{name} is within a typical range."


def _feature_to_readable(feature: str) -> str:
    return _FEATURE_NAMES.get(feature, feature.replace("_", " ").title())
