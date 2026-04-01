"""
Natural language alerts service.

Converts technical risk metrics and vital sign data into
patient-friendly, plain-language messages.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CONSTANTS
#   - _ALERT_MESSAGES.................. Line 70  (Template messages)
#
# FUNCTIONS
#   - generate_natural_language_alert(). Line 25  (Convert alert to text)
#   - format_risk_summary()............ Line 110 (Risk to plain text)
#   - _severity_to_urgency()........... Line 145 (Map severity levels)
#
# BUSINESS CONTEXT:
# - LLM-powered (future) natural language generation
# - Currently template-based for reliability
# - Patient-friendly push notification text
# =============================================================================
"""

import logging
from typing import Dict, Any, Optional, List

from app.config import get_settings

logger = logging.getLogger(__name__)


def generate_ai_risk_summary(
    risk_score: float,
    risk_level: str,
    drivers: List[str],
    avg_heart_rate: Optional[int] = None,
    avg_spo2: Optional[int] = None,
    alert_count_24h: Optional[int] = None,
) -> str:
    """
    Generate a Gemini-powered natural-language risk summary.

    Raises:
        RuntimeError: If Gemini is not configured or generation fails.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key is not configured")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)

        context_lines = [
            f"Risk level: {risk_level}",
            f"Risk score: {risk_score:.2f}",
            f"Top risk drivers: {', '.join(drivers[:5]) if drivers else 'No explicit drivers provided'}",
        ]
        if avg_heart_rate is not None:
            context_lines.append(f"Average heart rate (24h): {avg_heart_rate} BPM")
        if avg_spo2 is not None:
            context_lines.append(f"Average SpO2 (24h): {avg_spo2}%")
        if alert_count_24h is not None:
            context_lines.append(f"Alerts in last 24h: {alert_count_24h}")

        prompt = (
            "You are a cardiac rehabilitation AI assistant writing a concise clinical insight summary for a clinician dashboard.\n"
            "Rules:\n"
            "- Use only the provided metrics; do not invent values.\n"
            "- 3 to 5 sentences, plain language, clinically useful.\n"
            "- Mention current status, likely drivers, and immediate monitoring focus.\n"
            "- Do not provide diagnosis or medication changes.\n\n"
            "Patient context:\n"
            + "\n".join(context_lines)
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=220,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text
    except Exception as exc:
        logger.error(f"Gemini risk summary generation failed: {exc}")
        raise RuntimeError("Gemini summary generation failed")


def generate_natural_language_alert(
    alert_type: str,
    severity: str,
    trigger_value: Optional[str] = None,
    threshold_value: Optional[str] = None,
    risk_score: Optional[float] = None,
    risk_level: Optional[str] = None,
    patient_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert technical alert data into a patient-friendly message.
    """
    name = patient_name.split()[0] if patient_name else None  # Use first name only for a friendly greeting

    # Look up the message template for this alert type
    message_data = _ALERT_MESSAGES.get(
        alert_type,
        _ALERT_MESSAGES.get("other", _DEFAULT_MESSAGE),  # Fall back to a generic message if type unknown
    )

    greeting = f"Hi {name}, " if name else ""  # Add a personal greeting if we know the name

    friendly_message = greeting + message_data["message"]  # Build the patient-friendly message
    if trigger_value:
        friendly_message = friendly_message.replace("{value}", str(trigger_value))  # Insert the actual value
    else:
        friendly_message = friendly_message.replace(" ({value})", "")  # Remove placeholder if no value
        friendly_message = friendly_message.replace("{value}", "elevated")

    action_steps = message_data["actions"]  # What the patient should do next

    urgency = _severity_to_urgency(severity)  # Convert technical severity to patient-friendly urgency

    risk_context = None  # Extra context about overall risk (if available)
    if risk_score is not None:
        risk_context = _risk_score_to_plain_language(risk_score, risk_level)

    return {
        "friendly_message": friendly_message,
        "action_steps": action_steps,
        "urgency_level": urgency,
        "risk_context": risk_context,
        "original_alert_type": alert_type,
        "original_severity": severity,
    }


def format_risk_summary(
    risk_score: float,
    risk_level: str,
    drivers: List[str],
    patient_name: Optional[str] = None,
    heart_rate: Optional[int] = None,
    spo2: Optional[float] = None,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    hrv: Optional[float] = None,
    assessment_date: Optional[str] = None,
    clinical_notes: Optional[List[str]] = None,
    patient_age: Optional[int] = None,
) -> str:
    """
    Clinician-focused risk summary built entirely from structured data.
    Produces a detailed 4-6 sentence paragraph suitable for a clinical dashboard.
    """
    name = patient_name or "The patient"
    level_label = risk_level.upper()
    score_pct = int(round(risk_score * 100))

    # Sentence 1 — status overview
    if risk_level in ("critical", "high"):
        status = (
            f"{name} is currently assessed at {level_label} cardiac risk "
            f"(score: {score_pct}%), indicating immediate clinical attention is warranted."
        )
    elif risk_level == "moderate":
        status = (
            f"{name} is currently assessed at {level_label} cardiac risk "
            f"(score: {score_pct}%), suggesting closer monitoring of vital trends."
        )
    else:
        status = (
            f"{name} is currently assessed at {level_label} cardiac risk "
            f"(score: {score_pct}%), with vitals largely within acceptable parameters."
        )

    # Sentence 2 — contributing factors
    if drivers and drivers != ["Vitals are within expected safe limits."]:
        active_drivers = [d for d in drivers if "within expected" not in d]
        if active_drivers:
            factor_list = "; ".join(active_drivers[:4])
            factors = f"Key contributing factors include: {factor_list}."
        else:
            factors = "No significant risk factors were identified in the current assessment."
    else:
        factors = "No significant risk factors were identified in the current assessment."

    # Sentence 3 — vitals snapshot
    vitals_parts = []
    if heart_rate is not None:
        vitals_parts.append(f"HR {heart_rate} BPM")
    if spo2 is not None:
        vitals_parts.append(f"SpO\u2082 {spo2:.0f}%")
    if systolic_bp is not None and diastolic_bp is not None:
        vitals_parts.append(f"BP {systolic_bp}/{diastolic_bp} mmHg")
    elif systolic_bp is not None:
        vitals_parts.append(f"SBP {systolic_bp} mmHg")
    if hrv is not None:
        vitals_parts.append(f"HRV {hrv:.1f} ms")

    if vitals_parts:
        vitals_snap = f"Vitals at assessment: {', '.join(vitals_parts)}."
    else:
        vitals_snap = ""

    # Sentence 4 — monitoring focus
    if risk_level in ("critical", "high"):
        focus = (
            "Recommend continuous monitoring of heart rate and oxygen saturation; "
            "consider escalation protocol if values deteriorate further."
        )
    elif risk_level == "moderate":
        focus = (
            "Recommend increased monitoring frequency and review of activity intensity "
            "to prevent progression to high-risk status."
        )
    else:
        focus = (
            "Routine monitoring is sufficient. Encourage adherence to the current "
            "rehabilitation programme."
        )

    # Sentence 5 — clinician notes context
    notes_line = ""
    if clinical_notes:
        latest = clinical_notes[0][:120] + ("..." if len(clinical_notes[0]) > 120 else "")
        count = len(clinical_notes)
        notes_line = (
            f"Latest clinician note ({count} total): \"{latest}\""
        )

    parts = [status, factors]
    if vitals_snap:
        parts.append(vitals_snap)
    parts.append(focus)
    if notes_line:
        parts.append(notes_line)

    return " ".join(parts)


def format_patient_risk_summary(
    risk_score: float,
    risk_level: str,
    drivers: List[str],
    patient_name: Optional[str] = None,
    heart_rate: Optional[int] = None,
    spo2: Optional[float] = None,
) -> str:
    """
    Patient-friendly risk summary in plain, reassuring language.
    Avoids clinical jargon. Suitable for the patient's own mobile/web screen.
    """
    first_name = patient_name.split()[0] if patient_name else "You"
    greeting = f"Hi {first_name}."

    if risk_level in ("critical", "high"):
        status = (
            "Your recent health readings show some patterns that need attention. "
            "Your care team has been notified."
        )
        action = (
            "We recommend you rest, avoid strenuous activity, and contact your "
            "healthcare provider today."
        )
    elif risk_level == "moderate":
        status = (
            "Your recent health readings are slightly outside your normal range. "
            "Nothing alarming, but worth keeping an eye on."
        )
        action = (
            "Take it easy for now, stay hydrated, and keep monitoring your vitals "
            "as usual."
        )
    else:
        status = "Your recent health readings look good overall. Keep it up!"
        action = "Continue following your rehabilitation plan and stay active."

    # Plain-language driver mention (1 max, simplified)
    plain_drivers = [_simplify_driver(d) for d in drivers if "within expected" not in d]
    detail = ""
    if plain_drivers:
        detail = f"We noticed: {plain_drivers[0].lower()}."

    vitals_note = ""
    parts = [greeting, status]
    if detail:
        parts.append(detail)
    parts.append(action)

    return " ".join(parts)


_DEFAULT_MESSAGE = {
    "message": "We noticed something unusual in your recent readings. Please check in with how you're feeling.",
    "actions": [
        "Take a moment to rest",
        "Check how you're feeling",
        "Contact your doctor if concerned",
    ],
}

_ALERT_MESSAGES = {
    "high_heart_rate": {
        "message": "your heart rate is higher than usual ({value}). This could mean your body is working harder than it should.",
        "actions": [
            "Stop any physical activity and sit down",
            "Take slow, deep breaths for 2 minutes",
            "Drink some water",
            "If it doesn't come down in 10 minutes, call your doctor",
        ],
    },
    "low_heart_rate": {
        "message": "your heart rate is lower than expected ({value}). This might mean your body needs attention.",
        "actions": [
            "Sit or lie down if you feel dizzy",
            "Avoid sudden movements",
            "Contact your healthcare provider if you feel unwell",
        ],
    },
    "low_spo2": {
        "message": "your blood oxygen level has dropped ({value}). This means your body may not be getting enough oxygen.",
        "actions": [
            "Sit upright to help your breathing",
            "Take slow, deep breaths",
            "If you feel short of breath or dizzy, seek medical help immediately",
            "Do not ignore this. Low oxygen can be serious",
        ],
    },
    "high_blood_pressure": {
        "message": "your blood pressure reading is elevated ({value}). This is worth keeping an eye on.",
        "actions": [
            "Sit down and relax for 5 minutes",
            "Avoid caffeine and salty foods",
            "Take another reading in 15 minutes",
            "If it stays high, contact your healthcare provider",
        ],
    },
    "irregular_rhythm": {
        "message": "we detected an irregular pattern in your heartbeat. This may be nothing, but it's worth checking.",
        "actions": [
            "Stay calm and sit down",
            "Note any symptoms (dizziness, chest pain, shortness of breath)",
            "Contact your healthcare provider to discuss this reading",
        ],
    },
    "abnormal_activity": {
        "message": "your activity pattern looks different from usual. Your body might need a different approach today.",
        "actions": [
            "Consider reducing your workout intensity",
            "Listen to your body. Rest if you feel tired",
            "Stay hydrated",
        ],
    },
    "other": _DEFAULT_MESSAGE,
}


def _severity_to_urgency(severity: str) -> str:
    """Convert technical severity to patient-friendly urgency."""
    mapping = {
        "emergency": "act_now",
        "critical": "urgent",
        "warning": "attention_needed",
        "info": "for_your_info",
    }
    return mapping.get(severity, "for_your_info")


def _risk_score_to_plain_language(score: float, level: Optional[str] = None) -> str:
    """Convert risk score to plain language."""
    if level:
        lvl = level.lower()
    else:
        lvl = ""

    if score >= 0.8 or lvl in ("critical", "high"):
        return "Your recent readings suggest a higher level of risk."
    if score >= 0.5 or lvl == "moderate":
        return "Your readings are slightly elevated."
    return "Your readings look stable and within a safe range."


def _simplify_driver(driver: str) -> str:
    """Simplify risk drivers into plain language."""
    replacements = {
        "hr": "heart rate",
        "spo2": "blood oxygen",
        "bp": "blood pressure",
    }
    text = driver
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text
