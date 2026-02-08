"""
Natural language alerts service.

Converts technical risk metrics and vital sign data into
patient-friendly, plain-language messages.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


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
    name = patient_name.split()[0] if patient_name else None

    message_data = _ALERT_MESSAGES.get(
        alert_type,
        _ALERT_MESSAGES.get("other", _DEFAULT_MESSAGE),
    )

    greeting = f"Hi {name}, " if name else ""

    friendly_message = greeting + message_data["message"]
    if trigger_value:
        friendly_message = friendly_message.replace("{value}", str(trigger_value))
    else:
        friendly_message = friendly_message.replace(" ({value})", "")
        friendly_message = friendly_message.replace("{value}", "elevated")

    action_steps = message_data["actions"]

    urgency = _severity_to_urgency(severity)

    risk_context = None
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
) -> str:
    """
    Convert a risk assessment into a plain-language summary.
    """
    name = patient_name.split()[0] if patient_name else "Your"
    possessive = f"{name}'s" if patient_name else "Your"

    if risk_level in ("critical", "high"):
        opener = f"{possessive} health readings show some concerning patterns."
    elif risk_level == "moderate":
        opener = f"{possessive} readings are slightly outside the normal range."
    else:
        opener = f"{possessive} readings look good overall."

    plain_drivers = [_simplify_driver(d) for d in drivers[:3]]
    if plain_drivers:
        details = " Specifically: " + "; ".join(plain_drivers) + "."
    else:
        details = ""

    if risk_level in ("critical", "high"):
        action = " Please rest and consider contacting your healthcare provider."
    elif risk_level == "moderate":
        action = " Take it easy and keep monitoring your vitals."
    else:
        action = " Keep up the good work!"

    return opener + details + action


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
