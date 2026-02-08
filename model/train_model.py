"""
Train an improved heart-risk model with clinically realistic data.

v2.0 fixed critical failures (30 BPM classified as low-risk, etc.).

v3.0 improvements:
  - Gradient Boosting ensemble for better probability calibration
  - 4,150+ training samples across 15 clinical scenarios
  - Better moderate-risk coverage (borderline SpO2, mild tachycardia)
  - Hypertension-related risk scenarios
  - Multi-factor gradual decline patterns
  - Improved feature engineering with recovery_hr_ratio

Usage:
    cd <repo-root>
    python model/train_model.py
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Reproducibility
RNG = np.random.RandomState(42)

# Output directory (this script lives inside model/)
MODEL_DIR = Path(__file__).resolve().parent

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


# ---------------------------------------------------------------------------
# Helper: compute derived features (same logic as ml_prediction.py)
# ---------------------------------------------------------------------------

def _engineer(
    age, baseline_hr, max_safe_hr,
    avg_hr, peak_hr, min_hr,
    avg_spo2, duration, recovery,
    activity_type="walking",
):
    hr_pct = peak_hr / max_safe_hr if max_safe_hr > 0 else 0
    hr_elev = avg_hr - baseline_hr
    hr_range = peak_hr - min_hr
    dur_int = duration * hr_pct
    rec_eff = recovery / duration if duration > 0 else 0
    spo2_dev = 98 - avg_spo2
    age_rf = age / 70
    act_map = {"walking": 1, "yoga": 1, "jogging": 2, "cycling": 2, "swimming": 3}
    act_int = act_map.get(activity_type, 2)

    return [
        age, baseline_hr, max_safe_hr,
        avg_hr, peak_hr, min_hr,
        avg_spo2, duration, recovery,
        hr_pct, hr_elev, hr_range,
        dur_int, rec_eff, spo2_dev,
        age_rf, act_int,
    ]


# ---------------------------------------------------------------------------
# Data generation: clinically grounded scenarios
# ---------------------------------------------------------------------------
# Medical reference ranges used:
#   Normal resting HR: 60-100 BPM (AHA)
#   Bradycardia: < 60 BPM; dangerous < 50 BPM
#   Max HR (age-predicted): 220 - age (Tanaka formula)
#   Normal SpO2: 95-100% (WHO)
#   Hypoxemia: < 92% requires intervention
#   Exercise HR zones: 50-85% of max HR is target zone


def _generate_normal_exercise(n: int):
    """Healthy patients exercising within safe parameters."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(20, 70)
        baseline = RNG.randint(58, 82)
        max_safe = 220 - age
        # During exercise HR goes up but stays within safe zone
        avg_hr = RNG.randint(baseline + 10, min(int(0.80 * max_safe), baseline + 60))
        peak_hr = RNG.randint(avg_hr, min(int(0.85 * max_safe), avg_hr + 25))
        min_hr = RNG.randint(max(baseline - 5, 50), baseline + 5)
        spo2 = RNG.randint(95, 100)
        duration = RNG.randint(10, 60)
        recovery = RNG.randint(2, 8)
        act = RNG.choice(["walking", "jogging", "cycling", "swimming", "yoga"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(0)
    return rows, labels


def _generate_normal_resting(n: int):
    """Healthy patients at rest — low risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(20, 75)
        baseline = RNG.randint(58, 85)
        max_safe = 220 - age
        avg_hr = RNG.randint(baseline - 5, baseline + 8)
        peak_hr = RNG.randint(avg_hr, avg_hr + 10)
        min_hr = RNG.randint(max(baseline - 10, 50), baseline)
        spo2 = RNG.randint(96, 100)
        duration = RNG.randint(5, 30)
        recovery = RNG.randint(1, 5)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(0)
    return rows, labels


def _generate_bradycardia(n: int):
    """Dangerously low heart rate — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(30, 85)
        baseline = RNG.randint(55, 80)
        max_safe = 220 - age
        # Abnormally low HR during monitoring
        avg_hr = RNG.randint(28, 48)
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 15, 55))
        min_hr = RNG.randint(max(avg_hr - 10, 20), avg_hr)
        spo2 = RNG.randint(85, 96)
        duration = RNG.randint(5, 40)
        recovery = RNG.randint(5, 20)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(1)
    return rows, labels


def _generate_tachycardia_at_rest(n: int):
    """Resting tachycardia — HR > 100 at rest — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(25, 80)
        baseline = RNG.randint(60, 80)
        max_safe = 220 - age
        avg_hr = RNG.randint(105, 150)
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 30, 200))
        min_hr = RNG.randint(90, avg_hr)
        spo2 = RNG.randint(88, 97)
        duration = RNG.randint(5, 30)
        recovery = RNG.randint(8, 25)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(1)
    return rows, labels


def _generate_exceeded_max_hr(n: int):
    """HR exceeds age-adjusted max during exercise — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(40, 80)
        baseline = RNG.randint(60, 85)
        max_safe = 220 - age
        # Exceed max safe HR
        peak_hr = RNG.randint(max_safe + 5, max_safe + 40)
        avg_hr = RNG.randint(int(0.85 * max_safe), peak_hr)
        min_hr = RNG.randint(baseline - 5, baseline + 15)
        spo2 = RNG.randint(88, 96)
        duration = RNG.randint(15, 60)
        recovery = RNG.randint(10, 25)
        act = RNG.choice(["jogging", "cycling", "swimming"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(1)
    return rows, labels


def _generate_hypoxemia(n: int):
    """Low SpO2 (< 92%) — HIGH risk regardless of HR."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(30, 85)
        baseline = RNG.randint(60, 85)
        max_safe = 220 - age
        avg_hr = RNG.randint(60, 120)
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 20, 160))
        min_hr = RNG.randint(max(avg_hr - 15, 45), avg_hr)
        spo2 = RNG.randint(70, 91)  # Dangerously low
        duration = RNG.randint(5, 40)
        recovery = RNG.randint(5, 20)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(1)
    return rows, labels


def _generate_elderly_high_risk(n: int):
    """Elderly patients with combined risk factors — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(65, 90)
        baseline = RNG.randint(65, 90)
        max_safe = 220 - age
        # Moderate to high HR for age
        avg_hr = RNG.randint(int(0.7 * max_safe), int(0.95 * max_safe))
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 25, max_safe + 15))
        min_hr = RNG.randint(max(baseline - 10, 50), baseline + 5)
        spo2 = RNG.randint(88, 94)  # Borderline low
        duration = RNG.randint(20, 60)
        recovery = RNG.randint(10, 30)
        act = RNG.choice(["walking", "jogging"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(1)
    return rows, labels


def _generate_poor_recovery(n: int):
    """Long recovery time relative to activity — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(40, 80)
        baseline = RNG.randint(65, 85)
        max_safe = 220 - age
        avg_hr = RNG.randint(int(0.65 * max_safe), int(0.85 * max_safe))
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 20, max_safe + 5))
        min_hr = RNG.randint(baseline - 5, baseline + 10)
        spo2 = RNG.randint(90, 96)
        duration = RNG.randint(10, 30)
        # Recovery much longer than exercise
        recovery = RNG.randint(max(duration, 15), min(duration * 3, 60))
        act = RNG.choice(["walking", "jogging", "cycling"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(1)
    return rows, labels


def _generate_moderate_exercise_healthy(n: int):
    """Vigorous but safe exercise in healthy adults — LOW risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(20, 55)
        baseline = RNG.randint(55, 75)
        max_safe = 220 - age
        # High-intensity but within safe zone
        avg_hr = RNG.randint(int(0.65 * max_safe), int(0.80 * max_safe))
        peak_hr = RNG.randint(avg_hr, min(int(0.85 * max_safe), avg_hr + 20))
        min_hr = RNG.randint(max(baseline - 5, 48), baseline + 5)
        spo2 = RNG.randint(95, 100)
        duration = RNG.randint(20, 90)
        recovery = RNG.randint(2, 8)
        act = RNG.choice(["jogging", "cycling", "swimming"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(0)
    return rows, labels


def _generate_athlete_high_intensity(n: int):
    """Athletes with naturally low resting HR doing intense exercise — LOW risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(18, 40)
        baseline = RNG.randint(45, 60)  # Athletic bradycardia is normal
        max_safe = 220 - age
        avg_hr = RNG.randint(int(0.70 * max_safe), int(0.85 * max_safe))
        peak_hr = RNG.randint(avg_hr, min(int(0.90 * max_safe), avg_hr + 20))
        min_hr = RNG.randint(max(baseline - 5, 40), baseline + 5)
        spo2 = RNG.randint(96, 100)
        duration = RNG.randint(30, 120)
        recovery = RNG.randint(1, 5)
        act = RNG.choice(["jogging", "cycling", "swimming"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(0)
    return rows, labels


def _generate_wide_hr_range_risk(n: int):
    """Very wide HR range (arrhythmia indicator) — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(35, 80)
        baseline = RNG.randint(60, 85)
        max_safe = 220 - age
        min_hr = RNG.randint(35, 55)
        peak_hr = RNG.randint(max(140, max_safe - 10), max_safe + 20)
        avg_hr = RNG.randint(min_hr + 20, peak_hr - 10)
        spo2 = RNG.randint(88, 95)
        duration = RNG.randint(10, 40)
        recovery = RNG.randint(8, 25)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(1)
    return rows, labels


# -- v3.0 additions ----------------------------------------------------------

def _generate_borderline_moderate(n: int):
    """Borderline vitals that should be moderate risk, not low or high."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(40, 70)
        baseline = RNG.randint(65, 82)
        max_safe = 220 - age
        # HR slightly above comfortable zone but below danger
        avg_hr = RNG.randint(int(0.78 * max_safe), int(0.88 * max_safe))
        peak_hr = RNG.randint(avg_hr, min(int(0.92 * max_safe), avg_hr + 15))
        min_hr = RNG.randint(max(baseline - 5, 55), baseline + 5)
        spo2 = RNG.randint(92, 95)  # Borderline SpO2
        duration = RNG.randint(20, 50)
        recovery = RNG.randint(6, 14)
        act = RNG.choice(["walking", "jogging", "cycling"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(1)
    return rows, labels


def _generate_mild_tachycardia_resting(n: int):
    """Mild resting tachycardia (100-115 BPM) with otherwise OK vitals — moderate risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(30, 70)
        baseline = RNG.randint(62, 80)
        max_safe = 220 - age
        avg_hr = RNG.randint(100, 115)
        peak_hr = RNG.randint(avg_hr, avg_hr + 15)
        min_hr = RNG.randint(85, avg_hr)
        spo2 = RNG.randint(94, 98)
        duration = RNG.randint(5, 25)
        recovery = RNG.randint(6, 15)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(1)
    return rows, labels


def _generate_gradual_decline(n: int):
    """Simulates gradual fitness decline — slightly elevated everything — HIGH risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(50, 80)
        baseline = RNG.randint(75, 92)  # Higher resting HR indicates deconditioning
        max_safe = 220 - age
        avg_hr = RNG.randint(baseline + 15, min(int(0.85 * max_safe), baseline + 50))
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 20, max_safe + 5))
        min_hr = RNG.randint(baseline - 5, baseline + 5)
        spo2 = RNG.randint(91, 95)
        duration = RNG.randint(10, 30)
        recovery = RNG.randint(12, 30)  # Poor recovery
        act = RNG.choice(["walking", "yoga"])
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, act))
        labels.append(1)
    return rows, labels


def _generate_elderly_safe_walking(n: int):
    """Elderly patients walking gently with good vitals — LOW risk."""
    rows, labels = [], []
    for _ in range(n):
        age = RNG.randint(65, 85)
        baseline = RNG.randint(62, 80)
        max_safe = 220 - age
        avg_hr = RNG.randint(baseline, min(baseline + 20, int(0.65 * max_safe)))
        peak_hr = RNG.randint(avg_hr, min(avg_hr + 10, int(0.70 * max_safe)))
        min_hr = RNG.randint(max(baseline - 8, 50), baseline)
        spo2 = RNG.randint(95, 100)
        duration = RNG.randint(10, 30)
        recovery = RNG.randint(2, 7)
        rows.append(_engineer(age, baseline, max_safe, avg_hr, peak_hr, min_hr, spo2, duration, recovery, "walking"))
        labels.append(0)
    return rows, labels


# ---------------------------------------------------------------------------
# Build the full dataset
# ---------------------------------------------------------------------------

def generate_dataset():
    """Assemble a balanced dataset of clinically realistic scenarios."""
    all_rows, all_labels = [], []

    generators = [
        # Low-risk scenarios (label 0)
        (_generate_normal_exercise, 600),
        (_generate_normal_resting, 400),
        (_generate_moderate_exercise_healthy, 400),
        (_generate_athlete_high_intensity, 200),
        (_generate_elderly_safe_walking, 200),
        # High-risk scenarios (label 1)
        (_generate_bradycardia, 300),
        (_generate_tachycardia_at_rest, 250),
        (_generate_exceeded_max_hr, 300),
        (_generate_hypoxemia, 300),
        (_generate_elderly_high_risk, 200),
        (_generate_poor_recovery, 200),
        (_generate_wide_hr_range_risk, 150),
        (_generate_borderline_moderate, 250),
        (_generate_mild_tachycardia_resting, 200),
        (_generate_gradual_decline, 200),
    ]

    for gen_fn, count in generators:
        rows, labels = gen_fn(count)
        all_rows.extend(rows)
        all_labels.extend(labels)

    X = np.array(all_rows, dtype=np.float64)
    y = np.array(all_labels, dtype=np.int32)

    logger.info("Dataset: %d samples (%d low-risk, %d high-risk)",
                len(y), int((y == 0).sum()), int((y == 1).sum()))
    return X, y


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train():
    logger.info("=" * 60)
    logger.info("Training improved heart-risk model (v3.0)")
    logger.info("=" * 60)

    X, y = generate_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    # Fit scaler (needed for pipeline consistency even though tree models don't require it)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Train Gradient Boosting for better probability calibration
    # GBM produces smoother, more reliable risk scores than RF
    base_clf = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        min_samples_split=10,
        min_samples_leaf=5,
        subsample=0.8,
        random_state=42,
    )
    # Calibrate probabilities with Platt scaling for clinical reliability
    clf = CalibratedClassifierCV(base_clf, cv=5, method="sigmoid")
    clf.fit(X_train_s, y_train)

    # Evaluate
    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    logger.info("\n--- Test-set metrics ---")
    logger.info("Accuracy : %.4f", acc)
    logger.info("Precision: %.4f", prec)
    logger.info("Recall   : %.4f  (critical: must be high to catch real risks)", rec)
    logger.info("F1       : %.4f", f1)
    logger.info("\n%s", classification_report(y_test, y_pred, target_names=["low-risk", "high-risk"]))
    logger.info("Confusion matrix:\n%s", confusion_matrix(y_test, y_pred))

    # Save artefacts
    joblib.dump(clf, MODEL_DIR / "risk_model.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")

    with open(MODEL_DIR / "feature_columns.json", "w") as f:
        json.dump(FEATURE_COLUMNS, f)

    metadata = {
        "model_name": "GradientBoosting",
        "version": "3.0",
        "accuracy": f"{acc * 100:.1f}%",
        "precision": f"{prec * 100:.1f}%",
        "recall": f"{rec * 100:.1f}%",
        "f1_score": f"{f1 * 100:.1f}%",
        "records_used": len(y),
        "train_records": len(y_train),
        "test_records": len(y_test),
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "v3.0: GradientBoosting + calibration; 15 clinical scenarios; "
            "better moderate-risk detection; diet & coaching guidance"
        ),
    }
    with open(MODEL_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("\nModel artefacts saved to %s", MODEL_DIR)
    return clf, scaler, metadata


# ---------------------------------------------------------------------------
# Comparison with existing model
# ---------------------------------------------------------------------------

def compare_models(new_clf, new_scaler):
    """Run clinical scenarios through both old and new models and print comparison."""
    # Try loading old model
    old_model_dir = MODEL_DIR.parent / "ml_models"
    old_model_path = old_model_dir / "risk_model.pkl"
    old_scaler_path = old_model_dir / "scaler.pkl"

    if not old_model_path.exists():
        logger.info("Old model not found at %s — skipping comparison.", old_model_path)
        return

    old_clf = joblib.load(old_model_path)
    old_scaler = joblib.load(old_scaler_path)

    test_cases = [
        {
            "name": "Bradycardia (30 BPM avg, 88% SpO2)",
            "expected": "HIGH",
            "params": (65, 72, 155, 30, 40, 28, 88, 30, 5, "walking"),
        },
        {
            "name": "Normal vitals at rest",
            "expected": "LOW",
            "params": (35, 72, 185, 75, 82, 68, 98, 20, 3, "walking"),
        },
        {
            "name": "70-year-old, HR 160, SpO2 89%",
            "expected": "HIGH",
            "params": (70, 80, 150, 160, 180, 100, 89, 45, 15, "jogging"),
        },
        {
            "name": "Bradycardia (40 BPM, SpO2 90%)",
            "expected": "HIGH",
            "params": (55, 60, 165, 40, 50, 35, 90, 20, 10, "walking"),
        },
        {
            "name": "Healthy jogging (age 28)",
            "expected": "LOW",
            "params": (28, 65, 192, 130, 150, 70, 98, 30, 3, "jogging"),
        },
        {
            "name": "Severe hypoxemia (SpO2 82%)",
            "expected": "HIGH",
            "params": (60, 75, 160, 100, 120, 80, 82, 20, 8, "walking"),
        },
        {
            "name": "Resting tachycardia (HR 130)",
            "expected": "HIGH",
            "params": (50, 72, 170, 130, 145, 120, 94, 10, 15, "walking"),
        },
        {
            "name": "Athlete low resting HR (50 BPM), exercising safely",
            "expected": "LOW",
            "params": (25, 50, 195, 140, 160, 55, 98, 45, 3, "jogging"),
        },
    ]

    logger.info("\n" + "=" * 80)
    logger.info("MODEL COMPARISON: Old vs New (v3.0)")
    logger.info("=" * 80)
    header = f"{'Scenario':<48} {'Expect':>6}  {'Old':>8}  {'New':>8}  {'Fixed?':>6}"
    logger.info(header)
    logger.info("-" * 80)

    old_correct = 0
    new_correct = 0

    for tc in test_cases:
        feats = np.array([_engineer(*tc["params"])], dtype=np.float64)

        old_s = old_scaler.transform(feats)
        old_prob = old_clf.predict_proba(old_s)[0][1]
        old_level = "HIGH" if old_prob >= 0.50 else "LOW"

        new_s = new_scaler.transform(feats)
        new_prob = new_clf.predict_proba(new_s)[0][1]
        new_level = "HIGH" if new_prob >= 0.50 else "LOW"

        expected = tc["expected"]
        old_ok = old_level == expected
        new_ok = new_level == expected
        old_correct += int(old_ok)
        new_correct += int(new_ok)

        fixed = ""
        if not old_ok and new_ok:
            fixed = "✅ YES"
        elif old_ok and new_ok:
            fixed = "— ok"
        elif old_ok and not new_ok:
            fixed = "⚠️ REGR"
        else:
            fixed = "❌ BOTH"

        logger.info(
            f"{tc['name']:<48} {expected:>6}  {old_prob:>7.3f}  {new_prob:>7.3f}  {fixed:>6}"
        )

    logger.info("-" * 80)
    logger.info(f"Old model correct: {old_correct}/{len(test_cases)}")
    logger.info(f"New model correct: {new_correct}/{len(test_cases)}")
    logger.info("=" * 80)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    clf, scaler, meta = train()
    compare_models(clf, scaler)
    logger.info("\nDone. New model artefacts are in: %s", MODEL_DIR)
