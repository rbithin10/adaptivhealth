"""Quick test to verify ML model loads correctly."""

from app.services.ml_prediction import get_ml_service

# Try loading the model
ml_service = get_ml_service()

if ml_service.is_loaded:
    print("✅ SUCCESS: ML model loaded!")
    print(f"   Model loaded: {ml_service.is_loaded}")
    print(f"   Feature columns: {len(ml_service.feature_columns)} columns")
    
    # Try a test prediction
    print("\n🧪 Testing prediction with sample data...")
    result = ml_service.predict_risk(
        age=65,
        baseline_hr=70,
        max_safe_hr=155,
        avg_heart_rate=120,
        peak_heart_rate=130,
        min_heart_rate=68,
        avg_spo2=96,
        duration_minutes=30,
        recovery_time_minutes=5,
        activity_type="walking"
    )
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Recommendation: {result['recommendation']}")
    print("\n✅ /api/v1/predict/risk endpoint should now work!")
else:
    print("❌ FAILED: Model did not load")
    print("   Check that ml_models/ folder has all required files")
    print("   Expected files: risk_model.pkl, scaler.pkl, feature_columns.json")
