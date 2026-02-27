"""
train_tflite_model.py — Train a Keras MLP and convert to TFLite for on-device
cardiac risk prediction in the AdaptivHealth Flutter app.

What this does:
  1. Generates 1,500 synthetic cardiac samples across 4 risk scenarios
  2. Engineers the same 17 features used by the backend (ml_prediction.py)
  3. Trains a small MLP (17→64→32→1 sigmoid) with BatchNorm + Dropout
  4. Converts to TFLite with dynamic-range quantization
  5. Saves scaler_params.json + risk_model.tflite
  6. Copies both files to mobile-app/assets/ml_models/
  7. Runs 4 validation test cases and prints expected vs actual risk levels

Usage:
    pip install tensorflow numpy
    python ml_models/train_tflite_model.py

Expected test case outputs:
    REST       → riskScore < 0.30  → LOW
    WORKOUT    → riskScore 0.35–0.65 (varies with window) → LOW/MODERATE
    PEAK       → riskScore 0.55–0.80 → MODERATE
    EMERGENCY  → riskScore > 0.80  → HIGH
"""

import json
import shutil
from pathlib import Path

import numpy as np

try:
    import tensorflow as tf
except ImportError:
    raise SystemExit(
        "\nTensorFlow not found. Install it with:\n"
        "    pip install tensorflow numpy\n"
        "then re-run this script.\n"
    )

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE_DIR         = Path(__file__).resolve().parent
FLUTTER_ASSETS   = BASE_DIR.parent / "mobile-app" / "assets" / "ml_models"
TFLITE_OUT       = BASE_DIR / "risk_model.tflite"
SCALER_OUT       = BASE_DIR / "scaler_params.json"

# ── Feature columns (must match app/services/ml_prediction.py exactly) ─────────

FEATURE_COLUMNS = [
    "age",
    "baseline_hr",
    "max_safe_hr",
    "avg_heart_rate",
    "peak_heart_rate",
    "min_heart_rate",
    "avg_spo2",
    "duration_minutes",
    "recovery_time_minutes",
    "hr_pct_of_max",
    "hr_elevation",
    "hr_range",
    "duration_intensity",
    "recovery_efficiency",
    "spo2_deviation",
    "age_risk_factor",
    "activity_intensity",
]

ACTIVITY_MAP = {
    "walking": 1, "yoga": 1,
    "jogging": 2, "cycling": 2,
    "swimming": 3,
}


# ── Feature engineering (direct port of ml_prediction.py engineer_features) ────

def engineer_features(
    age, baseline_hr, max_safe_hr,
    avg_hr, peak_hr, min_hr,
    avg_spo2, duration_min, recovery_min,
    activity_type="walking",
):
    """Compute 17 features from raw vitals — identical to backend logic."""
    hr_pct_of_max       = peak_hr / max_safe_hr if max_safe_hr > 0 else 0.0
    hr_elevation        = float(avg_hr - baseline_hr)
    hr_range            = float(peak_hr - min_hr)
    duration_intensity  = duration_min * hr_pct_of_max
    recovery_efficiency = recovery_min / duration_min if duration_min > 0 else 0.0
    spo2_deviation      = float(98 - avg_spo2)
    age_risk_factor     = age / 70.0
    activity_intensity  = float(ACTIVITY_MAP.get(activity_type, 2))

    return [
        float(age), float(baseline_hr), float(max_safe_hr),
        float(avg_hr), float(peak_hr), float(min_hr),
        float(avg_spo2), float(duration_min), float(recovery_min),
        hr_pct_of_max, hr_elevation, hr_range,
        duration_intensity, recovery_efficiency, spo2_deviation,
        age_risk_factor, activity_intensity,
    ]


# ── Synthetic data generation ──────────────────────────────────────────────────

rng = np.random.default_rng(42)


def _gen_batch(n, age_lo, age_hi, base_lo, base_hi,
               avg_pct_lo, avg_pct_hi,
               peak_pct_lo, peak_pct_hi,
               spo2_lo, spo2_hi,
               dur_lo, dur_hi,
               rec_lo, rec_hi,
               activities, label):
    """
    Generate n samples for one risk scenario.

    HR values are expressed as fractions of max_safe_hr (220 - age).
    SpO2, duration, and recovery are drawn from uniform ranges.
    """
    rows, labels = [], []
    for _ in range(n):
        age      = int(rng.integers(age_lo, age_hi))
        baseline = int(rng.integers(base_lo, base_hi))
        max_hr   = 220 - age

        avg_hr   = int(max_hr * rng.uniform(avg_pct_lo,  avg_pct_hi))
        peak_hr  = int(max_hr * rng.uniform(peak_pct_lo, peak_pct_hi))
        min_hr   = max(40, baseline - int(rng.integers(0, 15)))
        avg_hr   = max(min_hr + 1, avg_hr)   # keep ordering valid
        peak_hr  = max(avg_hr, peak_hr)

        spo2     = int(rng.integers(spo2_lo,  spo2_hi))
        dur      = int(rng.integers(dur_lo,   dur_hi))
        rec      = int(rng.integers(rec_lo,   rec_hi))
        act      = rng.choice(activities)

        rows.append(engineer_features(
            age, baseline, max_hr, avg_hr, peak_hr, min_hr,
            spo2, dur, rec, act,
        ))
        labels.append(label)
    return rows, labels


# ── 4 scenarios ── label scheme:
#   0 = low risk  (model learns this is safe)
#   1 = high risk (model learns this is dangerous)
#
# The sigmoid output naturally spreads:
#   extreme label-1 features (emergency)   → score ~0.88–0.99  → HIGH
#   moderate label-1 features (peak)       → score ~0.55–0.80  → MODERATE
#   label-0 features (rest/light workout)  → score ~0.05–0.40  → LOW

rest_rows,   rest_lbl   = _gen_batch(
    500,
    25, 70, 55, 82,
    avg_pct_lo=0.34, avg_pct_hi=0.48,   # avg HR 34–48% of max
    peak_pct_lo=0.44, peak_pct_hi=0.56,  # peak HR 44–56% of max
    spo2_lo=97, spo2_hi=100,
    dur_lo=5, dur_hi=30,
    rec_lo=2, rec_hi=10,
    activities=["walking", "yoga"],
    label=0,
)

light_rows,  light_lbl  = _gen_batch(
    300,
    25, 65, 58, 85,
    avg_pct_lo=0.50, avg_pct_hi=0.65,
    peak_pct_lo=0.62, peak_pct_hi=0.74,
    spo2_lo=94, spo2_hi=99,
    dur_lo=10, dur_hi=45,
    rec_lo=3, rec_hi=15,
    activities=["walking", "jogging"],
    label=0,
)

peak_rows,   peak_lbl   = _gen_batch(
    350,
    30, 70, 60, 88,
    avg_pct_lo=0.74, avg_pct_hi=0.88,   # avg HR 74–88% of max
    peak_pct_lo=0.86, peak_pct_hi=0.96,  # peak HR 86–96% of max
    spo2_lo=90, spo2_hi=96,
    dur_lo=15, dur_hi=55,
    rec_lo=5, rec_hi=22,
    activities=["jogging", "cycling", "swimming"],
    label=1,
)

emerg_rows,  emerg_lbl  = _gen_batch(
    350,
    35, 78, 65, 92,
    avg_pct_lo=0.88, avg_pct_hi=1.05,   # avg HR exceeds safe zone
    peak_pct_lo=0.96, peak_pct_hi=1.12,  # peak HR well above max
    spo2_lo=83, spo2_hi=92,
    dur_lo=8, dur_hi=60,
    rec_lo=3, rec_hi=30,
    activities=["jogging", "swimming"],
    label=1,
)

all_rows   = rest_rows   + light_rows   + peak_rows   + emerg_rows
all_labels = rest_lbl    + light_lbl    + peak_lbl    + emerg_lbl

X = np.array(all_rows,   dtype=np.float32)
y = np.array(all_labels, dtype=np.float32)

# Shuffle
idx = rng.permutation(len(X))
X, y = X[idx], y[idx]

print(f"Dataset: {len(X)} samples  "
      f"(low-risk={int((y==0).sum())}  high-risk={int((y==1).sum())})")

# ── Normalise (numpy StandardScaler equivalent) ────────────────────────────────

mean  = X.mean(axis=0)
scale = X.std(axis=0)
scale[scale == 0] = 1.0          # guard zero-variance columns
X_scaled = (X - mean) / scale

# Save scaler params (same JSON format as convert_to_tflite.py output)
scaler_data = {
    "mean":            mean.tolist(),
    "scale":           scale.tolist(),
    "feature_columns": FEATURE_COLUMNS,
}
with open(SCALER_OUT, "w") as f:
    json.dump(scaler_data, f, indent=2)
print(f"Scaler saved  → {SCALER_OUT}")

# ── Train / validation split ───────────────────────────────────────────────────

split     = int(0.80 * len(X_scaled))
X_tr, X_v = X_scaled[:split], X_scaled[split:]
y_tr, y_v = y[:split], y[split:]

# ── Build Keras MLP ────────────────────────────────────────────────────────────

model = tf.keras.Sequential(
    [
        tf.keras.layers.Input(shape=(17,)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ],
    name="cardiac_risk_mlp",
)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss="binary_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
)

print("\nTraining cardiac risk MLP …")
model.fit(
    X_tr, y_tr,
    validation_data=(X_v, y_v),
    epochs=80,
    batch_size=32,
    verbose=1,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=12, restore_best_weights=True,
        )
    ],
)

_, val_acc, val_auc = model.evaluate(X_v, y_v, verbose=0)
print(f"\nValidation  accuracy={val_acc:.3f}  AUC={val_auc:.3f}")
if val_acc < 0.88:
    print("WARNING: val_accuracy below 0.88 — check training data distribution.")

# ── Convert to TFLite ──────────────────────────────────────────────────────────

converter              = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]   # dynamic-range quant
tflite_bytes           = converter.convert()

with open(TFLITE_OUT, "wb") as f:
    f.write(tflite_bytes)
print(f"TFLite model → {TFLITE_OUT}  ({len(tflite_bytes)/1024:.1f} KB)")

# ── Built-in validation test cases ────────────────────────────────────────────

print("\nValidation test cases:")
print("-" * 60)

def _predict(name, age, baseline, avg_hr, peak_hr, min_hr, spo2,
             dur, rec, act, expected_level):
    max_hr   = 220 - age
    feat     = engineer_features(age, baseline, max_hr, avg_hr, peak_hr,
                                 min_hr, spo2, dur, rec, act)
    feat_arr = np.array(feat, dtype=np.float32)
    scaled   = (feat_arr - mean) / scale
    prob     = float(model.predict(np.array([scaled]), verbose=0)[0][0])
    level    = "high" if prob >= 0.80 else ("moderate" if prob >= 0.50 else "low")
    ok       = "✓" if level == expected_level else "✗"
    print(f"  {ok}  {name:22s}  score={prob:.3f}  ({level})  expected {expected_level}")

# age, baseline, avg_hr, peak_hr, min_hr, spo2, dur, rec, act, expected
_predict("REST",           45, 72, 75,  85,  65, 98, 10, 3,  "walking",  "low")
_predict("WORKOUT steady", 35, 68, 130, 148, 90, 95, 30, 8,  "jogging",  "low")
_predict("WORKOUT peak",   45, 72, 158, 172, 98, 93, 35, 12, "jogging",  "moderate")
_predict("EMERGENCY",      55, 78, 183, 195, 108, 87, 20, 15, "swimming", "high")

print("-" * 60)

# ── Copy files to Flutter assets ───────────────────────────────────────────────

FLUTTER_ASSETS.mkdir(parents=True, exist_ok=True)
shutil.copy(TFLITE_OUT,   FLUTTER_ASSETS / "risk_model.tflite")
shutil.copy(SCALER_OUT,   FLUTTER_ASSETS / "scaler_params.json")

print(f"\nCopied to Flutter assets: {FLUTTER_ASSETS}")
print("  • risk_model.tflite")
print("  • scaler_params.json")
print("\nNext steps:")
print("  cd mobile-app && flutter pub get && flutter run")
