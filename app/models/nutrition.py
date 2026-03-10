"""
=============================================================================
ADAPTIV HEALTH - Nutrition Entry Model
=============================================================================
SQLAlchemy model for nutrition tracking (meals, calories, macros).

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# ENUMS
#   - MealType.......................... Line 30  (breakfast, lunch, dinner, snack)
#
# CLASS: NutritionEntry (SQLAlchemy Model)
#   - Primary Key....................... Line 45  (entry_id)
#   - Foreign Key....................... Line 50  (user_id → users)
#   - Meal Info......................... Line 55  (meal_type, description)
#   - Nutritional Data.................. Line 65  (calories, protein, carbs, fat)
#   - Metadata.......................... Line 75  (timestamp, indexes)
#   - Relationships..................... Line 85  (user)
#
# BUSINESS CONTEXT:
# - Non-PHI nutrition logging for patients
# - Meal tracking with calorie and macro recording
# - Production feature for personal health management
# =============================================================================
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# =============================================================================
# Enums
# =============================================================================

class MealType(str, Enum):
    """The different meal categories a patient can log."""
    BREAKFAST = "breakfast"  # Morning meal
    LUNCH = "lunch"  # Midday meal
    DINNER = "dinner"  # Evening meal
    SNACK = "snack"  # Small bite between meals
    OTHER = "other"  # Anything else (drinks, supplements, etc.)


# =============================================================================
# Model
# =============================================================================

class NutritionEntry(Base):
    """
    Nutrition entry model for meal/food logging.
    
    Tracks calories and basic macros (protein, carbs, fat).
    Non-PHI data for personal health tracking.
    """

    __tablename__ = "nutrition_entries"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    entry_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for this food entry

    # -------------------------------------------------------------------------
    # Foreign Key — which patient logged this meal
    # -------------------------------------------------------------------------
    user_id = Column(  # The patient who ate this meal
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Meal Information
    # -------------------------------------------------------------------------
    meal_type = Column(
        String(50),
        nullable=False,
        default=MealType.OTHER.value,
        comment="Type of meal: breakfast, lunch, dinner, snack, other"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Optional description of the meal or food items"
    )

    # -------------------------------------------------------------------------
    # Nutritional Data
    # -------------------------------------------------------------------------
    calories = Column(
        Integer,
        nullable=False,
        comment="Total calories for this meal/entry"
    )
    
    protein_grams = Column(
        Integer,
        nullable=True,
        comment="Protein in grams (optional)"
    )
    
    carbs_grams = Column(
        Integer,
        nullable=True,
        comment="Carbohydrates in grams (optional)"
    )
    
    fat_grams = Column(
        Integer,
        nullable=True,
        comment="Fat in grams (optional)"
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When the entry was created"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="nutrition_entries")

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_nutrition_user_timestamp', 'user_id', 'timestamp'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<NutritionEntry(entry_id={self.entry_id}, user_id={self.user_id}, meal_type={self.meal_type}, calories={self.calories})>"
