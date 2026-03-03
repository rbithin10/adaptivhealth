"""
Pydantic schemas for food image and barcode analysis.

Used by the Food Analysis API endpoints.
"""

from pydantic import BaseModel, Field


class FoodAnalysisResponse(BaseModel):
    """Response schema for AI food image analysis."""

    food_name: str = Field(..., description="Detected or inferred food name")
    calories: int = Field(..., ge=0, description="Estimated calories")
    protein_grams: float = Field(..., ge=0, description="Estimated protein in grams")
    carbs_grams: float = Field(..., ge=0, description="Estimated carbohydrates in grams")
    fat_grams: float = Field(..., ge=0, description="Estimated fat in grams")
    is_cardiac_friendly: bool = Field(..., description="Cardiac-friendliness assessment")
    cardiac_notes: str = Field(..., description="Cardiac-focused dietary notes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")


class BarcodeProductResponse(BaseModel):
    """Response schema for barcode product lookup."""

    product_name: str = Field(..., description="Product name")
    brand: str = Field(..., description="Product brand")
    serving_size: str = Field(..., description="Serving size text")
    calories: int = Field(..., ge=0, description="Calories estimate")
    protein_grams: float = Field(..., ge=0, description="Protein grams")
    carbs_grams: float = Field(..., ge=0, description="Carbohydrate grams")
    fat_grams: float = Field(..., ge=0, description="Fat grams")
    is_cardiac_friendly: bool = Field(..., description="Cardiac-friendliness assessment")
    cardiac_notes: str = Field(..., description="Cardiac-focused notes")