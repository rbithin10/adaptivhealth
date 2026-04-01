"""
Shared risk-driver builder utilities.

Two entry points:
  - build_drivers_from_features()  — for session-based paths (predict.py)
  - build_drivers_from_vitals()    — for point-in-time vital-sign paths (vital_signs.py)
"""

from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


def build_drivers_from_features(user: "User", features: dict[str, Any]) -> list[str]:
    """
    Human-readable risk drivers derived from an activity session feature dict.

    Expected keys: peak_heart_rate, avg_heart_rate, avg_spo2, duration_minutes,
    peak_intensity (optional).
    """
    drivers: list[str] = []

    baseline = user.baseline_hr or 72
    max_safe = user.max_safe_hr or (220 - (user.age or 45))

    peak = features["peak_heart_rate"]
    avg = features["avg_heart_rate"]
    spo2 = features["avg_spo2"]

    if peak > max_safe:
        drivers.append(f"Peak heart rate exceeded safe limit ({peak} > {max_safe}).")
    if avg - baseline >= 25:
        drivers.append(f"Average heart rate elevated vs baseline ({avg} vs {baseline}).")
    if spo2 <= 92:
        drivers.append(f"Average SpO\u2082 is low ({spo2}%).")
    if features["duration_minutes"] >= 45 and peak > int(0.8 * max_safe):
        drivers.append("Sustained high intensity for long duration.")

    if not drivers:
        drivers.append("Vitals are within expected safe limits.")

    return drivers


def build_drivers_from_vitals(
    user: "User",
    hr: int,
    spo2: float,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    hrv: Optional[float] = None,
) -> list[str]:
    """
    Human-readable risk drivers derived from a single point-in-time vital reading.

    Used by vital_signs.py paths (batch_cloud, edge_sync, critical_push) where
    there is no full activity-session feature dict.
    """
    drivers: list[str] = []

    baseline = user.baseline_hr or 72
    max_safe = user.max_safe_hr or (220 - (user.age or 45))

    if hr > max_safe:
        drivers.append(f"Heart rate exceeded safe limit ({hr} > {max_safe}).")
    if hr - baseline >= 25:
        drivers.append(f"Heart rate elevated vs baseline ({hr} vs {baseline}).")
    if spo2 <= 92:
        drivers.append(f"SpO\u2082 is low ({spo2}%).")

    if systolic_bp is not None:
        if systolic_bp >= 140:
            drivers.append(f"Systolic blood pressure is high ({systolic_bp} mmHg).")
        elif systolic_bp <= 90:
            drivers.append(f"Systolic blood pressure is low ({systolic_bp} mmHg).")

    if hrv is not None and hrv <= 20:
        drivers.append(f"HRV is very low ({hrv:.1f} ms), indicating stress or fatigue.")

    if not drivers:
        drivers.append("Vitals are within expected safe limits.")

    return drivers
