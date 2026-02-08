"""
Tests for the AI health coaching service.

Validates exercise plan generation and diet guidance
for different risk levels and patient profiles.
"""


class TestExercisePlan:
    """Exercise plan adapts to risk level, age, and vitals."""

    def test_critical_risk_recovery_plan(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="critical", risk_score=0.95, age=65,
        )
        assert plan["plan_type"] == "recovery"
        assert plan["weekly_goal_minutes"] > 0
        assert any("breathing" in s["activity"].lower() for s in plan["weekly_sessions"])

    def test_high_risk_rehabilitation_plan(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="high", risk_score=0.80, age=70,
        )
        assert plan["plan_type"] == "rehabilitation"
        assert plan["weekly_sessions"][0]["intensity"] in ("low", "very_low")
        assert len(plan["warnings"]) > 0

    def test_moderate_risk_improvement_plan(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="moderate", risk_score=0.55, age=50,
        )
        assert plan["plan_type"] == "guided_improvement"
        assert any("walking" in s["activity"].lower() for s in plan["weekly_sessions"])

    def test_moderate_with_low_spo2_adds_breathing(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="moderate", risk_score=0.55, age=55, avg_spo2=92,
        )
        breathing = [s for s in plan["weekly_sessions"] if "breathing" in s["activity"].lower()]
        assert len(breathing) >= 1

    def test_low_risk_progressive_plan(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="low", risk_score=0.15, age=35,
        )
        assert plan["plan_type"] == "progressive_training"
        assert plan["weekly_goal_minutes"] > 100

    def test_plan_has_target_hr_zones(self):
        from app.services.health_coaching import generate_exercise_plan

        plan = generate_exercise_plan(
            risk_level="low", risk_score=0.10, age=40, baseline_hr=70, max_safe_hr=180,
        )
        session = plan["weekly_sessions"][0]
        assert session["target_hr"]["min"] > 0
        assert session["target_hr"]["max"] > session["target_hr"]["min"]

    def test_elderly_gets_shorter_sessions(self):
        from app.services.health_coaching import generate_exercise_plan

        young = generate_exercise_plan(risk_level="high", risk_score=0.80, age=35)
        elder = generate_exercise_plan(risk_level="high", risk_score=0.80, age=70)
        young_dur = young["weekly_sessions"][0]["duration_minutes"]
        elder_dur = elder["weekly_sessions"][0]["duration_minutes"]
        assert elder_dur <= young_dur


class TestDietGuidance:
    """Diet guidance adapts to risk level and health state."""

    def test_high_risk_diet_has_priority_actions(self):
        from app.services.health_coaching import generate_diet_guidance

        guidance = generate_diet_guidance(
            risk_level="high", risk_score=0.85, age=60,
        )
        assert "priority_actions" in guidance
        assert "meal_suggestions" in guidance
        assert "foods_to_avoid" in guidance
        assert len(guidance["foods_to_avoid"]) > 0

    def test_low_risk_diet_has_maintenance_tips(self):
        from app.services.health_coaching import generate_diet_guidance

        guidance = generate_diet_guidance(
            risk_level="low", risk_score=0.10, age=30,
        )
        assert "priority_actions" in guidance
        assert "meal_suggestions" in guidance

    def test_low_spo2_adds_oxygen_foods(self):
        from app.services.health_coaching import generate_diet_guidance

        guidance = generate_diet_guidance(
            risk_level="moderate", risk_score=0.55, age=60, avg_spo2=91,
        )
        assert "oxygen_support_foods" in guidance
        assert len(guidance["oxygen_support_foods"]) > 0

    def test_senior_gets_nutrition_tips(self):
        from app.services.health_coaching import generate_diet_guidance

        guidance = generate_diet_guidance(
            risk_level="low", risk_score=0.10, age=70,
        )
        assert "senior_nutrition_tips" in guidance

    def test_general_principles_always_present(self):
        from app.services.health_coaching import generate_diet_guidance

        for level in ("critical", "high", "moderate", "low"):
            guidance = generate_diet_guidance(risk_level=level, risk_score=0.5, age=50)
            assert "general_principles" in guidance
            assert len(guidance["general_principles"]) >= 5


class TestCoachingPlan:
    """Full coaching plan combines exercise + diet + coaching message."""

    def test_coaching_plan_has_all_sections(self):
        from app.services.health_coaching import generate_coaching_plan

        plan = generate_coaching_plan(
            risk_level="moderate", risk_score=0.55, age=55,
        )
        assert "coaching_message" in plan
        assert "exercise_plan" in plan
        assert "diet_guidance" in plan

    def test_critical_coaching_message_urges_rest(self):
        from app.services.health_coaching import generate_coaching_plan

        plan = generate_coaching_plan(
            risk_level="critical", risk_score=0.95, age=65,
        )
        assert "rest" in plan["coaching_message"].lower()

    def test_low_risk_coaching_is_encouraging(self):
        from app.services.health_coaching import generate_coaching_plan

        plan = generate_coaching_plan(
            risk_level="low", risk_score=0.10, age=30,
        )
        assert "great" in plan["coaching_message"].lower() or "good" in plan["coaching_message"].lower()
