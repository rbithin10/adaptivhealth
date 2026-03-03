"""
Nutrition Entry Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - MealType.......................... Line 20  (breakfast, lunch, etc.)
#
# SCHEMAS
#   - NutritionEntryBase................ Line 30  (Common fields)
#   - NutritionCreate................... Line 45  (Create entry input)
#   - NutritionResponse................. Line 60  (Full entry output)
#   - NutritionListResponse............. Line 75  (Paginated list)
#
# BUSINESS CONTEXT:
# - Nutrition logging for patients
# - Production feature for calorie and macro tracking
# =============================================================================
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime, date
from enum import Enum


class MealType(str, Enum):
    """Types of meals."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    OTHER = "other"


class NutritionEntryBase(BaseModel):
    """Base schema for nutrition entries."""
    meal_type: str = Field(..., description="Type of meal")
    description: Optional[str] = Field(None, max_length=500, description="Optional meal description")
    calories: int = Field(..., ge=0, le=10000, description="Total calories")
    protein_grams: Optional[int] = Field(None, ge=0, le=500, description="Protein in grams")
    carbs_grams: Optional[int] = Field(None, ge=0, le=1000, description="Carbohydrates in grams")
    fat_grams: Optional[int] = Field(None, ge=0, le=500, description="Fat in grams")

    @field_validator('meal_type')
    @classmethod
    def validate_meal_type(cls, v: str) -> str:
        """Validate meal type is one of allowed values."""
        allowed = [mt.value for mt in MealType]
        if v.lower() not in allowed:
            raise ValueError(f"meal_type must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty string")
        return v.strip() if v else None


class NutritionCreate(NutritionEntryBase):
    """
    Schema for creating a new nutrition entry.

    User ID is inferred from authentication.
    Timestamp defaults to current time.
    """
    logged_at: Optional[datetime] = Field(
        None,
        description="Optional timestamp for the meal. Defaults to current time if omitted. "
                    "Allows patients to log meals retroactively.",
    )


class NutritionLogItem(BaseModel):
    """Single food item included in a logged meal."""
    food_name: str = Field(..., min_length=1, max_length=200)
    portion: Optional[str] = Field(None, max_length=100)
    calories: Optional[int] = Field(None, ge=0, le=5000)


class NutritionLogCreate(BaseModel):
    """Schema for the /nutrition/logs endpoint payload."""
    user_id: Optional[int] = Field(
        None,
        description="Optional user ID from client payload. Server uses authenticated user.",
    )
    meal_type: str = Field(..., description="Type of meal")
    meal_id: Optional[str] = Field(None, max_length=100, description="Recommendation meal ID")
    items: List[NutritionLogItem] = Field(default_factory=list, description="Meal items")
    total_calories: int = Field(..., ge=0, le=10000, description="Total meal calories")
    timestamp: Optional[datetime] = Field(None, description="Meal timestamp")
    notes: Optional[str] = Field(None, max_length=500, description="Optional user notes")
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=10, description="Satisfaction 1-10")

    @field_validator("meal_type")
    @classmethod
    def validate_meal_type_for_log(cls, v: str) -> str:
        """Validate meal type for meal logs."""
        allowed = [mt.value for mt in MealType]
        if v.lower() not in allowed:
            raise ValueError(f"meal_type must be one of: {', '.join(allowed)}")
        return v.lower()


class NutritionLogResponse(BaseModel):
    """Response schema for /nutrition/logs endpoint."""
    log_id: str
    user_id: int
    meal_type: str
    timestamp: datetime
    total_calories: int
    adherence_to_recommendation: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    status: str = "logged"
    meal_date: Optional[date] = Field(
        None,
        description="Date the meal was consumed (YYYY-MM-DD). "
                    "Used for daily grouping/aggregation. Defaults to today.",
    )


class NutritionResponse(NutritionEntryBase):
    """
    Schema for nutrition entry response.
    
    Includes all fields plus entry_id, user_id, and timestamp.
    """
    entry_id: int = Field(..., description="Unique entry ID")
    user_id: int = Field(..., description="User who owns this entry")
    timestamp: datetime = Field(..., description="When the entry was created")

    class Config:
        from_attributes = True


class NutritionListResponse(BaseModel):
    """
    Schema for paginated nutrition entry list.
    """
    entries: List[NutritionResponse] = Field(..., description="List of nutrition entries")
    total_count: int = Field(..., description="Total number of entries for this user")
    limit: int = Field(..., description="Number of entries returned")

    class Config:
        from_attributes = True


# =============================================================================
# Nutrition Recommendation Schemas
# =============================================================================

class DailyNutritionGoals(BaseModel):
    """Daily macro and micronutrient targets based on cardiac health profile."""
    calories_target: int = Field(..., description="Daily calorie target")
    potassium_mg: int = Field(..., description="Daily potassium target in milligrams")
    water_liters: float = Field(..., description="Daily water intake goal in liters")
    fiber_grams: int = Field(..., description="Daily fiber target in grams")
    protein_grams: int = Field(..., description="Daily protein target in grams")


class MealNutritionalInfo(BaseModel):
    """Nutritional breakdown for a single meal."""
    calories: int = Field(..., ge=0, description="Calories")
    potassium_mg: int = Field(..., ge=0, description="Potassium in milligrams")
    protein_grams: int = Field(..., ge=0, description="Protein in grams")
    fiber_grams: int = Field(..., ge=0, description="Fiber in grams")
    saturated_fat_grams: float = Field(..., ge=0, description="Saturated fat in grams")


class MealRecommendation(BaseModel):
    """A single meal suggestion with portion sizes and nutritional info."""
    meal_type: str = Field(..., description="Meal slot: breakfast, lunch, snack, dinner")
    meal_id: str = Field(..., description="Unique meal identifier")
    suggested_items: List[str] = Field(..., description="Food items in this meal")
    portion_sizes: Dict[str, str] = Field(..., description="Portion size for each item")
    nutritional_info: MealNutritionalInfo = Field(..., description="Macro/micro totals")
    benefits: str = Field(..., description="Health benefits summary")
    cardiovascular_notes: Optional[str] = Field(None, description="Heart-health notes")
    prep_time_minutes: Optional[int] = Field(None, ge=0, description="Preparation time")
    difficulty: Optional[str] = Field(None, description="Difficulty level")


class DailySummary(BaseModel):
    """Aggregated totals for all recommended meals."""
    total_calories: int = Field(..., ge=0)
    total_potassium_mg: int = Field(..., ge=0)
    total_protein_grams: int = Field(..., ge=0)
    total_fiber_grams: int = Field(..., ge=0)
    total_saturated_fat_grams: float = Field(..., ge=0)


class StatusVsGoals(BaseModel):
    """Comparison of recommendations against daily targets."""
    potassium: str = Field(..., description="Potassium status relative to target")
    water: str = Field(..., description="Hydration reminder")
    notes: str = Field(..., description="Overall diet quality note")


class NutritionRecommendationResponse(BaseModel):
    """
    Full daily nutrition recommendation payload.

    Includes personalised goals, 4-meal plan (breakfast, lunch, snack, dinner),
    daily summary aggregations, and goal comparison.
    """
    date: str = Field(..., description="Recommendation date (YYYY-MM-DD)")
    user_id: int = Field(..., description="Patient ID")
    daily_nutrition_goals: DailyNutritionGoals
    meal_restrictions: List[str] = Field(..., description="Dietary restrictions for cardiac patients")
    meals: List[MealRecommendation] = Field(..., description="Recommended meals for the day")
    daily_summary: DailySummary
    status_vs_goals: StatusVsGoals
    nutritionist_note: str = Field(..., description="Context-aware dietary guidance")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    last_updated: datetime = Field(..., description="Timestamp of recommendation generation")
