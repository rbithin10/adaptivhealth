"""
Natural Language API Endpoints.

FastAPI routes for AI coach natural-language summaries.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
#
# ENDPOINTS
#   - GET /nl/risk-summary............. Line 45
#   - GET /nl/todays-workout........... Line 100
#   - GET /nl/alert-explanation........ Line 170
#   - GET /nl/progress-summary......... Line 235
#
# BUSINESS CONTEXT:
# - Patient-friendly AI coach summaries
# - todays-workout wired to ExerciseRecommendation table
# - All responses include structured data + natural language text
# =============================================================================
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.auth import get_current_user
from sqlalchemy import func as sa_func

from app.models.user import User
from app.models.recommendation import ExerciseRecommendation
from app.models.risk_assessment import RiskAssessment
from app.models.vital_signs import VitalSignRecord
from app.models.alert import Alert
from app.models.activity import ActivitySession
from app.schemas.nl import (
    RiskSummaryResponse,
    KeyFactors,
    TodaysWorkoutResponse,
    AlertExplanationResponse,
    AlertContext,
    ProgressSummaryResponse,
    Period,
)
from app.services.nl_builders import (
    build_risk_summary_text,
    build_todays_workout_text,
    build_alert_explanation_text,
    build_progress_summary_text,
    compute_trend,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# RISK SUMMARY ENDPOINT
# =============================================================================

@router.get("/risk-summary", response_model=RiskSummaryResponse)
async def get_risk_summary(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a natural-language risk summary for the authenticated user.

    Queries the latest RiskAssessment, recent vitals, and alert count
    within the requested time window, then returns structured health
    metrics plus an encouraging, patient-safe NL summary.

    Args:
        time_window_hours: Lookback window for vitals and alerts.
        db: Database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        RiskSummaryResponse with structured data and NL summary.
    """
    user_id = current_user.user_id
    logger.info(f"Generating risk summary for user {user_id}, window={time_window_hours}h")

    window_start = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

    # Latest risk assessment for this user
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(RiskAssessment.assessment_date.desc())
        .first()
    )

    if latest_risk:
        risk_level = latest_risk.risk_level.upper()
        risk_score = round(latest_risk.risk_score, 2)
    else:
        risk_level = "LOW"
        risk_score = 0.0

    # Aggregate vitals within the time window
    vitals_agg = (
        db.query(
            sa_func.avg(VitalSignRecord.heart_rate).label("avg_hr"),
            sa_func.max(VitalSignRecord.heart_rate).label("max_hr"),
            sa_func.avg(VitalSignRecord.spo2).label("avg_spo2"),
        )
        .filter(
            VitalSignRecord.user_id == user_id,
            VitalSignRecord.timestamp >= window_start,
        )
        .first()
    )

    avg_heart_rate = int(round(vitals_agg.avg_hr)) if vitals_agg and vitals_agg.avg_hr else 72
    max_heart_rate = int(vitals_agg.max_hr) if vitals_agg and vitals_agg.max_hr else avg_heart_rate
    avg_spo2 = int(round(vitals_agg.avg_spo2)) if vitals_agg and vitals_agg.avg_spo2 else 98

    # Count alerts in the time window
    alert_count = (
        db.query(sa_func.count(Alert.alert_id))
        .filter(
            Alert.user_id == user_id,
            Alert.created_at >= window_start,
        )
        .scalar()
    ) or 0

    # Derive safety status from risk level
    safety_map = {"LOW": "SAFE", "MODERATE": "CAUTION", "HIGH": "UNSAFE", "CRITICAL": "UNSAFE"}
    safety_status = safety_map.get(risk_level, "SAFE")

    # Build NL summary
    nl_summary = build_risk_summary_text(
        risk_level=risk_level,
        risk_score=risk_score,
        time_window_hours=time_window_hours,
        avg_heart_rate=avg_heart_rate,
        max_heart_rate=max_heart_rate,
        avg_spo2=avg_spo2,
        alert_count=alert_count,
        safety_status=safety_status,
    )

    return RiskSummaryResponse(
        user_id=user_id,
        time_window_hours=time_window_hours,
        risk_level=risk_level,
        risk_score=risk_score,
        key_factors=KeyFactors(
            avg_heart_rate=avg_heart_rate,
            max_heart_rate=max_heart_rate,
            avg_spo2=avg_spo2,
            alert_count=alert_count,
        ),
        safety_status=safety_status,
        nl_summary=nl_summary,
    )


# =============================================================================
# TODAY'S WORKOUT ENDPOINT
# =============================================================================

@router.get("/todays-workout", response_model=TodaysWorkoutResponse)
async def get_todays_workout(
    date_param: Optional[date] = Query(None, alias="date", description="Date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a natural-language workout recommendation for today.

    Queries ExerciseRecommendation for the authenticated user where the
    target date falls within [valid_from, valid_until].  Falls back to the
    most recent recommendation regardless of validity window, or generates
    a safe default low-risk recommendation if none exists.

    Args:
        date_param: Target date (defaults to today).
        db: Database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        TodaysWorkoutResponse with structured data and NL summary.
    """
    target_date = date_param or date.today()
    user_id = current_user.user_id
    logger.info(f"Generating workout plan for user {user_id}, date={target_date}")

    # Convert target date to a timezone-aware datetime for comparison
    target_dt = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)

    # 1. Try to find a recommendation valid for the target date
    recommendation = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.user_id == user_id,
            ExerciseRecommendation.valid_from <= target_dt,
            ExerciseRecommendation.valid_until >= target_dt,
        )
        .order_by(ExerciseRecommendation.created_at.desc())
        .first()
    )

    # 2. Fall back to the most recent recommendation for this user
    if recommendation is None:
        recommendation = (
            db.query(ExerciseRecommendation)
            .filter(ExerciseRecommendation.user_id == user_id)
            .order_by(ExerciseRecommendation.created_at.desc())
            .first()
        )

    # 3. Look up the user's latest risk level for context
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(RiskAssessment.assessment_date.desc())
        .first()
    )
    risk_level = (latest_risk.risk_level.upper() if latest_risk else "LOW")

    # 4. Use DB recommendation or generate a safe default
    if recommendation:
        activity_type = (recommendation.suggested_activity or "WALKING").upper()
        intensity_level = (recommendation.intensity_level or "low").upper()
        duration_minutes = recommendation.duration_minutes or 20
        target_hr_min = recommendation.target_heart_rate_min or 85
        target_hr_max = recommendation.target_heart_rate_max or 110
    else:
        # WHY: Default to a conservative walking plan so the patient
        # always receives safe guidance even without prior recommendations.
        activity_type = "WALKING"
        intensity_level = "LIGHT"
        duration_minutes = 20
        target_hr_min = 85
        target_hr_max = 110

    # Build NL summary
    nl_summary = build_todays_workout_text(
        activity_type=activity_type,
        intensity_level=intensity_level,
        duration_minutes=duration_minutes,
        target_hr_min=target_hr_min,
        target_hr_max=target_hr_max,
        risk_level=risk_level,
    )

    return TodaysWorkoutResponse(
        user_id=user_id,
        date=target_date,
        activity_type=activity_type,
        intensity_level=intensity_level,
        duration_minutes=duration_minutes,
        target_hr_min=target_hr_min,
        target_hr_max=target_hr_max,
        risk_level=risk_level,
        nl_summary=nl_summary,
    )


# =============================================================================
# ALERT EXPLANATION ENDPOINT
# =============================================================================

@router.get("/alert-explanation", response_model=AlertExplanationResponse)
async def get_alert_explanation(
    alert_id: Optional[int] = Query(None, description="Alert ID (defaults to latest)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a natural-language explanation of an alert.

    Queries the real Alert record (by ID or most recent), checks whether
    the alert occurred during an activity session, fetches the nearest
    vital-sign reading, and returns structured data plus a calm, clear
    NL explanation of what triggered it, how serious it is, and what to
    do next.

    Args:
        alert_id: Specific alert to explain. If omitted, uses the latest.
        db: Database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        AlertExplanationResponse with structured data and NL summary.
    """
    user_id = current_user.user_id
    logger.info(f"Generating alert explanation for user {user_id}, alert_id={alert_id}")

    # ------------------------------------------------------------------
    # 1. Fetch the alert record
    # ------------------------------------------------------------------
    if alert_id is not None:
        alert_record = (
            db.query(Alert)
            .filter(Alert.alert_id == alert_id, Alert.user_id == user_id)
            .first()
        )
        if not alert_record:
            raise HTTPException(
                status_code=404,
                detail="Alert not found or does not belong to this user.",
            )
    else:
        alert_record = (
            db.query(Alert)
            .filter(Alert.user_id == user_id)
            .order_by(Alert.created_at.desc())
            .first()
        )
        if not alert_record:
            return AlertExplanationResponse(
                user_id=user_id,
                alert_id=0,
                alert_type="none",
                severity_level="LOW",
                alert_time=datetime.now(timezone.utc),
                context=AlertContext(during_activity=False),
                recommended_action="CONTINUE",
                nl_summary="No recent alerts \u2014 you're doing great!",
            )

    # ------------------------------------------------------------------
    # 2. Extract core alert fields
    # ------------------------------------------------------------------
    alert_type = (alert_record.alert_type or "unknown").upper()
    severity_raw = (alert_record.severity or "info").upper()
    alert_time = alert_record.created_at or datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 3. Check if the alert occurred during an activity session
    # ------------------------------------------------------------------
    session = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == user_id,
            ActivitySession.start_time <= alert_time,
            (ActivitySession.end_time >= alert_time) | (ActivitySession.end_time.is_(None)),
        )
        .first()
    )
    during_activity = session is not None
    activity_type = session.activity_type if session else None

    # ------------------------------------------------------------------
    # 4. Get the nearest vital-sign reading at or before the alert
    # ------------------------------------------------------------------
    vital = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == user_id,
            VitalSignRecord.timestamp <= alert_time,
        )
        .order_by(VitalSignRecord.timestamp.desc())
        .first()
    )
    heart_rate = vital.heart_rate if vital else None
    spo2 = int(vital.spo2) if vital and vital.spo2 is not None else None

    # ------------------------------------------------------------------
    # 5. Map severity to recommended action
    # ------------------------------------------------------------------
    severity_action_map = {
        "LOW": "CONTINUE",
        "INFO": "CONTINUE",
        "MEDIUM": "SLOW_DOWN",
        "WARNING": "SLOW_DOWN",
        "HIGH": "STOP_AND_REST",
        "CRITICAL": "CONTACT_DOCTOR",
        "EMERGENCY": "CONTACT_DOCTOR",
    }
    recommended_action = severity_action_map.get(severity_raw, "SLOW_DOWN")

    # ------------------------------------------------------------------
    # 6. Build NL summary
    # ------------------------------------------------------------------
    nl_summary = build_alert_explanation_text(
        alert_type=alert_type,
        severity_level=severity_raw,
        alert_time=alert_time,
        during_activity=during_activity,
        activity_type=activity_type,
        heart_rate=heart_rate,
        spo2=spo2,
        recommended_action=recommended_action,
    )

    return AlertExplanationResponse(
        user_id=user_id,
        alert_id=alert_record.alert_id,
        alert_type=alert_type,
        severity_level=severity_raw,
        alert_time=alert_time,
        context=AlertContext(
            during_activity=during_activity,
            activity_type=activity_type,
            heart_rate=heart_rate,
            spo2=spo2,
        ),
        recommended_action=recommended_action,
        nl_summary=nl_summary,
    )


# =============================================================================
# PROGRESS SUMMARY ENDPOINT
# =============================================================================

@router.get("/progress-summary", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    range_param: str = Query("7d", alias="range", description="Time range (7d or 30d)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a motivational natural-language progress summary.

    Queries ActivitySession, Alert, and RiskAssessment tables for both
    the current and previous periods (7d or 30d), computes trend
    indicators, and returns an encouraging NL summary comparing progress.

    Args:
        range_param: Time range — ``7d`` or ``30d``.
        db: Database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        ProgressSummaryResponse with period stats, trends, and NL summary.
    """
    user_id = current_user.user_id
    logger.info(f"Generating progress summary for user {user_id}, range={range_param}")

    # ------------------------------------------------------------------
    # 1. Parse range and compute period boundaries
    # ------------------------------------------------------------------
    if range_param == "7d":
        days = 7
    elif range_param == "30d":
        days = 30
    else:
        raise HTTPException(status_code=400, detail="Range must be '7d' or '30d'")

    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=days)
    current_end = now
    previous_start = current_start - timedelta(days=days)
    previous_end = current_start

    # ------------------------------------------------------------------
    # 2. Helper: build a Period from DB data for a given time window
    # ------------------------------------------------------------------
    def _build_period(start: datetime, end: datetime) -> Period:
        """Query DB aggregates for a single time window."""

        # Activity sessions — count and total duration
        activity_agg = (
            db.query(
                sa_func.count(ActivitySession.session_id),
                sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0),
            )
            .filter(
                ActivitySession.user_id == user_id,
                ActivitySession.start_time >= start,
                ActivitySession.start_time < end,
            )
            .one()
        )
        workout_count: int = activity_agg[0]
        total_active_minutes: int = int(activity_agg[1])

        # Alert count
        alert_count: int = (
            db.query(sa_func.count(Alert.alert_id))
            .filter(
                Alert.user_id == user_id,
                Alert.created_at >= start,
                Alert.created_at < end,
            )
            .scalar()
        ) or 0

        # Average risk level across RiskAssessments in the window
        avg_risk_score = (
            db.query(sa_func.avg(RiskAssessment.risk_score))
            .filter(
                RiskAssessment.user_id == user_id,
                RiskAssessment.assessment_date >= start,
                RiskAssessment.assessment_date < end,
            )
            .scalar()
        )
        if avg_risk_score is not None:
            if avg_risk_score >= 0.7:
                avg_risk_level = "HIGH"
            elif avg_risk_score >= 0.4:
                avg_risk_level = "MODERATE"
            else:
                avg_risk_level = "LOW"
        else:
            avg_risk_level = "LOW"

        # Time in safe zone vs above — based on activity sessions
        # Safe zone: risk_score < 0.4 (LOW); above: risk_score >= 0.4
        safe_minutes: int = int(
            db.query(
                sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0)
            )
            .filter(
                ActivitySession.user_id == user_id,
                ActivitySession.start_time >= start,
                ActivitySession.start_time < end,
                ActivitySession.risk_score < 0.4,
            )
            .scalar()
        )
        above_minutes: int = int(
            db.query(
                sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0)
            )
            .filter(
                ActivitySession.user_id == user_id,
                ActivitySession.start_time >= start,
                ActivitySession.start_time < end,
                ActivitySession.risk_score >= 0.4,
            )
            .scalar()
        )

        return Period(
            start=start,
            end=end,
            workout_count=workout_count,
            total_active_minutes=total_active_minutes,
            avg_risk_level=avg_risk_level,
            time_in_safe_zone_minutes=safe_minutes,
            time_above_safe_zone_minutes=above_minutes,
            alert_count=alert_count,
        )

    # ------------------------------------------------------------------
    # 3. Build periods from real data
    # ------------------------------------------------------------------
    current_period = _build_period(current_start, current_end)
    previous_period = _build_period(previous_start, previous_end)

    # ------------------------------------------------------------------
    # 4. Compute trend and NL summary
    # ------------------------------------------------------------------
    trend = compute_trend(current_period, previous_period)

    nl_summary = build_progress_summary_text(
        current=current_period,
        previous=previous_period,
        trend=trend,
    )

    return ProgressSummaryResponse(
        user_id=user_id,
        range=range_param,
        current_period=current_period,
        previous_period=previous_period,
        trend=trend,
        nl_summary=nl_summary,
    )
