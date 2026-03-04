"""
Hybrid Chat Service — Template + Gemini LLM.

Routes patient messages to fast template responses for known topics,
or to Gemini for complex/open-ended questions. All patient data is
de-identified before being sent to the external LLM.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
# CONSTANTS........................... Line 35
#
# FUNCTIONS
#   - _classify_intent().............. Line 45  (Keyword-based intent routing)
#   - _get_template_response()........ Line 100 (Call existing NL builders)
#   - _build_patient_context()........ Line 150 (De-identified patient summary)
#   - _call_gemini().................. Line 230 (LLM call with safety prompt)
#   - generate_chat_response()........ Line 290 (Main entry point)
#
# BUSINESS CONTEXT:
# - Hybrid approach: templates for known topics, Gemini for the long tail
# - De-identifies all patient data before sending to external LLM
# - Fallback chain: Template → Gemini → Generic response
# - Uses same Gemini 2.0 Flash free tier as document extraction
# =============================================================================
"""

import logging
import re as _re
from typing import Optional, Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, desc

logger = logging.getLogger(__name__)

# Gemini response timeout
GEMINI_TIMEOUT_SECONDS = 15

# Generic fallback when both template and Gemini fail
FALLBACK_RESPONSE = (
    "I can help you understand your heart health status, workout plans, "
    "nutrition guidance, alerts, and your progress. "
    "What would you like to know?"
)

DISCLAIMER_SUFFIX = (
    "\n\n_I'm an AI health coach, not a doctor. "
    "For medical decisions, please consult your care team._"
)


# =============================================================================
# Intent Classification (keyword-based, server-side)
# =============================================================================

def _word_in(word: str, text: str) -> bool:
    """Return True if `word` appears as a whole word (word-boundary) in `text`."""
    return bool(_re.search(r"\b" + _re.escape(word) + r"\b", text))


def _classify_intent(message: str) -> Optional[str]:
    """
    Classify user message into a known intent using keyword matching.

    Uses word-boundary checks for short ambiguous words (e.g. 'health'
    must not match 'healthy') to prevent false-positive intent matches.

    Returns intent string or None if no match.
    """
    lower = message.lower()

    # Nutrition / Diet — checked FIRST so that "healthy food/diet" doesn't
    # fall through to the risk_summary 'health' keyword below.
    if any(_word_in(kw, lower) for kw in [
        "nutrition", "food", "eat", "diet", "meal",
    ]):
        return "nutrition"

    # Health / Risk status
    if any(kw in lower for kw in [
        "heart rate", "blood pressure", "spo2", "pulse",
        "oxygen", "vitals", "how am i", "doing", "status",
    ]) or _word_in("health", lower) or _word_in("risk", lower) or _word_in("safe", lower):
        return "risk_summary"

    # Workout / Exercise
    if any(kw in lower for kw in [
        "workout", "exercise", "activity", "moving", "today's plan",
        "should i run", "can i walk", "fitness",
    ]):
        return "workout"

    # Alerts / Warnings
    if any(kw in lower for kw in [
        "alert", "warning", "problem", "wrong", "alarm",
    ]):
        return "alert"

    # Progress / Trends
    if any(kw in lower for kw in [
        "progress", "improve", "trend",
    ]) or _word_in("better", lower) or _word_in("week", lower) or _word_in("month", lower):
        return "progress"

    # Sleep
    if _word_in("sleep", lower):
        return "sleep"

    # Contact doctor
    if any(kw in lower for kw in [
        "doctor", "clinician", "message", "contact care",
    ]):
        return "contact_doctor"

    # Help / Features
    if any(kw in lower for kw in [
        "help", "what can you do", "features",
    ]):
        return "help"

    return None


# =============================================================================
# Template Response Generation
# =============================================================================

def _handle_risk_summary(user_id: int, db: Session, _message: str) -> str:
    """Build template response for risk summary intent."""
    from app.models.risk_assessment import RiskAssessment
    from app.models.vital_signs import VitalSignRecord
    from app.models.alert import Alert
    from app.services.nl_builders import build_risk_summary_text

    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    risk_level = latest_risk.risk_level.upper() if latest_risk else "LOW"
    risk_score = round(latest_risk.risk_score, 2) if latest_risk else 0.0

    vitals_agg = (
        db.query(
            sa_func.avg(VitalSignRecord.heart_rate).label("avg_hr"),
            sa_func.max(VitalSignRecord.heart_rate).label("max_hr"),
            sa_func.avg(VitalSignRecord.spo2).label("avg_spo2"),
        )
        .filter(VitalSignRecord.user_id == user_id, VitalSignRecord.timestamp >= window_start)
        .first()
    )
    avg_hr = int(round(vitals_agg.avg_hr)) if vitals_agg and vitals_agg.avg_hr else 72
    max_hr = int(vitals_agg.max_hr) if vitals_agg and vitals_agg.max_hr else avg_hr
    avg_spo2 = int(round(vitals_agg.avg_spo2)) if vitals_agg and vitals_agg.avg_spo2 else 98

    alert_count = (
        db.query(sa_func.count(Alert.alert_id))
        .filter(Alert.user_id == user_id, Alert.created_at >= window_start)
        .scalar()
    ) or 0

    safety_map = {"LOW": "SAFE", "MODERATE": "CAUTION", "HIGH": "UNSAFE", "CRITICAL": "UNSAFE"}
    return build_risk_summary_text(
        risk_level=risk_level,
        risk_score=risk_score,
        time_window_hours=24,
        avg_heart_rate=avg_hr,
        max_heart_rate=max_hr,
        avg_spo2=avg_spo2,
        alert_count=alert_count,
        safety_status=safety_map.get(risk_level, "SAFE"),
    )


def _handle_workout(user_id: int, db: Session, _message: str) -> str:
    """Build template response for workout intent."""
    from app.models.risk_assessment import RiskAssessment
    from app.models.recommendation import ExerciseRecommendation
    from app.services.nl_builders import build_todays_workout_text

    rec = (
        db.query(ExerciseRecommendation)
        .filter(ExerciseRecommendation.user_id == user_id)
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    risk_level = latest_risk.risk_level.upper() if latest_risk else "LOW"

    if rec:
        return build_todays_workout_text(
            activity_type=(rec.suggested_activity or "WALKING").upper(),
            intensity_level=(rec.intensity_level or "low").upper(),
            duration_minutes=rec.duration_minutes or 20,
            target_hr_min=rec.target_heart_rate_min or 85,
            target_hr_max=rec.target_heart_rate_max or 110,
            risk_level=risk_level,
        )

    return build_todays_workout_text(
        activity_type="WALKING",
        intensity_level="LIGHT",
        duration_minutes=20,
        target_hr_min=85,
        target_hr_max=110,
        risk_level=risk_level,
    )


def _handle_alert(user_id: int, db: Session, _message: str) -> str:
    """Build template response for alert intent."""
    from app.models.alert import Alert
    from app.services.nl_builders import build_alert_explanation_text

    latest_alert = (
        db.query(Alert)
        .filter(Alert.user_id == user_id)
        .order_by(desc(Alert.created_at))
        .first()
    )
    if latest_alert:
        return build_alert_explanation_text(
            alert_type=(latest_alert.alert_type or "OTHER").upper(),
            severity_level=(latest_alert.severity or "LOW").upper(),
            alert_time=latest_alert.created_at or datetime.now(timezone.utc),
            during_activity=False,
            activity_type=None,
            heart_rate=None,
            spo2=None,
            recommended_action="CONTACT_DOCTOR" if (latest_alert.severity or "").upper() in ("HIGH", "CRITICAL") else "SLOW_DOWN",
        )

    return "No recent alerts. That's good news — your vitals have been within safe ranges."


def _handle_progress(user_id: int, db: Session, _message: str) -> str:
    """Build template response for progress intent."""
    from app.models.activity import ActivitySession
    from app.models.alert import Alert
    from app.models.risk_assessment import RiskAssessment
    from app.schemas.nl import Period
    from app.services.nl_builders import compute_trend, build_progress_summary_text

    now = datetime.now(timezone.utc)
    days = 7
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    def _period(start, end):
        act_agg = (
            db.query(
                sa_func.count(ActivitySession.session_id),
                sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0),
            )
            .filter(ActivitySession.user_id == user_id, ActivitySession.start_time >= start, ActivitySession.start_time < end)
            .one()
        )
        a_count = (
            db.query(sa_func.count(Alert.alert_id))
            .filter(Alert.user_id == user_id, Alert.created_at >= start, Alert.created_at < end)
            .scalar()
        ) or 0
        avg_rs = (
            db.query(sa_func.avg(RiskAssessment.risk_score))
            .filter(RiskAssessment.user_id == user_id, RiskAssessment.assessment_date >= start, RiskAssessment.assessment_date < end)
            .scalar()
        )
        avg_rl = "HIGH" if avg_rs and avg_rs >= 0.7 else ("MODERATE" if avg_rs and avg_rs >= 0.4 else "LOW")
        safe = int(
            db.query(sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0))
            .filter(ActivitySession.user_id == user_id, ActivitySession.start_time >= start, ActivitySession.start_time < end, ActivitySession.risk_score < 0.4)
            .scalar()
        )
        above = int(
            db.query(sa_func.coalesce(sa_func.sum(ActivitySession.duration_minutes), 0))
            .filter(ActivitySession.user_id == user_id, ActivitySession.start_time >= start, ActivitySession.start_time < end, ActivitySession.risk_score >= 0.4)
            .scalar()
        )
        return Period(
            start=start,
            end=end,
            workout_count=act_agg[0],
            total_active_minutes=int(act_agg[1]),
            avg_risk_level=avg_rl,
            time_in_safe_zone_minutes=safe,
            time_above_safe_zone_minutes=above,
            alert_count=a_count,
        )

    current_period = _period(current_start, now)
    previous_period = _period(previous_start, current_start)
    trend = compute_trend(current_period, previous_period)
    return build_progress_summary_text(current=current_period, previous=previous_period, trend=trend)


_TEMPLATE_HANDLERS: dict[str, Callable[[int, Session, str], str]] = {
    "risk_summary": _handle_risk_summary,
    "workout": _handle_workout,
    "alert": _handle_alert,
    "progress": _handle_progress,
}

def _get_template_response(intent: str, user_id: int, db: Session, message: str) -> str:
    """
    Generate a template response for a matched intent.

    Calls the same NL builder functions used by the existing /nl/ endpoints.
    Returns the nl_summary text string.
    """
    handler = _TEMPLATE_HANDLERS.get(intent)
    if not handler:
        return FALLBACK_RESPONSE
    return handler(user_id, db, message)


# =============================================================================
# De-Identified Patient Context Builder
# =============================================================================

def _build_patient_context(user_id: int, db: Session) -> str:
    """
    Build a de-identified patient summary for Gemini context.

    SECURITY: This function NEVER includes:
    - Patient name, email, phone, or any PII
    - User IDs, database IDs
    - Dates of birth, addresses
    - Emergency contact information

    Only includes clinical summary data needed for health coaching.
    """
    from app.models.user import User
    from app.models.risk_assessment import RiskAssessment
    from app.models.vital_signs import VitalSignRecord
    from app.models.alert import Alert
    from app.models.recommendation import ExerciseRecommendation
    from app.api.medical_history import build_medical_profile

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return "No patient data available."

    parts = []

    # Demographics (de-identified)
    age = user.age or "unknown"
    gender = user.gender or "unknown"
    parts.append(f"Patient: {age}-year-old {gender}")

    # Lifestyle screening summary
    if user.smoking_status:
        parts.append(f"Smoking status: {user.smoking_status}")
    if user.alcohol_frequency:
        parts.append(f"Alcohol frequency: {user.alcohol_frequency}")
    if user.sedentary_hours is not None:
        parts.append(f"Sedentary hours/day: {user.sedentary_hours}")
    if user.phq2_score is not None:
        parts.append(f"PHQ-2 score: {user.phq2_score}/6")

    # Risk status
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )
    if latest_risk:
        parts.append(f"Current risk level: {latest_risk.risk_level.upper()} (score: {round(latest_risk.risk_score, 2)})")
        if latest_risk.primary_concern:
            parts.append(f"Primary concern: {latest_risk.primary_concern}")

    # Recent vitals (24h average)
    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    vitals_agg = (
        db.query(
            sa_func.avg(VitalSignRecord.heart_rate).label("avg_hr"),
            sa_func.max(VitalSignRecord.heart_rate).label("max_hr"),
            sa_func.min(VitalSignRecord.heart_rate).label("min_hr"),
            sa_func.avg(VitalSignRecord.spo2).label("avg_spo2"),
        )
        .filter(VitalSignRecord.user_id == user_id, VitalSignRecord.timestamp >= window_start)
        .first()
    )
    if vitals_agg and vitals_agg.avg_hr:
        parts.append(
            f"24h vitals: avg HR {int(round(vitals_agg.avg_hr))} BPM "
            f"(range {int(vitals_agg.min_hr)}-{int(vitals_agg.max_hr)}), "
            f"avg SpO2 {int(round(vitals_agg.avg_spo2 or 98))}%"
        )

    # Baseline HR and max safe HR
    if user.baseline_hr:
        parts.append(f"Baseline resting HR: {user.baseline_hr} BPM")
    if user.max_safe_hr:
        parts.append(f"Max safe HR: {user.max_safe_hr} BPM")

    # Recent alerts
    alert_count = (
        db.query(sa_func.count(Alert.alert_id))
        .filter(Alert.user_id == user_id, Alert.created_at >= window_start)
        .scalar()
    ) or 0
    parts.append(f"Alerts in last 24h: {alert_count}")

    # Current recommendation
    rec = (
        db.query(ExerciseRecommendation)
        .filter(ExerciseRecommendation.user_id == user_id)
        .order_by(desc(ExerciseRecommendation.created_at))
        .first()
    )
    if rec:
        parts.append(
            f"Current recommendation: {rec.suggested_activity} ({rec.intensity_level} intensity, "
            f"{rec.duration_minutes} min)"
        )
        if rec.warnings:
            parts.append(f"Warnings: {rec.warnings}")

    # Medical profile (conditions + medications as types only, no personal details)
    try:
        med_profile = build_medical_profile(user_id, db)
        active_conditions = [c.condition_type.replace("_", " ") for c in med_profile.conditions if c.status == "active"]
        if active_conditions:
            parts.append(f"Active conditions: {', '.join(active_conditions)}")
        active_meds = [f"{m.drug_name} ({m.drug_class.replace('_', ' ')})" for m in med_profile.medications if m.status == "active"]
        if active_meds:
            parts.append(f"Active medications: {', '.join(active_meds)}")
        flags = []
        if med_profile.is_on_beta_blocker:
            flags.append("on beta-blocker (HR blunted)")
        if med_profile.is_on_anticoagulant:
            flags.append("on anticoagulant (fall/bleed risk)")
        if med_profile.has_prior_mi:
            flags.append("prior myocardial infarction")
        if med_profile.has_heart_failure:
            hf_class = f" NYHA {med_profile.heart_failure_class}" if med_profile.heart_failure_class else ""
            flags.append(f"heart failure{hf_class}")
        if flags:
            parts.append(f"Clinical flags: {', '.join(flags)}")
    except Exception as e:
        logger.debug(f"Could not load medical profile for context: {e}")

    return "\n".join(parts)


# =============================================================================
# Gemini LLM Call
# =============================================================================

SYSTEM_PROMPT = """You are Ada, a supportive AI health coach for a cardiac rehabilitation patient.

RULES:
- You are NOT a doctor. Never diagnose conditions or prescribe medications.
- Always recommend the patient contact their care team for medical concerns.
- Be warm, encouraging, and concise (2-4 sentences max).
- Use the patient context below to personalize your response.
- If you don't know something, say so honestly.
- Never reveal or reference the patient's name, ID, or other identifying information.
- Never make up vital signs, test results, or medical data that isn't in the context.
- Focus on education, motivation, and emotional support.
- If the patient asks about stopping or changing medication, firmly advise them to consult their doctor."""


async def _call_gemini(
    user_message: str,
    patient_context: str,
    conversation_history: list[dict],
    gemini_api_key: str,
    screen_context: Optional[str] = None,
) -> Optional[str]:
    """
    Call Gemini 2.0 Flash with de-identified patient context.

    Returns the generated response text, or None on failure.
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        # Build conversation context (last 5 exchanges)
        history_text = ""
        recent = conversation_history[-10:] if conversation_history else []
        if recent:
            history_lines = []
            for msg in recent:
                role = "Patient" if msg.get("role") == "user" else "Ada"
                history_lines.append(f"{role}: {msg.get('text', '')}")
            history_text = "\n".join(history_lines)

        screen_line = f"The patient is currently viewing the {screen_context} screen.\n\n" if screen_context else ""

        prompt = f"""PATIENT CONTEXT:
{patient_context}

    {screen_line}
{f"RECENT CONVERSATION:{chr(10)}{history_text}{chr(10)}{chr(10)}" if history_text else ""}Patient says: {user_message}"""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                max_output_tokens=300,
            ),
        )

        text = response.text.strip()
        if text:
            logger.info(f"Gemini chat response: {len(text)} chars")
            return text
        return None

    except Exception as e:
        logger.error(f"Gemini chat call failed: {e}")
        return None


# =============================================================================
# Main Entry Point
# =============================================================================

async def generate_chat_response(
    user_message: str,
    user_id: int,
    db: Session,
    conversation_history: list[dict] | None = None,
    screen_context: Optional[str] = None,
) -> dict:
    """
    Generate a chat response using the hybrid template + Gemini approach.

    Fallback chain: Template → Gemini → Generic response.

    Args:
        user_message: The patient's message text.
        user_id: Authenticated patient's user ID.
        db: Database session.
        conversation_history: Optional list of recent messages for context.

    Returns:
        Dict with 'response' (str) and 'source' ("template"|"gemini"|"fallback").
    """
    conversation_history = conversation_history or []

    # Parse inline context prefix if provided by client message payload.
    # Format: [Context: Home] how am I doing?
    if user_message.startswith("[Context: "):
        closing_bracket = user_message.find("]")
        if closing_bracket != -1:
            extracted = user_message[len("[Context: "):closing_bracket].strip()
            if extracted:
                screen_context = extracted
            user_message = user_message[closing_bracket + 1:].strip()

    # Step 1: Try keyword-based intent classification
    intent = _classify_intent(user_message)

    if intent in _TEMPLATE_HANDLERS:
        try:
            template_text = _get_template_response(intent, user_id, db, user_message)
            logger.info(f"Chat response via template (intent={intent}) for user {user_id}")
            return {"response": template_text, "source": "template"}
        except Exception as e:
            logger.warning(f"Template response failed for intent={intent}: {e}")
            # Fall through to Gemini

    # Step 2: Try Gemini for unmatched or complex questions
    from app.config import get_settings
    settings = get_settings()

    if settings.gemini_api_key:
        patient_context = _build_patient_context(user_id, db)
        gemini_response = await _call_gemini(
            user_message=user_message,
            patient_context=patient_context,
            conversation_history=conversation_history,
            gemini_api_key=settings.gemini_api_key,
            screen_context=screen_context,
        )
        if gemini_response:
            # Add safety disclaimer for Gemini responses
            response_with_disclaimer = gemini_response + DISCLAIMER_SUFFIX
            logger.info(f"Chat response via Gemini for user {user_id}")
            return {"response": response_with_disclaimer, "source": "gemini"}
    else:
        logger.debug("Gemini API key not configured, skipping LLM fallback")

    # Step 3: Generic fallback
    logger.info(f"Chat response via fallback for user {user_id}")
    return {"response": FALLBACK_RESPONSE, "source": "fallback"}
