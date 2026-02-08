"""
Personalized baseline optimization service.

Auto-adjusts a patient's baseline heart rate based on recent resting data,
improving the accuracy of risk calculations over time.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def compute_optimized_baseline(
    resting_readings: List[Dict[str, Any]],
    current_baseline: Optional[int] = None,
    smoothing_factor: float = 0.3,
) -> Dict[str, Any]:
    """
    Compute an optimized baseline heart rate from recent resting readings.

    Uses exponential moving average to gradually adjust baseline while
    preventing sudden jumps from noisy data.
    """
    if not resting_readings or len(resting_readings) < 5:
        return {
            "status": "insufficient_data",
            "message": "Need at least 5 resting readings to optimize baseline.",
            "current_baseline": current_baseline,
            "new_baseline": current_baseline,
            "adjusted": False,
            "readings_used": len(resting_readings) if resting_readings else 0,
        }

    hr_values = [
        r["heart_rate"]
        for r in resting_readings
        if r.get("heart_rate") is not None and 40 <= r["heart_rate"] <= 120
    ]

    if len(hr_values) < 5:
        return {
            "status": "insufficient_valid_data",
            "message": "Not enough valid resting readings (40-120 BPM range).",
            "current_baseline": current_baseline,
            "new_baseline": current_baseline,
            "adjusted": False,
            "readings_used": len(hr_values),
        }

    mean_hr = sum(hr_values) / len(hr_values)
    std_hr = _std(hr_values)

    if std_hr > 0:
        filtered = [v for v in hr_values if abs(v - mean_hr) <= 1.5 * std_hr]
    else:
        filtered = hr_values

    if len(filtered) < 3:
        filtered = hr_values

    filtered_mean = sum(filtered) / len(filtered)

    if current_baseline is not None:
        new_baseline = int(
            round(current_baseline * (1 - smoothing_factor) + filtered_mean * smoothing_factor)
        )
    else:
        new_baseline = int(round(filtered_mean))

    new_baseline = max(40, min(120, new_baseline))

    adjustment = new_baseline - (current_baseline or new_baseline)
    adjusted = abs(adjustment) >= 1

    confidence = min(1.0, len(filtered) / 20.0) * max(0.3, 1.0 - (std_hr / 20.0))

    return {
        "status": "ok",
        "current_baseline": current_baseline,
        "new_baseline": new_baseline,
        "adjustment": adjustment,
        "adjusted": adjusted,
        "confidence": round(confidence, 3),
        "readings_used": len(filtered),
        "readings_total": len(resting_readings),
        "stats": {
            "mean_hr": round(filtered_mean, 1),
            "std_hr": round(std_hr, 1),
            "min_hr": min(filtered),
            "max_hr": max(filtered),
        },
    }


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)
    return variance ** 0.5
