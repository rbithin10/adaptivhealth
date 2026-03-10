"""
Food analysis API endpoints.

Provides:
- AI image-based food macro estimation
- Barcode-based nutrition lookup from OpenFoodFacts
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from google import genai
from google.genai import types
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.schemas.food_analysis import BarcodeProductResponse, FoodAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_json_payload(raw_text: str) -> Dict[str, Any]:
    """Extract JSON object from a model text response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):  # Strip markdown code fences the AI sometimes wraps around JSON
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)  # Try parsing the cleaned text as JSON directly
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)  # Fall back to finding any JSON object in the text
        if not match:
            raise
        return json.loads(match.group(0))  # Parse whatever JSON-looking block was found


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        if value is None or value == "":  # Treat missing or blank values as the default
            return default
        return float(value)
    except (TypeError, ValueError):  # If conversion fails, return the safe default
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert value to int safely."""
    return int(round(_safe_float(value, float(default))))  # Convert to float first, then round to whole number


def _extract_serving_grams(serving_size: Optional[str]) -> Optional[float]:
    """Extract serving grams from a serving size text like '30 g'."""
    if not serving_size:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*g", serving_size.lower())  # Look for a number followed by 'g' (grams)
    if not match:
        return None
    return _safe_float(match.group(1), default=0.0)  # Return the numeric gram value


@router.post("/analyze-image", response_model=FoodAnalysisResponse)
async def analyze_food_image(file: UploadFile = File(...)):
    """Analyze uploaded food image with Gemini Vision and return macro estimates."""
    image_bytes = await file.read()  # Read the uploaded image into memory
    if not image_bytes:  # Reject empty uploads
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )

    settings = get_settings()
    if not settings.gemini_api_key:  # Make sure the AI service is configured
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key not configured",
        )

    prompt = (
        "Analyze this food image. Return ONLY valid JSON: "
        "{food_name, estimated_calories, protein_grams, carbs_grams, fat_grams, "
        "is_cardiac_friendly, cardiac_notes}. "
        "For cardiac_notes, mention if the food is high in saturated fat or processed."
    )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)  # Connect to Google Gemini AI

        response = client.models.generate_content(  # Send the image + prompt to Gemini for analysis
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_text(text=prompt),  # The instruction telling AI what to return
                types.Part.from_bytes(
                    data=image_bytes,  # The actual food image
                    mime_type=file.content_type or "image/jpeg",
                ),
            ],
        )

        payload = _extract_json_payload(response.text or "")  # Parse the AI's JSON response

    except json.JSONDecodeError as exc:
        logger.error(f"Gemini image analysis returned non-JSON payload: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned invalid JSON format",
        )
    except Exception as exc:
        logger.error(f"Gemini image analysis failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Food image analysis failed",
        )

    confidence = _safe_float(payload.get("confidence"), default=0.75)  # How confident the AI is (0 to 1)
    if confidence < 0.0:  # Clamp to valid range
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0

    return FoodAnalysisResponse(  # Build the response with all the nutrition data the AI found
        food_name=str(payload.get("food_name") or "Unknown food"),
        calories=_safe_int(payload.get("estimated_calories"), default=0),
        protein_grams=_safe_float(payload.get("protein_grams"), default=0.0),
        carbs_grams=_safe_float(payload.get("carbs_grams"), default=0.0),
        fat_grams=_safe_float(payload.get("fat_grams"), default=0.0),
        is_cardiac_friendly=bool(payload.get("is_cardiac_friendly", True)),
        cardiac_notes=str(payload.get("cardiac_notes") or "No additional cardiac notes."),
        confidence=confidence,
    )


@router.get("/barcode/{barcode}", response_model=BarcodeProductResponse)
async def analyze_food_barcode(barcode: str):
    """Lookup barcode nutrition from OpenFoodFacts and assess cardiac-friendliness."""
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"  # Free food database API

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:  # 15-second timeout for the lookup
            response = await client.get(url)  # Fetch product data by barcode
            response.raise_for_status()  # Raise an error if the API returned a failure code
            data = response.json()  # Parse the response as JSON
    except httpx.HTTPStatusError as exc:
        logger.error(f"OpenFoodFacts HTTP error for barcode {barcode}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch barcode product data",
        )
    except httpx.RequestError as exc:
        logger.error(f"OpenFoodFacts request error for barcode {barcode}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Barcode service request failed",
        )

    product = data.get("product") or {}  # Extract the product info section
    nutriments = product.get("nutriments") or {}  # Nutrition values per 100g

    product_name = str(product.get("product_name") or "Unknown product")
    brand = str(product.get("brands") or "Unknown brand")
    serving_size = str(product.get("serving_size") or "100 g")

    serving_grams = _extract_serving_grams(serving_size)  # Pull numeric grams from text like "30 g"
    factor = (serving_grams / 100.0) if serving_grams and serving_grams > 0 else 1.0  # Scale per-100g values to one serving

    # Get nutrition values per 100 grams from the database
    calories_per_100g = _safe_float(nutriments.get("energy-kcal_100g"), default=0.0)
    protein_per_100g = _safe_float(nutriments.get("proteins_100g"), default=0.0)
    carbs_per_100g = _safe_float(nutriments.get("carbohydrates_100g"), default=0.0)
    fat_per_100g = _safe_float(nutriments.get("fat_100g"), default=0.0)
    sat_fat_per_100g = _safe_float(nutriments.get("saturated-fat_100g"), default=0.0)

    # Convert per-100g values to per-serving values
    calories = int(round(calories_per_100g * factor))
    protein_grams = round(protein_per_100g * factor, 2)
    carbs_grams = round(carbs_per_100g * factor, 2)
    fat_grams = round(fat_per_100g * factor, 2)
    saturated_fat_per_serving = round(sat_fat_per_100g * factor, 2)

    is_cardiac_friendly = saturated_fat_per_serving <= 5.0  # Heart-safe if saturated fat stays under 5g
    if is_cardiac_friendly:
        cardiac_notes = (
            f"Estimated saturated fat is {saturated_fat_per_serving}g per serving, "
            "which is within a heart-friendly range."
        )
    else:
        cardiac_notes = (
            f"Estimated saturated fat is {saturated_fat_per_serving}g per serving, "
            "which is high for cardiac-friendly nutrition."
        )

    return BarcodeProductResponse(
        product_name=product_name,
        brand=brand,
        serving_size=serving_size,
        calories=calories,
        protein_grams=protein_grams,
        carbs_grams=carbs_grams,
        fat_grams=fat_grams,
        is_cardiac_friendly=is_cardiac_friendly,
        cardiac_notes=cardiac_notes,
    )