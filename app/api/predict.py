"""
Risk prediction routes.

These endpoints use the AI model to estimate heart risk.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 30
# REQUEST/RESPONSE SCHEMAS............. Line 55
#
# ENDPOINTS - PUBLIC/SYSTEM
#   - GET /predict/status.............. Line 227 (Model health check)
#
# ENDPOINTS - ML PREDICTION
#   - POST /predict/risk............... Line 245 (Predict from manual input)
#   - GET /predict/user/{id}/risk...... Line 317 (Clinician predict for patient)
#   - GET /predict/my-risk............. Line 405 (Patient's own prediction)
#
# ENDPOINTS - RISK ASSESSMENT (stored records)
#   - POST /risk-assessments/compute... Line 518 (Compute & store patient risk)
#   - POST /patients/{id}/risk-....... Line 604 (Clinician compute for patient)
#   - GET /risk-assessments/latest..... Line 695 (Patient's latest assessment)
#   - GET /patients/{id}/risk-......... Line 721 (Clinician view patient risk)
#
# ENDPOINTS - RECOMMENDATIONS
#   - GET /recommendations/latest...... Line 753 (Patient's exercise recommendation)
#   - GET /patients/{id}/recommend..... Line 782 (Clinician view patient rec)
#
# BUSINESS CONTEXT:
# - ML model predicts cardiac risk from vitals + activity
# - Risk levels: LOW (<0.3), MODERATE (0.3-0.6), HIGH (>0.6)
# - Used to generate personalized exercise recommendations
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import time
from datetime import datetime, timedelta, timezone, date
import json

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.risk_assessment import RiskAssessment
from app.models.vital_signs import VitalSignRecord
from app.models.recommendation import ExerciseRecommendation
from app.models.nutrition import NutritionEntry
from app.models.sleep import SleepEntry
from app.services.ml_prediction import get_ml_service, MLPredictionService, apply_medical_adjustments, get_adjusted_max_hr
from app.services.recommendation_ranking import select_exercise
from app.services.risk_drivers import build_drivers_from_features
from app.services.confidence_scorer import compute_confidence_score
from app.api.auth import get_current_user, get_current_doctor_user, check_clinician_phi_access

# Logger
logger = logging.getLogger(__name__)

# Router
router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RiskPredictionRequest(BaseModel):
    """Input data for risk prediction."""
    age: int = Field(..., ge=18, le=100, description="Patient age")
    baseline_hr: int = Field(..., ge=25, le=110, description="Resting HR. Beta-blockers/sleep: 25-40 OK")
    max_safe_hr: int = Field(..., ge=100, le=220, description="Maximum safe heart rate")
    avg_heart_rate: int = Field(..., ge=25, le=220, description="Average HR during session")
    peak_heart_rate: int = Field(..., ge=40, le=250, description="Peak HR during session")
    min_heart_rate: int = Field(..., ge=20, le=200, description="Minimum HR during session")
    avg_spo2: int = Field(..., ge=85, le=100, description="Average SpO2 during session")
    duration_minutes: int = Field(..., ge=1, le=300, description="Session duration in minutes")
    recovery_time_minutes: int = Field(..., ge=1, le=60, description="Recovery time in minutes")
    activity_type: str = Field(default="walking", description="Activity type")


class RiskPredictionResponse(BaseModel):
    """Response from risk prediction."""
    risk_score: float = Field(..., description="Risk score 0.0 to 1.0")
    risk_level: str = Field(..., description="low, moderate, or high")
    high_risk: bool = Field(..., description="True if high risk")
    confidence: float = Field(..., description="Model confidence")
    recommendation: str = Field(..., description="Safety recommendation")
    inference_time_ms: float = Field(..., description="Prediction time in ms")
    model_info: Dict[str, Any] = Field(..., description="Model details")
    features_used: Optional[Dict[str, float]] = Field(None, description="Engineered features")


class RiskAssessmentComputeResponse(BaseModel):
    assessment_id: int
    user_id: int
    risk_score: float
    risk_level: str
    confidence: float | None = None
    inference_time_ms: float | None = None
    drivers: list[str] = []
    based_on: dict[str, Any] = {}


class RecommendationResponse(BaseModel):
    recommendation_id: int
    user_id: int
    title: str
    suggested_activity: str
    intensity_level: str
    duration_minutes: int
    target_heart_rate_min: int | None = None
    target_heart_rate_max: int | None = None
    description: str | None = None
    warnings: str | None = None
    created_at: str | None = None


class RecommendationCompleteRequest(BaseModel):
    actual_minutes: Optional[int] = Field(None, ge=1)


class SleepLogRequest(BaseModel):
    bedtime: datetime
    wake_time: datetime
    quality_rating: int = Field(..., ge=1, le=5)
    notes: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def _get_recent_vitals_window(
    db: Session, user_id: int, window_minutes: int = 30
) -> list[VitalSignRecord]:
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)  # How far back to look
    return (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == user_id,  # Only this patient's readings
            VitalSignRecord.timestamp >= since,  # Within the time window
            VitalSignRecord.is_valid == True  # Skip any flagged-bad readings
        )
        .order_by(VitalSignRecord.timestamp.asc())  # Oldest first
        .all()
    )


def _aggregate_session_features_from_vitals(vitals: list[VitalSignRecord]) -> dict[str, Any]:
    """
    Convert raw vitals into the session-style fields the ML model expects.
    If only 1 reading exists, we still produce a valid feature set.
    """
    if not vitals:
        raise ValueError("No vitals to aggregate")

    hrs = [v.heart_rate for v in vitals]  # Collect all heart rate readings
    spo2s = [v.spo2 for v in vitals if v.spo2 is not None]  # Collect all valid SpO2 readings

    start = vitals[0].timestamp  # When the monitoring window started
    end = vitals[-1].timestamp  # When it ended
    duration_minutes = max(1, int((end - start).total_seconds() / 60)) if start and end else 10  # How long in minutes

    avg_hr = int(sum(hrs) / len(hrs))  # Average heart rate across all readings
    peak_hr = int(max(hrs))  # Highest heart rate recorded
    min_hr = int(min(hrs))  # Lowest heart rate recorded
    avg_spo2 = int(sum(spo2s) / len(spo2s)) if spo2s else 97  # Average blood oxygen level

    activity_type = vitals[-1].activity_type or "walking"  # Use the latest reading's activity type

    # Recovery time is not directly observable from a vitals window.
    # For now, use a safe default or infer from phase if you store it.
    recovery_time_minutes = 5

    return {
        "avg_heart_rate": avg_hr,
        "peak_heart_rate": peak_hr,
        "min_heart_rate": min_hr,
        "avg_spo2": avg_spo2,
        "duration_minutes": duration_minutes,
        "recovery_time_minutes": recovery_time_minutes,
        "activity_type": activity_type,
        "start_time": start.isoformat() if start else None,
        "end_time": end.isoformat() if end else None,
        "points": len(vitals),
        "latest_hr": vitals[-1].heart_rate,
        "latest_spo2": vitals[-1].spo2
    }



def _generate_recommendation_payload(
    user: User,
    risk_level: str,
    risk_score: float,
    drivers: list[str],
    last_activity: Optional[str] = None,
    medical_flags: Optional[Dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build a recommendation payload by selecting from the exercise library.

    Picks a random template appropriate for *risk_level*, avoids repeating
    the same suggested_activity as *last_activity*, then overlays
    personalised heart-rate targets from the patient's profile.

    Args:
        user: The patient's User model (provides baseline_hr, max_safe_hr, age).
        risk_level: Risk classification string ("critical", "high", "moderate", "low").
        risk_score: Numeric risk score 0.0-1.0 (reserved for future granularity).
        drivers: Human-readable risk-driver strings (unused here, kept for parity).
        last_activity: The suggested_activity of the patient's most recent
                       recommendation, used to avoid consecutive repeats.
        medical_flags: Optional dict with is_on_beta_blocker, is_on_anticoagulant etc.

    Returns:
        Dict matching the ExerciseRecommendation column set.
    """
    med = medical_flags or {}
    baseline = user.baseline_hr or 72

    # Use adjusted max HR if patient is on beta-blocker
    if med.get("is_on_beta_blocker"):
        max_safe = get_adjusted_max_hr(user.age or 45, True)
    else:
        max_safe = user.max_safe_hr or (220 - (user.age or 45))

    # Select exercise template from the library (avoids last_activity repeat)
    exercise = select_exercise(risk_level, last_activity=last_activity)

    # Compute personalised heart-rate targets based on risk tier
    if risk_level in ("critical", "high"):
        target_hr_min = None
        target_hr_max = min(max_safe - 20, baseline + 20)
    elif risk_level == "moderate":
        target_hr_min = baseline + 10
        target_hr_max = min(int(0.75 * max_safe), baseline + 35)
    else:  # low
        target_hr_min = baseline + 15
        target_hr_max = min(int(0.80 * max_safe), baseline + 45)

    # Build warnings from exercise template + medication flags
    warnings_parts = []
    if exercise.get("warnings"):
        warnings_parts.append(exercise["warnings"])
    if med.get("is_on_anticoagulant"):
        warnings_parts.append("Patient on anticoagulant — avoid contact sports and high-fall-risk activities.")
    if med.get("is_on_beta_blocker"):
        warnings_parts.append(f"Target HR adjusted for beta-blocker therapy (max HR: {max_safe} bpm).")

    return {
        "title": exercise["title"],
        "suggested_activity": exercise["suggested_activity"],
        "intensity_level": exercise["intensity_level"],
        "duration_minutes": exercise["duration_minutes"],
        "target_heart_rate_min": target_hr_min,
        "target_heart_rate_max": target_hr_max,
        "description": exercise["description"],
        "warnings": " ".join(warnings_parts) if warnings_parts else exercise.get("warnings"),
    }


def _resolve_date(date_str: Optional[str]) -> date:
    if not date_str:
        return datetime.now(timezone.utc).date()
    return date.fromisoformat(date_str)


# Risk-adjusted daily calorie burn targets (kcal) — lower targets for higher-risk patients
_CALORIE_BURN_TARGET: dict[str, int] = {'low': 300, 'moderate': 200, 'high': 150, 'critical': 75}
# Risk-adjusted daily calorie intake goals (kcal)
_CALORIE_INTAKE_GOAL: dict[str, int] = {'low': 2200, 'moderate': 2000, 'high': 1800, 'critical': 1600}


def _get_risk_multiplier(risk_score: float) -> float:
    if risk_score >= 0.8:
        return 0.25
    if risk_score >= 0.6:
        return 0.5
    if risk_score >= 0.3:
        return 0.75
    return 1.0


def _calculate_daily_recovery_score(
    db: Session,
    user: User,
    target_date: date,
) -> dict[str, Any]:
    activities = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == user.user_id,
            func.date(ActivitySession.start_time) == target_date,
            or_(ActivitySession.status == "completed", ActivitySession.status.is_(None))
        )
        .all()
    )

    total_actual_mins = sum((a.duration_minutes or 0) for a in activities)
    workouts_completed = len(activities)
    total_calories_burned = sum((a.calories_burned or 0) for a in activities)

    # Fetch risk level first so targets can be adjusted for this patient's risk
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user.user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    risk_score = latest_risk.risk_score if latest_risk else 0.0
    risk_level = latest_risk.risk_level if latest_risk else "low"
    multiplier = _get_risk_multiplier(risk_score)

    completed_recs = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.user_id == user.user_id,
            ExerciseRecommendation.is_completed == True,
            func.date(ExerciseRecommendation.updated_at) == target_date,
        )
        .all()
    )

    if completed_recs:
        total_target_mins = sum((r.duration_minutes or 0) for r in completed_recs)
    else:
        total_target_mins = workouts_completed * 30

    # Workout component: 60% from time, 40% from calories burned vs risk-adjusted target
    calorie_burn_target = _CALORIE_BURN_TARGET.get(risk_level, 300)
    time_ratio = min(total_actual_mins / max(total_target_mins, 1), 1.0) if total_actual_mins > 0 else 0.0
    calorie_burn_ratio = min(total_calories_burned / calorie_burn_target, 1.0) if calorie_burn_target > 0 else 0.0
    workout_ratio = (time_ratio * 0.60) + (calorie_burn_ratio * 0.40)

    nutrition_entries = (
        db.query(NutritionEntry)
        .filter(
            NutritionEntry.user_id == user.user_id,
            func.date(NutritionEntry.timestamp) == target_date,
        )
        .all()
    )
    total_calories = sum((n.calories or 0) for n in nutrition_entries)
    calorie_goal = _CALORIE_INTAKE_GOAL.get(risk_level, 2000)
    calorie_ratio = min(total_calories / max(calorie_goal, 1), 1.0)

    sleep_entry = (
        db.query(SleepEntry)
        .filter(
            SleepEntry.user_id == user.user_id,
            SleepEntry.date == target_date,
        )
        .order_by(desc(SleepEntry.created_at))
        .first()
    )
    sleep_hours = sleep_entry.duration_hours if sleep_entry and sleep_entry.duration_hours else 0.0
    sleep_ratio = min(sleep_hours / 8.0, 1.0) if sleep_hours > 0 else 0.0

    base = (workout_ratio * 35) + (calorie_ratio * 35) + (sleep_ratio * 30)
    score = int(base * multiplier)

    return {
        "date": target_date.isoformat(),
        "score": score,
        "workout_score": int(workout_ratio * 100),
        "nutrition_score": int(calorie_ratio * 100),
        "sleep_score": int(sleep_ratio * 100),
        "risk_level": risk_level,
        "risk_multiplier": multiplier,
        "workouts_completed": workouts_completed,
        "actual_minutes": total_actual_mins,
        "target_minutes": total_target_mins,
        "total_minutes": total_actual_mins,
        "calories_burned": total_calories_burned,
        "calorie_burn_target": calorie_burn_target,
        "calories_consumed": total_calories,
        "calorie_goal": calorie_goal,
        "sleep_hours": round(sleep_hours, 2),
    }


def _compute_risk_assessment(
    user_id: int,
    vitals: list[VitalSignRecord],
    medical_conditions: list,
    medications: list,
    db: Session,
) -> dict:
    """Compute, store, and return a risk assessment and recommendation payload."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    features = _aggregate_session_features_from_vitals(vitals)
    drivers = build_drivers_from_features(user, features)

    active_conditions = [
        condition for condition in medical_conditions
        if getattr(condition, "status", None) == "active"
    ]
    active_medications = [
        medication for medication in medications
        if getattr(medication, "status", None) == "active"
    ]

    heart_failure_class = None
    for condition in active_conditions:
        if getattr(condition, "condition_type", None) == "heart_failure":
            detail = (getattr(condition, "condition_detail", "") or "").upper()
            for cls in ["IV", "III", "II", "I"]:
                if cls in detail:
                    heart_failure_class = cls
                    break
            if heart_failure_class:
                break

    med_flags = {
        "has_prior_mi": any(
            getattr(condition, "condition_type", None) == "prior_mi"
            for condition in active_conditions
        ),
        "has_heart_failure": any(
            getattr(condition, "condition_type", None) == "heart_failure"
            for condition in active_conditions
        ),
        "heart_failure_class": heart_failure_class,
        "is_on_beta_blocker": any(
            getattr(medication, "drug_class", None) == "beta_blocker"
            for medication in active_medications
        ),
        "is_on_anticoagulant": any(
            getattr(medication, "is_anticoagulant", False)
            or getattr(medication, "drug_class", None) == "anticoagulant"
            for medication in active_medications
        ),
    }

    adjusted_max_hr = get_adjusted_max_hr(user.age or 45, med_flags["is_on_beta_blocker"])  # Lower max HR if on beta blockers

    start_time = time.time()  # Start timing the AI prediction
    result = service.predict_risk(
        age=user.age or 45,
        baseline_hr=user.baseline_hr or 72,
        max_safe_hr=adjusted_max_hr,
        avg_heart_rate=features["avg_heart_rate"],
        peak_heart_rate=features["peak_heart_rate"],
        min_heart_rate=features["min_heart_rate"],
        avg_spo2=features["avg_spo2"],
        duration_minutes=features["duration_minutes"],
        recovery_time_minutes=features["recovery_time_minutes"],
        activity_type=features["activity_type"],
    )
    inference_ms = (time.time() - start_time) * 1000  # How long the prediction took in milliseconds

    adjusted_score, med_adjustments = apply_medical_adjustments(result["risk_score"], med_flags)  # Adjust risk for medications
    result["risk_score"] = adjusted_score
    if adjusted_score >= 0.80:  # Reclassify risk level based on adjusted score
        result["risk_level"] = "high"
    elif adjusted_score >= 0.50:
        result["risk_level"] = "moderate"
    else:
        result["risk_level"] = "low"
    drivers.extend(med_adjustments)  # Add any medication-related risk factors

    adjusted_confidence = compute_confidence_score(
        ml_confidence=result.get("confidence") or 0.5,
        user=user,
        db=db,
    )
    ra = RiskAssessment(  # Save the risk assessment to the database
        user_id=user_id,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        confidence=adjusted_confidence,
        inference_time_ms=round(inference_ms, 2),
        model_name=result.get("model_info", {}).get("name"),
        model_version=result.get("model_info", {}).get("version"),
        input_heart_rate=features["avg_heart_rate"],
        input_spo2=features["avg_spo2"],
        input_blood_pressure_sys=vitals[-1].systolic_bp,
        input_blood_pressure_dia=vitals[-1].diastolic_bp,
        input_hrv=vitals[-1].hrv,
        primary_concern=drivers[0] if drivers else None,
        risk_factors_json=json.dumps(drivers),
        assessment_type="vitals_window",
        generated_by="cloud_ai",
    )
    db.add(ra)
    db.commit()
    db.refresh(ra)

    prev_rec = (  # Check what exercise was last recommended to avoid repeats
        db.query(ExerciseRecommendation)
        .filter(ExerciseRecommendation.user_id == user_id)
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    last_activity = prev_rec.suggested_activity if prev_rec else None

    rec_payload = _generate_recommendation_payload(  # Pick a new exercise recommendation
        user,
        ra.risk_level,
        ra.risk_score,
        drivers,
        last_activity=last_activity,
        medical_flags=med_flags,
    )
    rec = ExerciseRecommendation(  # Save the new exercise recommendation to the database
        user_id=user_id,
        title=rec_payload["title"],
        suggested_activity=rec_payload["suggested_activity"],
        intensity_level=rec_payload["intensity_level"],
        duration_minutes=rec_payload["duration_minutes"],
        target_heart_rate_min=rec_payload["target_heart_rate_min"],
        target_heart_rate_max=rec_payload["target_heart_rate_max"],
        description=rec_payload["description"],
        warnings=rec_payload["warnings"],
        based_on_risk_assessment_id=ra.assessment_id,
        model_name=ra.model_name,
        confidence_score=ra.confidence,
        generated_by="cloud_ai",
    )
    db.add(rec)
    db.commit()

    return {
        "assessment_id": ra.assessment_id,
        "user_id": user_id,
        "risk_score": ra.risk_score,
        "risk_level": ra.risk_level,
        "confidence": ra.confidence,
        "inference_time_ms": ra.inference_time_ms,
        "drivers": drivers,
        "based_on": {
            "window_minutes": 30,
            "points": features["points"],
            "activity_type": features["activity_type"],
        },
    }


# =============================================================================
# Endpoints
# =============================================================================

# =============================================
# CHECK_MODEL_STATUS - ML model health check
# Used by: System monitoring, deployment checks
# Returns: Model ready status and feature count
# Roles: PUBLIC (no auth required)
# =============================================
@router.get("/predict/status")
async def check_model_status():
    """Check if the ML model is loaded and ready."""
    try:
        service = get_ml_service()
        return {
            "status": "ready" if service.is_loaded else "not_loaded",
            "model_loaded": service.is_loaded,
            "features_count": len(service.feature_columns) if service.feature_columns else 0
        }
    except Exception as e:
        return {
            "status": "error",
            "model_loaded": False,
            "error": str(e)
        }


# =============================================
# PREDICT_RISK - Core ML prediction endpoint
# Used by: Mobile app during activity sessions
# Returns: RiskPredictionResponse with score + recommendation
# Roles: ALL authenticated users
# =============================================
@router.post("/predict/risk", response_model=RiskPredictionResponse)
async def predict_risk(
    request: RiskPredictionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Predict cardiovascular risk for a workout session.
    
    It takes the user’s readings and returns a risk score and a short tip.
    The mobile app uses this to warn users during exercise.
    """
    # Load ML service
    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model not loaded. Check server logs."
        )

    # Run prediction with timing
    start_time = time.time()

    try:
        # Call MLPredictionService to:
        # 1. Engineer features from raw vitals
        # 2. Run model inference
        # 3. Map probability to risk level
        # 4. Generate text recommendation
        result = service.predict_risk(
            age=request.age,
            baseline_hr=request.baseline_hr,
            max_safe_hr=request.max_safe_hr,
            avg_heart_rate=request.avg_heart_rate,
            peak_heart_rate=request.peak_heart_rate,
            min_heart_rate=request.min_heart_rate,
            avg_spo2=request.avg_spo2,
            duration_minutes=request.duration_minutes,
            recovery_time_minutes=request.recovery_time_minutes,
            activity_type=request.activity_type
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )

    # Calculate inference time
    # WHY track inference time:
    # - Monitor if model slows down (memory pressure, I/O bottleneck)
    # - Alert if prediction takes >1s (indicates server issue)
    # - Mobile app uses this to show \"computing...\" vs instant response
    inference_ms = (time.time() - start_time) * 1000

    logger.info(
        f"Risk prediction for user {current_user.user_id}: "
        f"score={result['risk_score']}, level={result['risk_level']}, "
        f"time={inference_ms:.1f}ms"
    )

    return RiskPredictionResponse(
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        high_risk=result["high_risk"],
        confidence=result["confidence"],
        recommendation=result["recommendation"],
        inference_time_ms=round(inference_ms, 2),
        model_info=result["model_info"],
        features_used=result["features_used"]
    )


# =============================================
# PREDICT_USER_RISK_FROM_LATEST_SESSION - Clinician patient check
# Used by: Clinician dashboard patient detail view
# Returns: Risk prediction from patient's latest activity session
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/predict/user/{user_id}/risk")
async def predict_user_risk_from_latest_session(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Clinicians can check a patient's latest session risk here.
    Only clinicians and admins can use it.

    ENDPOINT PURPOSE:
    - Allows healthcare providers to review patient's risk from latest session
    - Similar to predict_risk, but uses data from database instead of request body
    - Used in clinician dashboard to understand patient's recent activity risk
    
    DATA SOURCES:
    - Patient profile: age, baseline_hr, max_safe_hr (pulled from User model)
    - Latest session: avg_heart_rate, peak_heart_rate, duration, etc. (from ActivitySession table)
    - Database query: Gets most recent session for the patient from AWS RDS
    
    ACCESS CONTROL:
    - Requires get_current_doctor_user dependency (checks role = \"doctor\" or \"admin\")
    - Prevents patients from requesting predictions for other patients
    - Prevents unauthorized access to patient activity data
    
    RATIONALE FOR SEPARATE ENDPOINT:
    - Real-time predictions use /predict/risk (mobile app, inline)
    - Clinician tools use this endpoint (dashboard, patient review)
    - Decouples patient-facing real-time API from clinician tools
    
    FALLBACK STRATEGY:
    - Uses 'or' defaults for missing user fields (age || 55)
    - Prevents 500 error if patient never filled profile
    - Allows prediction even with incomplete patient data
    - Could be improved: Show warning if using defaults
    """
    # Get user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    check_clinician_phi_access(current_user, user)

    # Get the most recent session for this user.
    session = db.query(ActivitySession)\
        .filter(ActivitySession.user_id == user_id)\
        .order_by(desc(ActivitySession.start_time))\
        .first()

    if not session:
        raise HTTPException(status_code=404, detail="No activity sessions found for user")

    # Load ML service
    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    # Run prediction using user profile + session data
    start_time = time.time()
    result = service.predict_risk(
        age=user.age or 45,
        baseline_hr=user.baseline_hr or 72,
        max_safe_hr=user.max_safe_hr or (220 - (user.age or 45)),
        avg_heart_rate=session.avg_heart_rate or 90,
        peak_heart_rate=session.peak_heart_rate or 120,
        min_heart_rate=session.min_heart_rate or 65,
        avg_spo2=session.avg_spo2 or 96,
        duration_minutes=session.duration_minutes or 30,
        recovery_time_minutes=session.recovery_time_minutes or 8,
        activity_type=session.activity_type or "walking"
    )
    inference_ms = (time.time() - start_time) * 1000

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "session_id": session.session_id,
        "session_date": session.start_time.isoformat() if session.start_time else None,
        "prediction": {
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"],
            "high_risk": result["high_risk"],
            "confidence": result["confidence"],
            "recommendation": result["recommendation"]
        },
        "inference_time_ms": round(inference_ms, 2)
    }

# =============================================
# GET_MY_RISK_HISTORY - Patient's own risk trend
# Used by: Mobile app history/trends view
# Returns: List of recent risk assessments
# Roles: ALL authenticated users (own data only)
# =============================================
@router.get("/predict/my-risk")
async def get_my_risk_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """
    Get current patient's own risk assessment history.
    Available to all authenticated users (patients, doctors, admins).

    ENDPOINT PURPOSE:
    - Shows patient their historical risk assessments
    - Useful for tracking trends (improving or declining?)
    - Mobile app displays this in \"History\" or \"Trends\" view
    
    ACCESS CONTROL:
    - Requires authentication (get_current_user)
    - Patient only sees their own history
    - Doctors can access their patient's history via different endpoint
    - No role restriction (both patient and clinician can view their own)
    
    DATA SOURCE:
    - RiskAssessment table (database records of all risk evaluations)
    - Ordered by most recent first (assessment_date DESC)
    - Limited to last N records (default 10, configurable)
    
    RESPONSE STRUCTURE:
    - user_id: Who the assessments belong to
    - risk_assessments: Array with risk_score, risk_level, assessment_date, etc.
    - Custom recommendation: Generated from risk_level (not stored in DB)
    
    WHY GENERATE RECOMMENDATIONS HERE:
    - Recommendations may change based on updated guidelines
    - Avoids storing redundant data (can be computed from risk_level)
    - Allows updating recommendation logic without database migration
    - Each historical record shows what recommendation would be TODAY
    
    FUTURE ENHANCEMENT:
    - Could filter by date range (\"Show last month\", \"Show last 3 months\")
    - Could compute trend (Is risk improving or worsening?)
    - Could correlate with activity (Which activities cause higher risk?)
    """
    # Get user's risk assessments
    assessments = db.query(RiskAssessment)\
        .filter(RiskAssessment.user_id == current_user.user_id)\
        .order_by(desc(RiskAssessment.assessment_date))\
        .limit(limit)\
        .all()

    if not assessments:
        return {
            "user_id": current_user.user_id,
            "user_name": current_user.full_name,
            "risk_assessments": [],
            "message": "No risk assessments found yet"
        }

    def get_recommendation(risk_level: str, risk_score: float) -> str:
        """
        Generate user-facing recommendation based on risk level.
        
        DESIGN PHILOSOPHY:
        - Recommendations are ACTION-ORIENTED (what should user do?)
        - Escalate with risk level: Normal → Monitor → Concern → Emergency
        - Consistent across all APIs (same recommendation logic everywhere)
        
        WHY NOT STORE IN DATABASE:
        - Recommendations may change as medical guidelines evolve
        - Computing from risk_level is reliable (inverse operation)
        - Avoids storing redundant string data (risk_level → recommendation)
        
        RISK LEVEL THRESHOLDS:
        - \"critical\": Immediate danger, seek emergency care
        - \"high\": Concerning, contact healthcare provider
        - \"moderate\": Caution, monitor condition
        - \"low\": Normal, safe to continue
        
        These thresholds match /vitals/submit alert checking logic.
        """
        if risk_level == "critical":
            return "Seek immediate medical attention"
        elif risk_level == "high":
            return "Contact your healthcare provider today"
        elif risk_level == "moderate":
            return "Monitor your vitals closely and take it easy"
        else:
            return "Continue normal activities with regular monitoring"
    
    return {
        "user_id": current_user.user_id,
        "user_name": current_user.full_name,
        "assessment_count": len(assessments),
        "risk_assessments": [
            {
                "assessment_id": a.assessment_id,
                "risk_score": a.risk_score,
                "risk_level": a.risk_level,
                "assessment_type": a.assessment_type,
                "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None,
                "confidence": a.confidence,
                "primary_concern": a.primary_concern,
                "recommendation": get_recommendation(a.risk_level, a.risk_score),
                "generated_by": a.generated_by
            }
            for a in assessments
        ]
    }


# =============================================================================
# New Risk Assessment & Recommendation Endpoints
# =============================================================================

# =============================================
# COMPUTE_MY_RISK_ASSESSMENT - Patient self-assessment
# Used by: Mobile app "Check My Risk" button
# Returns: RiskAssessmentComputeResponse with drivers
# Roles: ALL authenticated users (own data)
# =============================================
@router.post("/risk-assessments/compute", response_model=RiskAssessmentComputeResponse)
async def compute_my_risk_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vitals = _get_recent_vitals_window(db, current_user.user_id, window_minutes=30)
    if not vitals:
        raise HTTPException(status_code=404, detail="No recent vitals found")

    from app.api.medical_history import build_medical_profile
    med_profile = build_medical_profile(current_user.user_id, db)
    result = _compute_risk_assessment(
        user_id=current_user.user_id,
        vitals=vitals,
        medical_conditions=med_profile.conditions,
        medications=med_profile.medications,
        db=db,
    )
    return RiskAssessmentComputeResponse(**result)


# =============================================
# COMPUTE_PATIENT_RISK_ASSESSMENT - Clinician computes for patient
# Used by: Clinician dashboard patient detail view
# Returns: RiskAssessmentComputeResponse with drivers
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.post("/patients/{user_id}/risk-assessments/compute", response_model=RiskAssessmentComputeResponse)
async def compute_patient_risk_assessment(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="User not found")

    check_clinician_phi_access(current_user, patient)

    vitals = _get_recent_vitals_window(db, user_id, window_minutes=30)
    if not vitals:
        raise HTTPException(status_code=404, detail="No recent vitals found")

    from app.api.medical_history import build_medical_profile
    med_profile = build_medical_profile(user_id, db)
    result = _compute_risk_assessment(
        user_id=user_id,
        vitals=vitals,
        medical_conditions=med_profile.conditions,
        medications=med_profile.medications,
        db=db,
    )
    return RiskAssessmentComputeResponse(**result)


# =============================================
# GET_MY_LATEST_RISK_ASSESSMENT - Patient's most recent
# Used by: Mobile app home screen risk card
# Returns: Latest risk assessment with drivers
# Roles: ALL authenticated users (own data)
# =============================================
@router.get("/risk-assessments/latest")
async def get_my_latest_risk_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ra = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == current_user.user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    if not ra:
        raise HTTPException(status_code=404, detail="No risk assessments found")

    drivers = json.loads(ra.risk_factors_json) if ra.risk_factors_json else []
    return {
        "assessment_id": ra.assessment_id,
        "user_id": ra.user_id,
        "risk_score": ra.risk_score,
        "risk_level": ra.risk_level,
        "confidence": ra.confidence,
        "assessment_date": ra.assessment_date.isoformat() if ra.assessment_date else None,
        "drivers": drivers
    }


# =============================================
# GET_PATIENT_LATEST_RISK_ASSESSMENT - Clinician view
# Used by: Clinician dashboard patient card
# Returns: Patient's latest risk assessment
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/patients/{user_id}/risk-assessments/latest")
async def get_patient_latest_risk_assessment(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="User not found")
    check_clinician_phi_access(current_user, patient)

    ra = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    if not ra:
        raise HTTPException(status_code=404, detail="No risk assessments found")

    drivers = json.loads(ra.risk_factors_json) if ra.risk_factors_json else []
    return {
        "assessment_id": ra.assessment_id,
        "user_id": ra.user_id,
        "risk_score": ra.risk_score,
        "risk_level": ra.risk_level,
        "confidence": ra.confidence,
        "assessment_date": ra.assessment_date.isoformat() if ra.assessment_date else None,
        "drivers": drivers
    }


# =============================================
# GET_MY_LATEST_RECOMMENDATION - Patient's exercise guidance
# Used by: Mobile app home screen recommendation card
# Returns: Latest exercise recommendation
# Roles: ALL authenticated users (own data)
# =============================================
@router.get("/recommendations/latest", response_model=RecommendationResponse)
async def get_my_latest_recommendation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.user_id == current_user.user_id,
            ExerciseRecommendation.is_completed == False,
        )
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    if not rec:  # pragma: no cover
        raise HTTPException(status_code=404, detail="No recommendations found")

    return RecommendationResponse(
        recommendation_id=rec.recommendation_id,
        user_id=rec.user_id,
        title=rec.title,
        suggested_activity=rec.suggested_activity,
        intensity_level=rec.intensity_level,
        duration_minutes=rec.duration_minutes,
        target_heart_rate_min=rec.target_heart_rate_min,
        target_heart_rate_max=rec.target_heart_rate_max,
        description=rec.description,
        warnings=rec.warnings,
        created_at=rec.created_at.isoformat() if rec.created_at else None
    )


# =============================================
# GET_PATIENT_LATEST_RECOMMENDATION - Clinician view
# Used by: Clinician dashboard patient detail
# Returns: Patient's latest exercise recommendation
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/patients/{user_id}/recommendations/latest", response_model=RecommendationResponse)
async def get_patient_latest_recommendation(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="User not found")
    check_clinician_phi_access(current_user, patient)

    rec = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.user_id == user_id,
            ExerciseRecommendation.is_completed == False,
        )
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    if not rec:  # pragma: no cover
        raise HTTPException(status_code=404, detail="No recommendations found")

    return RecommendationResponse(
        recommendation_id=rec.recommendation_id,
        user_id=rec.user_id,
        title=rec.title,
        suggested_activity=rec.suggested_activity,
        intensity_level=rec.intensity_level,
        duration_minutes=rec.duration_minutes,
        target_heart_rate_min=rec.target_heart_rate_min,
        target_heart_rate_max=rec.target_heart_rate_max,
        description=rec.description,
        warnings=rec.warnings,
        created_at=rec.created_at.isoformat() if rec.created_at else None
    )


# =============================================
# COMPLETE_RECOMMENDATION - Mark exercise as done
# Used by: Mobile app workout completion
# =============================================
@router.post("/recommendations/{recommendation_id}/complete")
async def complete_recommendation(
    recommendation_id: int,
    body: RecommendationCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.recommendation_id == recommendation_id,
            ExerciseRecommendation.user_id == current_user.user_id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    target = rec.duration_minutes or 0
    actual = body.actual_minutes

    if actual is not None and target > 0 and actual < target:
        remaining = max(target - actual, 1)
        rec.duration_minutes = remaining
        rec.description = f"Remaining: {remaining} min of original {target} min"
        rec.is_completed = False
        rec.status = "pending"
    else:
        rec.is_completed = True
        rec.status = "completed"

    db.commit()
    db.refresh(rec)

    return {
        "recommendation_id": rec.recommendation_id,
        "user_id": rec.user_id,
        "title": rec.title,
        "suggested_activity": rec.suggested_activity,
        "intensity_level": rec.intensity_level,
        "duration_minutes": rec.duration_minutes,
        "target_heart_rate_min": rec.target_heart_rate_min,
        "target_heart_rate_max": rec.target_heart_rate_max,
        "description": rec.description,
        "warnings": rec.warnings,
        "status": rec.status,
        "is_completed": rec.is_completed,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }


# =============================================
# DAILY RECOVERY SCORE - Composite score endpoint
# Used by: Mobile app recovery screen
# =============================================
@router.get("/recovery/daily-score")
async def get_daily_recovery_score(
    date_str: Optional[str] = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_date = _resolve_date(date_str)
    return _calculate_daily_recovery_score(db, current_user, target_date)


# =============================================
# WEEKLY RECOVERY SCORES - 7 day trend
# Used by: Mobile app history chart
# =============================================
@router.get("/recovery/weekly-scores")
async def get_weekly_recovery_scores(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(timezone.utc).date()
    scores: list[dict[str, Any]] = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        daily = _calculate_daily_recovery_score(db, current_user, day)
        scores.append({
            "date": daily["date"],
            "score": daily["score"],
            "workout_score": daily["workout_score"],
            "nutrition_score": daily["nutrition_score"],
            "sleep_score": daily["sleep_score"],
        })
    return {"scores": scores}


# =============================================
# SLEEP LOGGING ENDPOINTS
# =============================================
@router.post("/sleep")
async def log_sleep(
    request: SleepLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bedtime = request.bedtime
    wake_time = request.wake_time
    if wake_time < bedtime:
        wake_time = wake_time + timedelta(days=1)

    duration_hours = round((wake_time - bedtime).total_seconds() / 3600, 2)
    duration_ratio = min(duration_hours / 8.0, 1.0) if duration_hours > 0 else 0.0
    quality_ratio = request.quality_rating / 5.0
    sleep_score = int(round((duration_ratio * 60) + (quality_ratio * 40)))

    sleep_date = wake_time.date()

    entry = SleepEntry(
        user_id=current_user.user_id,
        date=sleep_date,
        bedtime=bedtime,
        wake_time=wake_time,
        duration_hours=duration_hours,
        quality_rating=request.quality_rating,
        sleep_score=sleep_score,
        notes=request.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "sleep_id": entry.sleep_id,
        "user_id": entry.user_id,
        "date": entry.date.isoformat(),
        "bedtime": entry.bedtime.isoformat() if entry.bedtime else None,
        "wake_time": entry.wake_time.isoformat() if entry.wake_time else None,
        "duration_hours": entry.duration_hours,
        "quality_rating": entry.quality_rating,
        "sleep_score": entry.sleep_score,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("/sleep/latest")
async def get_latest_sleep(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entry = (
        db.query(SleepEntry)
        .filter(SleepEntry.user_id == current_user.user_id)
        .order_by(desc(SleepEntry.date), desc(SleepEntry.created_at))
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="No sleep entries found")

    return {
        "sleep_id": entry.sleep_id,
        "user_id": entry.user_id,
        "date": entry.date.isoformat(),
        "bedtime": entry.bedtime.isoformat() if entry.bedtime else None,
        "wake_time": entry.wake_time.isoformat() if entry.wake_time else None,
        "duration_hours": entry.duration_hours,
        "quality_rating": entry.quality_rating,
        "sleep_score": entry.sleep_score,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("/sleep")
async def get_sleep_history(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    days = max(1, min(days, 30))
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    entries = (
        db.query(SleepEntry)
        .filter(
            SleepEntry.user_id == current_user.user_id,
            SleepEntry.date >= start_date,
        )
        .order_by(desc(SleepEntry.date), desc(SleepEntry.created_at))
        .all()
    )

    return {
        "entries": [
            {
                "sleep_id": entry.sleep_id,
                "date": entry.date.isoformat(),
                "bedtime": entry.bedtime.isoformat() if entry.bedtime else None,
                "wake_time": entry.wake_time.isoformat() if entry.wake_time else None,
                "duration_hours": entry.duration_hours,
                "quality_rating": entry.quality_rating,
                "sleep_score": entry.sleep_score,
                "notes": entry.notes,
            }
            for entry in entries
        ],
        "days": days,
    }