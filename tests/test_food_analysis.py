"""
Tests for food analysis endpoints.

Covers image analysis and barcode lookup endpoints with mocked external services.
"""

import os
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-thats-long-enough-32chars")
os.environ.setdefault("DEBUG", "true")

from app.main import app as fastapi_app


@pytest.fixture
def client():
    return TestClient(fastapi_app)


class _FakeSettings:
    gemini_api_key = "test-gemini-key"


class _FakeGenerateResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeGenModel:
    def __init__(self, _model_name: str):
        pass

    def generate_content(self, _parts):
        return _FakeGenerateResponse(
            '{"food_name":"Oatmeal","estimated_calories":220,"protein_grams":8,'
            '"carbs_grams":40,"fat_grams":4,"is_cardiac_friendly":true,'
            '"cardiac_notes":"Low saturated fat","confidence":0.9}'
        )


class _FakeGenAi:
    @staticmethod
    def configure(api_key: str):
        assert api_key == "test-gemini-key"

    GenerativeModel = _FakeGenModel


class _FakeHttpResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "product": {
                "product_name": "Heart Oats",
                "brands": "Adaptiv Foods",
                "serving_size": "40 g",
                "nutriments": {
                    "energy-kcal_100g": 380,
                    "proteins_100g": 10,
                    "carbohydrates_100g": 65,
                    "fat_100g": 7,
                    "saturated-fat_100g": 1.2,
                },
            }
        }


class _FakeAsyncClient:
    def __init__(self, timeout: float):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, _url: str):
        return _FakeHttpResponse()


def test_analyze_food_image_success(client, monkeypatch):
    """Image endpoint returns parsed macro estimates when Gemini returns JSON."""
    monkeypatch.setattr("app.api.food_analysis.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.api.food_analysis.genai", _FakeGenAi)

    files = {"file": ("food.jpg", b"fake-image-bytes", "image/jpeg")}
    response = client.post("/api/v1/food/analyze-image", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["food_name"] == "Oatmeal"
    assert payload["calories"] == 220
    assert payload["is_cardiac_friendly"] is True
    assert payload["confidence"] == 0.9


def test_barcode_lookup_success(client, monkeypatch):
    """Barcode endpoint returns product nutrition and cardiac guidance."""
    monkeypatch.setattr("app.api.food_analysis.httpx.AsyncClient", _FakeAsyncClient)

    response = client.get("/api/v1/food/barcode/1234567890123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_name"] == "Heart Oats"
    assert payload["brand"] == "Adaptiv Foods"
    assert payload["is_cardiac_friendly"] is True
    assert payload["calories"] > 0
