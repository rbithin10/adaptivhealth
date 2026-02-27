# ML Model Troubleshooting Guide

**Issue**: Dashboard shows "Some data failed to load: anomaly detection, trend forecast, baseline optimization, recommendation ranking" and ML features don't work.

**Root Cause**: The backend ML model failed to load on startup, causing all advanced ML endpoints to return 503 (Service Unavailable) errors.

---

## Quick Fix

### Step 1: Verify Model Files Exist

Check that these files are present in the `ml_models/` directory:

```bash
ml_models/
├── risk_model.pkl           # Trained Random Forest model
├── scaler.pkl               # Feature scaler
├── feature_columns.json     # Feature names in correct order
├── scaler_params.json       # Optional: scaler parameters
└── model_metadata.json      # Optional: model training metadata
```

**Verify with**:
```bash
dir ml_models\*.pkl          # Windows
ls -l ml_models/*.pkl        # Linux/Mac
```

You should see:
- `risk_model.pkl` (~500 KB)
- `scaler.pkl` (~5 KB)
- `feature_columns.json` (~500 bytes)

### Step 2: Check Backend Logs

When you start the backend, check the startup log for these messages:

```bash
python start_server.py
```

**Expected (success)**:
```
INFO: ML model loaded successfully at startup
```

**Problem indicators**:
```
WARNING: ML model failed to load - prediction endpoints will return 503
WARNING: ML model loading skipped due to error: <error message>
```

Common errors:
- `FileNotFoundError: risk_model.pkl not found` → Model files missing
- `ModuleNotFoundError: No module named 'sklearn'` → scikit-learn not installed
- `ValueError: Unknown format` → Wrong scikit-learn version

### Step 3: Verify scikit-learn Version

The model was trained with **scikit-learn 1.8.0** and requires this exact version:

```bash
pip show scikit-learn
```

Should show:
```
Name: scikit-learn
Version: 1.8.0
```

**If version is wrong**:
```bash
pip install scikit-learn==1.8.0
```

### Step 4: Restart Backend

After fixing any issues:

```bash
python start_server.py
```

Watch for "ML model loaded successfully at startup" message.

---

## Dashboard Changes (Already Implemented)

The dashboard has been updated to handle ML model unavailability gracefully:

### 1. No More Error Messages for Optional Features

**Before**:
```
❌ Some data failed to load: anomaly detection, trend forecast, baseline optimization, recommendation ranking
```

**After**:
- Advanced ML features silently hide when unavailable
- Only core features (vitals, alerts, activities) show errors if they fail
- Advanced ML panels show helpful setup instructions instead

### 2. Helpful Messages in UI

**Anomaly Detection Panel** now shows:
```
⚠️ Advanced ML features unavailable

The backend ML model is not loaded. To enable anomaly detection and other advanced features:

• Check backend logs for model loading errors
• Ensure ml_models/ folder contains: risk_model.pkl, scaler.pkl, feature_columns.json
• Restart backend: python start_server.py
```

**Trend Forecast Panel** shows:
```
💡 Trend forecasting requires ML model to be loaded on backend.
See anomaly detection panel above for setup instructions.
```

### 3. Better Error Handling for Buttons

**"Explain Risk Using Latest Vitals" button**:
- Shows alert with clear message if model not loaded:
  ```
  ML model not loaded on backend. Please check backend logs and restart
  with model files present in ml_models/ folder.
  ```

**"Run AI Assessment" button**:
- Shows error message in UI (not alert):
  ```
  ML model not loaded on backend. Check backend logs, ensure model files
  exist in ml_models/, and restart the backend.
  ```

---

## Testing After Fix

### 1. Test Backend Endpoints

**Check model status**:
```bash
curl http://localhost:8080/api/v1/predict/status
```

Should return `200 OK` (not 503).

**Test risk prediction**:
```bash
curl -X POST http://localhost:8080/api/v1/predictions/risk \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "heart_rate": 85,
    "spo2": 97,
    "systolic_bp": 120,
    "diastolic_bp": 80
  }'
```

Should return risk assessment (not 503 error).

### 2. Test Dashboard Features

1. **Login** to web dashboard
2. **Navigate** to patient detail page
3. **Check** that advanced ML panels now show data or instructions
4. **Click** "Run AI Assessment" → Should compute risk successfully
5. **Click** "Explain Risk Using Latest Vitals" → Should show feature importance

---

## Architecture Overview

### How ML Model Loading Works

```
Backend Startup (main.py)
    ↓
lifespan() context manager
    ↓
load_ml_model() from services/ml_prediction.py
    ↓
Loads: risk_model.pkl, scaler.pkl, feature_columns.json
    ↓
Stores in module-level globals: model, scaler, feature_columns
    ↓
is_model_loaded() checks if all 3 are non-None
```

### Advanced ML Endpoints

All these endpoints check `if not service.is_loaded:` and return 503 if model not loaded:

**In `app/api/advanced_ml.py`**:
- `GET /anomaly-detection` - Detect unusual vital patterns
- `GET /trend-forecast` - Predict future vital trends
- `GET /baseline-optimization` - Compute optimal resting HR
- `GET /recommendation-ranking` - A/B test recommendations
- `POST /predict/explain` - SHAP-like feature importance
- `GET /risk-summary/natural-language` - Plain-language risk summary

**In `app/api/predict.py`**:
- `POST /predictions/risk` - Compute risk score (0.0-1.0)

### Dashboard API Calls

**PatientDetailPage.tsx** calls these on load:
```typescript
const results = await Promise.allSettled([
  api.getUserById(userId),
  api.getLatestVitalSignsForUser(userId),
  api.getLatestRiskAssessmentForUser(userId),
  api.getLatestRecommendationForUser(userId),
  api.getAlertsForUser(userId, 1, 5),
  api.getActivitiesForUser(userId, 5, 0),
  api.getVitalSignsHistoryForUser(userId, days, 1, 100),
  
  // Advanced ML (now optional - don't fail page load)
  api.getAnomalyDetection(userId, anomalyHours),
  api.getTrendForecast(userId, days),
  api.getBaselineOptimization(userId, days),
  api.getRankedRecommendation(userId, riskLevel),
  api.getNaturalLanguageRiskSummary(userId),
  api.getRetrainingStatus(),
  api.getRetrainingReadiness(),
]);
```

---

## Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'sklearn'"

**Solution**:
```bash
pip install scikit-learn==1.8.0
```

### Issue 2: "FileNotFoundError: risk_model.pkl not found"

**Solution**:
- Check if `ml_models/` folder exists
- Verify model files are present
- Check file permissions (readable by backend user)

### Issue 3: "ValueError: Unknown format" or "Incompatible version"

**Solution**:
- Model was trained with scikit-learn 1.8.0
- Install exact version: `pip install scikit-learn==1.8.0`
- If persists, retrain model with current scikit-learn version

### Issue 4: Model loads but predictions fail

**Check**:
1. Feature columns match training data (17 features)
2. Feature names in `feature_columns.json` are correct
3. Scaler parameters match training data
4. Input data is valid (no NaN, correct types)

**Debug**:
```python
# In Python shell
from app.services.ml_prediction import is_model_loaded, feature_columns
print(is_model_loaded())  # Should be True
print(feature_columns)    # Should show 17 feature names
```

### Issue 5: Dashboard still shows errors after fixing backend

**Solution**:
- Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
- Clear browser cache
- Check browser console for JavaScript errors
- Verify backend is actually running and responding (check logs)

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Verify all 3 model files present and readable
- [ ] Confirm scikit-learn version matches training (1.8.0)
- [ ] Test model loading on server environment (not just local)
- [ ] Check file paths work with production path structure
- [ ] Verify ML endpoints return 200 (not 503)
- [ ] Test with real patient data (e.g., test@example.com)
- [ ] Confirm advanced ML panels show data in dashboard
- [ ] Check backend logs show "ML model loaded successfully"
- [ ] Document any environment-specific configuration

---

## Related Files

**Backend**:
- `app/main.py` - Startup and lifespan management
- `app/services/ml_prediction.py` - Model loading and prediction logic
- `app/api/advanced_ml.py` - Advanced ML endpoints
- `app/api/predict.py` - Basic risk prediction endpoint

**Dashboard**:
- `web-dashboard/src/pages/PatientDetailPage.tsx` - Patient detail view with ML features
- `web-dashboard/src/services/api.ts` - API client methods

**Model Files**:
- `ml_models/risk_model.pkl` - Trained Random Forest classifier
- `ml_models/scaler.pkl` - StandardScaler for feature normalization
- `ml_models/feature_columns.json` - Feature names in prediction order

**Documentation**:
- `docs/READ_RECEIPTS_IMPLEMENTATION.md` - Recent messaging features
- `MASTER_CHECKLIST.md` - Project completion status
- `.github/copilot-instructions.md` - Project conventions

---

## Summary

**Problem**: ML model not loaded → Advanced ML endpoints return 503 → Dashboard shows errors

**Solution**:
1. ✅ Dashboard updated to handle missing model gracefully
2. ⚠️ Backend needs ML model files + scikit-learn 1.8.0
3. ♻️ Restart backend after fixing model files

**Result**: Dashboard no longer shows errors, provides helpful setup instructions instead.
