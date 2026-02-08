"""
AI health coaching service.

Provides personalised exercise plans and heart-healthy diet guidance
based on the patient's current risk level, age, and vital signs.

This is the "AI coach" described in the project brief: it turns raw
risk assessments into actionable lifestyle recommendations that help
cardiovascular patients live better.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exercise plan generator
# ---------------------------------------------------------------------------

# Heart-rate training zones based on Karvonen formula (% of HR reserve)
_HR_ZONES = {
    "recovery": (0.50, 0.60),
    "fat_burn": (0.60, 0.70),
    "aerobic": (0.70, 0.80),
    "threshold": (0.80, 0.90),
}


def generate_exercise_plan(
    risk_level: str,
    risk_score: float,
    age: int,
    baseline_hr: Optional[int] = None,
    max_safe_hr: Optional[int] = None,
    avg_spo2: Optional[int] = None,
    recovery_time_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a personalised weekly exercise plan.

    The plan adapts to:
      - Current risk level (critical → gentle recovery; low → progressive)
      - Age (older → lower intensity targets)
      - SpO2 (low → breathing-focused exercises)
      - Recovery fitness (poor recovery → shorter sessions)
    """
    baseline = baseline_hr or 72
    max_hr = max_safe_hr or (220 - age)
    hr_reserve = max_hr - baseline

    level = risk_level.lower()
    plan: Dict[str, Any] = {
        "risk_level": level,
        "risk_score": round(risk_score, 4),
        "patient_profile": {
            "age": age,
            "baseline_hr": baseline,
            "max_safe_hr": max_hr,
        },
    }

    if level == "critical":
        plan.update(_critical_plan(baseline, hr_reserve))
    elif level == "high":
        plan.update(_high_risk_plan(baseline, hr_reserve, age))
    elif level == "moderate":
        plan.update(_moderate_plan(baseline, hr_reserve, age, avg_spo2))
    else:
        plan.update(_low_risk_plan(baseline, hr_reserve, age, recovery_time_minutes))

    return plan


def _hr_range(baseline: int, hr_reserve: int, zone: str):
    lo, hi = _HR_ZONES.get(zone, _HR_ZONES["recovery"])
    return {
        "min": int(baseline + hr_reserve * lo),
        "max": int(baseline + hr_reserve * hi),
        "zone": zone,
    }


def _critical_plan(baseline: int, hr_reserve: int) -> Dict[str, Any]:
    return {
        "plan_type": "recovery",
        "summary": (
            "Your vitals suggest you need rest right now. "
            "Focus on gentle breathing and light movement only."
        ),
        "weekly_sessions": [
            {
                "day": "Daily",
                "activity": "Diaphragmatic breathing",
                "duration_minutes": 10,
                "intensity": "very_low",
                "target_hr": _hr_range(baseline, hr_reserve, "recovery"),
                "instructions": (
                    "Sit comfortably. Breathe in through your nose for 4 seconds, "
                    "hold for 2 seconds, exhale through pursed lips for 6 seconds. "
                    "Repeat for 10 minutes."
                ),
            },
            {
                "day": "Daily",
                "activity": "Gentle stretching",
                "duration_minutes": 5,
                "intensity": "very_low",
                "target_hr": _hr_range(baseline, hr_reserve, "recovery"),
                "instructions": (
                    "Seated neck rolls, shoulder shrugs, and ankle circles. "
                    "Do not stand if you feel dizzy."
                ),
            },
        ],
        "weekly_goal_minutes": 70,
        "warnings": [
            "Do not exercise if you feel chest pain, severe dizziness, or shortness of breath.",
            "Contact your healthcare provider before increasing activity.",
        ],
    }


def _high_risk_plan(baseline: int, hr_reserve: int, age: int) -> Dict[str, Any]:
    dur = 15 if age >= 65 else 20
    return {
        "plan_type": "rehabilitation",
        "summary": (
            "Your risk is elevated. Start with very light activity and "
            "gradually increase as your vitals improve."
        ),
        "weekly_sessions": [
            {
                "day": "Mon / Wed / Fri",
                "activity": "Slow walking",
                "duration_minutes": dur,
                "intensity": "low",
                "target_hr": _hr_range(baseline, hr_reserve, "recovery"),
                "instructions": (
                    f"Walk at a comfortable pace for {dur} minutes on flat ground. "
                    "Stop if your heart rate exceeds your target zone or if you "
                    "feel breathless."
                ),
            },
            {
                "day": "Tue / Thu",
                "activity": "Seated exercises + breathing",
                "duration_minutes": 15,
                "intensity": "very_low",
                "target_hr": _hr_range(baseline, hr_reserve, "recovery"),
                "instructions": (
                    "Seated leg lifts (10 reps each leg), arm raises with light "
                    "weights or water bottles (10 reps), followed by 5 minutes "
                    "of deep breathing."
                ),
            },
            {
                "day": "Sat / Sun",
                "activity": "Rest and recovery",
                "duration_minutes": 0,
                "intensity": "rest",
                "target_hr": None,
                "instructions": "Complete rest. Stay hydrated and monitor your vitals.",
            },
        ],
        "weekly_goal_minutes": dur * 3 + 30,
        "warnings": [
            "Keep your heart rate in the recovery zone.",
            "Stop immediately if you feel chest tightness or dizziness.",
        ],
    }


def _moderate_plan(
    baseline: int, hr_reserve: int, age: int, avg_spo2: Optional[int]
) -> Dict[str, Any]:
    dur = 20 if age >= 60 else 25
    zone = "fat_burn"
    extras: List[Dict[str, Any]] = []

    # If SpO2 is borderline, add breathing exercises
    if avg_spo2 is not None and avg_spo2 < 95:
        extras.append({
            "day": "Daily",
            "activity": "Pursed-lip breathing practice",
            "duration_minutes": 10,
            "intensity": "very_low",
            "target_hr": None,
            "instructions": (
                "Your blood oxygen is slightly low. Practice pursed-lip "
                "breathing: inhale through nose for 2 seconds, exhale slowly "
                "through pursed lips for 4 seconds. This helps improve oxygen "
                "levels over time."
            ),
        })

    return {
        "plan_type": "guided_improvement",
        "summary": (
            "Your vitals show room for improvement. Follow this balanced "
            "plan to strengthen your heart safely."
        ),
        "weekly_sessions": [
            {
                "day": "Mon / Wed / Fri",
                "activity": "Brisk walking",
                "duration_minutes": dur,
                "intensity": "low_to_moderate",
                "target_hr": _hr_range(baseline, hr_reserve, zone),
                "instructions": (
                    f"Walk briskly for {dur} minutes. You should be able to "
                    "talk but not sing. Cool down with 3 minutes of slow walking."
                ),
            },
            {
                "day": "Tue / Thu",
                "activity": "Light yoga or stretching",
                "duration_minutes": 20,
                "intensity": "low",
                "target_hr": _hr_range(baseline, hr_reserve, "recovery"),
                "instructions": (
                    "Gentle yoga poses: cat-cow, child's pose, seated twist. "
                    "Focus on steady breathing throughout."
                ),
            },
        ] + extras,
        "weekly_goal_minutes": dur * 3 + 40,
        "warnings": [
            "Monitor your heart rate during exercise.",
            "If you feel unusually fatigued, take an extra rest day.",
        ],
    }


def _low_risk_plan(
    baseline: int, hr_reserve: int, age: int, recovery_minutes: Optional[int]
) -> Dict[str, Any]:
    dur = 25 if age >= 55 else 30
    zone = "aerobic"
    # Good recovery → can push a bit harder
    if recovery_minutes is not None and recovery_minutes <= 5:
        zone = "threshold"
        dur += 5

    return {
        "plan_type": "progressive_training",
        "summary": (
            "Your vitals look great! This plan helps you build cardiovascular "
            "fitness progressively."
        ),
        "weekly_sessions": [
            {
                "day": "Mon / Wed / Fri",
                "activity": "Brisk walking or light jogging",
                "duration_minutes": dur,
                "intensity": "moderate",
                "target_hr": _hr_range(baseline, hr_reserve, zone),
                "instructions": (
                    f"Alternate between 3 minutes of brisk walking and 2 minutes "
                    "of light jogging. Aim for steady breathing. Cool down with "
                    "5 minutes of slow walking."
                ),
            },
            {
                "day": "Tue / Thu",
                "activity": "Cycling or swimming",
                "duration_minutes": dur,
                "intensity": "moderate",
                "target_hr": _hr_range(baseline, hr_reserve, "fat_burn"),
                "instructions": (
                    "Steady-state cardio at a comfortable pace. These low-impact "
                    "activities are excellent for heart health."
                ),
            },
            {
                "day": "Sat",
                "activity": "Longer walk or hike",
                "duration_minutes": 45,
                "intensity": "low_to_moderate",
                "target_hr": _hr_range(baseline, hr_reserve, "fat_burn"),
                "instructions": (
                    "Enjoy a longer walk outdoors. Nature walks reduce stress "
                    "and improve cardiovascular recovery."
                ),
            },
            {
                "day": "Sun",
                "activity": "Active recovery — yoga or stretching",
                "duration_minutes": 20,
                "intensity": "low",
                "target_hr": None,
                "instructions": (
                    "Gentle stretching or yoga to improve flexibility and "
                    "reduce muscle tension from the week."
                ),
            },
        ],
        "weekly_goal_minutes": dur * 4 + 65,
        "warnings": [
            "Listen to your body. Extra rest is fine when needed.",
            "Stay hydrated before, during, and after exercise.",
        ],
    }


# ---------------------------------------------------------------------------
# Diet guidance generator
# ---------------------------------------------------------------------------

def generate_diet_guidance(
    risk_level: str,
    risk_score: float,
    age: int,
    avg_spo2: Optional[int] = None,
    avg_heart_rate: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate heart-healthy diet guidance based on risk level and vitals.

    Based on AHA dietary recommendations for cardiovascular health.
    """
    level = risk_level.lower()

    guidance: Dict[str, Any] = {
        "risk_level": level,
        "risk_score": round(risk_score, 4),
        "general_principles": [
            "Eat plenty of fruits and vegetables (aim for 5+ servings/day).",
            "Choose whole grains over refined grains.",
            "Limit sodium intake to less than 2,300 mg/day (ideally 1,500 mg).",
            "Choose lean proteins: fish, poultry, beans, and nuts.",
            "Limit added sugars to less than 25 g/day for women, 36 g for men.",
            "Stay well hydrated — aim for 8 glasses of water per day.",
        ],
    }

    if level in ("critical", "high"):
        guidance["priority_actions"] = [
            "Avoid caffeine and energy drinks — they can elevate heart rate.",
            "Reduce sodium significantly: avoid processed foods, canned soups, and deli meats.",
            "Eat potassium-rich foods: bananas, sweet potatoes, spinach, avocados.",
            "Include omega-3 fatty acids: salmon, mackerel, walnuts, flaxseed.",
            "Avoid alcohol entirely until your risk level improves.",
        ]
        guidance["meal_suggestions"] = {
            "breakfast": "Oatmeal with berries and walnuts, or whole-grain toast with avocado.",
            "lunch": "Grilled salmon salad with leafy greens, olive oil dressing, and quinoa.",
            "dinner": "Baked chicken breast with steamed broccoli and sweet potato.",
            "snacks": "Fresh fruit, unsalted nuts, or low-fat yogurt.",
        }
        guidance["foods_to_avoid"] = [
            "Processed meats (bacon, sausage, hot dogs)",
            "Fried foods and fast food",
            "Sugary beverages and sodas",
            "High-sodium snacks (chips, pretzels, canned soups)",
            "Excessive red meat",
        ]
    elif level == "moderate":
        guidance["priority_actions"] = [
            "Limit caffeine to 1-2 cups of coffee per day.",
            "Cook at home more often to control sodium and fat intake.",
            "Add more fiber to your diet: beans, lentils, whole grains.",
            "Include omega-3 rich foods at least twice per week.",
            "Limit alcohol to 1 drink per day (women) or 2 drinks per day (men).",
        ]
        guidance["meal_suggestions"] = {
            "breakfast": "Greek yogurt with mixed berries and a sprinkle of granola.",
            "lunch": "Turkey and avocado wrap with whole-grain tortilla and side salad.",
            "dinner": "Grilled fish with roasted vegetables and brown rice.",
            "snacks": "Apple slices with almond butter, or carrot sticks with hummus.",
        }
        guidance["foods_to_avoid"] = [
            "Heavily processed snacks",
            "Sugary desserts (limit to occasional treats)",
            "Excessive saturated fats",
        ]
    else:  # low
        guidance["priority_actions"] = [
            "Maintain your current healthy eating patterns.",
            "Explore the Mediterranean or DASH diet for long-term heart health.",
            "Ensure adequate protein for muscle recovery after exercise.",
            "Consider adding fermented foods for gut health (yogurt, kimchi).",
            "Stay consistent with hydration, especially during exercise.",
        ]
        guidance["meal_suggestions"] = {
            "breakfast": "Smoothie with spinach, banana, berries, and protein powder.",
            "lunch": "Quinoa bowl with grilled chicken, roasted vegetables, and tahini.",
            "dinner": "Mediterranean plate: grilled fish, hummus, tabbouleh, and pita.",
            "snacks": "Trail mix with nuts and dried fruit, or whole-grain crackers with cheese.",
        }
        guidance["foods_to_avoid"] = [
            "Excessive processed foods (moderation is key)",
        ]

    # SpO2-specific advice
    if avg_spo2 is not None and avg_spo2 < 95:
        guidance["oxygen_support_foods"] = [
            "Iron-rich foods help oxygen transport: spinach, red meat (lean), lentils, fortified cereals.",
            "Vitamin C aids iron absorption: citrus fruits, bell peppers, strawberries.",
            "Beetroot juice may help improve oxygen delivery to muscles.",
            "Avoid smoking and secondhand smoke — they reduce oxygen levels.",
        ]

    # Age-specific advice
    if age >= 65:
        guidance["senior_nutrition_tips"] = [
            "Ensure adequate calcium and vitamin D for bone health.",
            "Eat smaller, more frequent meals if appetite is reduced.",
            "Protein is important: aim for 1.0-1.2 g per kg of body weight daily.",
            "Stay hydrated — thirst signals decrease with age.",
        ]

    return guidance


# ---------------------------------------------------------------------------
# Combined coaching response
# ---------------------------------------------------------------------------

def generate_coaching_plan(
    risk_level: str,
    risk_score: float,
    age: int,
    baseline_hr: Optional[int] = None,
    max_safe_hr: Optional[int] = None,
    avg_spo2: Optional[int] = None,
    avg_heart_rate: Optional[int] = None,
    recovery_time_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a complete AI coaching plan combining exercise and diet.

    This is the main entry point for the AI coach feature.
    """
    exercise = generate_exercise_plan(
        risk_level=risk_level,
        risk_score=risk_score,
        age=age,
        baseline_hr=baseline_hr,
        max_safe_hr=max_safe_hr,
        avg_spo2=avg_spo2,
        recovery_time_minutes=recovery_time_minutes,
    )

    diet = generate_diet_guidance(
        risk_level=risk_level,
        risk_score=risk_score,
        age=age,
        avg_spo2=avg_spo2,
        avg_heart_rate=avg_heart_rate,
    )

    level = risk_level.lower()
    if level == "critical":
        coaching_message = (
            "Right now, your health needs immediate attention. Focus on rest, "
            "gentle breathing, and heart-healthy eating. Your AI coach is here "
            "to guide you step by step."
        )
    elif level == "high":
        coaching_message = (
            "Your vitals show some concern. Let's start with gentle activity "
            "and a heart-protective diet. Small steps lead to big improvements."
        )
    elif level == "moderate":
        coaching_message = (
            "You're doing okay, but there's room to improve. Follow this "
            "balanced plan to strengthen your heart and feel better."
        )
    else:
        coaching_message = (
            "Great job! Your vitals look healthy. Keep up the good work with "
            "this progressive plan to maintain and build on your fitness."
        )

    return {
        "coaching_message": coaching_message,
        "exercise_plan": exercise,
        "diet_guidance": diet,
    }
