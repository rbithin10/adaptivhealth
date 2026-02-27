"""
Tests for Nutrition Entry endpoints.

Verifies CRUD operations for nutrition logging.
"""

import os
import sys
from datetime import datetime, timezone

# Set test environment before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long-for-jwt-signing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_nutrition.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app as fastapi_app
from app.database import Base, get_db
import app.models as app_models
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.models.nutrition import NutritionEntry
from app.services.auth_service import AuthService

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_nutrition.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a new database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with a database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        age=30,
        role=UserRole.PATIENT,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create auth credential
    auth_cred = AuthCredential(
        user_id=user.user_id,
        hashed_password=AuthService.hash_password("testpass123")
    )
    db.add(auth_cred)
    db.commit()
    
    return user


@pytest.fixture(scope="function")
def auth_token(client, test_user):
    """Get authentication token for test user."""
    response = client.post(
        "/api/v1/login",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestNutritionEndpoints:
    """Test nutrition entry endpoints."""
    
    def test_create_nutrition_entry_success(self, client, auth_token):
        """Test successful nutrition entry creation."""
        response = client.post(
            "/api/v1/nutrition",
            json={
                "meal_type": "breakfast",
                "description": "Oatmeal with berries",
                "calories": 350,
                "protein_grams": 12,
                "carbs_grams": 45,
                "fat_grams": 14
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meal_type"] == "breakfast"
        assert data["calories"] == 350
        assert data["protein_grams"] == 12
        assert "entry_id" in data
        assert "timestamp" in data
    
    def test_create_nutrition_entry_minimal(self, client, auth_token):
        """Test nutrition entry with only required fields."""
        response = client.post(
            "/api/v1/nutrition",
            json={
                "meal_type": "snack",
                "calories": 150
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meal_type"] == "snack"
        assert data["calories"] == 150
        assert data["protein_grams"] is None
    
    def test_create_nutrition_entry_unauthorized(self, client):
        """Test that unauthorized access is rejected."""
        response = client.post(
            "/api/v1/nutrition",
            json={
                "meal_type": "lunch",
                "calories": 400
            }
        )
        assert response.status_code == 401
    
    def test_create_nutrition_entry_invalid_meal_type(self, client, auth_token):
        """Test validation of meal type."""
        response = client.post(
            "/api/v1/nutrition",
            json={
                "meal_type": "invalid_meal",
                "calories": 300
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422
    
    def test_create_nutrition_entry_negative_calories(self, client, auth_token):
        """Test validation of calories (must be >= 0)."""
        response = client.post(
            "/api/v1/nutrition",
            json={
                "meal_type": "dinner",
                "calories": -100
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422
    
    def test_get_recent_nutrition_entries_empty(self, client, auth_token):
        """Test getting entries when none exist."""
        response = client.get(
            "/api/v1/nutrition/recent",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []
        assert data["total_count"] == 0
        assert data["limit"] == 5
    
    def test_get_recent_nutrition_entries_with_data(self, client, auth_token, db, test_user):
        """Test getting recent entries."""
        # Create test entries
        for i in range(3):
            entry = NutritionEntry(
                user_id=test_user.user_id,
                meal_type="breakfast" if i == 0 else "lunch",
                calories=300 + i * 50,
                protein_grams=10 + i * 5
            )
            db.add(entry)
        db.commit()
        
        response = client.get(
            "/api/v1/nutrition/recent",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 3
        assert data["total_count"] == 3
        # Should be ordered by timestamp descending
        assert data["entries"][0]["calories"] >= data["entries"][-1]["calories"]
    
    def test_get_recent_nutrition_entries_with_limit(self, client, auth_token, db, test_user):
        """Test limit parameter for recent entries."""
        # Create 10 test entries
        for i in range(10):
            entry = NutritionEntry(
                user_id=test_user.user_id,
                meal_type="snack",
                calories=100 + i * 10
            )
            db.add(entry)
        db.commit()
        
        response = client.get(
            "/api/v1/nutrition/recent?limit=3",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 3
        assert data["total_count"] == 10
        assert data["limit"] == 3
    
    def test_get_recent_nutrition_entries_unauthorized(self, client):
        """Test that unauthorized access to entries is rejected."""
        response = client.get("/api/v1/nutrition/recent")
        assert response.status_code == 401
    
    def test_delete_nutrition_entry_success(self, client, auth_token, db, test_user):
        """Test successful deletion of nutrition entry."""
        # Create entry
        entry = NutritionEntry(
            user_id=test_user.user_id,
            meal_type="dinner",
            calories=500
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        # Delete entry
        response = client.delete(
            f"/api/v1/nutrition/{entry.entry_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 204
        
        # Verify entry is deleted
        deleted_entry = db.query(NutritionEntry).filter(
            NutritionEntry.entry_id == entry.entry_id
        ).first()
        assert deleted_entry is None
    
    def test_delete_nutrition_entry_not_found(self, client, auth_token):
        """Test deletion of non-existent entry."""
        response = client.delete(
            "/api/v1/nutrition/99999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_delete_nutrition_entry_unauthorized(self, client):
        """Test that unauthorized deletion is rejected."""
        response = client.delete("/api/v1/nutrition/1")
        assert response.status_code == 401
    
    def test_user_can_only_access_own_entries(self, client, db):
        """Test that users can only access their own nutrition entries."""
        # Create two users
        user1 = User(email="user1@example.com", name="User 1", age=25, role=UserRole.PATIENT)
        user2 = User(email="user2@example.com", name="User 2", age=30, role=UserRole.PATIENT)
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)
        
        # Create auth credentials
        auth1 = AuthCredential(user_id=user1.user_id, hashed_password=AuthService.hash_password("pass1"))
        auth2 = AuthCredential(user_id=user2.user_id, hashed_password=AuthService.hash_password("pass2"))
        db.add_all([auth1, auth2])
        db.commit()
        
        # Create entries for both users
        entry1 = NutritionEntry(user_id=user1.user_id, meal_type="breakfast", calories=300)
        entry2 = NutritionEntry(user_id=user2.user_id, meal_type="lunch", calories=400)
        db.add_all([entry1, entry2])
        db.commit()
        db.refresh(entry1)
        db.refresh(entry2)
        
        # Login as user1
        login_response = client.post(
            "/api/v1/login",
            data={"username": "user1@example.com", "password": "pass1"}
        )
        token1 = login_response.json()["access_token"]
        
        # User1 should only see their own entries
        response = client.get(
            "/api/v1/nutrition/recent",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["entries"][0]["user_id"] == user1.user_id
        
        # User1 should not be able to delete user2's entry
        response = client.delete(
            f"/api/v1/nutrition/{entry2.entry_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 404  # Returns 404 instead of 403 for security
