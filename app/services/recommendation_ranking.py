"""
Activity recommendation ranking service.

A/B testing framework for exercise recommendations.
Tracks which recommendation variants lead to better patient outcomes.
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Recommendation variants for A/B testing
RECOMMENDATION_VARIANTS = {
    "high": {
        "A": {
            "title": "Recovery & Monitoring",
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
    variant_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a recommendation with A/B variant assignment.

    Deterministically assigns users to variant A or B based on user_id hash
    so the same user always gets the same variant (consistent experience).

    Args:
        user_id: User ID for deterministic variant assignment.
        risk_level: Current risk level (low/moderate/high).
        variant_override: Force a specific variant (for testing).

    Returns:
        Dict with recommendation and variant metadata.
    """
    # Normalize risk level
    level = risk_level.lower()
    if level in ("critical", "high"):
        level = "high"
    elif level not in ("moderate", "low"):
        level = "low"

    variants = RECOMMENDATION_VARIANTS.get(level, RECOMMENDATION_VARIANTS["low"])

    # Determine variant
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
    outcome_value: Optional[float] = None
) -> Dict[str, Any]:
    """
    Record the outcome of a recommendation for A/B analysis.

    Args:
        user_id: User who received the recommendation.
        experiment_id: Which experiment this belongs to.
        variant: Which variant (A or B) was shown.
        outcome: What happened (completed, skipped, partial).
        outcome_value: Optional numeric outcome (e.g., post-session risk score).

    Returns:
        Recorded outcome data.
    """
    record = {
        "user_id": user_id,
        "experiment_id": experiment_id,
        "variant": variant,
        "outcome": outcome,
        "outcome_value": outcome_value,
        "status": "recorded"
    }

    logger.info(
        f"A/B outcome recorded: user={user_id}, experiment={experiment_id}, "
        f"variant={variant}, outcome={outcome}"
    )

    return record


def _assign_variant(user_id: int) -> str:
    """Deterministically assign A or B based on user_id.

    MD5 is used here solely for fast, deterministic bucketing — not for
    any security purpose. It provides a uniform distribution of users
    across variants, which is all that A/B assignment requires.
    """
    hash_val = hashlib.md5(str(user_id).encode()).hexdigest()  # noqa: S324
    return "A" if int(hash_val, 16) % 2 == 0 else "B"
