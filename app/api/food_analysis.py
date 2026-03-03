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

import google.generativeai as genai
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.schemas.food_analysis import BarcodeProductResponse, FoodAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_json_payload(raw_text: str) -> Dict[str, Any]:
    """Extract JSON object from a model text response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert value to int safely."""
    return int(round(_safe_float(value, float(default))))


def _extract_serving_grams(serving_size: Optional[str]) -> Optional[float]:
    """Extract serving grams from a serving size text like '30 g'."""
    if not serving_size:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*g", serving_size.lower())
    if not match:
        return None
    return _safe_float(match.group(1), default=0.0)


@router.post("/analyze-image", response_model=FoodAnalysisResponse)
async def analyze_food_image(file: UploadFile = File(...)):
    """Analyze uploaded food image with Gemini Vision and return macro estimates."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )

    settings = get_settings()
    if not settings.gemini_api_key:
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
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            [
                prompt,
                {
                    "mime_type": file.content_type or "image/jpeg",
                    "data": image_bytes,
                },
            ]
        )

        payload = _extract_json_payload(response.text or "")

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

    confidence = _safe_float(payload.get("confidence"), default=0.75)
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0

    return FoodAnalysisResponse(
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
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
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

    product = data.get("product") or {}
    nutriments = product.get("nutriments") or {}

    product_name = str(product.get("product_name") or "Unknown product")
    brand = str(product.get("brands") or "Unknown brand")
    serving_size = str(product.get("serving_size") or "100 g")

    serving_grams = _extract_serving_grams(serving_size)
    factor = (serving_grams / 100.0) if serving_grams and serving_grams > 0 else 1.0

    calories_per_100g = _safe_float(nutriments.get("energy-kcal_100g"), default=0.0)
    protein_per_100g = _safe_float(nutriments.get("proteins_100g"), default=0.0)
    carbs_per_100g = _safe_float(nutriments.get("carbohydrates_100g"), default=0.0)
    fat_per_100g = _safe_float(nutriments.get("fat_100g"), default=0.0)
    sat_fat_per_100g = _safe_float(nutriments.get("saturated-fat_100g"), default=0.0)

    calories = int(round(calories_per_100g * factor))
    protein_grams = round(protein_per_100g * factor, 2)
    carbs_grams = round(carbs_per_100g * factor, 2)
    fat_grams = round(fat_per_100g * factor, 2)
    saturated_fat_per_serving = round(sat_fat_per_100g * factor, 2)

    is_cardiac_friendly = saturated_fat_per_serving <= 5.0
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