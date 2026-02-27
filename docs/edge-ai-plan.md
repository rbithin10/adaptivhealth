# Edge AI Planning Document: AdaptivHealth ML on Device

**Date**: February 22, 2026  
**Status**: Architecture Planning (No Implementation Required)  
**Scope**: Strategic evaluation of ML components for on-device vs cloud deployment

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current ML Component Inventory](#current-ml-component-inventory)
3. [On-Device vs Cloud Evaluation Matrix](#on-device-vs-cloud-evaluation-matrix)
4. [Recommended Deployment Strategy](#recommended-deployment-strategy)
5. [Technical Approach for Flutter Edge ML](#technical-approach-for-flutter-edge-ml)
6. [API Boundaries & Conflict Resolution](#api-boundaries--conflict-resolution)
7. [Phased Implementation Roadmap](#phased-implementation-roadmap)
8. [Risk & Mitigation](#risk--mitigation)
9. [Timeline & Resource Estimates](#timeline--resource-estimates)

---

## Executive Summary

### Vision
AdaptivHealth will eventually deploy a **hybrid edge-cloud ML architecture** where lightweight, latency-critical ML inference runs on patient devices (Flutter mobile app), while heavyweight training, complex analysis, and model updates remain in the cloud backend. This balances:

- **Patient Privacy**: Sensitive vitals can be processed locally without transmission
- **Latency**: Real-time alerts computed instantly without network round trips
- **Offline Capability**: Patients receive guidance even without connectivity
- **Scalability**: Cloud handles personalization, analytics, and continuous learning
- **Safety**: Mission-critical alerts have fallback paths

### Strategic Goal
**Phase 1 (Now–Q2 2026)**: Document and prototype edge ML architecture  
**Phase 2 (Q3–Q4 2026)**: Deploy basic risk scoring and anomaly detection on device  
**Phase 3 (Q1 2027+)**: Full hybrid system with advanced analytics

---

## Current ML Component Inventory

### Deployed ML Services (FastAPI Backend)

| Component | Purpose | Current Location | Model Type | Complexity |
|-----------|---------|------------------|------------|-----------|
| **Risk Prediction** | Cardiac risk 0.0–1.0 from vitals | `app/services/ml_prediction.py` | Random Forest (scikit-learn) | Medium |
| **Anomaly Detection** | Detect abnormal vital patterns | `app/services/anomaly_detection.py` | Statistical/Isolation Forest | Medium |
| **Trend Forecasting** | Predict vital trends (7-day forecast) | `app/services/trend_forecasting.py` | ARIMA / Prophet | Medium-High |
| **Baseline Optimization** | Personalize resting HR baselines | `app/services/baseline_optimization.py` | Time-series analysis | Low-Medium |
| **Explainability (SHAP)** | Explain risk prediction drivers | `app/services/explainability.py` | SHAP values from model | High |
| **Recommendation Ranking** | Rank exercise recommendations | `app/services/recommendation_ranking.py` | Collaborative filtering | High |
| **Retraining Pipeline** | Evaluate and schedule model retraining | `app/services/retraining_pipeline.py` | Model evaluation & orchestration | Medium-High |
| **Natural Language Alerts** | LLM-generated alert text | `app/services/natural_language_alerts.py` | LLM (GPT-3.5 or local) | High |

### API Endpoints Exposing ML

**Core Prediction Endpoints** (`POST /api/v1/predict/risk`, `GET /api/v1/predict/my-risk`):
- Input: Vitals, activity, demographics
- Output: Risk score, confidence, inference time
- Latency: ~100ms typical

**Advanced ML Endpoints** (`GET /api/v1/anomaly-detection`, `GET /api/v1/trend-forecast`, etc.):
- Input: User historical vitals
- Output: Anomalies, trends, explanations
- Latency: 500ms–2s typical

---

## On-Device vs Cloud Evaluation Matrix

### Evaluation Criteria

| Criterion | Description | On-Device? | Cloud? |
|-----------|-------------|-----------|--------|
| **Latency Requirement** | Must complete within real-time window | <50ms = yes | >500ms = cloud |
| **Data Sensitivity** | PHI involved; requires privacy consideration | Yes = candidate | No = cloud OK |
| **Model Size** | Fits in mobile memory (<50MB TF Lite) | <50MB = candidate | >50MB = cloud |
| **Compute Demand** | CPU/GPU resource intensity | Low = candidate | High = cloud |
| **Update Frequency** | How often model retrains | Stable = candidate | Weekly+ = cloud |
| **Offline Need** | Works without network connectivity | Required = candidate | Optional = cloud |
| **Feature Engineering** | Can features be computed locally? | Simple = candidate | Complex = cloud |

### Detailed Component Analysis

#### 1. **Risk Prediction (Random Forest)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | ~5ms inference ✅ | ON-DEVICE CANDIDATE |
| **Model Size** | ~2MB (scikit-learn) → ~1MB (ONNX) ✅ | ON-DEVICE CANDIDATE |
| **Compute** | Tree traversal on 17 features, low CPU ✅ | ON-DEVICE CANDIDATE |
| **Privacy** | Vitals + baseline HR (sensitive) ✅ | ON-DEVICE CANDIDATE |
| **Update Freq** | Retrains monthly, not real-time ✅ | ON-DEVICE CANDIDATE |
| **Offline** | Required for immediate alerts ✅ | ON-DEVICE CANDIDATE |
| **Features** | Engineerable from local vitals ✅ | ON-DEVICE CANDIDATE |

**RECOMMENDATION**: ✅ **TIER 1 PRIORITY FOR ON-DEVICE**  
*Rationale*: Lightweight, fast, privacy-sensitive, essential for offline alerts. Convert scikit-learn Random Forest to ONNX or TensorFlow Lite, package in app.

---

#### 2. **Anomaly Detection (Isolation Forest / Statistical)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | ~20–50ms for single window ✅ | ON-DEVICE CANDIDATE |
| **Model Size** | ~3–5MB (depends on tree depth) ✅ | ON-DEVICE CANDIDATE |
| **Compute** | Isolation trees, moderate CPU ✅ | ON-DEVICE CANDIDATE |
| **Privacy** | Processes only local vitals ✅ | ON-DEVICE CANDIDATE |
| **Update Freq** | Monthly retraining OK ✅ | ON-DEVICE CANDIDATE |
| **Offline** | Essential for real-time anomaly alerts ✅ | ON-DEVICE CANDIDATE |
| **Features** | Statistical features (mean, std, slope) ✅ | ON-DEVICE CANDIDATE |

**RECOMMENDATION**: ✅ **TIER 1 PRIORITY FOR ON-DEVICE**  
*Rationale*: Complements risk prediction, detects sudden abnormalities (e.g., arrhythmias). Simpler logic than full risk model.

---

#### 3. **Baseline Optimization (Time-Series Analysis)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | Batch computation at app startup or nightly ⏱️ | CLOUD PREFERRED |
| **Model Size** | ~1MB (lightweight) ✅ | ON-DEVICE OK |
| **Compute** | Statistical aggregation over weeks of data | CLOUD PREFERRED |
| **Privacy** | Historical vitals (sensitive) ✅ | ON-DEVICE OK |
| **Update Freq** | Recomputed weekly or triggered by activity | CLOUD PREFERRED |
| **Offline** | Not time-critical, sync when available | CLOUD PREFERRED |
| **Features** | Requires full history analysis | CLOUD PREFERRED |

**RECOMMENDATION**: 🟡 **HYBRID (Compute in Cloud, Cache on Device)**  
*Rationale*: Cloud computes optimal baseline periodically; device caches result. Baseline used as input to local risk scoring.

**Implementation**: 
- Cloud endpoint: `GET /api/v1/baseline-optimization?user_id=X` (cached, 24h TTL)
- Mobile caches result locally; falls back to population average baseline

---

#### 4. **Trend Forecasting (ARIMA / Prophet)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | 1–5s per forecast with full history | CLOUD PREFERRED |
| **Model Size** | Prophet: ~50MB serialized 🔴 | CLOUD ONLY |
| **Compute** | Time-series fitting, matrix ops | CLOUD PREFERRED |
| **Privacy** | Processes sensitive historical vitals ✅ | ON-DEVICE OK |
| **Update Freq** | Recomputed daily on new vitals | CLOUD PREFERRED |
| **Offline** | Non-critical; batch job | CLOUD ONLY |
| **Features** | Full history required, complex | CLOUD PREFERRED |

**RECOMMENDATION**: ☁️ **CLOUD ONLY**  
*Rationale*: Model too large, compute too intensive. Useful for clinician dashboards and long-term planning, not real-time alerts.

**Implementation**: 
- Mobile calls `GET /api/v1/trend-forecast?user_id=X&horizon_days=7`
- Cloud returns pre-computed forecast; mobile caches for offline view

---

#### 5. **Explainability (SHAP)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | 500ms–2s per explanation | CLOUD PREFERRED |
| **Model Size** | SHAP computation logic: ~5MB | CLOUD PREFERRED |
| **Compute** | Feature interaction analysis, intensive | CLOUD PREFERRED |
| **Privacy** | Analyzes patient-specific risk | CLOUD PREFERRED |
| **Update Freq** | Computed on-demand | CLOUD PREFERRED |
| **Offline** | Not needed offline | CLOUD ONLY |
| **Features** | Requires full model context | CLOUD ONLY |

**RECOMMENDATION**: ☁️ **CLOUD ONLY (Clinician Feature)**  
*Rationale*: For clinician dashboard only. Not needed on patient mobile app.

**Implementation**: 
- Web dashboard calls `POST /api/v1/predict/explain` for care team review
- Mobile never calls this endpoint

---

#### 6. **Recommendation Ranking (Collaborative Filtering / Bandit)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | ~200ms ranking + DB lookup | CLOUD PREFERRED |
| **Model Size** | Embedding matrix: 10–50MB depending on scale | BORDERLINE |
| **Compute** | Similarity search, A/B test logic | CLOUD PREFERRED |
| **Privacy** | User outcome data aggregated in cloud | CLOUD PREFERRED |
| **Update Freq** | Daily or weekly with new cohort data | CLOUD PREFERRED |
| **Offline** | Can serve cached top-K recommendations | ON-DEVICE OK |
| **Features** | Requires cohort/population data | CLOUD ONLY |

**RECOMMENDATION**: 🟡 **HYBRID (Compute in Cloud, Cache Top-K on Device)**  
*Rationale*: Cloud runs full A/B test engine. Mobile caches top-3 personalized recommendations; updates daily.

**Implementation**:
- Cloud endpoint: `GET /api/v1/recommendation-ranking?user_id=X` (top-5 with scores)
- Mobile caches and rotates through list offline
- Outcome logged when activity completes: `POST /api/v1/recommendation-ranking/outcome`

---

#### 7. **Retraining Pipeline (Model Management)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | Hours to days (batch job) | CLOUD ONLY |
| **Model Size** | Entire training dataset | CLOUD ONLY |
| **Compute** | GPUs, hyperparameter tuning | CLOUD ONLY |
| **Privacy** | Aggregate population analytics | CLOUD ONLY |
| **Update Freq** | Monthly or triggered by data drift | CLOUD ONLY |
| **Offline** | Batch background process | CLOUD ONLY |
| **Features** | Cross-user analytics | CLOUD ONLY |

**RECOMMENDATION**: ☁️ **CLOUD ONLY (Backend Infrastructure)**  
*Rationale*: Backend responsibility. Mobile receives updated models when available.

**Implementation**:
- Backend: `GET /api/v1/model/retraining-status` → tells mobile if new model available
- Mobile checks weekly; downloads if new version (same way web updates)

---

#### 8. **Natural Language Alerts (LLM)**

| Dimension | Evaluation | Verdict |
|-----------|-----------|---------|
| **Latency** | 1–5s for LLM call (GPT-3.5) | CLOUD PREFERRED |
| **Model Size** | LLM: 7B–13B parameters (GB scale) 🔴 | CLOUD ONLY |
| **Compute** | Inference requires GPU | CLOUD ONLY |
| **Privacy** | Summarizes risk-sensitive data | CLOUD PREFERRED |
| **Update Freq** | On-demand per alert | CLOUD ONLY |
| **Offline** | Not critical; queued for later | CLOUD ONLY |
| **Features** | Full context from backend | CLOUD ONLY |

**RECOMMENDATION**: ☁️ **CLOUD ONLY (Care Team Feature)**  
*Rationale*: LLM inference too resource-intensive. Used in clinician dashboards and automated notifications.

**Implementation**:
- Backend generates for clinicians: `POST /api/v1/alerts/natural-language`
- Optional: Mobile receives pre-generated summary from backend for offline viewing

---

### Summary Table: On-Device vs Cloud Decision

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Risk Prediction** | ✅ ON-DEVICE | Real-time alerts, offline critical, small model, fast |
| **Anomaly Detection** | ✅ ON-DEVICE | Complements risk pred, detects sudden changes, offline essential |
| **Baseline Optimization** | 🟡 HYBRID | Cache cloud-computed baseline locally |
| **Trend Forecasting** | ☁️ CLOUD | Too large, clinician/dashboard feature |
| **Explainability (SHAP)** | ☁️ CLOUD | Clinician dashboard only |
| **Recommendation Ranking** | 🟡 HYBRID | Cache top-K locally, compute ranking in cloud |
| **Retraining Pipeline** | ☁️ CLOUD | Backend infrastructure, no mobile involvement |
| **Natural Language Alerts** | ☁️ CLOUD | LLM too large, clinician notification feature |

---

## Recommended Deployment Strategy

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       PATIENT DEVICE (OFFLINE)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FLUTTER APP                                            │ │
│  │ ┌────────────────────────────────────────────────────┐│ │
│  │ │ EDGE ML LAYER (TensorFlow Lite, ONNX Runtime)    ││ │
│  │ │ ┌──────────────────┐  ┌──────────────────────┐   ││ │
│  │ │ │ Risk Prediction  │  │ Anomaly Detection    │   ││ │
│  │ │ │ (Random Forest)  │  │ (Isolation Forest)   │   ││ │
│  │ │ └──────┬───────────┘  └──────┬───────────────┘   ││ │
│  │ │        │ [Real-time vitals]  │                    ││ │
│  │ │        ├──────────────────────┤                    ││ │
│  │ │        │ ALERT GENERATION     │                    ││ │
│  │ │        │ - HIGH_HR            │                    ││ │
│  │ │        │ - LOW_SPO2           │                    ││ │
│  │ │        │ - ANOMALY_DETECTED   │                    ││ │
│  │ │        └──────────────────────┘                    ││ │
│  │ │                                                     ││ │
│  │ │ LOCAL CACHE LAYER                                  ││ │
│  │ │ ┌──────────────────┐  ┌──────────────────────┐   ││ │
│  │ │ │ Baseline HR      │  │ Top-K Recommendations│   ││ │
│  │ │ │ (updated daily)  │  │ (updated daily)      │   ││ │
│  │ │ │ Trend forecast   │  │ Recent anomalies     │   ││ │
│  │ │ └──────────────────┘  └──────────────────────┘   ││ │
│  │ └────────────────────────────────────────────────────┘│ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                        │
└────────────────────┼────────────────────────────────────────┘
                     │ (When Connected)
                     │ Data Sync, Model Updates, Conflict Resolution
                     │
┌────────────────────┴──────────────────────────────────────┐
│              ADAPTIVHEALTH CLOUD BACKEND                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ CLOUD ML SERVICES (FastAPI)                          │ │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────────┐    │ │
│  │ │ Full Risk  │ │ Trend      │ │ Explainability│    │ │
│  │ │ Ensemble   │ │ Forecasting│ │ (SHAP)        │    │ │
│  │ │ (Validation)
│ │ │ (LLM Alerts)    │    │
│  │ └────────────┘ └────────────┘ └────────────────┘    │ │
│  │                                                      │ │
│  │ ┌────────────────────────────────────────────────┐  │ │
│  │ │ RETRAINING PIPELINE (Background Jobs)          │  │ │
│  │ │ - Data aggregation from all devices            │  │ │
│  │ │ - Model drift detection                        │  │ │
│  │ │ - New model training & validation              │  │ │
│  │ │ - Model versioning & deployment               │  │ │
│  │ └────────────────────────────────────────────────┘  │ │
│  │                                                      │ │
│  │ ┌────────────────────────────────────────────────┐  │ │
│  │ │ PERSONALIZATION ENGINE                         │  │ │
│  │ │ - Baseline optimization (cohort + individual)  │  │ │
│  │ │ - Recommendation ranking & A/B testing         │  │ │
│  │ │ - Outcome feedback loop                        │  │ │
│  │ └────────────────────────────────────────────────┘  │ │
│  │                                                      │ │
│  │ ┌────────────────────────────────────────────────┐  │ │
│  │ │ CLINICIAN DASHBOARDS                           │  │ │
│  │ │ - Risk summaries w/ explanations (SHAP)        │  │ │
│  │ │ - Trend analysis                               │  │ │
│  │ │ - Alert management                             │  │ │
│  │ └────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

**Real-Time Alert Detection (Offline)**:
1. Patient device records vitals (HR=155, SpO2=92%)
2. Edge ML instantly runs: Risk Prediction + Anomaly Detection
3. If risk_score > 0.7 or anomaly detected → Show local alert
4. Alert queued for sync when connected

**Daily Sync Flow (When Connected)**:
1. Mobile sends vitals batch to cloud
2. Cloud validates edge predictions vs cloud predictions
3. If mismatch > threshold, flags for clinician review
4. Cloud sends:
   - Updated baseline optimization (if changed)
   - Top-5 personalized recommendations
   - New model versions (if available)
5. Mobile updates local caches

**Clinician Flow** (Cloud + Web):
1. Clinician views patient in dashboard
2. System shows:
   - Cloud-computed risk with SHAP explanations
   - Trend forecasts
   - Recommendations with A/B test results
   - Edge vs Cloud prediction comparison (if mismatch)

---

## Technical Approach for Flutter Edge ML

### Framework Selection

#### Option 1: TensorFlow Lite (Recommended)
- **Pros**: Supporting both Random Forest and Isolation Forest via ONNX then TFLite; excellent Flutter support via `tflite_flutter` plugin
- **Cons**: Model conversion pipeline (scikit-learn → ONNX → TFLite)
- **Target Platforms**: iOS (Core ML interop) + Android (TFLite native)

#### Option 2: ONNX Runtime
- **Pros**: Direct scikit-learn export to ONNX; unified cross-platform
- **Cons**: Larger runtime; fewer Flutter plugins
- **Status**: Emerging Flutter support

#### Option 3: Platform-Specific ML Kits
- **iOS**: Core ML (Apple's native framework)
- **Android**: ML Kit (Google's framework)
- **Cons**: Different models per platform; higher maintenance
- **Use Case**: If iOS-first strategy

**RECOMMENDATION**: **TensorFlow Lite + Flutter Plugin** (`tflite_flutter`)
- Industry standard for mobile ML
- Good documentation for scikit-learn conversion
- Proven performance on Pixel/iPhone

---

### Model Format & Versioning

#### Model Lifecycle

```
1. TRAINING (Cloud)
   scikit-learn Random Forest
   └─ Trained on population cohort data
   └─ Evaluated on validation set
   └─ Version: risk_prediction_v1.2.3

2. EXPORT
   scikit-learn → "risk_prediction_v1.2.3.pkl"
   └─ ONNX converter: onnxmltools.convert_sklearn()
   └─ Output: "risk_prediction_v1.2.3.onnx" (~1.5MB)
   └─ TFLite converter: onnx-tf, then tflite_convert
   └─ Final: "risk_prediction_v1.2.3.tflite" (~1MB)
   └─ Size check: Must be <50MB (target: <10MB for both models)

3. VERSION REGISTRY (Backend)
   POST /api/v1/model/versions
   {
     "model_type": "risk_prediction",
     "version": "1.2.3",
     "tflite_url": "https://cdn.adaptiv.io/models/risk_v1.2.3.tflite",
     "onnx_url": "...",
     "size_bytes": 1024000,
     "checksum_sha256": "abc123...",
     "min_app_version": "2.1.0",
     "released_at": "2026-03-15T10:00:00Z",
     "deprecates": "1.2.2",
     "status": "stable" | "beta" | "deprecated"
   }

4. DEPLOYMENT (Mobile)
   a) Check `GET /api/v1/model/versions/latest?model=risk_prediction`
   b) Compare local version vs latest
   c) If newer available:
      - Download: GET {tflite_url}
      - Verify checksum (SHA256)
      - Atomic swap: move old to backup, use new
      - Log: "Loaded risk_prediction_v1.2.3"
   d) Fallback: If download fails or corrupted, revert to backup
```

#### File Organization (Mobile)

```
Mobile App Storage Structure:
├── ml_models/
│   ├── v1/
│   │   ├── risk_prediction_v1.2.2.tflite (current)
│   │   ├── anomaly_detection_v1.1.5.tflite (current)
│   │   └── metadata.json
│   ├── v1_backup/
│   │   ├── risk_prediction_v1.2.1.tflite (rollback)
│   │   └── anomaly_detection_v1.1.4.tflite
│   └── pending/
│       └── risk_prediction_v1.2.3.tflite (downloading)
├── ml_runtime.dart (TFLite wrapper)
├── ml_cache.dart (Feature/prediction caching)
└── ml_version.dart (Version management)
```

---

### On-Device ML Execution Layer (Proposed)

```dart
// lib/services/edge_ml_service.dart

import 'package:tflite_flutter/tflite_flutter.dart';

class EdgeMLService {
  late Interpreter _riskPredictor;
  late Interpreter _anomalyDetector;
  late Map<String, dynamic> _modelMetadata;

  Future<void> initialize() async {
    // Load models from secure storage
    _riskPredictor = await Interpreter.fromAsset(
      'assets/ml_models/risk_prediction_v1.2.3.tflite'
    );
    _anomalyDetector = await Interpreter.fromAsset(
      'assets/ml_models/anomaly_detection_v1.1.5.tflite'
    );
    
    // Load feature engineering config
    _modelMetadata = await _loadMetadata();
  }

  /// Compute risk score from vitals (10ms typical)
  Future<RiskPredictionResult> predictRisk({
    required int age,
    required int baselineHR,
    required int maxSafeHR,
    required int avgHeartRate,
    required int peakHeartRate,
    required int minHeartRate,
    required int avgSpO2,
    required int durationMinutes,
    required int recoveryTimeMinutes,
  }) async {
    try {
      // 1. Engineer features locally
      final features = _engineerFeatures(
        age: age,
        baselineHR: baselineHR,
        // ... other params
      );

      // 2. Run inference on TFLite model
      final output = List<List<double>>.filled(1, List.filled(2, 0));
      _riskPredictor.run(features, output);

      // 3. Interpret output: [probability_low, probability_high]
      final riskScore = output[0][1]; // Prob of high risk
      final riskLevel = _classifyRisk(riskScore);
      
      // 4. Return result
      return RiskPredictionResult(
        riskScore: riskScore,
        riskLevel: riskLevel,
        inferenceTimeMs: _stopwatch.elapsedMilliseconds,
        modelVersion: '1.2.3',
        source: 'edge',
      );
    } catch (e) {
      logger.error('Risk prediction failed: $e');
      // Fallback: return neutral score, notify cloud
      return _getFallbackRisk();
    }
  }

  /// Detect anomalies in recent vitals (20ms typical)
  Future<AnomalyDetectionResult> detectAnomalies({
    required List<VitalWindow> recentVitals, // Last 5 minutes
  }) async {
    try {
      // Similar pattern: feature engineering → inference → interpretation
      final features = _prepareAnomalyFeatures(recentVitals);
      final output = List<List<double>>.filled(1, List.filled(1, 0));
      _anomalyDetector.run(features, output);

      final anomalyScore = output[0][0];
      final isAnomaly = anomalyScore > 0.7; // Threshold
      
      return AnomalyDetectionResult(
        isAnomalyDetected: isAnomaly,
        anomalyScore: anomalyScore,
        anomalyType: _classifyAnomaly(recentVitals, anomalyScore),
        inferenceTimeMs: _stopwatch.elapsedMilliseconds,
        modelVersion: '1.1.5',
        source: 'edge',
      );
    } catch (e) {
      logger.error('Anomaly detection failed: $e');
      return _getFallbackAnomaly();
    }
  }

  /// Feature engineering (offline, reproducible)
  Map<String, double> _engineerFeatures({
    required int age,
    required int baselineHR,
    // ... other vitals
  }) {
    // Same 17 features as backend ML service
    final hrPercentOfMax = peakHeartRate / maxSafeHR;
    final hrReserve = maxSafeHR - baselineHR;
    // ... compute all 17 features identically to backend
    
    return {
      'age': age.toDouble(),
      'hr_pct_of_max': hrPercentOfMax,
      'hr_reserve': hrReserve.toDouble(),
      // ... all 17 features
    };
  }
}

// Entry point for VitalSigns processing
class DeviceVitalProcessor {
  final EdgeMLService _edgeML;
  
  Future<LocalAlertDecision> processVital(VitalSignRecord vital) async {
    // 1. Run edge ML
    final riskPred = await _edgeML.predictRisk(...vital);
    final anomalyDet = await _edgeML.detectAnomalies([vital]);

    // 2. Decide: Should we show an alert?
    if (riskPred.riskScore > 0.75 || anomalyDet.isAnomalyDetected) {
      return LocalAlertDecision(
        shouldAlert: true,
        severity: _determineSeverity(riskPred, anomalyDet),
        title: _alertTitle(riskPred),
        message: _alertMessage(riskPred),
        recommendations: _localRecommendations(riskPred),
      );
    }

    return LocalAlertDecision(shouldAlert: false);
  }
}
```

---

### Model Update Mechanism

#### Update Trigger
- Weekly automatic check: `GET /api/v1/model/versions/latest`
- Manual check on app open (if last check >7 days ago)
- User-initiated: Settings → Advanced → Check for ML Model Updates

#### Download & Verification
```dart
class MLModelUpdateService {
  Future<void> checkAndUpdateModels() async {
    try {
      // 1. Check latest versions
      final versions = await apiClient.getLatestModelVersions([
        'risk_prediction',
        'anomaly_detection',
      ]);

      // 2. For each outdated model, download and verify
      for (final modelSpec in versions) {
        if (!_isLocalVersionCurrent(modelSpec.version)) {
          await _downloadAndVerifyModel(modelSpec);
        }
      }

      // 3. Atomic swap: old → backup, new → active
      await _activateModels();
    } catch (e) {
      logger.warn('Model update check failed, will retry later: $e');
      // On failure, keep using current models
    }
  }

  Future<void> _downloadAndVerifyModel(ModelVersion spec) async {
    // Download to temp location
    final tempPath = await _downloadFile(spec.tfliteUrl);
    
    // Verify checksum
    final actual = await _sha256(tempPath);
    if (actual != spec.checksumSha256) {
      throw Exception('Checksum mismatch: $actual vs ${spec.checksumSha256}');
    }

    // Move to pending folder
    await File(tempPath).rename(_pendingPath(spec));
  }

  Future<void> _activateModels() async {
    // Only swap if ALL models are ready
    // If swap fails midway, keep old models
    final transaction = await _newModelTransaction();
    try {
      transaction.moveModelToActive('risk_prediction');
      transaction.moveModelToActive('anomaly_detection');
      transaction.commit();
    } catch (e) {
      transaction.rollback();
      rethrow;
    }
  }
}
```

---

### Fallback Behavior

**Scenario 1: Model Load Fails**
```dart
// At app startup
EdgeMLService edgeML = ...;
try {
  await edgeML.initialize();
  isEdgeMLReady = true;
} catch (e) {
  logger.error('Edge ML init failed: $e');
  isEdgeMLReady = false;
  // Fall back to cloud-only predictions
}

// Later, when processing vitals
if (isEdgeMLReady) {
  final edgeResult = await edgeML.predictRisk(...);
} else {
  // Cloud fallback
  final cloudResult = await apiClient.predictRisk(...);
}
```

**Scenario 2: Inference Crashes**
```dart
Future<RiskResult> predictRisk(...) async {
  if (!isEdgeMLReady) {
    return await _cloudFallback();
  }

  try {
    return await edgeML.predictRisk(...);
  } catch (e) {
    logger.error('Edge prediction crashed: $e');
    // Mark as unhealthy
    isEdgeMLReady = false;
    // Log to analytics for backend investigation
    await analytics.logEdgeMLFailed(exception: e);
    // Fall back to cloud
    return await _cloudFallback();
  }
}
```

**Scenario 3: Device Offline, No Recent Cache**
```dart
// When submitting vitals but offline
final vital = VitalSignRecord(...);

// Try edge ML
if (isEdgeMLReady) {
  final edgePred = await edgeML.predictRisk(...);
  vital.edgeRiskScore = edgePred.riskScore;
  // Queue sync when online
} else {
  // No model, no connection → neutral score
  vital.riskScore = null;
  vital.syncNeeded = true;
}

showAlert(vital); // Based on thresholds
```

---

## API Boundaries & Conflict Resolution

### Server-Device Data Contract

#### Data Sent from Mobile to Cloud

**Periodic Sync** (Every 15 minutes or on manual sync):
```json
POST /api/v1/sync/vitals-and-predictions
{
  "device_id": "flutter_app_xyz",
  "timestamp": "2026-03-15T14:30:00Z",
  "app_version": "2.1.4",
  "vitals_batch": [
    {
      "timestamp": "2026-03-15T14:25:00Z",
      "heart_rate": 155,
      "spo2": 92,
      "systolic_bp": 145,
      "diastolic_bp": 85,
      "edge_risk_score": 0.74,
      "edge_anomaly_detected": true,
      "edge_model_versions": {
        "risk_prediction": "1.2.3",
        "anomaly_detection": "1.1.5"
      },
      "device_alert_shown": "HIGH_HEART_RATE"
    }
  ],
  "model_versions": {
    "risk_prediction": "1.2.3",
    "anomaly_detection": "1.1.5"
  }
}
```

**Outcome Feedback** (When activity completes or event acknowledged):
```json
POST /api/v1/sync/outcomes
{
  "device_id": "flutter_app_xyz",
  "outcomes": [
    {
      "vital_id": "vital_xyz",
      "cloud_risk_score": 0.71,
      "edge_risk_score": 0.74,
      "prediction_mismatch": {
        "delta": 0.03,
        "edge_higher": true
      },
      "actual_outcome": "patient_felt_fine",
      "recommendation_presented": "rest_5_min",
      "recommendation_followed": true,
      "time_to_recovery_seconds": 180
    }
  ]
}
```

#### Data Sent from Cloud to Mobile

**Model Update Notification**:
```json
GET /api/v1/model/versions/latest?models=risk_prediction,anomaly_detection
{
  "models": [
    {
      "model_type": "risk_prediction",
      "version": "1.2.4",
      "tflite_url": "https://cdn.adaptiv.io/models/risk_v1.2.4.tflite",
      "size_bytes": 1048576,
      "checksum_sha256": "def456...",
      "min_app_version": "2.1.0",
      "released_at": "2026-03-14T10:00:00Z",
      "status": "stable",
      "changelog": "Improved sensitivity to atrial fibrillation patterns"
    }
  ]
}
```

**Personalization Cache**:
```json
GET /api/v1/baseline-optimization?user_id=X
{
  "optimized_baseline_hr": 62,
  "confidence": 0.92,
  "data_points_used": 1247,
  "last_updated": "2026-03-14T10:00:00Z",
  "recommendation": "Rest HR now estimated at 62 (was 60); adjust settings"
}

GET /api/v1/recommendation-ranking?user_id=X
{
  "recommendations": [
    {
      "rank": 1,
      "exercise_type": "walking",
      "target_hr_zone": "moderate",
      "duration_minutes": 20,
      "confidence": 0.85,
      "ab_test_variant": "variant_b"
    },
    // ...
  ],
  "last_updated": "2026-03-14T08:00:00Z"
}
```

---

### Conflict Resolution Matrix

#### When Edge and Cloud Predictions Disagree

| Scenario | Edge Score | Cloud Score | Delta | Action | Reason |
|----------|-----------|------------|-------|--------|--------|
| **Risk ↑ Edge** | 0.78 | 0.65 | +0.13 | 🔴 ALERT USER | Edge more sensitive; edge gets priority |
| **Risk ↓ Edge** | 0.55 | 0.72 | -0.17 | 🟡 ALERT (from risk ↑) | Cloud more conservative; sync scores |
| **Minor δ** | 0.70 | 0.72 | -0.02 | ✅ OK | Within tolerance; no action |
| **Model Outdated** | 0.70 (v1.2.2) | 0.65 (v1.2.4) | Unknown | 📥 DOWNLOAD NEW | Update promptly |
| **Feature Mismatch** | Can't compute feature | 0.68 | — | ⚠️ FALLBACK | Cloud value sent to device, cached |
| **Network Error** | 0.70 | — (timeout) | — | ✅ TRUST EDGE | Device shows alert while queuing sync |

#### Resolution Logic

```dart
class ConflictResolution {
  /// Should we override edge prediction with cloud?
  bool shouldOverrideEdge({
    required double edgeScore,
    required double cloudScore,
    required bool isEdgeModelCurrent,
  }) {
    // Never override if edge model is newer than 7 days old
    if (isEdgeModelCurrent) return false;

    // Override only if:
    // 1. Edge model is outdated (>30 days), AND
    // 2. Cloud and edge differ by >20%, AND
    // 3. Cloud is more conservative (lower risk)
    final delta = (cloudScore - edgeScore).abs();
    if (delta > 0.2 && cloudScore < edgeScore) {
      logger.warn('Override: edge=$edgeScore, cloud=$cloudScore, delta=$delta');
      return true;
    }

    return false;
  }

  /// Log discrepancy for model monitoring
  Future<void> logPredictionMismatch({
    required double edgeScore,
    required double cloudScore,
    required String edgeModelVersion,
    required String cloudModelVersion,
  }) async {
    if ((edgeScore - cloudScore).abs() > 0.1) {
      await analytics.logEvent('prediction_mismatch', {
        'edge_score': edgeScore,
        'cloud_score': cloudScore,
        'delta': (cloudScore - edgeScore).abs(),
        'edge_model_v': edgeModelVersion,
        'cloud_model_v': cloudModelVersion,
      });
    }
  }
}
```

#### Debugging Tools (for DevOps/ML Team)

```dart
// Settings → Developer → Edge ML Diagnostics
class EdgeMLDebugPanel {
  void showDebugInfo() {
    print('=== EDGE ML STATUS ===');
    print('Risk Model: $activeRiskPredictorVersion');
    print('Anomaly Model: $activeAnomalyDetectorVersion');
    print('Last Model Check: $lastModelCheckTime');
    print('Inference Latency (avg): ${avgInferenceMs}ms');
    print('Cache Hit Rate: $cacheHitRate');
    
    print('\n=== RECENT PREDICTIONS ===');
    for (final pred in recentPredictions.last(5)) {
      print('Edge: ${pred.edgeScore}, Cloud: ${pred.cloudScore}, Δ: ${pred.delta}');
    }
  }
}
```

---

## Phased Implementation Roadmap

### Phase 1: Foundation & Prototyping (Q2 2026 – 3 months)

**Objective**: Document architecture, build prototypes, validate feasibility.

**Deliverables**:
1. ✅ **Edge AI Strategy Document** (This document)
2. ⏳ **Model Export Pipeline**
   - Automate scikit-learn → ONNX → TFLite conversion
   - Create CI/CD step in model training pipeline
   - Set up model versioning in artifact registry
   - Target: <10MB for both risk model and anomaly model
3. ⏳ **Flutter TFLite Integration POC**
   - Prototype TFLite runtime wrapper in Dart
   - Test inference speed (<50ms for risk pred, <30ms for anomaly)
   - Package as reusable plugin: `edge_ml_service`
4. ⏳ **Feature Engineering Alignment**
   - Ensure mobile feature engineering matches backend exactly
   - Create unit tests comparing mobile vs backend features
   - Document any platform-specific rounding behavior
5. ⏳ **Model Cache & Update Mechanism**
   - Design version registry in backend
   - Build download + checksum verification flow
   - Test atomic model swap (old → backup, new → active)
6. ⏳ **Fallback & Error Handling Design**
   - Document failure scenarios
   - Implement cloud fallback layer
   - Test offline scenarios
7. ⏳ **Performance Profiling**
   - Benchmark TFLite inference on Pixel 6a, iPhone 13, etc.
   - Memory usage during inference
   - Battery impact (inference power draw)
8. ⏳ **Data Sync Protocol Design**
   - Define edge-to-cloud sync message format
   - Design conflict resolution rules
   - Plan analytics/telemetry

**Timeline**: 12 weeks  
**Resources**: 1 ML Engineer (backend), 1 Mobile Engineer (Flutter), 1 DevOps (model pipeline)  
**Success Criteria**:
- Risk model inference <30ms on Pixel 6a
- Anomaly model inference <20ms
- Both models <10MB each
- 100% feature alignment (mobile vs backend)
- Fallback tested on 3+ error scenarios

**Outcome**: Prototypes validated; go/no-go decision for Phase 2

---

### Phase 2: Limited On-Device Deployment (Q3–Q4 2026 – 4 months)

**Objective**: Deploy basic risk scoring and anomaly detection to subset of users.

**Deliverables**:

1. ⏳ **Production Model Export & Versioning**
   - Export current risk_prediction and anomaly_detection models
   - Version as `risk_v1.0.0.tflite`, `anomaly_v1.0.0.tflite`
   - Upload to CDN; create version registry entry

2. ⏳ **Mobile App Integration**
   - Add `EdgeMLService` to production app
   - Integrate at VitalsScreen level
   - Add model download on first launch (async, with fallback)
   - Show local alerts when risk_score > 0.7 or anomaly detected
   - Queue vitals for sync (with edge predictions included)

3. ⏳ **Backend Sync Endpoint**
   - Implement `POST /api/v1/sync/vitals-and-predictions`
   - Accept edge predictions + model versions
   - Validate edge vs cloud predictions
   - Flag mismatches for monitoring

4. ⏳ **Monitoring & Analytics**
   - Track edge vs cloud prediction agreement
   - Monitor inference latency distribution
   - Alert on inference failures
   - Log model version adoption
   - Dashboard: Edge ML Health (agreement %, latency %, errors %)

5. ⏳ **Beta Rollout**
   - Release to 10% of user base in week 1
   - Monitor for 1 week (zero crashes acceptable, >95% inference success rate)
   - Expand to 50% in week 2
   - Full rollout in week 3 if no issues
   - Collect user feedback

6. ⏳ **Fallback Activation**
   - If edge inference success rate drops <90%, auto-fallback to cloud
   - Alert on failure; dispatch hotfix if needed

7. ⏳ **Documentation**
   - Update API docs with sync endpoint
   - Create debugging guide for support team
   - Document troubleshooting for edge ML failures

**Timeline**: 16 weeks  
**Resources**: 2 Mobile Engineers, 1 Backend Engineer, 1 DevOps, 1 QA  
**Success Criteria**:
- <1% crash rate on edge ML
- >95% inference success rate
- Edge vs cloud agreement >90% on risk classification
- Model version adoption >85% within 4 weeks
- <100ms end-to-end latency (vitals captured → alert shown)

**Outcome**: Edge ML running in production on subset; production metrics baseline established

---

### Phase 3: Full Hybrid System (Q1 2027+ – Ongoing)

**Objective**: Expand edge ML to all features; cloud focuses on training and analytics.

**Deliverables**:

1. ⏳ **Extended Edge ML Services**
   - Deploy baseline optimization model (cached locally, computed in cloud)
   - Deploy recommendation ranking (cache top-5, show offline)
   - Deploy trend forecasting visualization (pre-computed in cloud, cached on device)

2. ⏳ **Advanced Features**
   - Personalized anomaly thresholds (learned per user on device)
   - Adaptive alert frequency (shows fewer redundant alerts based on history)
   - Offline workout guidance (uses last known recommendation when offline)

3. ⏳ **Model Personalization**
   - Explore federated learning: send device-side model updates to cloud
   - (Advanced: Train lightweight user-specific models on device, share insights with cloud)

4. ⏳ **Retraining Automation**
   - Collect edge predictions + outcomes from all devices
   - Automated retraining pipeline: weekly evaluation + monthly model updates if drift detected
   - A/B test new model versions on subset before full rollout

5. ⏳ **Explainability on Device**
   - Lightweight SHAP approximation for local explanations
   - Show "Why did I get this alert?" in app

6. ⏳ **User Controls**
   - Settings → Edge ML Preferences
   - "Enable offline alerts" / "Disable offline alerts"
   - "Update models now" / "Wait for Wi-Fi"
   - "Share data with research" (for federated learning)

7. ⏳ **Compliance & Privacy**
   - Audit trail: Which data went to cloud vs processed locally
   - HIPAA compliance: Edge processing doesn't change regulatory requirements
   - Data retention: Edge caches expire after 30 days unless synced

**Timeline**: 12+ weeks (ongoing)  
**Resources**: 2–3 Mobile Engineers, 2–3 Backend/ML Engineers, 1 DevOps  
**Success Criteria**:
- >95% of users have edge ML enabled
- Baseline optimization deployed and cached correctly
- Recommendations show top-5 even when offline
- New models deployed monthly with <5% false positive increase
- Federated learning prototype running on beta cohort

**Outcome**: Fully hybrid system; patients get intelligent alerts with or without connectivity

---

## Risk & Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Model too large for mobile** | Medium | High | Export to ONNX/TFLite early; set hard limit <10MB; if exceeded, rollback to cloud-only |
| **Inference latency >100ms** | Low-Medium | Medium | Profile on Pixel 6a, iPhone 13 in Phase 1; use quantization if needed |
| **Edge/cloud predictions diverge significantly** | Medium | Medium | Implement conflict resolution; flag mismatches; retrain models with aligned data |
| **Model update download fails** | Low | Medium | Implement retry with exponential backoff; keep old model as fallback; notify user to check Wi-Fi |
| **Inference causes app crash** | Low | High | Wrap all TFLite calls in try-catch; auto-disable if crash rate >5%; fallback to cloud |
| **Feature engineering bugs** | Medium | High | Unit tests comparing mobile vs backend features; run A/B tests; monitor agreement % |
| **Old model on device causes alert storm** | Medium | Medium | Deprecation timeline: 30 days support old models; nudge users to update; fallback if outdated |

### Data & Privacy Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Local model file exposed** (if device compromised) | Low | High | Encrypt model files at rest; require OS-level security (encrypted storage on Android/iOS) |
| **Prediction logs contain PHI** | Medium | Medium | Never log raw vitals; only log features/scores; use differential privacy if analyzing trends |
| **Sync failure leaks unsent vitals** | Low | Medium | Encrypt local vital storage; only cache until sync succeeds; auto-delete after 7 days |
| **User opts out of sync** | Low | Medium | Edge ML still works offline; sync is optional but recommended; clear privacy label |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Model becomes stale** (>6 months no update) | Medium | Medium | Auto-download new model monthly; alert if >3 months old; fallback to cloud if too old |
| **N+1 problems with versioning** | Medium | High | Version registry single source of truth; automated testing of export pipeline; manual QA step |
| **Monitoring/alerting not set up** | High | High | Set up Day 1: Edge ML health dashboard; alert on <90% success rate; auto-fallback if <85% |
| **Support team not trained** | Medium | Low | Create debugging guide; log diagnostic info in app; enable remote debugging in Phase 1 |
| **User confusion** (why different alerts?) | Low-Medium | Low | Transparent UI: "Based on your device" vs "From your doctor"; show confidence levels |

### Mitigation Strategy
- **Phase 1**: Prototyping mitigates largest risks; go/no-go before Phase 2
- **Phase 2**: Beta rollout with metrics; auto-fallback if issues detected
- **Phase 3**: Full rollout only after Phase 2 success; federated learning audited by privacy team

---

## Timeline & Resource Estimates

### Phase-by-Phase Allocation

#### Phase 1: Foundation (Q2 2026, 12 weeks)

| Role | Allocation | Key Tasks |
|------|-----------|-----------|
| **Backend ML Engineer** | 100% | Model export pipeline, feature alignment, versioning |
| **Flutter Engineer** | 100% | TFLite wrapper, POC app, performance profiling |
| **ML Ops / DevOps** | 50% | CI/CD for model export, artifact registry, version control |
| **Data Engineer** | 25% | Sync protocol design, analytics schema |

**Effort**: 5.5 FTE-months  
**Budget**: ~$55K-70K (salaries + AWS/GCP for testing)

---

#### Phase 2: Limited Deployment (Q3–Q4 2026, 16 weeks)

| Role | Allocation | Key Tasks |
|------|-----------|-----------|
| **Flutter Engineers** | 150% (2 people) | App integration, UI, testing, beta rollout |
| **Backend Engineer** | 100% | Sync endpoint, validation, conflict resolution |
| **DevOps** | 75% | Monitoring, alerting, model deployment |
| **QA / Test Lead** | 50% | Beta testing, edge case validation |
| **Product / Analytics** | 25% | Monitoring dashboards, user feedback |

**Effort**: 5.5 FTE-months  
**Budget**: ~$60K-75K

---

#### Phase 3: Full System (Q1 2027+, 12+ weeks)

| Role | Allocation | Key Tasks |
|------|-----------|-----------|
| **Flutter Engineers** | 100% (1–2 people) | Advanced features, user controls |
| **ML Engineers** | 100% (1–2 people) | Personalization, federated learning, retraining |
| **Backend Engineers** | 50% | Retraining orchestration, API updates |
| **DevOps** | 50% | Infrastructure for federated learning |

**Effort**: 3.5–5 FTE-months (ongoing)  
**Budget**: ~$40K-60K per phase

---

### Total Investment (Phases 1–3)

| Phase | Timeline | Effort (FTE-months) | Budget (USD) |
|-------|----------|-------------------|-------------|
| **Phase 1** | 12 weeks | 5.5 | ~$60K |
| **Phase 2** | 16 weeks | 5.5 | ~$70K |
| **Phase 3+** | 12+ weeks | 4–5 (ongoing) | ~$50K–65K |
| **TOTAL** | ~10 months | 15–16 FTE-months | ~$180K–195K |

---

## Decision Gates & Go/No-Go Criteria

### Phase 1 → Phase 2 Gate (End of Q2 2026)

**Go Criteria**:
- ✅ Risk model exports to TFLite <10MB
- ✅ Inference latency <50ms on Pixel 6a + iPhone 13
- ✅ 100% feature engineering agreement (mobile vs backend)
- ✅ Model download + checksum verification working
- ✅ 5 fallback scenarios tested, no data loss
- ✅ No blockers from privacy/compliance team

**No-Go Criteria**:
- ❌ Model size >15MB or inference latency >200ms → Fall back to cloud-only strategy
- ❌ Feature engineering bugs found in >3 tests → Delay Phase 2 for debugging
- ❌ TFLite runtime instability → Evaluate alternative frameworks

---

### Phase 2 → Phase 3 Gate (End of Q4 2026)

**Go Criteria**:
- ✅ <1% crash rate during 50% user rollout
- ✅ >95% inference success rate
- ✅ Edge vs cloud agreement >90%
- ✅ User retention unchanged (alerts not causing app uninstalls)
- ✅ <5% false positive rate increase vs baseline

**No-Go Criteria**:
- ❌ Crash rate >2% → Disable edge ML, investigate
- ❌ Agreement <85% → Retrain models or revert to cloud
- ❌ Privacy incident → Pause deployment, audit

---

## Conclusion

This Edge AI plan positions AdaptivHealth for a **hybrid on-device + cloud ML architecture** that:

✅ **Improves UX**: Real-time alerts even when offline  
✅ **Enhances Privacy**: Sensitive vitals processed locally  
✅ **Reduces Latency**: No network round trip for time-critical alerts  
✅ **Scales Cloud**: Focus on personalization, training, analytics  
✅ **Maintains Safety**: Fallback paths, cloud validation, gradual rollout  

**The phased roadmap** balances innovation with risk management, with clear success metrics at each stage.

---

## Appendices

### A. Model Conversion Reference

**Scikit-learn Random Forest → TensorFlow Lite:**

```bash
# Step 1: Export to ONNX
python -c "
import onnxmltools
from sklearn.ensemble import RandomForestClassifier
import joblib

model = joblib.load('risk_model.pkl')
onnx_model = onnxmltools.convert_sklearn(model)
onnxmltools.utils.save_model(onnx_model, 'risk_model.onnx')
"

# Step 2: ONNX to TFLite (requires onnx-tf + tensorflow)
pip install onnx onnx-tf tensorflow

onnx_tf_graph_def -i risk_model.onnx -o risk_model_tf
tflite_convert \
  --saved_model=risk_model_tf \
  --output_file=risk_model.tflite \
  --target_ops=TFLITE_BUILTINS \
  --optimizations=DEFAULT

# Verify size
ls -lh risk_model.tflite  # Target: <2MB
```

### B. Flutter Integration Template

**File**: `lib/services/edge_ml_service.dart`

See earlier code section for full `EdgeMLService` implementation.

### C. API Spec: Model Version Registry

**Endpoint**: `GET /api/v1/model/versions/{model_type}`

**Request**:
```
GET /api/v1/model/versions/risk_prediction?limit=5
```

**Response**:
```json
{
  "models": [
    {
      "version": "1.0.0",
      "status": "stable",
      "released_at": "2026-03-15T10:00:00Z",
      "tflite_url": "https://cdn.adaptiv.io/models/risk_v1.0.0.tflite",
      "size_bytes": 1048576,
      "checksum_sha256": "abc123..."
    }
  ]
}
```

### D. Conflict Resolution Algorithm (Pseudocode)

See earlier `ConflictResolution` class in API Boundaries section.

### E. Deployment Checklist (Phase 2)

- [ ] Risk model exported, tested, <10MB
- [ ] Anomaly model exported, tested, <10MB
- [ ] TFLite runtime wrapper tested on 3+ devices
- [ ] Model version registry endpoint live
- [ ] Mobile app downloads + verifies models
- [ ] Sync endpoint accepts edge predictions
- [ ] Fallback to cloud tested at 5+ error points
- [ ] Monitoring dashboard live (agreement %, latency %)
- [ ] Beta user cohort selected (10%, representative)
- [ ] Feature flag for on/off toggle
- [ ] Runbook for disabling edge ML remotely
- [ ] Support team trained

---

**Document Status**: ✅ **Architecture Planning Complete**  
**Next Step**: Proceed to Phase 1 (Week of March 17, 2026)  
**Owner**: ML + Mobile Engineering Lead  
**Review Cycle**: Quarterly (update as implementation progresses)
