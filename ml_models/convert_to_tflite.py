"""
Convert scikit-learn Random Forest → edge-compatible format for Flutter.

This script exports the trained risk_model.pkl into:
  1. tree_ensemble.json   — Decision tree data for pure-Dart inference
  2. scaler_params.json   — StandardScaler mean/scale for normalization
  3. edge_model_metadata.json — Version, features, thresholds
  4. risk_model.tflite    — TFLite model (optional, for tflite_flutter plugin)

The PRIMARY approach is tree_ensemble.json (pure Dart, zero native deps).
The TFLite file is an optional optimization for later.

USAGE:
    cd ml_models
    pip install joblib numpy scikit-learn
    python convert_to_tflite.py

OUTPUT FILES → copied to mobile-app/assets/ml_models/
"""

import json
import joblib
import numpy as np
from pathlib import Path

# ============================================================================
# Paths
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "risk_model.pkl"
SCALER_PATH = BASE_DIR / "scaler.pkl"
FEATURES_PATH = BASE_DIR / "feature_columns.json"
METADATA_PATH = BASE_DIR / "model_metadata.json"

# Output paths
TREE_OUTPUT = BASE_DIR / "tree_ensemble.json"
SCALER_OUTPUT = BASE_DIR / "scaler_params.json"
EDGE_META_OUTPUT = BASE_DIR / "edge_model_metadata.json"

# Flutter assets destination
FLUTTER_ASSETS_DIR = BASE_DIR.parent / "mobile-app" / "assets" / "ml_models"


def main():
    print("=" * 60)
    print("AdaptivHealth: Random Forest → Edge AI Export")
    print("=" * 60)

    # ----------------------------------------------------------------
    # Step 1: Load model artifacts
    # ----------------------------------------------------------------
    print("\n[1/4] Loading model artifacts...")
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    with open(FEATURES_PATH, "r") as f:
        feature_columns = json.load(f)

    print(f"  Model: {type(model).__name__} with {model.n_estimators} trees")
    print(f"  Features: {len(feature_columns)}")
    print(f"  Classes: {list(model.classes_)}")

    # ----------------------------------------------------------------
    # Step 2: Export scaler parameters
    # ----------------------------------------------------------------
    print("\n[2/4] Exporting scaler parameters...")
    scaler_params = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "feature_columns": feature_columns,
        "n_features": len(feature_columns),
    }
    with open(SCALER_OUTPUT, "w") as f:
        json.dump(scaler_params, f, indent=2)
    print(f"  Saved: {SCALER_OUTPUT.name} ({SCALER_OUTPUT.stat().st_size:,} bytes)")

    # ----------------------------------------------------------------
    # Step 3: Export decision trees as JSON for pure-Dart inference
    # ----------------------------------------------------------------
    print("\n[3/4] Exporting decision tree ensemble...")
    trees = []
    for i, estimator in enumerate(model.estimators_):
        tree = estimator.tree_

        # Normalize leaf values to probabilities (sum to 1.0 per leaf)
        raw_values = tree.value.copy()
        sums = raw_values.sum(axis=2, keepdims=True)
        sums[sums == 0] = 1  # Avoid division by zero
        norm_values = (raw_values / sums).tolist()

        # Replace NaN thresholds (sklearn uses NaN for leaf nodes in some
        # versions) with -2.0 (TREE_UNDEFINED) so the JSON is strictly valid.
        import math
        thresholds = [
            -2.0 if math.isnan(v) else v
            for v in tree.threshold.tolist()
        ]

        trees.append({
            "feature": tree.feature.tolist(),
            "threshold": thresholds,
            "children_left": tree.children_left.tolist(),
            "children_right": tree.children_right.tolist(),
            "value": norm_values,
        })

    ensemble = {
        "n_estimators": model.n_estimators,
        "n_classes": len(model.classes_),
        "classes": [int(c) for c in model.classes_],
        "trees": trees,
    }

    with open(TREE_OUTPUT, "w") as f:
        json.dump(ensemble, f)  # No indent to save space
    tree_size = TREE_OUTPUT.stat().st_size
    print(f"  Saved: {TREE_OUTPUT.name} ({tree_size:,} bytes / {tree_size/1024:.0f} KB)")

    # Validate: compare Dart-style inference vs sklearn predict_proba
    print("  Validating inference accuracy...")
    _validate_ensemble(model, scaler, feature_columns, trees)

    # ----------------------------------------------------------------
    # Step 4: Generate edge model metadata
    # ----------------------------------------------------------------
    print("\n[4/4] Generating metadata...")
    metadata = {}
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)

    edge_metadata = {
        "model_name": "RandomForest",
        "model_version": metadata.get("version", "1.0"),
        "accuracy": metadata.get("accuracy", "unknown"),
        "n_features": len(feature_columns),
        "feature_columns": feature_columns,
        "classes": [int(c) for c in model.classes_],
        "n_estimators": model.n_estimators,
        "risk_thresholds": {
            "high": 0.80,
            "moderate": 0.50,
            "low": 0.0,
        },
        "alert_thresholds": {
            "hr_critical_high": 180,
            "hr_warning_high": 150,
            "hr_critical_low": 40,
            "hr_warning_low": 50,
            "spo2_critical": 88,
            "spo2_warning": 92,
            "bp_systolic_critical": 180,
            "bp_systolic_warning": 160,
        },
    }
    with open(EDGE_META_OUTPUT, "w") as f:
        json.dump(edge_metadata, f, indent=2)
    print(f"  Saved: {EDGE_META_OUTPUT.name}")

    # ----------------------------------------------------------------
    # Copy to Flutter assets
    # ----------------------------------------------------------------
    print("\n  Copying to Flutter assets...")
    FLUTTER_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    import shutil
    for src in [TREE_OUTPUT, SCALER_OUTPUT, EDGE_META_OUTPUT]:
        shutil.copy2(src, FLUTTER_ASSETS_DIR / src.name)

    total_size = sum(
        (FLUTTER_ASSETS_DIR / f.name).stat().st_size
        for f in [TREE_OUTPUT, SCALER_OUTPUT, EDGE_META_OUTPUT]
    )

    print(f"\n{'=' * 60}")
    print(f"  EXPORT COMPLETE")
    print(f"  Total edge AI payload: {total_size:,} bytes ({total_size/1024:.0f} KB)")
    print(f"  Files in: {FLUTTER_ASSETS_DIR}")
    print(f"{'=' * 60}")


def _validate_ensemble(model, scaler, feature_columns, trees):
    """Compare pure-Python tree walk vs sklearn predict_proba."""
    # Generate 10 random test samples
    rng = np.random.RandomState(42)
    n_features = len(feature_columns)

    test_cases = [
        # Normal patient vitals
        {"age": 55, "baseline_hr": 72, "max_safe_hr": 165,
         "avg_heart_rate": 85, "peak_heart_rate": 100, "min_heart_rate": 70,
         "avg_spo2": 97, "duration_minutes": 20, "recovery_time_minutes": 5},
        # High risk patient
        {"age": 68, "baseline_hr": 80, "max_safe_hr": 152,
         "avg_heart_rate": 145, "peak_heart_rate": 165, "min_heart_rate": 90,
         "avg_spo2": 89, "duration_minutes": 30, "recovery_time_minutes": 15},
        # Low risk patient
        {"age": 35, "baseline_hr": 60, "max_safe_hr": 185,
         "avg_heart_rate": 80, "peak_heart_rate": 95, "min_heart_rate": 65,
         "avg_spo2": 99, "duration_minutes": 15, "recovery_time_minutes": 3},
    ]

    from ml_prediction import engineer_features

    max_delta = 0.0
    for case in test_cases:
        features = engineer_features(**case, activity_type="walking")
        feature_array = np.array([[features[col] for col in feature_columns]])
        scaled = scaler.transform(feature_array)

        # Sklearn prediction
        sk_proba = model.predict_proba(scaled)[0]

        # Manual tree walk (same as Dart code)
        total_probs = np.zeros(len(model.classes_))
        for tree_data in trees:
            node = 0
            while tree_data["children_left"][node] != -1:
                feat_idx = tree_data["feature"][node]
                thresh = tree_data["threshold"][node]
                if scaled[0, feat_idx] <= thresh:
                    node = tree_data["children_left"][node]
                else:
                    node = tree_data["children_right"][node]
            leaf_probs = tree_data["value"][node][0]
            total_probs += np.array(leaf_probs)

        manual_proba = total_probs / len(trees)
        delta = abs(sk_proba[1] - manual_proba[1])
        max_delta = max(max_delta, delta)

    if max_delta < 0.001:
        print(f"  ✅ PASSED — Max prediction delta: {max_delta:.6f}")
    else:
        print(f"  ⚠️  WARNING — Max prediction delta: {max_delta:.6f} (>0.001)")
