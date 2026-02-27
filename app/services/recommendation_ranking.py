"""
Activity recommendation ranking service.

Exercise library with categorised templates for risk-aware recommendations,
plus an A/B testing framework for tracking recommendation outcomes.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CONSTANTS
#   - EXERCISE_LIBRARY................. Line 30  (12+ exercise templates)
#   - RECOMMENDATION_VARIANTS.......... Line 145 (A/B variant definitions)
#
# FUNCTIONS
#   - select_exercise()................ Line 100 (Pick exercise avoiding repeat)
#   - get_ranked_recommendation()...... Line 200 (Get variant for user)
#   - record_recommendation_outcome().. Line 230 (Track user action)
#   - _assign_variant()................ Line 255 (Deterministic hashing)
#
# BUSINESS CONTEXT:
# - 4 categories: cardio, flexibility, breathing, strength
# - 3 risk levels: high (recovery), moderate (gentle), low (active)
# - Deduplication avoids repeating the same activity consecutively
# - A/B testing framework for variant analysis
# =============================================================================
"""

import hashlib
import logging
import random
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Exercise Library — categorised templates by risk level
# =============================================================================
# WHY: A richer pool means patients see varied guidance instead of the same
# plan every time.  Categories align with cardiac rehabilitation best
# practices: aerobic conditioning, flexibility, respiratory training,
# and progressive resistance.

EXERCISE_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "high": [
        # --- breathing ---
        {
            "category": "breathing",
            "title": "Box Breathing Recovery",
            "suggested_activity": "Box breathing (4-4-4-4)",
            "intensity_level": "low",
            "duration_minutes": 10,
            "description": (
                "Sit comfortably and follow a box breathing pattern: "
                "inhale 4 s, hold 4 s, exhale 4 s, hold 4 s. "
                "Repeat for the full duration."
            ),
            "warnings": "If dizziness or chest pain occurs, stop and seek medical attention.",
        },
        {
            "category": "breathing",
            "title": "Diaphragmatic Breathing Recovery",
            "suggested_activity": "Diaphragmatic breathing",
            "intensity_level": "low",
            "duration_minutes": 10,
            "description": (
                "Lie on your back with one hand on your chest and the other on "
                "your abdomen. Breathe slowly through your nose, letting your "
                "abdomen rise. Exhale gently through pursed lips."
            ),
            "warnings": "Stop if you feel lightheaded. Contact a healthcare provider if symptoms persist.",
        },
        # --- flexibility ---
        {
            "category": "flexibility",
            "title": "Seated Stretch Recovery",
            "suggested_activity": "Seated gentle stretching",
            "intensity_level": "low",
            "duration_minutes": 10,
            "description": (
                "Remain seated and perform slow neck rolls, shoulder shrugs, "
                "and ankle circles. Focus on relaxing each muscle group."
            ),
            "warnings": "Avoid any stretch that causes sharp pain. Stay hydrated.",
        },
        {
            "category": "flexibility",
            "title": "Chair Yoga Recovery",
            "suggested_activity": "Chair yoga",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": (
                "Use a sturdy chair for seated cat-cow stretches, seated "
                "twists, and gentle forward folds. Keep movements slow."
            ),
            "warnings": "If symptoms worsen, stop immediately and contact your care team.",
        },
    ],
    "moderate": [
        # --- cardio ---
        {
            "category": "cardio",
            "title": "Easy-Pace Walking",
            "suggested_activity": "Walking at easy pace",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": (
                "Walk on flat ground at a comfortable conversational pace. "
                "Monitor how you feel and slow down if needed."
            ),
            "warnings": "Pause if dizziness, chest pain, or unusual breathlessness occurs.",
        },
        # --- flexibility ---
        {
            "category": "flexibility",
            "title": "Standing Stretch Routine",
            "suggested_activity": "Standing stretches",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": (
                "Perform standing quad stretches, calf raises, hamstring "
                "stretches, and side bends. Hold each stretch 20-30 seconds."
            ),
            "warnings": "Use a wall for balance if needed. Stop if any stretch causes sharp pain.",
        },
        # --- breathing ---
        {
            "category": "breathing",
            "title": "Mindful Walking",
            "suggested_activity": "Walking meditation",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": (
                "Walk slowly and synchronise your breathing with your steps: "
                "inhale for 3 steps, exhale for 4 steps. Stay relaxed."
            ),
            "warnings": "Stay on flat terrain. Pause if dizziness or chest tightness occurs.",
        },
        # --- strength ---
        {
            "category": "strength",
            "title": "Light Balance Exercises",
            "suggested_activity": "Bodyweight balance drills",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": (
                "Perform single-leg stands (30 s each), heel-to-toe walks, "
                "and gentle wall push-ups. Use a chair for support."
            ),
            "warnings": "Keep a support surface nearby. Stop if you feel unsteady.",
        },
    ],
    "low": [
        # --- cardio ---
        {
            "category": "cardio",
            "title": "Brisk Walking Session",
            "suggested_activity": "Brisk walking",
            "intensity_level": "moderate",
            "duration_minutes": 20,
            "description": (
                "Walk at a pace where you can talk but not sing. "
                "Maintain steady effort and stay hydrated."
            ),
            "warnings": "Monitor for symptoms. Avoid sudden spikes in intensity.",
        },
        {
            "category": "cardio",
            "title": "Light Cycling Session",
            "suggested_activity": "Light cycling",
            "intensity_level": "moderate",
            "duration_minutes": 20,
            "description": (
                "Cycle on flat terrain or a stationary bike at moderate "
                "resistance. Keep a smooth, consistent cadence."
            ),
            "warnings": "Stay seated if on a road bike. Reduce effort if heart rate spikes.",
        },
        # --- strength ---
        {
            "category": "strength",
            "title": "Bodyweight Strength Circuit",
            "suggested_activity": "Bodyweight circuit",
            "intensity_level": "moderate",
            "duration_minutes": 20,
            "description": (
                "Alternate between squats, wall push-ups, lunges, and "
                "standing calf raises. Rest 30 s between exercises."
            ),
            "warnings": "Keep movements controlled. Stop if chest pain or dizziness occurs.",
        },
        # --- flexibility ---
        {
            "category": "flexibility",
            "title": "Dynamic Mobility Routine",
            "suggested_activity": "Dynamic stretching",
            "intensity_level": "moderate",
            "duration_minutes": 15,
            "description": (
                "Perform leg swings, arm circles, hip openers, and torso "
                "rotations. Move through full range of motion at a steady pace."
            ),
            "warnings": "Warm up for 2 minutes before starting. Avoid bouncing.",
        },
    ],
}


def select_exercise(
    risk_level: str,
    last_activity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pick a random exercise template from the pool for *risk_level*,
    avoiding the same *suggested_activity* as *last_activity*.

    Args:
        risk_level: One of "high", "moderate", or "low".
                    "critical" is treated as "high".
        last_activity: The suggested_activity string of the patient's
                       most recent recommendation (used for dedup).

    Returns:
        A copy of the selected exercise template dict.
    """
    level = risk_level.lower()
    if level in ("critical", "high"):
        level = "high"
    elif level not in ("moderate", "low"):
        level = "low"

    pool = EXERCISE_LIBRARY[level]

    # Filter out last activity to avoid repetition
    if last_activity:
        candidates = [
            ex for ex in pool if ex["suggested_activity"] != last_activity
        ]
        # Fall back to full pool if all were filtered (single-item pool edge case)
        if not candidates:
            candidates = pool
    else:
        candidates = pool

    return random.choice(candidates).copy()


# =============================================================================
# A/B Recommendation Variants (legacy / experiment framework)
# =============================================================================

RECOMMENDATION_VARIANTS = {
    "high": {
        "A": {
            "title": "Recovery and Monitoring",
            "suggested_activity": "Rest and light breathing",
            "intensity_level": "low",
            "duration_minutes": 10,
            "description": "Stop intense activity. Sit down, hydrate, and do slow breathing.",
        },
        "B": {
            "title": "Guided Recovery",
            "suggested_activity": "Seated breathing exercises",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": "Follow guided breathing: inhale 4s, hold 4s, exhale 6s. Stay seated.",
        },
    },
    "moderate": {
        "A": {
            "title": "Low-Intensity Session",
            "suggested_activity": "Walking",
            "intensity_level": "low",
            "duration_minutes": 15,
            "description": "Reduce intensity today. Aim for a steady pace and monitor how you feel.",
        },
        "B": {
            "title": "Gentle Movement",
            "suggested_activity": "Stretching and light yoga",
            "intensity_level": "low",
            "duration_minutes": 20,
            "description": "Focus on gentle stretches and deep breathing to aid recovery.",
        },
    },
    "low": {
        "A": {
            "title": "Continue Safe Training",
            "suggested_activity": "Walking / Light cardio",
            "intensity_level": "moderate",
            "duration_minutes": 20,
            "description": "You are in a safe zone. Keep steady effort and stay hydrated.",
        },
        "B": {
            "title": "Progress Your Workout",
            "suggested_activity": "Brisk walking or cycling",
            "intensity_level": "moderate",
            "duration_minutes": 25,
            "description": "Your vitals are great! Try increasing pace slightly for extra benefit.",
        },
    },
}


def get_ranked_recommendation(
    user_id: int,
    risk_level: str,
    variant_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a recommendation with A/B variant assignment.

    Deterministically assigns users to variant A or B based on user_id hash
    so the same user always gets the same variant.
    """
    level = risk_level.lower()
    if level in ("critical", "high"):
        level = "high"
    elif level not in ("moderate", "low"):
        level = "low"

    variants = RECOMMENDATION_VARIANTS.get(level, RECOMMENDATION_VARIANTS["low"])

    if variant_override and variant_override.upper() in variants:
        variant = variant_override.upper()
    else:
        variant = _assign_variant(user_id)

    recommendation = variants[variant].copy()

    return {
        "variant": variant,
        "risk_level": level,
        "recommendation": recommendation,
        "experiment_id": f"rec_ranking_{level}_v1",
        "user_id": user_id,
    }


def record_recommendation_outcome(
    user_id: int,
    experiment_id: str,
    variant: str,
    outcome: str,
    outcome_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Record the outcome of a recommendation for A/B analysis.
    """
    record = {
        "user_id": user_id,
        "experiment_id": experiment_id,
        "variant": variant,
        "outcome": outcome,
        "outcome_value": outcome_value,
        "status": "recorded",
    }

    logger.info(
        "A/B outcome recorded: user=%s, experiment=%s, variant=%s, outcome=%s",
        user_id,
        experiment_id,
        variant,
        outcome,
    )

    return record


def _assign_variant(user_id: int) -> str:
    """
    Deterministically assign A or B based on user_id.

    MD5 is used here solely for fast, deterministic bucketing, not for security.
    """
    hash_val = hashlib.md5(str(user_id).encode()).hexdigest()  # noqa: S324
    return "A" if int(hash_val, 16) % 2 == 0 else "B"
