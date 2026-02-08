"""
Risk prediction routes.

These endpoints use the AI model to estimate heart risk.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import time
from datetime import datetime, timedelta, timezone
import json

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.risk_assessment import RiskAssessment
from app.models.vital_signs import VitalSignRecord
from app.models.recommendation import ExerciseRecommendation
from app.services.ml_prediction import get_ml_service, MLPredictionService
from app.api.auth import get_current_user, get_current_doctor_user

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
    baseline_hr: int = Field(..., ge=40, le=100, description="Resting heart rate")
    max_safe_hr: int = Field(..., ge=100, le=220, description="Maximum safe heart rate")
    avg_heart_rate: int = Field(..., ge=40, le=220, description="Average HR during session")
    peak_heart_rate: int = Field(..., ge=40, le=250, description="Peak HR during session")
    min_heart_rate: int = Field(..., ge=30, le=200, description="Minimum HR during session")
    avg_spo2: int = Field(..., ge=70, le=100, description="Average SpO2 during session")
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


# =============================================================================
# Helper Functions
# =============================================================================

def _get_recent_vitals_window(
    db: Session, user_id: int, window_minutes: int = 30
) -> list[VitalSignRecord]:
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    return (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True
        )
        .order_by(VitalSignRecord.timestamp.asc())
        .all()
    )


def _aggregate_session_features_from_vitals(vitals: list[VitalSignRecord]) -> dict[str, Any]:
    """
    Convert raw vitals into the session-style fields the ML model expects.
    If only 1 reading exists, we still produce a valid feature set.
    """
    if not vitals:
        raise ValueError("No vitals to aggregate")

    hrs = [v.heart_rate for v in vitals]
    spo2s = [v.spo2 for v in vitals if v.spo2 is not None]

    start = vitals[0].timestamp
    end = vitals[-1].timestamp
    duration_minutes = max(1, int((end - start).total_seconds() / 60)) if start and end else 10

    avg_hr = int(sum(hrs) / len(hrs))
    peak_hr = int(max(hrs))
    min_hr = int(min(hrs))
    avg_spo2 = int(sum(spo2s) / len(spo2s)) if spo2s else 97

    activity_type = vitals[-1].activity_type or "walking"

    # Recovery time is not directly observable from a vitals window.
    # For MVP, use a safe default or infer from phase if you store it.
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


def _build_drivers(user: User, features: dict[str, Any]) -> list[str]:
    """
    Human-readable explanations so the AI feels real in UI.
    Keep it short and decisive.
    """
    drivers = []

    baseline = user.baseline_hr or 72
    max_safe = user.max_safe_hr or (220 - (user.age or 55))

    peak = features["peak_heart_rate"]
    avg = features["avg_heart_rate"]
    spo2 = features["avg_spo2"]

    if peak > max_safe:
        drivers.append(f"Peak heart rate exceeded safe limit ({peak} > {max_safe}).")
    if avg - baseline >= 25:
        drivers.append(f"Average heart rate elevated vs baseline ({avg} vs {baseline}).")
    if spo2 <= 92:
        drivers.append(f"Average SpO₂ is low ({spo2}%).")
    if features["duration_minutes"] >= 45 and peak > int(0.8 * max_safe):
        drivers.append("Sustained high intensity for long duration.")

    if not drivers:
        drivers.append("Vitals are within expected safe limits.")

    return drivers


def _generate_recommendation_payload(
    user: User, risk_level: str, risk_score: float, drivers: list[str]
) -> dict[str, Any]:
    baseline = user.baseline_hr or 72
    max_safe = user.max_safe_hr or (220 - (user.age or 55))

    # Target zone logic (simple but credible)
    if risk_level in ("critical", "high"):
        return {
            "title": "Recovery & Monitoring",
            "suggested_activity": "Rest and light breathing",
            "intensity_level": "low",
            "duration_minutes": 10,
            "target_heart_rate_min": None,
            "target_heart_rate_max": min(max_safe - 20, baseline + 20),
            "description": (
                "Stop intense activity. Sit down, hydrate, and do slow breathing. "
                "Eat potassium-rich foods and avoid caffeine."
            ),
            "warnings": "If symptoms persist or worsen, contact a healthcare provider.",
        }

    if risk_level == "moderate":
        return {
            "title": "Low-Intensity Session",
            "suggested_activity": "Walking",
            "intensity_level": "low",
            "duration_minutes": 15,
            "target_heart_rate_min": baseline + 10,
            "target_heart_rate_max": min(int(0.75 * max_safe), baseline + 35),
            "description": (
                "Reduce intensity today. Aim for a steady pace and monitor how you feel. "
                "A heart-healthy meal after: grilled fish with vegetables and whole grains."
            ),
            "warnings": "Pause if dizziness, chest pain, or unusual breathlessness occurs.",
        }

    # low
    return {
        "title": "Continue Safe Training",
        "suggested_activity": "Walking / Light cardio",
        "intensity_level": "moderate",
        "duration_minutes": 20,
        "target_heart_rate_min": baseline + 15,
        "target_heart_rate_max": min(int(0.80 * max_safe), baseline + 45),
        "description": (
            "You are in a safe zone. Keep steady effort and stay hydrated. "
            "Refuel with lean protein, fruits, and plenty of water."
        ),
        "warnings": "Monitor for symptoms. Avoid sudden spikes in intensity.",
    }


# =============================================================================
# Endpoints
# =============================================================================

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
        age=user.age or 55,
        baseline_hr=user.baseline_hr or 72,
        max_safe_hr=user.max_safe_hr or (220 - (user.age or 55)),
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

@router.post("/risk-assessments/compute", response_model=RiskAssessmentComputeResponse)
async def compute_my_risk_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    vitals = _get_recent_vitals_window(db, current_user.user_id, window_minutes=30)
    if not vitals:
        raise HTTPException(status_code=404, detail="No recent vitals found")

    features = _aggregate_session_features_from_vitals(vitals)
    drivers = _build_drivers(current_user, features)

    start_time = time.time()
    result = service.predict_risk(
        age=current_user.age or 55,
        baseline_hr=current_user.baseline_hr or 72,
        max_safe_hr=current_user.max_safe_hr or (220 - (current_user.age or 55)),
        avg_heart_rate=features["avg_heart_rate"],
        peak_heart_rate=features["peak_heart_rate"],
        min_heart_rate=features["min_heart_rate"],
        avg_spo2=features["avg_spo2"],
        duration_minutes=features["duration_minutes"],
        recovery_time_minutes=features["recovery_time_minutes"],
        activity_type=features["activity_type"]
    )
    inference_ms = (time.time() - start_time) * 1000

    # Store risk assessment
    ra = RiskAssessment(
        user_id=current_user.user_id,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        confidence=result.get("confidence"),
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
        generated_by="cloud_ai"
    )
    db.add(ra)
    db.commit()
    db.refresh(ra)

    # Generate & store recommendation (linked)
    rec_payload = _generate_recommendation_payload(current_user, ra.risk_level, ra.risk_score, drivers)
    rec = ExerciseRecommendation(
        user_id=current_user.user_id,
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
        generated_by="cloud_ai"
    )
    db.add(rec)
    db.commit()

    return RiskAssessmentComputeResponse(
        assessment_id=ra.assessment_id,
        user_id=current_user.user_id,
        risk_score=ra.risk_score,
        risk_level=ra.risk_level,
        confidence=ra.confidence,
        inference_time_ms=ra.inference_time_ms,
        drivers=drivers,
        based_on={"window_minutes": 30, "points": features["points"], "activity_type": features["activity_type"]}
    )


@router.post("/patients/{user_id}/risk-assessments/compute", response_model=RiskAssessmentComputeResponse)
async def compute_patient_risk_assessment(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(User.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="User not found")

    service = get_ml_service()
    if not service.is_loaded:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    vitals = _get_recent_vitals_window(db, user_id, window_minutes=30)
    if not vitals:
        raise HTTPException(status_code=404, detail="No recent vitals found")

    features = _aggregate_session_features_from_vitals(vitals)
    drivers = _build_drivers(patient, features)

    start_time = time.time()
    result = service.predict_risk(
        age=patient.age or 55,
        baseline_hr=patient.baseline_hr or 72,
        max_safe_hr=patient.max_safe_hr or (220 - (patient.age or 55)),
        avg_heart_rate=features["avg_heart_rate"],
        peak_heart_rate=features["peak_heart_rate"],
        min_heart_rate=features["min_heart_rate"],
        avg_spo2=features["avg_spo2"],
        duration_minutes=features["duration_minutes"],
        recovery_time_minutes=features["recovery_time_minutes"],
        activity_type=features["activity_type"]
    )
    inference_ms = (time.time() - start_time) * 1000

    ra = RiskAssessment(
        user_id=user_id,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        confidence=result.get("confidence"),
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
        generated_by="cloud_ai"
    )
    db.add(ra)
    db.commit()
    db.refresh(ra)

    rec_payload = _generate_recommendation_payload(patient, ra.risk_level, ra.risk_score, drivers)
    rec = ExerciseRecommendation(
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
        generated_by="cloud_ai"
    )
    db.add(rec)
    db.commit()

    return RiskAssessmentComputeResponse(
        assessment_id=ra.assessment_id,
        user_id=user_id,
        risk_score=ra.risk_score,
        risk_level=ra.risk_level,
        confidence=ra.confidence,
        inference_time_ms=ra.inference_time_ms,
        drivers=drivers,
        based_on={"window_minutes": 30, "points": features["points"], "activity_type": features["activity_type"]}
    )


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


@router.get("/patients/{user_id}/risk-assessments/latest")
async def get_patient_latest_risk_assessment(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
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


@router.get("/recommendations/latest", response_model=RecommendationResponse)
async def get_my_latest_recommendation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = (
        db.query(ExerciseRecommendation)
        .filter(ExerciseRecommendation.user_id == current_user.user_id)
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    if not rec:
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


@router.get("/patients/{user_id}/recommendations/latest", response_model=RecommendationResponse)
async def get_patient_latest_recommendation(
    user_id: int,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    rec = (
        db.query(ExerciseRecommendation)
        .filter(ExerciseRecommendation.user_id == user_id)
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    if not rec:
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