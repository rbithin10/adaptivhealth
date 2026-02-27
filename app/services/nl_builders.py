"""
Natural Language Builder Functions.

Service layer for generating patient-friendly natural language summaries
from structured health data.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# RISK SUMMARY BUILDERS
#   - build_risk_summary_text()........ Line 35
#
# WORKOUT BUILDERS
#   - build_todays_workout_text()...... Line 90
#
# ALERT BUILDERS
#   - build_alert_explanation_text()... Line 145
#
# PROGRESS BUILDERS
#   - build_progress_summary_text().... Line 215
#   - _compute_trend()................. Line 280
#
# HELPER FUNCTIONS
#   - _get_risk_adjective()............ Line 320
#   - _get_activity_friendly_name().... Line 330
# =============================================================================
"""

from typing import Literal
from datetime import datetime, date
from uuid import UUID
from app.schemas.nl import Period, Trend


# =============================================================================
# RISK SUMMARY BUILDERS
# =============================================================================

def build_risk_summary_text(
    risk_level: Literal["LOW", "MODERATE", "HIGH"],
    risk_score: float,
    time_window_hours: int,
    avg_heart_rate: int,
    max_heart_rate: int,
    avg_spo2: int,
    alert_count: int,
    safety_status: Literal["SAFE", "CAUTION", "UNSAFE"],
) -> str:
    """
    Build an encouraging, patient-safe natural-language risk summary.
    
    Returns 2-4 sentences mentioning:
    - Risk level and time window
    - Key vitals (heart rate, alerts)
    - Simple safety statement
    """
    # Opening sentence based on risk level
    if risk_level == "LOW":
        opener = f"Over the past {time_window_hours} hours, your health readings look stable and within safe ranges."
    elif risk_level == "MODERATE":
        opener = f"Over the past {time_window_hours} hours, your readings show some variation that we're monitoring carefully."
    else:  # HIGH
        opener = f"Over the past {time_window_hours} hours, we've noticed some concerning patterns in your readings."
    
    # Vitals mention
    vitals = f"Your average heart rate was {avg_heart_rate} BPM (peak: {max_heart_rate} BPM), and oxygen levels averaged {avg_spo2}%."
    
    # Alert context
    if alert_count == 0:
        alert_text = "No alerts were triggered, which is great."
    elif alert_count == 1:
        alert_text = "One alert was triggered—please review it when you can."
    else:
        alert_text = f"{alert_count} alerts were triggered—please check them soon."
    
    # Safety guidance
    if safety_status == "SAFE":
        safety = "You're okay for light to moderate activities, just listen to your body."
    elif safety_status == "CAUTION":
        safety = "Take it easy—stick to light activities and rest if you feel unwell."
    else:  # UNSAFE
        safety = "Please rest and avoid strenuous activities. Contact your care team if symptoms persist."
    
    return f"{opener} {vitals} {alert_text} {safety}"


# =============================================================================
# WORKOUT BUILDERS
# =============================================================================

def build_todays_workout_text(
    activity_type: Literal["WALKING", "CYCLING", "OTHER"],
    intensity_level: Literal["LIGHT", "MODERATE", "VIGOROUS"],
    duration_minutes: int,
    target_hr_min: int,
    target_hr_max: int,
    risk_level: Literal["LOW", "MODERATE", "HIGH"],
) -> str:
    """
    Build an NL summary for today's recommended workout.
    
    Includes:
    - What to do and for how long
    - Target heart-rate range
    - 1-2 safety cues
    """
    # Activity description
    activity_name = _get_activity_friendly_name(activity_type)
    intensity_adj = intensity_level.lower()
    
    if intensity_level == "LIGHT":
        pace = "at a comfortable, easy pace"
    elif intensity_level == "MODERATE":
        pace = "at a steady, moderate pace"
    else:  # VIGOROUS
        pace = "at a brisk, challenging pace"
    
    intro = f"Today's recommendation: Try a {intensity_adj} {activity_name} for {duration_minutes} minutes {pace}."
    
    # Heart rate guidance
    hr_guidance = f"Aim to keep your heart rate between {target_hr_min}-{target_hr_max} BPM during the activity."
    
    # Safety cues based on risk level
    if risk_level == "LOW":
        safety = "If you feel any discomfort, chest pain, or severe breathlessness, stop and rest. Otherwise, enjoy your workout!"
    elif risk_level == "MODERATE":
        safety = "Monitor yourself closely—if you feel chest pain, dizziness, or unusual breathlessness, stop immediately and rest. Take breaks as needed."
    else:  # HIGH
        safety = "Important: Stop immediately if you feel chest pain, dizziness, palpitations, or severe breathlessness. Consider a shorter session and inform your care team if symptoms occur."
    
    return f"{intro} {hr_guidance} {safety}"


# =============================================================================
# ALERT BUILDERS
# =============================================================================

def build_alert_explanation_text(
    alert_type: Literal["HIGH_HEART_RATE", "LOW_OXYGEN", "OTHER"],
    severity_level: Literal["LOW", "MEDIUM", "HIGH"],
    alert_time: datetime,
    during_activity: bool,
    activity_type: str | None,
    heart_rate: int | None,
    spo2: int | None,
    recommended_action: Literal[
        "CONTINUE",
        "SLOW_DOWN",
        "STOP_AND_REST",
        "CONTACT_DOCTOR",
        "EMERGENCY"
    ],
) -> str:
    """
    Explain an alert in calm, clear language.
    
    Covers:
    - What triggered the alert
    - How serious it is
    - Clear next step
    """
    # Format time
    time_str = alert_time.strftime("%I:%M %p")
    
    # What happened
    if alert_type == "HIGH_HEART_RATE" and heart_rate:
        if during_activity and activity_type:
            trigger = f"At {time_str}, your heart rate reached {heart_rate} BPM during {activity_type.lower()}."
        else:
            trigger = f"At {time_str}, your heart rate reached {heart_rate} BPM while at rest."
    elif alert_type == "LOW_OXYGEN" and spo2:
        trigger = f"At {time_str}, your oxygen level dropped to {spo2}%."
    else:
        trigger = f"At {time_str}, we detected an unusual reading."
    
    # Severity assessment
    if severity_level == "LOW":
        severity_text = "This is a minor concern—your body was working a bit harder than usual."
    elif severity_level == "MEDIUM":
        severity_text = "This requires attention—it's outside your typical safe range."
    else:  # HIGH
        severity_text = "This is a significant concern that needs immediate attention."
    
    # Recommended action
    if recommended_action == "CONTINUE":
        action = "You can continue your current activity, but stay aware of how you feel."
    elif recommended_action == "SLOW_DOWN":
        action = "Slow down the pace—ease up on intensity and see if your readings stabilize."
    elif recommended_action == "STOP_AND_REST":
        action = "Stop what you're doing and rest for at least 10-15 minutes. Monitor how you feel."
    elif recommended_action == "CONTACT_DOCTOR":
        action = "Stop and rest. Contact your care team as soon as possible to discuss these readings."
    else:  # EMERGENCY
        action = "⚠️ Stop immediately and seek emergency medical attention. Call 911 or your local emergency number if symptoms persist."
    
    return f"{trigger} {severity_text} {action}"


# =============================================================================
# PROGRESS BUILDERS
# =============================================================================

def build_progress_summary_text(
    current: Period,
    previous: Period,
    trend: Trend,
) -> str:
    """
    Build a motivational progress summary.
    
    Includes:
    - Current period stats
    - Comparison to previous period
    - Positive reinforcement
    - Concrete suggestion
    """
    # Current period summary
    days = (current.end - current.start).days
    summary = f"Over the past {days} days, you completed {current.workout_count} workout{'s' if current.workout_count != 1 else ''} totaling {current.total_active_minutes} active minutes."
    
    # Comparison to previous period
    workout_diff = current.workout_count - previous.workout_count
    alert_diff = current.alert_count - previous.alert_count
    
    comparisons = []
    
    # Workout comparison
    if workout_diff > 0:
        comparisons.append(f"{workout_diff} more workout{'s' if abs(workout_diff) != 1 else ''} than the previous period")
    elif workout_diff < 0:
        comparisons.append(f"{abs(workout_diff)} fewer workout{'s' if abs(workout_diff) != 1 else ''} than before")
    
    # Alert comparison
    if alert_diff < 0:
        comparisons.append(f"{abs(alert_diff)} fewer alert{'s' if abs(alert_diff) != 1 else ''}")
    elif alert_diff > 0:
        comparisons.append(f"{alert_diff} more alert{'s' if abs(alert_diff) != 1 else ''}")
    
    if comparisons:
        comparison_text = "That's " + " and ".join(comparisons) + "."
    else:
        comparison_text = "Your activity level is consistent with the previous period."
    
    # Tone and reinforcement based on overall trend
    if trend.overall == "IMPROVING":
        reinforcement = "Excellent progress! Your consistency is paying off."
        suggestion = "Keep up the great work—try to maintain at least this many sessions going forward."
    elif trend.overall == "STABLE":
        reinforcement = "You're maintaining a steady routine, which is important for long-term health."
        suggestion = "Consider adding one more short session per week to continue building your endurance."
    else:  # WORSENING
        reinforcement = "It's okay if you've had a challenging period—what matters is getting back on track."
        suggestion = "Let's aim for 2-3 gentle sessions this coming week. Small steps count, and your care team is here to support you."
    
    return f"{summary} {comparison_text} {reinforcement} {suggestion}"


def compute_trend(current: Period, previous: Period) -> Trend:
    """
    Compute trend indicators by comparing current and previous periods.
    
    Logic:
    - workout_frequency: more/same/less workouts → IMPROVING/STABLE/WORSENING
    - alerts: fewer/same/more → IMPROVING/STABLE/WORSENING
    - risk: compare numeric risk levels (LOW=1, MODERATE=2, HIGH=3)
    - overall: if 2+ improving → IMPROVING; if 2+ worsening → WORSENING; else STABLE
    """
    # Workout frequency trend
    workout_diff = current.workout_count - previous.workout_count
    if workout_diff > 0:
        workout_trend = "IMPROVING"
    elif workout_diff < 0:
        workout_trend = "WORSENING"
    else:
        workout_trend = "STABLE"
    
    # Alert trend (fewer is better)
    alert_diff = current.alert_count - previous.alert_count
    if alert_diff < 0:
        alert_trend = "IMPROVING"
    elif alert_diff > 0:
        alert_trend = "WORSENING"
    else:
        alert_trend = "STABLE"
    
    # Risk trend (lower is better)
    risk_map = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
    current_risk_value = risk_map[current.avg_risk_level]
    previous_risk_value = risk_map[previous.avg_risk_level]
    
    if current_risk_value < previous_risk_value:
        risk_trend = "IMPROVING"
    elif current_risk_value > previous_risk_value:
        risk_trend = "WORSENING"
    else:
        risk_trend = "STABLE"
    
    # Overall trend (majority vote)
    trends = [workout_trend, alert_trend, risk_trend]
    improving_count = trends.count("IMPROVING")
    worsening_count = trends.count("WORSENING")
    
    if improving_count >= 2:
        overall_trend = "IMPROVING"
    elif worsening_count >= 2:
        overall_trend = "WORSENING"
    else:
        overall_trend = "STABLE"
    
    return Trend(
        workout_frequency=workout_trend,
        alerts=alert_trend,
        risk=risk_trend,
        overall=overall_trend,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_risk_adjective(risk_level: str) -> str:
    """Get a patient-friendly adjective for risk level."""
    return {"LOW": "low", "MODERATE": "moderate", "HIGH": "elevated"}.get(
        risk_level, "moderate"
    )


def _get_activity_friendly_name(activity_type: str) -> str:
    """Get a friendly name for activity type."""
    return {
        "WALKING": "walk",
        "CYCLING": "bike ride",
        "OTHER": "exercise session",
    }.get(activity_type, "activity")
