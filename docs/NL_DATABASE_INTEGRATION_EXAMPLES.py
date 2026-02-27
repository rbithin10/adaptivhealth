"""
Example: Integrating NL endpoints with real database queries.

This file shows how to replace dummy data in nl_endpoints.py with
actual database queries using SQLAlchemy ORM.

NOT YET IMPLEMENTED - This is a reference guide for future integration.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.risk_assessment import RiskAssessment
from app.models.vital_signs import VitalSignRecord
from app.models.alert import Alert
from app.models.recommendation import ExerciseRecommendation
from app.models.activity import ActivitySession


# =============================================================================
# Example 1: Risk Summary with Real Data
# =============================================================================

def get_risk_summary_data(user_id: int, time_window_hours: int, db: Session) -> dict:
    """
    Fetch real data for risk summary endpoint.
    
    Replace the dummy data section in nl_endpoints.py with this logic.
    """
    # Get latest risk assessment
    risk_assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    
    if not risk_assessment:
        # Fallback to safe defaults if no assessment exists
        risk_level = "LOW"
        risk_score = 0.0
    else:
        risk_level = risk_assessment.risk_level.upper()
        risk_score = risk_assessment.risk_score
    
    # Get recent vitals in time window
    since = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
    vitals = (
        db.query(VitalSignRecord)
        .filter(
            VitalSignRecord.user_id == user_id,
            VitalSignRecord.timestamp >= since,
            VitalSignRecord.is_valid == True,
        )
        .all()
    )
    
    if vitals:
        heart_rates = [v.heart_rate for v in vitals if v.heart_rate]
        spo2_values = [v.spo2 for v in vitals if v.spo2]
        
        avg_heart_rate = int(sum(heart_rates) / len(heart_rates)) if heart_rates else 70
        max_heart_rate = max(heart_rates) if heart_rates else 90
        avg_spo2 = int(sum(spo2_values) / len(spo2_values)) if spo2_values else 98
    else:
        avg_heart_rate = 70
        max_heart_rate = 90
        avg_spo2 = 98
    
    # Count alerts in time window
    alert_count = (
        db.query(Alert)
        .filter(
            Alert.user_id == user_id,
            Alert.alert_time >= since,
        )
        .count()
    )
    
    # Determine safety status based on risk and alerts
    if risk_level == "HIGH" or alert_count >= 3:
        safety_status = "UNSAFE"
    elif risk_level == "MODERATE" or alert_count >= 1:
        safety_status = "CAUTION"
    else:
        safety_status = "SAFE"
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "avg_heart_rate": avg_heart_rate,
        "max_heart_rate": max_heart_rate,
        "avg_spo2": avg_spo2,
        "alert_count": alert_count,
        "safety_status": safety_status,
    }


# =============================================================================
# Example 2: Today's Workout with Real Data
# =============================================================================

def get_todays_workout_data(user_id: int, target_date: date, db: Session) -> dict:
    """
    Fetch real data for today's workout endpoint.
    
    Replace the dummy data section in nl_endpoints.py with this logic.
    """
    # Get active exercise recommendation for the date
    recommendation = (
        db.query(ExerciseRecommendation)
        .filter(
            ExerciseRecommendation.user_id == user_id,
            ExerciseRecommendation.valid_from <= target_date,
            ExerciseRecommendation.valid_to >= target_date,
        )
        .first()
    )
    
    if recommendation:
        activity_type = recommendation.activity_type.upper()
        intensity_level = recommendation.intensity_level.upper()
        duration_minutes = recommendation.duration_minutes
        target_hr_min = recommendation.target_hr_min
        target_hr_max = recommendation.target_hr_max
    else:
        # Fallback to safe default workout
        activity_type = "WALKING"
        intensity_level = "LIGHT"
        duration_minutes = 15
        target_hr_min = 80
        target_hr_max = 100
    
    # Get latest risk level
    risk_assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    
    risk_level = risk_assessment.risk_level.upper() if risk_assessment else "LOW"
    
    return {
        "activity_type": activity_type,
        "intensity_level": intensity_level,
        "duration_minutes": duration_minutes,
        "target_hr_min": target_hr_min,
        "target_hr_max": target_hr_max,
        "risk_level": risk_level,
    }


# =============================================================================
# Example 3: Alert Explanation with Real Data
# =============================================================================

def get_alert_explanation_data(user_id: int, alert_id: UUID | None, db: Session) -> dict:
    """
    Fetch real data for alert explanation endpoint.
    
    Replace the dummy data section in nl_endpoints.py with this logic.
    """
    # Get specific alert or latest
    if alert_id:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    else:
        alert = (
            db.query(Alert)
            .filter(Alert.user_id == user_id)
            .order_by(desc(Alert.alert_time))
            .first()
        )
    
    if not alert:
        raise HTTPException(status_code=404, detail="No alerts found for this user")
    
    # Map alert data
    alert_type = alert.alert_type.upper()
    severity_level = alert.severity_level.upper()
    alert_time = alert.alert_time
    
    # Get associated vital if exists
    vital = None
    if alert.vital_sign_id:
        vital = db.query(VitalSignRecord).filter(
            VitalSignRecord.vital_id == alert.vital_sign_id
        ).first()
    
    # Check if during activity
    session = None
    if vital:
        session = (
            db.query(ActivitySession)
            .filter(
                ActivitySession.user_id == user_id,
                ActivitySession.start_time <= vital.timestamp,
                ActivitySession.end_time >= vital.timestamp,
            )
            .first()
        )
    
    during_activity = session is not None
    activity_type = session.activity_type if session else None
    heart_rate = vital.heart_rate if vital else None
    spo2 = vital.spo2 if vital else None
    
    # Determine recommended action based on severity and context
    if severity_level == "EMERGENCY":
        recommended_action = "EMERGENCY"
    elif severity_level == "HIGH":
        if during_activity:
            recommended_action = "STOP_AND_REST"
        else:
            recommended_action = "CONTACT_DOCTOR"
    elif severity_level == "MEDIUM":
        if during_activity:
            recommended_action = "SLOW_DOWN"
        else:
            recommended_action = "STOP_AND_REST"
    else:  # LOW
        recommended_action = "CONTINUE"
    
    return {
        "alert_id": alert.alert_id,
        "alert_type": alert_type,
        "severity_level": severity_level,
        "alert_time": alert_time,
        "during_activity": during_activity,
        "activity_type": activity_type,
        "heart_rate": heart_rate,
        "spo2": spo2,
        "recommended_action": recommended_action,
    }


# =============================================================================
# Example 4: Progress Summary with Real Data
# =============================================================================

def get_progress_summary_data(user_id: int, days: int, db: Session) -> dict:
    """
    Fetch real data for progress summary endpoint.
    
    Replace the dummy data section in nl_endpoints.py with this logic.
    """
    from app.schemas.nl import Period
    
    now = datetime.now(timezone.utc)
    
    # Define current and previous periods
    current_start = now - timedelta(days=days)
    current_end = now
    previous_start = current_start - timedelta(days=days)
    previous_end = current_start
    
    # Helper function to get period stats
    def get_period_stats(start: datetime, end: datetime) -> Period:
        # Get activity sessions
        sessions = (
            db.query(ActivitySession)
            .filter(
                ActivitySession.user_id == user_id,
                ActivitySession.start_time >= start,
                ActivitySession.end_time <= end,
            )
            .all()
        )
        
        workout_count = len(sessions)
        total_active_minutes = sum(
            int((s.end_time - s.start_time).total_seconds() / 60)
            for s in sessions
        )
        time_in_safe_zone = sum(s.time_in_safe_zone_minutes or 0 for s in sessions)
        time_above_safe_zone = sum(s.time_above_safe_zone_minutes or 0 for s in sessions)
        
        # Get average risk level in period
        risk_assessments = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.user_id == user_id,
                RiskAssessment.assessment_date >= start,
                RiskAssessment.assessment_date <= end,
            )
            .all()
        )
        
        if risk_assessments:
            risk_map = {"low": 1, "moderate": 2, "high": 3}
            avg_risk_value = sum(
                risk_map.get(r.risk_level.lower(), 2) for r in risk_assessments
            ) / len(risk_assessments)
            
            if avg_risk_value <= 1.5:
                avg_risk_level = "LOW"
            elif avg_risk_value <= 2.5:
                avg_risk_level = "MODERATE"
            else:
                avg_risk_level = "HIGH"
        else:
            avg_risk_level = "LOW"
        
        # Count alerts
        alert_count = (
            db.query(Alert)
            .filter(
                Alert.user_id == user_id,
                Alert.alert_time >= start,
                Alert.alert_time <= end,
            )
            .count()
        )
        
        return Period(
            start=start,
            end=end,
            workout_count=workout_count,
            total_active_minutes=total_active_minutes,
            avg_risk_level=avg_risk_level,
            time_in_safe_zone_minutes=time_in_safe_zone,
            time_above_safe_zone_minutes=time_above_safe_zone,
            alert_count=alert_count,
        )
    
    current_period = get_period_stats(current_start, current_end)
    previous_period = get_period_stats(previous_start, previous_end)
    
    return {
        "current_period": current_period,
        "previous_period": previous_period,
    }


# =============================================================================
# Integration Example: Updated Route Handler
# =============================================================================

"""
Example of how to update nl_endpoints.py route with real data:

@router.get("/risk-summary", response_model=RiskSummaryResponse)
async def get_risk_summary(
    user_id: UUID = Query(..., description="User ID"),
    time_window_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),  # ADD THIS
):
    logger.info(f"Generating risk summary for user {user_id}")
    
    # REPLACE dummy data with:
    data = get_risk_summary_data(user_id, time_window_hours, db)
    
    # Build NL summary (unchanged)
    nl_summary = build_risk_summary_text(
        risk_level=data["risk_level"],
        risk_score=data["risk_score"],
        time_window_hours=time_window_hours,
        avg_heart_rate=data["avg_heart_rate"],
        max_heart_rate=data["max_heart_rate"],
        avg_spo2=data["avg_spo2"],
        alert_count=data["alert_count"],
        safety_status=data["safety_status"],
    )
    
    # Return response (unchanged structure)
    return RiskSummaryResponse(...)
"""
