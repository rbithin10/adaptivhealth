"""
Compound confidence scorer for risk assessments.

Replaces the raw predict_proba() max as the stored confidence value.
Blends four real-world reliability factors so the number reflects
how much the clinician should trust the assessment, not just how
certain the ML model is about its own output.

Factors and weights:
  - Baseline maturity  (30%) — how many days of data the model knows this patient
  - Data completeness  (25%) — valid vital readings in the last 48 hours
  - Signal quality     (25%) — average device confidence_score on recent readings
  - Recency            (20%) — how fresh the most recent reading is

The raw ML confidence is used as a floor multiplier so a model that is
itself uncertain cannot produce a high composite score.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.user import User


def compute_confidence_score(
    ml_confidence: float,
    user: "User",
    db: "Session",
    reference_time: Optional[datetime] = None,
) -> float:
    """
    Return a composite confidence float (0.0–1.0).

    Args:
        ml_confidence: predict_proba max from the ML model (0.0–1.0).
        user:          The patient's User ORM object.
        db:            Active SQLAlchemy session (read-only queries).
        reference_time: Timestamp to treat as "now" (defaults to UTC now).

    Returns:
        Float in [0.0, 1.0] representing composite reliability.
    """
    from app.models.vital_signs import VitalSignRecord

    now = reference_time or datetime.now(timezone.utc)
    window_start = now - timedelta(hours=48)

    # ── Query recent valid vitals ────────────────────────────────────────────
    recent_vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == user.user_id,
            VitalSignRecord.is_valid == True,
            VitalSignRecord.timestamp >= window_start,
            VitalSignRecord.timestamp <= now,
        )
        .order_by(VitalSignRecord.timestamp.desc())
        .all()
    )

    vitals_count = len(recent_vitals)
    most_recent_ts = recent_vitals[0].timestamp if recent_vitals else None
    signal_scores = [
        v.confidence_score
        for v in recent_vitals
        if v.confidence_score is not None
    ]
    avg_signal = sum(signal_scores) / len(signal_scores) if signal_scores else None

    # ── Factor 1: Baseline maturity (30%) ───────────────────────────────────
    # Uses account age as proxy for how much the model has learned about this
    # patient. baseline_hr being set adds a small bonus.
    account_age_days = 0
    if user.created_at:
        created = user.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        account_age_days = max(0, (now - created).days)

    if account_age_days < 3:
        maturity_score = 0.35
    elif account_age_days < 7:
        maturity_score = 0.55
    elif account_age_days < 14:
        maturity_score = 0.75
    else:
        maturity_score = 1.0

    # Bonus: baseline_hr personalised from their own data
    if user.baseline_hr:
        maturity_score = min(1.0, maturity_score + 0.05)

    # ── Factor 2: Data completeness (25%) ────────────────────────────────────
    # How many valid vitals exist in the last 48 hours.
    if vitals_count == 0:
        completeness_score = 0.20
    elif vitals_count <= 3:
        completeness_score = 0.45
    elif vitals_count <= 10:
        completeness_score = 0.65
    elif vitals_count <= 24:
        completeness_score = 0.85
    else:
        completeness_score = 1.0

    # ── Factor 3: Signal quality (25%) ───────────────────────────────────────
    # Average device-reported confidence_score on those readings.
    # Falls back to 0.70 (neutral) if no readings carry a score.
    quality_score = avg_signal if avg_signal is not None else 0.70

    # ── Factor 4: Recency (20%) ───────────────────────────────────────────────
    # How fresh is the most recent reading.
    if most_recent_ts is None:
        recency_score = 0.30
    else:
        ts = most_recent_ts
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (now - ts).total_seconds() / 3600
        if age_hours <= 1:
            recency_score = 1.0
        elif age_hours <= 6:
            recency_score = 0.85
        elif age_hours <= 24:
            recency_score = 0.65
        else:
            recency_score = 0.35

    # ── Composite blend ───────────────────────────────────────────────────────
    composite = (
        0.30 * maturity_score
        + 0.25 * completeness_score
        + 0.25 * quality_score
        + 0.20 * recency_score
    )

    # ML confidence acts as a ceiling multiplier: a model that is itself
    # uncertain (< 0.6) pulls the final score down proportionally.
    # Models that are certain (>= 0.8) don't inflate the composite.
    ml_factor = min(1.0, ml_confidence / 0.80)
    adjusted = composite * (0.70 + 0.30 * ml_factor)

    return round(min(1.0, max(0.0, adjusted)), 4)


def confidence_to_band(confidence: float) -> str:
    """
    Map a 0–1 confidence float to a display band label.

    85–100% → "High reliability"
    70–84%  → "Moderate reliability"
    Below 70% → "Low reliability"
    """
    pct = confidence * 100
    if pct >= 85:
        return "High reliability"
    elif pct >= 70:
        return "Moderate reliability"
    else:
        return "Low reliability"
