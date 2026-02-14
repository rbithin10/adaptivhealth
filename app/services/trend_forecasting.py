"""
Trend forecasting service.

Predicts future risk over weeks using linear regression on historical vitals.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# FUNCTIONS
#   - forecast_trends()................ Line 25  (Main entry point)
#   - _linear_regression()............. Line 100 (Slope/intercept calc)
#   - _parse_timestamp()............... Line 130 (Timestamp helper)
#   - _predict_direction()............. Line 145 (Trend classification)
#
# BUSINESS CONTEXT:
# - Linear regression forecasting for risk trends
# - Predicts "improving", "stable", or "declining" direction
# - Called by advanced_ml.py /trend-forecast endpoint
# =============================================================================
"""

from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def forecast_trends(
    readings: List[Dict[str, Any]],
    forecast_days: int = 14,
) -> Dict[str, Any]:
    """
    Forecast vital sign trends using linear regression.

    Each reading should have: heart_rate, spo2 (optional), timestamp.
    """
    if not readings or len(readings) < 7:
        return {
            "status": "insufficient_data",
            "message": "Need at least 7 readings for trend forecasting.",
            "total_readings": len(readings) if readings else 0,
            "forecast_days": forecast_days,
        }

    hr_series = []
    spo2_series = []

    base_time = _parse_timestamp(readings[0].get("timestamp"))
    for r in readings:
        ts = _parse_timestamp(r.get("timestamp"))
        if ts and base_time:
            day_offset = (ts - base_time).total_seconds() / 86400.0
        else:
            day_offset = 0.0

        if r.get("heart_rate") is not None:
            hr_series.append((day_offset, float(r["heart_rate"])))
        if r.get("spo2") is not None:
            spo2_series.append((day_offset, float(r["spo2"])))

    result: Dict[str, Any] = {
        "status": "ok",
        "total_readings": len(readings),
        "forecast_days": forecast_days,
        "trends": {},
    }

    if len(hr_series) >= 7:
        result["trends"]["heart_rate"] = _linear_forecast(hr_series, forecast_days)

    if len(spo2_series) >= 7:
        result["trends"]["spo2"] = _linear_forecast(spo2_series, forecast_days)

    result["risk_projection"] = _compute_risk_projection(result["trends"])
    return result


def _linear_forecast(series: List[tuple], forecast_days: int) -> Dict[str, Any]:
    """Simple linear regression forecast."""
    n = len(series)
    xs = [p[0] for p in series]
    ys = [p[1] for p in series]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))

    slope = 0.0 if denominator == 0 else numerator / denominator
    intercept = y_mean - slope * x_mean

    last_day = xs[-1]
    current_value = slope * last_day + intercept

    forecast_day = last_day + forecast_days
    forecasted_value = slope * forecast_day + intercept

    ss_res = sum((ys[i] - (slope * xs[i] + intercept)) ** 2 for i in range(n))
    ss_tot = sum((ys[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    if abs(slope) < 0.1:
        direction = "stable"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    return {
        "slope_per_day": round(slope, 4),
        "direction": direction,
        "current_fitted": round(current_value, 1),
        "forecasted_value": round(forecasted_value, 1),
        "forecast_day": forecast_days,
        "r_squared": round(r_squared, 4),
        "data_points": n,
    }


def _compute_risk_projection(trends: Dict[str, Any]) -> Dict[str, Any]:
    """Compute overall risk based on trend directions."""
    risk_factors = []
    risk_score_delta = 0.0

    hr_trend = trends.get("heart_rate")
    if hr_trend:
        if hr_trend["direction"] == "increasing" and hr_trend["slope_per_day"] > 0.5:
            risk_factors.append("Heart rate trending upward")
            risk_score_delta += 0.1
        elif hr_trend["direction"] == "decreasing" and hr_trend["slope_per_day"] < -0.5:
            risk_factors.append("Heart rate trending downward (improving)")
            risk_score_delta -= 0.05

    spo2_trend = trends.get("spo2")
    if spo2_trend:
        if spo2_trend["direction"] == "decreasing" and spo2_trend["slope_per_day"] < -0.1:
            risk_factors.append("SpO2 trending downward (concerning)")
            risk_score_delta += 0.15
        elif spo2_trend["direction"] == "increasing":
            risk_factors.append("SpO2 trending upward (improving)")
            risk_score_delta -= 0.05

    if not risk_factors:
        risk_factors.append("All trends appear stable")

    projected_risk_change = "stable"
    if risk_score_delta > 0.05:
        projected_risk_change = "increasing"
    elif risk_score_delta < -0.03:
        projected_risk_change = "decreasing"

    return {
        "risk_direction": projected_risk_change,
        "risk_score_delta": round(risk_score_delta, 3),
        "factors": risk_factors,
    }


def _parse_timestamp(ts) -> Optional[datetime]:
    """Parse timestamp from various formats."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    return None
