"""
Model retraining pipeline service.

Provides functionality to retrain the ML model with new patient data,
track model versions, and manage model artifacts.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CONSTANTS
#   - MODEL_DIR........................ Line 30  (Path to model files)
#
# FUNCTIONS
#   - evaluate_retraining_readiness().. Line 35  (Check if retrain needed)
#   - get_retraining_status().......... Line 80  (Current model metadata)
#   - trigger_retraining()............. Line 110 (Start retrain job)
#   - _save_model_version()............ Line 135 (Version management)
#
# BUSINESS CONTEXT:
# - Automated model retraining pipeline
# - Minimum 100 records + 7 days since last train
# - Version tracking for audit/rollback
# =============================================================================
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "ml_models"


def evaluate_retraining_readiness(
    new_records_count: int,
    last_retrain_date: Optional[str] = None,
    min_records: int = 100,
    min_days_since_last: int = 7,
) -> Dict[str, Any]:
    """Check if conditions are met to trigger a model retraining."""
    reasons = []
    ready = True

    if new_records_count < min_records:
        ready = False
        reasons.append(f"Only {new_records_count} new records (need {min_records})")

    if last_retrain_date:
        try:
            last_dt = datetime.fromisoformat(last_retrain_date.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last_dt).days
            if days_since < min_days_since_last:
                ready = False
                reasons.append(
                    f"Only {days_since} days since last retrain (need {min_days_since_last})"
                )
        except (ValueError, AttributeError):
            reasons.append("Could not parse last retrain date")

    if not reasons:
        reasons.append("All conditions met for retraining")

    return {
        "ready": ready,
        "new_records": new_records_count,
        "min_records_required": min_records,
        "last_retrain_date": last_retrain_date,
        "min_days_between_retrains": min_days_since_last,
        "reasons": reasons,
    }


def prepare_training_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare and validate training data from raw records."""
    if not records:
        return {
            "status": "no_data",
            "message": "No training records provided.",
            "total_records": 0,
            "valid_records": 0,
        }

    valid_records = []
    skipped = 0
    required_fields = ["heart_rate", "spo2", "risk_label"]

    for record in records:
        if all(record.get(f) is not None for f in required_fields):
            valid_records.append(record)
        else:
            skipped += 1

    return {
        "status": "ok" if valid_records else "no_valid_data",
        "total_records": len(records),
        "valid_records": len(valid_records),
        "skipped_records": skipped,
        "fields_required": required_fields,
        "ready_for_training": len(valid_records) >= 50,
        "data_quality_score": round(len(valid_records) / max(1, len(records)), 3),
    }


def get_retraining_status() -> Dict[str, Any]:
    """Get the current status of model artifacts and retraining metadata."""
    model_path = MODEL_DIR / "risk_model.pkl"
    scaler_path = MODEL_DIR / "scaler.pkl"
    features_path = MODEL_DIR / "feature_columns.json"
    metadata_path = MODEL_DIR / "model_metadata.json"

    status = {
        "model_dir": str(MODEL_DIR),
        "model_exists": model_path.exists(),
        "scaler_exists": scaler_path.exists(),
        "features_exists": features_path.exists(),
    }

    if model_path.exists():
        stat = model_path.stat()
        status["model_size_bytes"] = stat.st_size
        status["model_modified"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                status["metadata"] = json.load(f)
        except Exception:
            status["metadata"] = None
    else:
        status["metadata"] = {
            "model_name": "RandomForest",
            "version": "1.0",
            "accuracy": "96.9%",
            "note": "Initial model - no retrain history",
        }

    return status


def save_retraining_metadata(
    version: str,
    accuracy: float,
    records_used: int,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Save metadata about a retraining run."""
    metadata = {
        "model_name": "RandomForest",
        "version": version,
        "accuracy": round(accuracy, 4),
        "records_used": records_used,
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }

    metadata_path = MODEL_DIR / "model_metadata.json"
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info("Model metadata saved: version=%s, accuracy=%s", version, accuracy)
    except Exception as e:
        logger.error("Failed to save model metadata: %s", e)
        metadata["save_error"] = str(e)

    return metadata
