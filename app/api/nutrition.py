"""
Nutrition Entry API endpoints.

Simple nutrition logging for patients: meals, calories, basic macros.
Also provides personalised daily meal recommendations based on cardiac risk.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
#
# ENDPOINTS - PATIENT (own entries)
#   - POST /nutrition.................. Line 55  (Create nutrition entry)
#   - GET /nutrition/recent............ Line 100 (List recent entries)
#   - DELETE /nutrition/{id}........... Line 150 (Delete entry)
#   - GET /nutrition/recommendations... Line 200 (Daily meal recommendations)
#
# BUSINESS CONTEXT:
# - Patients log meals and track nutrition from mobile app
# - Recommendations leverage latest risk assessment for cardiac diet
# - Non-PHI data for personal health tracking
# - Production feature for fitness and wellness management
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Dict
from datetime import datetime, date, timezone, timedelta
import logging

from app.database import get_db
from app.models.user import User
from app.models.nutrition import NutritionEntry
from app.models.risk_assessment import RiskAssessment
from app.schemas.nutrition import (
    NutritionCreate,
    NutritionResponse,
    NutritionListResponse,
    NutritionRecommendationResponse,
    NutritionLogCreate,
    NutritionLogResponse,
)
from app.api.auth import get_current_user_session_or_bearer

logger = logging.getLogger(__name__)
router = APIRouter()


def _save_nutrition_entry(
    db: Session,
    current_user: User,
    meal_type: str,
    calories: int,
    description: Optional[str] = None,
    protein_grams: Optional[int] = None,
    carbs_grams: Optional[int] = None,
    fat_grams: Optional[int] = None,
    timestamp: Optional[datetime] = None,
) -> NutritionEntry:
    """Persist a nutrition entry and return the saved model."""
    nutrition_entry = NutritionEntry(  # Create a new meal log record
        user_id=current_user.user_id,
        meal_type=meal_type,
        description=description,
        calories=calories,
        protein_grams=protein_grams,
        carbs_grams=carbs_grams,
        fat_grams=fat_grams,
        timestamp=timestamp or datetime.now(timezone.utc),  # Default to right now if no time given
    )

    db.add(nutrition_entry)  # Add to database
    db.commit()  # Save permanently
    db.refresh(nutrition_entry)  # Reload to get the auto-generated ID
    return nutrition_entry


# =============================================================================
# Patient Endpoints
# =============================================================================

# =============================================
# CREATE_NUTRITION_ENTRY - Log a meal
# Used by: Mobile app nutrition screen
# Returns: NutritionResponse with entry details
# Roles: ALL authenticated users
# =============================================
@router.post("/nutrition", response_model=NutritionResponse, status_code=status.HTTP_201_CREATED)
async def create_nutrition_entry(
    entry_data: NutritionCreate,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Create a new nutrition entry for the current user.
    
    Args:
        entry_data: Nutrition entry data (meal type, calories, macros)
        current_user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        NutritionResponse: Created nutrition entry with ID and timestamp
    
    Raises:
        400: Invalid input data
    """
    try:
        nutrition_entry = _save_nutrition_entry(
            db=db,
            current_user=current_user,
            meal_type=entry_data.meal_type,
            description=entry_data.description,
            calories=entry_data.calories,
            protein_grams=entry_data.protein_grams,
            carbs_grams=entry_data.carbs_grams,
            fat_grams=entry_data.fat_grams,
            timestamp=entry_data.logged_at,
        )
        
        logger.info(
            f"Nutrition entry created: entry_id={nutrition_entry.entry_id}, "
            f"user_id={current_user.user_id}, meal_type={entry_data.meal_type}, "
            f"calories={entry_data.calories}"
        )
        
        return nutrition_entry
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create nutrition entry for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create nutrition entry"
        )


# =============================================
# LOG_MEAL_CONSUMPTION - Compatibility endpoint for nutrition logs
# Used by: UI contracts documented in backend API specification
# Returns: Logging receipt with adherence feedback
# Roles: ALL authenticated users
# =============================================
@router.post("/nutrition/logs", response_model=NutritionLogResponse, status_code=status.HTTP_201_CREATED)
async def log_meal_consumption(
    log_data: NutritionLogCreate,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """
    Log meal consumption using the `/nutrition/logs` contract.

    The underlying storage uses `nutrition_entries` to keep compatibility with
    existing mobile/dashboard behavior.
    """
    try:
        item_names = [item.food_name for item in log_data.items if item.food_name]  # Collect food names from the items list
        desc_parts: List[str] = []
        if item_names:
            desc_parts.append(", ".join(item_names))  # Join food names into a readable string
        if log_data.notes:
            desc_parts.append(f"notes: {log_data.notes}")  # Include any freeform notes
        if log_data.meal_id:
            desc_parts.append(f"meal_id: {log_data.meal_id}")  # Link back to a recommended meal
        description = " | ".join(desc_parts) if desc_parts else None

        nutrition_entry = _save_nutrition_entry(
            db=db,
            current_user=current_user,
            meal_type=log_data.meal_type,
            description=description,
            calories=log_data.total_calories,
            timestamp=log_data.timestamp,
        )

        has_recommendation_link = bool(log_data.meal_id)  # Was this meal linked to a recommendation?
        has_item_details = len(log_data.items) > 0  # Did the user provide food item details?
        adherence = 0.95 if has_recommendation_link and has_item_details else 0.85  # Higher score if following recommendations

        feedback = "Excellent choice! High fiber and nutrient-dense."  # Default positive feedback
        if log_data.satisfaction_rating is not None and log_data.satisfaction_rating <= 5:
            feedback = "Logged successfully. Consider adjusting portions or meal choices for better adherence."  # Gentle nudge for low satisfaction

        return NutritionLogResponse(
            log_id=f"log_{nutrition_entry.entry_id}",
            user_id=current_user.user_id,
            meal_type=nutrition_entry.meal_type,
            timestamp=nutrition_entry.timestamp,
            total_calories=nutrition_entry.calories,
            adherence_to_recommendation=adherence,
            feedback=feedback,
            status="logged",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log meal for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to log meal consumption",
        )


# =============================================
# GET_RECENT_ENTRIES - List recent nutrition entries
# Used by: Mobile app nutrition screen
# Returns: List of recent entries for current user
# Roles: ALL authenticated users
# =============================================
@router.get("/nutrition/recent", response_model=NutritionListResponse)
async def get_recent_nutrition_entries(
    limit: int = Query(default=5, ge=1, le=100, description="Number of entries to return"),
    date_str: Optional[str] = Query(default=None, alias="date", description="Filter entries by date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Get recent nutrition entries for the current user.
    
    Args:
        limit: Maximum number of entries to return (default: 5, max: 100)
        current_user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        NutritionListResponse: List of recent nutrition entries with total count
    """
    try:
        start_ts: Optional[datetime] = None
        end_ts: Optional[datetime] = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD",
                )
            start_ts = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
            end_ts = start_ts + timedelta(days=1)

        count_query = db.query(func.count(NutritionEntry.entry_id)).filter(
            NutritionEntry.user_id == current_user.user_id
        )
        if start_ts is not None and end_ts is not None:
            count_query = count_query.filter(
                NutritionEntry.timestamp >= start_ts,
                NutritionEntry.timestamp < end_ts,
            )
        total_count = count_query.scalar()
        
        # Get recent entries ordered by timestamp descending
        entries_query = db.query(NutritionEntry).filter(
            NutritionEntry.user_id == current_user.user_id
        )
        if start_ts is not None and end_ts is not None:
            entries_query = entries_query.filter(
                NutritionEntry.timestamp >= start_ts,
                NutritionEntry.timestamp < end_ts,
            )
        entries = (
            entries_query
            .order_by(desc(NutritionEntry.timestamp))
            .limit(limit)
            .all()
        )
        
        logger.info(
            f"Retrieved {len(entries)} nutrition entries for user {current_user.user_id} "
            f"(total: {total_count})"
        )
        
        return NutritionListResponse(
            entries=entries,
            total_count=total_count or 0,
            limit=limit
        )
    
    except Exception as e:
        logger.error(f"Failed to retrieve nutrition entries for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve nutrition entries"
        )


# =============================================
# DELETE_NUTRITION_ENTRY - Remove an entry
# Used by: Mobile app nutrition screen (delete action)
# Returns: Success message
# Roles: ALL authenticated users (own entries only)
# =============================================
@router.delete("/nutrition/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nutrition_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db)
):
    """
    Delete a nutrition entry.
    
    Users can only delete their own entries.
    
    Args:
        entry_id: ID of the nutrition entry to delete
        current_user: Authenticated user from JWT token
        db: Database session
    
    Raises:
        404: Entry not found or does not belong to current user
    """
    # Find entry
    entry = db.query(NutritionEntry).filter(
        NutritionEntry.entry_id == entry_id,  # Match the specific entry
        NutritionEntry.user_id == current_user.user_id  # Only allow deleting your own entries
    ).first()
    
    if not entry:
        logger.warning(
            f"Nutrition entry {entry_id} not found or does not belong to user {current_user.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nutrition entry not found"
        )
    
    # Delete entry
    try:
        db.delete(entry)
        db.commit()
        
        logger.info(
            f"Nutrition entry deleted: entry_id={entry_id}, user_id={current_user.user_id}"
        )
        
        return None  # 204 No Content
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete nutrition entry {entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete nutrition entry"
        )


# =============================================================================
# Cardiac Diet Library (hardcoded, clinically reviewed)
# WHY: Heart-healthy, high-potassium, anti-inflammatory meals aligned with
#      AHA dietary guidelines for cardiovascular patients.
# =============================================================================

_CARDIAC_DIET_LIBRARY: Dict[str, Dict] = {
    "low": {
        "goals": {
            "calories_target": 2100,
            "potassium_mg": 3500,
            "water_liters": 2.5,
            "fiber_grams": 28,
            "protein_grams": 80,
        },
        "meals": [
            {
                "meal_type": "breakfast",
                "meal_id": "low_b1",
                "suggested_items": ["oatmeal", "blueberries", "low-fat yogurt", "honey"],
                "portion_sizes": {
                    "oatmeal": "1/2 cup dry",
                    "blueberries": "1 cup",
                    "yogurt": "6 oz",
                    "honey": "1 tbsp",
                },
                "nutritional_info": {
                    "calories": 340,
                    "potassium_mg": 460,
                    "protein_grams": 14,
                    "fiber_grams": 8,
                    "saturated_fat_grams": 1.5,
                },
                "benefits": "High fiber, antioxidant-rich, supports heart health",
                "cardiovascular_notes": "Blueberries contain anthocyanins that improve vascular function",
                "prep_time_minutes": 5,
                "difficulty": "easy",
            },
            {
                "meal_type": "lunch",
                "meal_id": "low_l1",
                "suggested_items": ["grilled chicken breast", "brown rice", "steamed broccoli", "olive oil"],
                "portion_sizes": {
                    "chicken": "4 oz",
                    "rice": "1 cup cooked",
                    "broccoli": "2 cups",
                    "olive_oil": "1 tbsp",
                },
                "nutritional_info": {
                    "calories": 520,
                    "potassium_mg": 650,
                    "protein_grams": 35,
                    "fiber_grams": 5,
                    "saturated_fat_grams": 2.0,
                },
                "benefits": "Lean protein, whole grains, rich in vitamins",
                "cardiovascular_notes": "Focus on whole foods to support blood pressure management",
                "prep_time_minutes": 20,
                "difficulty": "easy",
            },
            {
                "meal_type": "snack",
                "meal_id": "low_s1",
                "suggested_items": ["almonds", "apple"],
                "portion_sizes": {
                    "almonds": "1 oz (23 nuts)",
                    "apple": "1 medium",
                },
                "nutritional_info": {
                    "calories": 180,
                    "potassium_mg": 195,
                    "protein_grams": 6,
                    "fiber_grams": 4,
                    "saturated_fat_grams": 1.0,
                },
                "benefits": "Healthy fats, natural sugars, sustained energy",
                "cardiovascular_notes": None,
                "prep_time_minutes": 0,
                "difficulty": "easy",
            },
            {
                "meal_type": "dinner",
                "meal_id": "low_d1",
                "suggested_items": ["baked salmon", "sweet potato", "asparagus"],
                "portion_sizes": {
                    "salmon": "5 oz",
                    "sweet_potato": "1 medium",
                    "asparagus": "1 cup",
                },
                "nutritional_info": {
                    "calories": 480,
                    "potassium_mg": 800,
                    "protein_grams": 32,
                    "fiber_grams": 6,
                    "saturated_fat_grams": 1.5,
                },
                "benefits": "Omega-3 rich, supports cardiovascular health",
                "cardiovascular_notes": "Salmon omega-3s promote healthy heart function and reduce inflammation",
                "prep_time_minutes": 25,
                "difficulty": "easy",
            },
        ],
        "note": "Maintaining a heart-healthy diet. Keep up the balanced meals and hydration.",
    },
    "moderate": {
        "goals": {
            "calories_target": 2000,
            "potassium_mg": 4000,
            "water_liters": 2.5,
            "fiber_grams": 30,
            "protein_grams": 75,
        },
        "meals": [
            {
                "meal_type": "breakfast",
                "meal_id": "mod_b1",
                "suggested_items": ["steel-cut oats", "banana", "walnuts", "cinnamon"],
                "portion_sizes": {
                    "oats": "1/2 cup dry",
                    "banana": "1 medium",
                    "walnuts": "1 oz",
                    "cinnamon": "1 tsp",
                },
                "nutritional_info": {
                    "calories": 380,
                    "potassium_mg": 550,
                    "protein_grams": 12,
                    "fiber_grams": 9,
                    "saturated_fat_grams": 1.0,
                },
                "benefits": "High potassium, anti-inflammatory",
                "cardiovascular_notes": "Walnuts provide alpha-linolenic acid; cinnamon may support healthy blood pressure",
                "prep_time_minutes": 10,
                "difficulty": "easy",
            },
            {
                "meal_type": "lunch",
                "meal_id": "mod_l1",
                "suggested_items": ["lentil soup", "whole-wheat bread", "mixed greens salad"],
                "portion_sizes": {
                    "soup": "1.5 cups",
                    "bread": "1 slice",
                    "salad": "2 cups",
                },
                "nutritional_info": {
                    "calories": 450,
                    "potassium_mg": 700,
                    "protein_grams": 22,
                    "fiber_grams": 12,
                    "saturated_fat_grams": 1.0,
                },
                "benefits": "Plant-based protein, very high fiber, supports gut and heart health",
                "cardiovascular_notes": "Lentils are rich in folate and magnesium which aid vascular relaxation",
                "prep_time_minutes": 30,
                "difficulty": "medium",
            },
            {
                "meal_type": "snack",
                "meal_id": "mod_s1",
                "suggested_items": ["carrot sticks", "hummus"],
                "portion_sizes": {
                    "carrots": "1 cup sticks",
                    "hummus": "3 tbsp",
                },
                "nutritional_info": {
                    "calories": 130,
                    "potassium_mg": 280,
                    "protein_grams": 5,
                    "fiber_grams": 5,
                    "saturated_fat_grams": 0.5,
                },
                "benefits": "Low calorie, high potassium, anti-inflammatory",
                "cardiovascular_notes": None,
                "prep_time_minutes": 0,
                "difficulty": "easy",
            },
            {
                "meal_type": "dinner",
                "meal_id": "mod_d1",
                "suggested_items": ["herb-crusted cod", "quinoa", "roasted beets"],
                "portion_sizes": {
                    "cod": "5 oz",
                    "quinoa": "3/4 cup cooked",
                    "beets": "1 cup diced",
                },
                "nutritional_info": {
                    "calories": 440,
                    "potassium_mg": 750,
                    "protein_grams": 34,
                    "fiber_grams": 7,
                    "saturated_fat_grams": 1.0,
                },
                "benefits": "Lean white fish, complete protein grain, nitrate-rich beets",
                "cardiovascular_notes": "Beet nitrates convert to nitric oxide, supporting vasodilation",
                "prep_time_minutes": 25,
                "difficulty": "medium",
            },
        ],
        "note": "Moderate risk detected — focusing on anti-inflammatory foods and consistent hydration.",
    },
    "high": {
        "goals": {
            "calories_target": 1800,
            "potassium_mg": 4500,
            "water_liters": 3.0,
            "fiber_grams": 35,
            "protein_grams": 70,
        },
        "meals": [
            {
                "meal_type": "breakfast",
                "meal_id": "high_b1",
                "suggested_items": ["chia seed pudding", "mango", "coconut milk"],
                "portion_sizes": {
                    "chia_seeds": "3 tbsp",
                    "mango": "1/2 cup diced",
                    "coconut_milk": "6 oz unsweetened",
                },
                "nutritional_info": {
                    "calories": 280,
                    "potassium_mg": 400,
                    "protein_grams": 8,
                    "fiber_grams": 12,
                    "saturated_fat_grams": 2.0,
                },
                "benefits": "Very high fiber, omega-3 from chia",
                "cardiovascular_notes": "Chia seeds reduce inflammation markers and support arterial health",
                "prep_time_minutes": 5,
                "difficulty": "easy",
            },
            {
                "meal_type": "lunch",
                "meal_id": "high_l1",
                "suggested_items": ["spinach-avocado salad", "grilled tofu", "lemon-tahini dressing"],
                "portion_sizes": {
                    "spinach": "3 cups",
                    "avocado": "1/2 medium",
                    "tofu": "4 oz",
                    "dressing": "2 tbsp",
                },
                "nutritional_info": {
                    "calories": 390,
                    "potassium_mg": 950,
                    "protein_grams": 20,
                    "fiber_grams": 10,
                    "saturated_fat_grams": 2.5,
                },
                "benefits": "Potassium-dense, heart-healthy fats, plant-based protein",
                "cardiovascular_notes": "Spinach and avocado supply magnesium and potassium to help regulate blood pressure",
                "prep_time_minutes": 15,
                "difficulty": "easy",
            },
            {
                "meal_type": "snack",
                "meal_id": "high_s1",
                "suggested_items": ["unsalted mixed nuts", "dried apricots"],
                "portion_sizes": {
                    "mixed_nuts": "1 oz",
                    "dried_apricots": "4 halves",
                },
                "nutritional_info": {
                    "calories": 200,
                    "potassium_mg": 350,
                    "protein_grams": 6,
                    "fiber_grams": 3,
                    "saturated_fat_grams": 1.5,
                },
                "benefits": "Potassium-rich, heart-healthy fats",
                "cardiovascular_notes": "Dried apricots are one of the highest potassium snack sources",
                "prep_time_minutes": 0,
                "difficulty": "easy",
            },
            {
                "meal_type": "dinner",
                "meal_id": "high_d1",
                "suggested_items": ["grilled mackerel", "steamed kale", "brown rice"],
                "portion_sizes": {
                    "mackerel": "4 oz",
                    "kale": "2 cups",
                    "brown_rice": "3/4 cup cooked",
                },
                "nutritional_info": {
                    "calories": 430,
                    "potassium_mg": 820,
                    "protein_grams": 30,
                    "fiber_grams": 7,
                    "saturated_fat_grams": 2.0,
                },
                "benefits": "Very high omega-3, anti-inflammatory, nutrient-dense greens",
                "cardiovascular_notes": "Mackerel is among the richest sources of EPA/DHA for cardiac protection",
                "prep_time_minutes": 20,
                "difficulty": "medium",
            },
        ],
        "note": "High risk detected — prioritise anti-inflammatory omega-3 sources and consistent hydration.",
    },
}

# Reuse the high-risk plan for critical level
_CARDIAC_DIET_LIBRARY["critical"] = _CARDIAC_DIET_LIBRARY["high"]  # Critical patients get the same strict diet as high-risk


def _build_daily_summary(meals: List[Dict]) -> Dict:
    """Aggregate nutritional totals across all meals."""
    totals = {  # Start with zeros and add up each meal's nutrition
        "total_calories": 0,
        "total_potassium_mg": 0,
        "total_protein_grams": 0,
        "total_fiber_grams": 0,
        "total_saturated_fat_grams": 0.0,
    }
    for meal in meals:
        info = meal["nutritional_info"]
        totals["total_calories"] += info["calories"]
        totals["total_potassium_mg"] += info["potassium_mg"]
        totals["total_protein_grams"] += info["protein_grams"]
        totals["total_fiber_grams"] += info["fiber_grams"]
        totals["total_saturated_fat_grams"] += info["saturated_fat_grams"]
    return totals


def _build_status_vs_goals(summary: Dict, goals: Dict) -> Dict:
    """Compare meal totals against daily goals."""
    potassium_pct = round(summary["total_potassium_mg"] / goals["potassium_mg"] * 100)  # How much of the daily potassium goal was met
    return {
        "potassium": f"{potassium_pct}% of recommended daily intake",
        "water": f"Track throughout the day ({goals['water_liters']} liters goal)",
        "notes": "Excellent for cardiovascular recovery. Focus on hydration.",
    }


# =============================================
# GET_NUTRITION_RECOMMENDATIONS - Daily meal plan
# Used by: Mobile app nutrition screen, Home summary
# Returns: Personalised cardiac-diet meal suggestions
# Roles: ALL authenticated users
# =============================================
@router.get("/nutrition/recommendations", response_model=NutritionRecommendationResponse)
async def get_nutrition_recommendations(
    date_str: Optional[str] = Query(
        default=None,
        alias="date",
        description="Date in YYYY-MM-DD format (defaults to today)",
    ),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """
    Get personalised daily meal recommendations based on cardiovascular risk.

    Selects meals from a clinically-reviewed cardiac diet library,
    using the user's latest risk assessment to determine potassium targets,
    hydration goals, and anti-inflammatory emphasis.

    Args:
        date_str: Optional date string (YYYY-MM-DD). Defaults to today.
        current_user: Authenticated user from JWT token.
        db: Database session.

    Returns:
        NutritionRecommendationResponse: Daily goals, 4 meals, summary, and goal comparison.

    Raises:
        400: Invalid date format.
    """
    # --- Validate or default the date ----------------------------------------
    if date_str:
        try:
            recommendation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
    else:
        recommendation_date = date.today()

    # --- Look up the user's latest risk assessment ---------------------------
    latest_risk = (  # Find the most recent risk score for this patient
        db.query(RiskAssessment)
        .filter(RiskAssessment.user_id == current_user.user_id)
        .order_by(desc(RiskAssessment.assessment_date))
        .first()
    )

    # Determine risk level (fall back to user.risk_level or "low")
    if latest_risk:
        risk_level = (latest_risk.risk_level or "low").lower()  # Use the assessed risk level
    elif current_user.risk_level:
        risk_level = current_user.risk_level.lower()  # Fall back to the user's profile risk
    else:
        risk_level = "low"  # Default to low risk if nothing is on record

    # Clamp to known keys
    if risk_level not in _CARDIAC_DIET_LIBRARY:  # Make sure the risk level has a matching meal plan
        risk_level = "low"

    # --- Build the recommendation from the diet library ----------------------
    plan = _CARDIAC_DIET_LIBRARY[risk_level]  # Pick the right meal plan for this risk level
    goals = plan["goals"]  # Daily nutrition targets
    meals = plan["meals"]  # Suggested meals for the day
    daily_summary = _build_daily_summary(meals)  # Add up all the nutrition across meals
    status_vs_goals = _build_status_vs_goals(daily_summary, goals)  # Compare totals to daily targets

    logger.info(
        f"Nutrition recommendations generated: user_id={current_user.user_id}, "
        f"date={recommendation_date}, risk_level={risk_level}"
    )

    return NutritionRecommendationResponse(
        date=str(recommendation_date),
        user_id=current_user.user_id,
        daily_nutrition_goals=goals,
        meal_restrictions=["saturated_fats", "processed_foods"],
        meals=meals,
        daily_summary=daily_summary,
        status_vs_goals=status_vs_goals,
        nutritionist_note=plan["note"],
        confidence_score=0.88,
        last_updated=datetime.now(timezone.utc),
    )


# =============================================
# GET_NUTRITION_PROGRESS - Date-range nutrition tracking summary
# Used by: Nutrition tab progress charts
# Returns: Daily summaries + trend and goal status
# Roles: ALL authenticated users
# =============================================
@router.get("/nutrition/progress")
async def get_nutrition_progress(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """Return nutrition progress summary for a date range."""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        ) from exc

    if end_dt < start_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )

    start_ts = datetime.combine(start_dt, datetime.min.time(), tzinfo=timezone.utc)  # Start of the first day
    end_ts = datetime.combine(end_dt, datetime.max.time(), tzinfo=timezone.utc)  # End of the last day

    entries = (  # Get all nutrition entries in the date range
        db.query(NutritionEntry)
        .filter(
            NutritionEntry.user_id == current_user.user_id,
            NutritionEntry.timestamp >= start_ts,
            NutritionEntry.timestamp <= end_ts,
        )
        .order_by(NutritionEntry.timestamp.asc())
        .all()
    )

    grouped = {}  # Group entries by date so we can summarise each day
    for entry in entries:
        key = entry.timestamp.date().isoformat()
        grouped.setdefault(key, []).append(entry)

    daily_summaries = []
    daily_calories = []  # Track daily calorie totals for trend analysis
    daily_adherence_scores = []  # Track how closely user followed recommendations
    for day_key in sorted(grouped.keys()):
        day_entries = grouped[day_key]
        total_calories = sum(item.calories or 0 for item in day_entries)  # Add up all calories for this day

        linked_count = 0  # Count entries that reference a recommended meal
        for item in day_entries:
            description = (item.description or "").lower()
            if "meal_id:" in description:  # Entry was linked to our recommendation system
                linked_count += 1

        adherence_score = 0.0  # Calculate how closely this day followed advice
        if day_entries:
            adherence_score = round((linked_count / len(day_entries)) * 0.4 + 0.55, 2)  # Base score + bonus for following recommendations

        daily_summaries.append({
            "date": day_key,
            "meals_logged": len(day_entries),
            "total_calories": total_calories,
            "adherence_score": adherence_score,
            "notes": "Good day, followed recommendations" if adherence_score >= 0.85 else "Keep improving meal consistency",
        })
        daily_calories.append(total_calories)
        daily_adherence_scores.append(adherence_score)

    days_total = (end_dt - start_dt).days + 1  # Total days in the requested range
    days_tracked = len(daily_summaries)  # How many days had at least one entry
    avg_calories = round(sum(daily_calories) / days_tracked, 2) if days_tracked else 0  # Average daily calories
    avg_adherence = round(sum(daily_adherence_scores) / days_tracked, 2) if days_tracked else 0  # Average adherence score

    calorie_trend = "No data"  # Determine if calorie intake is going up, down, or staying flat
    if len(daily_calories) >= 2:
        delta = daily_calories[-1] - daily_calories[0]  # Compare last day to first day
        if abs(delta) <= 100:
            calorie_trend = "Stable"  # Within 100 calories — no significant change
        elif delta > 100:
            calorie_trend = "Increasing"  # Eating more over time
        else:
            calorie_trend = "Decreasing"  # Eating less over time

    adherence_trend = "No data"  # Determine if recommendation adherence is improving or declining
    if len(daily_adherence_scores) >= 2:
        delta = daily_adherence_scores[-1] - daily_adherence_scores[0]
        if abs(delta) <= 0.05:
            adherence_trend = "Stable"
        elif delta > 0.05:
            adherence_trend = "Improving"
        else:
            adherence_trend = "Declining"

    consistency_text = f"Good - {days_tracked}/{days_total} days logged" if days_total else "No period selected"  # How consistently the user logged meals

    return {
        "period": {
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "days_tracked": days_tracked,
        },
        "daily_summaries": daily_summaries,
        "weekly_average": {
            "calories_per_day": avg_calories,
            "adherence_to_recommendations": avg_adherence,
            "consistency": consistency_text,
        },
        "trends": {
            "calorie_trend": calorie_trend,
            "recommendation_adherence": adherence_trend,
        },
        "goals_status": {
            "hydration": "Track throughout the day against hydration target",
            "recommendation": "Maintain consistent meal logging and hydration",
        },
    }
