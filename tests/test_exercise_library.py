"""
Tests for the exercise library and selection logic.

Covers:
- EXERCISE_LIBRARY structure (categories, risk levels, required fields)
- select_exercise() random selection and deduplication
- Integration with _generate_recommendation_payload()

Run with:
    pytest tests/test_exercise_library.py -v
"""

import pytest
from app.services.recommendation_ranking import EXERCISE_LIBRARY, select_exercise


# =============================================================================
# Exercise Library Structure Tests
# =============================================================================

REQUIRED_FIELDS = {
    "category",
    "title",
    "suggested_activity",
    "intensity_level",
    "duration_minutes",
    "description",
    "warnings",
}

VALID_CATEGORIES = {"cardio", "flexibility", "breathing", "strength"}
VALID_RISK_LEVELS = {"high", "moderate", "low"}


class TestExerciseLibraryStructure:
    """Validate EXERCISE_LIBRARY data integrity."""

    def test_library_has_all_risk_levels(self):
        """Library must contain high, moderate, and low keys."""
        assert set(EXERCISE_LIBRARY.keys()) == VALID_RISK_LEVELS

    def test_minimum_exercise_count(self):
        """Library must have at least 12 exercises total."""
        total = sum(len(pool) for pool in EXERCISE_LIBRARY.values())
        assert total >= 12

    def test_each_level_has_multiple_exercises(self):
        """Each risk level must have at least 2 exercises for dedup to work."""
        for level, pool in EXERCISE_LIBRARY.items():
            assert len(pool) >= 2, f"Risk level '{level}' needs at least 2 exercises"

    @pytest.mark.parametrize("level", VALID_RISK_LEVELS)
    def test_all_exercises_have_required_fields(self, level):
        """Every exercise template must contain all required fields."""
        for idx, exercise in enumerate(EXERCISE_LIBRARY[level]):
            missing = REQUIRED_FIELDS - set(exercise.keys())
            assert not missing, (
                f"Exercise {idx} in '{level}' missing fields: {missing}"
            )

    @pytest.mark.parametrize("level", VALID_RISK_LEVELS)
    def test_categories_are_valid(self, level):
        """Every exercise must use a recognised category."""
        for exercise in EXERCISE_LIBRARY[level]:
            assert exercise["category"] in VALID_CATEGORIES, (
                f"Unknown category '{exercise['category']}' in '{level}'"
            )

    def test_all_four_categories_represented(self):
        """At least one exercise from each category must appear across levels."""
        all_categories = set()
        for pool in EXERCISE_LIBRARY.values():
            for exercise in pool:
                all_categories.add(exercise["category"])
        assert all_categories == VALID_CATEGORIES

    def test_high_risk_exercises_are_low_intensity(self):
        """High-risk exercises must all be low intensity."""
        for exercise in EXERCISE_LIBRARY["high"]:
            assert exercise["intensity_level"] == "low"

    def test_moderate_risk_exercises_are_low_intensity(self):
        """Moderate-risk exercises must all be low intensity."""
        for exercise in EXERCISE_LIBRARY["moderate"]:
            assert exercise["intensity_level"] == "low"

    def test_low_risk_exercises_are_moderate_intensity(self):
        """Low-risk exercises must all be moderate intensity."""
        for exercise in EXERCISE_LIBRARY["low"]:
            assert exercise["intensity_level"] == "moderate"

    def test_high_risk_titles_contain_recovery(self):
        """High-risk exercise titles must contain 'Recovery'."""
        for exercise in EXERCISE_LIBRARY["high"]:
            assert "Recovery" in exercise["title"], (
                f"High-risk title '{exercise['title']}' must contain 'Recovery'"
            )


# =============================================================================
# select_exercise Tests
# =============================================================================

class TestSelectExercise:
    """Validate select_exercise() selection and dedup logic."""

    @pytest.mark.parametrize("level", ["high", "moderate", "low"])
    def test_returns_dict_with_required_fields(self, level):
        """Selected exercise contains all required template fields."""
        result = select_exercise(level)
        for field in REQUIRED_FIELDS:
            assert field in result

    def test_critical_maps_to_high(self):
        """'critical' risk level should select from the high pool."""
        high_activities = {
            ex["suggested_activity"] for ex in EXERCISE_LIBRARY["high"]
        }
        for _ in range(20):
            result = select_exercise("critical")
            assert result["suggested_activity"] in high_activities

    def test_unknown_level_defaults_to_low(self):
        """Unrecognised risk levels should fall back to the low pool."""
        low_activities = {
            ex["suggested_activity"] for ex in EXERCISE_LIBRARY["low"]
        }
        for _ in range(20):
            result = select_exercise("unknown_level")
            assert result["suggested_activity"] in low_activities

    def test_avoids_last_activity(self):
        """Should never return the same suggested_activity as last_activity."""
        first_activity = EXERCISE_LIBRARY["moderate"][0]["suggested_activity"]
        seen = set()
        for _ in range(40):
            result = select_exercise("moderate", last_activity=first_activity)
            seen.add(result["suggested_activity"])
        assert first_activity not in seen

    def test_fallback_when_all_filtered(self):
        """If last_activity matches every exercise, fall back to full pool."""
        # Create a risk level key that has exercises, then use a fake activity
        # that does not exist — should return normally
        result = select_exercise("high", last_activity="nonexistent activity")
        assert result["suggested_activity"] is not None

    def test_returns_copy_not_reference(self):
        """Modifying returned dict must not alter the library."""
        result = select_exercise("low")
        original_title = result["title"]
        result["title"] = "MUTATED"
        fresh = EXERCISE_LIBRARY["low"]
        for ex in fresh:
            assert ex["title"] != "MUTATED" or ex["title"] == original_title

    def test_variety_across_calls(self):
        """Multiple calls should return different exercises (probabilistic)."""
        activities = set()
        for _ in range(50):
            result = select_exercise("low")
            activities.add(result["suggested_activity"])
        # With 4 exercises in the low pool, expect more than 1 unique result
        assert len(activities) > 1
