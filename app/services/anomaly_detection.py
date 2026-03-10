"""
Anomaly detection service.

Detects unusual vital sign patterns beyond simple threshold checks
using statistical methods (Z-score, rolling window analysis).

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# FUNCTIONS
#   - detect_anomalies()............... Line 25  (Main entry point)
#   - _z_score_detect()................ Line 95  (Z-score calculation)
#   - _calculate_stats()............... Line 110 (Mean/std helper)
#
# BUSINESS CONTEXT:
# - Statistical anomaly detection beyond fixed thresholds
# - Z-score >2 indicates unusual reading
# - Called by advanced_ml.py /anomaly-detection endpoint
# =============================================================================
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def detect_anomalies(
    readings: List[Dict[str, Any]],
    z_threshold: float = 2.0,
) -> Dict[str, Any]:
    """
    Detect anomalies in a list of vital sign readings using Z-score analysis.

    Each reading should have keys: heart_rate, spo2 (optional), timestamp.
    """
    if not readings or len(readings) < 3:
        # We need at least 3 data points to detect anything unusual
        return {
            "anomalies": [],
            "total_readings": len(readings) if readings else 0,
            "anomaly_count": 0,
            "status": "insufficient_data",
            "message": "Need at least 3 readings for anomaly detection.",
        }

    # Collect all heart rate and oxygen values from the readings
    hr_values = [r["heart_rate"] for r in readings if r.get("heart_rate") is not None]
    spo2_values = [r["spo2"] for r in readings if r.get("spo2") is not None]

    anomalies: List[Dict[str, Any]] = []  # Will hold all detected unusual readings

    # Check heart rate values for statistical outliers (Z-score method)
    if len(hr_values) >= 3:
        hr_anomalies = _z_score_detect(hr_values, z_threshold)
        for idx, z in hr_anomalies:
            anomalies.append(
                {
                    "index": idx,  # Position in the readings list
                    "metric": "heart_rate",
                    "value": hr_values[idx],  # The actual reading that was unusual
                    "z_score": round(z, 2),  # How far from normal (higher = more unusual)
                    "direction": "high" if z > 0 else "low",  # Was it unusually high or low?
                    "timestamp": readings[idx].get("timestamp"),
                }
            )

    # Check blood oxygen values for statistical outliers
    if len(spo2_values) >= 3:
        spo2_anomalies = _z_score_detect(spo2_values, z_threshold)
        for idx, z in spo2_anomalies:
            anomalies.append(
                {
                    "index": idx,
                    "metric": "spo2",
                    "value": spo2_values[idx],
                    "z_score": round(z, 2),
                    "direction": "high" if z > 0 else "low",
                    "timestamp": readings[idx].get("timestamp"),
                }
            )

    # Also check for sudden big jumps between consecutive heart rate readings
    hr_variability_anomalies = _detect_hr_variability_anomalies(hr_values, readings)
    anomalies.extend(hr_variability_anomalies)

    status = "normal" if len(anomalies) == 0 else "anomalies_detected"  # Summary: any problems found?

    return {
        "anomalies": anomalies,
        "total_readings": len(readings),
        "anomaly_count": len(anomalies),
        "status": status,
        "stats": {  # Quick summary statistics for the whole batch
            "hr_mean": round(_mean(hr_values), 1) if hr_values else None,
            "hr_std": round(_std(hr_values), 1) if len(hr_values) >= 2 else None,
            "spo2_mean": round(_mean(spo2_values), 1) if spo2_values else None,
            "spo2_std": round(_std(spo2_values), 1) if len(spo2_values) >= 2 else None,
        },
        "z_threshold": z_threshold,
    }


def _z_score_detect(values: List[float], threshold: float) -> List[tuple]:
    """Return list of (index, z_score) for values exceeding threshold."""
    mean = _mean(values)  # Calculate the average of all values
    std = _std(values)  # Calculate how spread out the values are
    if std == 0:  # If all values are the same, nothing can be unusual
        return []
    results = []
    for i, v in enumerate(values):
        z = (v - mean) / std  # Z-score: how many standard deviations from the average
        if abs(z) > threshold:  # If the reading is too far from normal, flag it
            results.append((i, z))
    return results


def _detect_hr_variability_anomalies(
    hr_values: List[float],
    readings: List[Dict[str, Any]],
    jump_threshold: int = 40,  # Flag any heart rate jump of 40+ BPM between readings
) -> List[Dict[str, Any]]:
    """Detect sudden jumps in heart rate between consecutive readings."""
    anomalies = []
    for i in range(1, len(hr_values)):
        delta = abs(hr_values[i] - hr_values[i - 1])  # How much HR changed from previous reading
        if delta >= jump_threshold:  # If the jump is bigger than our threshold, flag it
            anomalies.append(
                {
                    "index": i,
                    "metric": "hr_variability",
                    "value": int(delta),  # The size of the jump in BPM
                    "z_score": None,
                    "direction": "spike" if hr_values[i] > hr_values[i - 1] else "drop",  # Did it jump up or down?
                    "timestamp": readings[i].get("timestamp") if i < len(readings) else None,
                }
            )
    return anomalies


def _mean(values: List[float]) -> float:
    """Calculate the average of a list of numbers."""
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    """Calculate how spread out the numbers are (standard deviation)."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)  # Average squared distance from the mean
    return variance ** 0.5  # Square root gives us the standard deviation
