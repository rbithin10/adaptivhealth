"""
Anomaly detection service.

Detects unusual vital sign patterns beyond simple threshold checks
using statistical methods (Z-score, rolling window analysis).
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
        return {
            "anomalies": [],
            "total_readings": len(readings) if readings else 0,
            "anomaly_count": 0,
            "status": "insufficient_data",
            "message": "Need at least 3 readings for anomaly detection.",
        }

    hr_values = [r["heart_rate"] for r in readings if r.get("heart_rate") is not None]
    spo2_values = [r["spo2"] for r in readings if r.get("spo2") is not None]

    anomalies: List[Dict[str, Any]] = []

    # Heart rate anomaly detection
    if len(hr_values) >= 3:
        hr_anomalies = _z_score_detect(hr_values, z_threshold)
        for idx, z in hr_anomalies:
            anomalies.append(
                {
                    "index": idx,
                    "metric": "heart_rate",
                    "value": hr_values[idx],
                    "z_score": round(z, 2),
                    "direction": "high" if z > 0 else "low",
                    "timestamp": readings[idx].get("timestamp"),
                }
            )

    # SpO2 anomaly detection
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

    # Heart rate variability anomaly (sudden jumps between consecutive readings)
    hr_variability_anomalies = _detect_hr_variability_anomalies(hr_values, readings)
    anomalies.extend(hr_variability_anomalies)

    status = "normal" if len(anomalies) == 0 else "anomalies_detected"

    return {
        "anomalies": anomalies,
        "total_readings": len(readings),
        "anomaly_count": len(anomalies),
        "status": status,
        "stats": {
            "hr_mean": round(_mean(hr_values), 1) if hr_values else None,
            "hr_std": round(_std(hr_values), 1) if len(hr_values) >= 2 else None,
            "spo2_mean": round(_mean(spo2_values), 1) if spo2_values else None,
            "spo2_std": round(_std(spo2_values), 1) if len(spo2_values) >= 2 else None,
        },
        "z_threshold": z_threshold,
    }


def _z_score_detect(values: List[float], threshold: float) -> List[tuple]:
    """Return list of (index, z_score) for values exceeding threshold."""
    mean = _mean(values)
    std = _std(values)
    if std == 0:
        return []
    results = []
    for i, v in enumerate(values):
        z = (v - mean) / std
        if abs(z) > threshold:
            results.append((i, z))
    return results


def _detect_hr_variability_anomalies(
    hr_values: List[float],
    readings: List[Dict[str, Any]],
    jump_threshold: int = 40,
) -> List[Dict[str, Any]]:
    """Detect sudden jumps in heart rate between consecutive readings."""
    anomalies = []
    for i in range(1, len(hr_values)):
        delta = abs(hr_values[i] - hr_values[i - 1])
        if delta >= jump_threshold:
            anomalies.append(
                {
                    "index": i,
                    "metric": "hr_variability",
                    "value": int(delta),
                    "z_score": None,
                    "direction": "spike" if hr_values[i] > hr_values[i - 1] else "drop",
                    "timestamp": readings[i].get("timestamp") if i < len(readings) else None,
                }
            )
    return anomalies


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)
    return variance ** 0.5
