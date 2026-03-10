"""
Pydantic schemas for food image and barcode analysis.

Used by the Food Analysis API endpoints.
"""

from pydantic import BaseModel, Field


class FoodAnalysisResponse(BaseModel):
    """Response schema for AI food image analysis."""

    food_name: str = Field(..., description="Detected or inferred food name")  # What food the AI thinks is in the photo
    calories: int = Field(..., ge=0, description="Estimated calories")  # How many calories the AI estimates
    protein_grams: float = Field(..., ge=0, description="Estimated protein in grams")  # Grams of protein in the food
    carbs_grams: float = Field(..., ge=0, description="Estimated carbohydrates in grams")  # Grams of carbs in the food
    fat_grams: float = Field(..., ge=0, description="Estimated fat in grams")  # Grams of fat in the food
    is_cardiac_friendly: bool = Field(..., description="Cardiac-friendliness assessment")  # Is this food good for heart patients?
    cardiac_notes: str = Field(..., description="Cardiac-focused dietary notes")  # Tips about this food for heart health
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")  # How sure the AI is about its analysis (0-1)


class BarcodeProductResponse(BaseModel):
    """Response schema for barcode product lookup."""

    product_name: str = Field(..., description="Product name")  # Name of the scanned product
    brand: str = Field(..., description="Product brand")  # Brand/manufacturer of the product
    serving_size: str = Field(..., description="Serving size text")  # How much counts as one serving
    calories: int = Field(..., ge=0, description="Calories estimate")  # Calories per serving
    protein_grams: float = Field(..., ge=0, description="Protein grams")  # Protein per serving
    carbs_grams: float = Field(..., ge=0, description="Carbohydrate grams")  # Carbs per serving
    fat_grams: float = Field(..., ge=0, description="Fat grams")  # Fat per serving
    is_cardiac_friendly: bool = Field(..., description="Cardiac-friendliness assessment")  # Is this product heart-healthy?
    cardiac_notes: str = Field(..., description="Cardiac-focused notes")  # Heart health notes for this product