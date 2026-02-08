"""
Advanced ML/AI routes.

Endpoints for anomaly detection, trend forecasting, baseline optimization,
recommendation ranking, natural language alerts, retraining readiness, and
prediction explainability.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.vital_signs import VitalSignRecord
from app.models.risk_assessment import RiskAssessment
from app.services.anomaly_detection import detect_anomalies
from app.services.trend_forecasting import forecast_trends
from app.services.baseline_optimization import compute_optimized_baseline
from app.services.recommendation_ranking import (
    get_ranked_recommendation,
    record_recommendation_outcome,
)
from app.services.natural_language_alerts import (
    generate_natural_language_alert,
    format_risk_summary,
)
from app.services.retraining_pipeline import (
    evaluate_retraining_readiness,
    get_retraining_status,
)
from app.services.explainability import explain_prediction
from app.services.ml_prediction import (
    get_ml_service,
    predict_risk as ml_predict_risk,
    model as ml_model,
    feature_columns as ml_feature_columns,
)
from app.api.auth import get_current_user, get_current_doctor_user

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RecommendationOutcomeRequest(BaseModel):
    experiment_id: str
    variant: str
    outcome: str = Field(..., description="completed, skipped, or partial")
    outcome_value: Optional[float] = None


class NaturalLanguageAlertRequest(BaseModel):
    alert_type: str = Field(..., description="e.g., high_heart_rate, low_spo2")
    severity: str = Field(..., description="info, warning, critical, emergency")
    trigger_value: Optional[str] = None
    threshold_value: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


class ExplainPredictionRequest(BaseModel):
    age: int = Field(..., ge=18, le=100)
    baseline_hr: int = Field(..., ge=40, le=100)
    max_safe_hr: int = Field(..., ge=100, le=220)
    avg_heart_rate: int = Field(..., ge=40, le=220)
    peak_heart_rate: int = Field(..., ge=40, le=250)
    min_heart_rate: int = Field(..., ge=30, le=200)
    avg_spo2: int = Field(..., ge=70, le=100)
    duration_minutes: int = Field(..., ge=1, le=300)
    recovery_time_minutes: int = Field(..., ge=1, le=60)
    activity_type: str = Field(default="walking")


# =============================================================================
# Anomaly Detection
# =============================================================================

@router.get("/anomaly-detection")
async def detect_vital_anomalies(
    hours: int = Query(24, ge=1, le=168, description="Hours of data to analyze"),
    z_threshold: float = Query(2.0, ge=1.0, le=4.0, description="Z-score threshold"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detect anomalies in the user's recent vital sign readings.

    Uses Z-score analysis and HR variability checks to find
    unusual patterns beyond simple threshold alerts.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == current_user.user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True,
        )
        .order_by(VitalSignRecord.timestamp.asc())
        .all()
    )

    readings = [
        {
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
        }
        for v in vitals
    ]

    result = detect_anomalies(readings, z_threshold=z_threshold)
    result["user_id"] = current_user.user_id
    result["window_hours"] = hours
    return result


# =============================================================================
# Trend Forecasting
# =============================================================================

@router.get("/trend-forecast")
async def forecast_vital_trends(
    days: int = Query(14, ge=7, le=90, description="Days of history to analyze"),
    forecast_days: int = Query(14, ge=7, le=30, description="Days to forecast"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Forecast vital sign trends using linear regression on historical data.

    Predicts future risk direction over the coming weeks.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == current_user.user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True,
        )
        .order_by(VitalSignRecord.timestamp.asc())
        .all()
    )

    readings = [
        {
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
        }
        for v in vitals
    ]

    result = forecast_trends(readings, forecast_days=forecast_days)
    result["user_id"] = current_user.user_id
    result["analysis_days"] = days
    return result


# =============================================================================
# Baseline Optimization
# =============================================================================

@router.get("/baseline-optimization")
async def optimize_baseline(
    days: int = Query(7, ge=3, le=30, description="Days of resting data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute an optimized baseline heart rate from recent resting data.

    Auto-adjusts the patient's baseline HR for more accurate risk calculations.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == current_user.user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True,
        )
        .order_by(VitalSignRecord.timestamp.asc())
        .all()
    )

    resting_readings = [
        {"heart_rate": v.heart_rate}
        for v in vitals
        if v.heart_rate is not None and v.heart_rate < 100
    ]

    result = compute_optimized_baseline(
        resting_readings=resting_readings,
        current_baseline=current_user.baseline_hr,
    )
    result["user_id"] = current_user.user_id
    result["data_window_days"] = days
    return result


@router.post("/baseline-optimization/apply")
async def apply_baseline_optimization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute and apply the optimized baseline to the user's profile."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == current_user.user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True,
        )
        .order_by(VitalSignRecord.timestamp.asc())
        .all()
    )

    resting_readings = [
        {"heart_rate": v.heart_rate}
        for v in vitals
        if v.heart_rate is not None and v.heart_rate < 100
    ]

    result = compute_optimized_baseline(
        resting_readings=resting_readings,
        current_baseline=current_user.baseline_hr,
    )

    if result.get("adjusted") and result.get("new_baseline"):
        current_user.baseline_hr = result["new_baseline"]
        db.commit()
        db.refresh(current_user)
        result["applied"] = True
        logger.info(
            "Baseline updated for user %s: %s -> %s",
            current_user.user_id,
            result.get("current_baseline"),
            result["new_baseline"],
        )
    else:
        result["applied"] = False

    result["user_id"] = current_user.user_id
    return result


# =============================================================================
# Recommendation Ranking (A/B Testing)
# =============================================================================

@router.get("/recommendation-ranking")
async def get_ranked_rec(
    risk_level: str = Query("low", description="Current risk level"),
    variant: Optional[str] = Query(None, description="Force variant A or B"),
    current_user: User = Depends(get_current_user),
):
    """
    Get a recommendation with A/B variant assignment for testing.
    """
    result = get_ranked_recommendation(
        user_id=current_user.user_id,
        risk_level=risk_level,
        variant_override=variant,
    )
    return result


@router.post("/recommendation-ranking/outcome")
async def record_rec_outcome(
    data: RecommendationOutcomeRequest,
    current_user: User = Depends(get_current_user),
):
    """Record outcome of a recommendation for A/B analysis."""
    result = record_recommendation_outcome(
        user_id=current_user.user_id,
        experiment_id=data.experiment_id,
        variant=data.variant,
        outcome=data.outcome,
        outcome_value=data.outcome_value,
    )
    return result


# =============================================================================
# Natural Language Alerts
# =============================================================================

@router.post("/alerts/natural-language")
async def get_natural_language_alert(
    data: NaturalLanguageAlertRequest,
    current_user: User = Depends(get_current_user),
):
    """Convert a technical alert into a patient-friendly message."""
    result = generate_natural_language_alert(
        alert_type=data.alert_type,
        severity=data.severity,
        trigger_value=data.trigger_value,
        threshold_value=data.threshold_value,
        risk_score=data.risk_score,
        risk_level=data.risk_level,
        patient_name=current_user.full_name,
    )
    return result


@router.get("/risk-summary/natural-language")
async def get_natural_language_risk_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a plain-language summary of the user's latest risk assessment."""
    ra = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == current_user.user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    if not ra:
        raise HTTPException(status_code=404, detail="No risk assessments found")

    import json as _json
    drivers = _json.loads(ra.risk_factors_json) if ra.risk_factors_json else []

    summary = format_risk_summary(
        risk_score=ra.risk_score,
        risk_level=ra.risk_level,
        drivers=drivers,
        patient_name=current_user.full_name,
    )

    return {
        "user_id": current_user.user_id,
        "risk_score": ra.risk_score,
        "risk_level": ra.risk_level,
        "plain_summary": summary,
        "assessment_date": ra.assessment_date.isoformat() if ra.assessment_date else None,
    }


# =============================================================================
# Model Retraining Pipeline
# =============================================================================

@router.get("/model/retraining-status")
async def model_retraining_status(
    current_user: User = Depends(get_current_doctor_user),
):
    """Get the current model status and retraining metadata (clinician only)."""
    return get_retraining_status()


@router.get("/model/retraining-readiness")
async def check_retraining_readiness(
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db),
):
    """
    Check if conditions are met to retrain the model (clinician only).
    """
    status_data = get_retraining_status()
    last_date = None
    if status_data.get("metadata"):
        last_date = status_data["metadata"].get("retrained_at")

    total_records = db.query(RiskAssessment).count()

    result = evaluate_retraining_readiness(
        new_records_count=total_records,
        last_retrain_date=last_date,
    )
    return result


# =============================================================================
# Explainability (SHAP-like)
# =============================================================================

@router.post("/predict/explain")
async def explain_risk_prediction(
    request: ExplainPredictionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Run a risk prediction and return feature importance explanations.
    """
    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model not loaded.",
        )

    prediction = ml_predict_risk(
        age=request.age,
        baseline_hr=request.baseline_hr,
        max_safe_hr=request.max_safe_hr,
        avg_heart_rate=request.avg_heart_rate,
        peak_heart_rate=request.peak_heart_rate,
        min_heart_rate=request.min_heart_rate,
        avg_spo2=request.avg_spo2,
        duration_minutes=request.duration_minutes,
        recovery_time_minutes=request.recovery_time_minutes,
        activity_type=request.activity_type,
    )

    explanation = explain_prediction(
        prediction_result=prediction,
        feature_columns=ml_feature_columns or [],
        model=ml_model,
    )

    return explanation
