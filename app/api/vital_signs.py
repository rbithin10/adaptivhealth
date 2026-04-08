"""
Vital signs routes.

This file saves heart data from devices and lets the app read it back.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 35
# HELPER FUNCTIONS
#   - check_vitals_for_alerts.......... Line 72  (Background alert checker)
#   - calculate_vitals_summary......... Line 165 (Stats calculation)
#
# BACKGROUND HELPERS
#   - _run_cloud_ml_on_batch........... (Cloud ML re-analysis on batch-sync payload)
#   - _detect_batch_anomalies.......... (Trend/anomaly detection on batch-sync payload)
#
# ENDPOINTS - PATIENT (own data)
#   --- SUBMIT VITALS ---
#   - POST /vitals..................... (Submit single reading)
#   - POST /vitals/batch............... (Submit multiple readings)
#   - POST /vitals/critical-alert...... (Immediate critical push — bypasses 15-min queue)
#   - POST /vitals/batch-sync.......... (Edge AI periodic batch from mobile)
#
#   --- READ VITALS ---
#   - GET /vitals/latest............... (Most recent reading)
#   - GET /vitals/summary.............. (Aggregated stats)
#   - GET /vitals/history.............. (Time-series data)
#
# ENDPOINTS - CLINICIAN (patient data)
#   - GET /vitals/user/{id}/latest..... (Patient's latest)
#   - GET /vitals/user/{id}/summary.... (Patient's stats)
#   - GET /vitals/user/{id}/history.... (Patient's history)
#
# BUSINESS CONTEXT:
# - Patients sync vitals from wearables (Fitbit, Apple Watch)
# - Mobile app shows latest readings on home screen
# - Clinician dashboard shows patient vitals with time trends
# - Alerts auto-create when thresholds exceeded (HR>180, SpO2<90)
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
import os
import socket

from app.database import get_db
from app.models.user import User, UserRole
from app.models.vital_signs import VitalSignRecord
from app.models.alert import Alert, AlertType, SeverityLevel
from app.models.risk_assessment import RiskAssessment
from app.schemas.vital_signs import (
    VitalSignCreate, VitalSignResponse, VitalSignBatchCreate,
    VitalSignsSummary, VitalSignsHistoryResponse, VitalSignsStats,
    EdgeBatchSyncRequest, EdgeBatchItem,
)
from app.services.encryption import encryption_service
from app.api.auth import get_current_user, get_current_doctor_user, check_clinician_phi_access
from app.rate_limiter import limiter
from app.services.ml_prediction import predict_risk, is_model_loaded
from app.services.risk_drivers import build_drivers_from_vitals
from app.services.confidence_scorer import compute_confidence_score

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def _backend_instance_id() -> str:
    return os.getenv("HOSTNAME") or socket.gethostname()


def _db_target(db: Session) -> str:
    try:
        row = db.execute(text(
            "SELECT current_database() AS db, "
            "COALESCE(inet_server_addr()::text, 'local') AS addr, "
            "COALESCE(inet_server_port(), 0) AS port"
        )).mappings().first()
        return f"{row['db']}@{row['addr']}:{row['port']}"
    except Exception as e:
        return f"unknown({e})"


# =============================================================================
# Helper Functions
# =============================================================================

# =============================================
# CHECK_VITALS_FOR_ALERTS - Background task for threshold monitoring
# Used by: Called after every vital submission
# Returns: None (creates Alert records in DB)
# Triggers: HR>180 (critical), SpO2<90 (critical), BP>160 (warning)
# =============================================
def check_vitals_for_alerts(user_id: int, vital_data: VitalSignCreate, db: Session = None):
    """
    Background task to check vital signs for alerts.
    
    Creates alert records and logs notifications when thresholds are exceeded.
    
    Args:
        user_id: User ID
        vital_data: Vital signs data
        db: Optional database session (for testing). If None, creates new session.
    """
    # Use provided session or create new one for background task
    from app.database import SessionLocal
    session_provided = db is not None
    if not session_provided:
        db = SessionLocal()
    
    try:
        logger.info(f"Checking vitals for alerts: user {user_id}")
        
        # Collect all alerts to create
        new_alerts = []
        
        # Check for high heart rate (critical threshold: >180 BPM)
        if vital_data.heart_rate > 180:
            logger.warning(f"High heart rate alert for user {user_id}: {vital_data.heart_rate} BPM")
            
            new_alerts.append(Alert(
                user_id=user_id,
                alert_type=AlertType.HIGH_HEART_RATE.value,
                severity=SeverityLevel.CRITICAL.value,
                title="High Heart Rate Detected",
                message=f"Heart rate of {vital_data.heart_rate} BPM exceeds safe threshold of 180 BPM",
                action_required="Rest immediately and monitor. Contact healthcare provider if symptoms persist.",
                trigger_value=f"{vital_data.heart_rate} BPM",
                threshold_value="180 BPM",
                acknowledged=False,
                is_sent_to_user=True,
                is_sent_to_caregiver=True,
                is_sent_to_clinician=True
            ))
        
        # Check for low oxygen (critical threshold: <90%)
        if vital_data.spo2 and vital_data.spo2 < 90:
            logger.warning(f"Low oxygen alert for user {user_id}: {vital_data.spo2}%")
            
            new_alerts.append(Alert(
                user_id=user_id,
                alert_type=AlertType.LOW_SPO2.value,
                severity=SeverityLevel.CRITICAL.value,
                title="Low Blood Oxygen Detected",
                message=f"Blood oxygen saturation of {vital_data.spo2}% is below safe threshold of 90%",
                action_required="Seek immediate medical attention. This may indicate respiratory distress.",
                trigger_value=f"{vital_data.spo2}%",
                threshold_value="90%",
                acknowledged=False,
                is_sent_to_user=True,
                is_sent_to_caregiver=True,
                is_sent_to_clinician=True
            ))
        
        # Check for high blood pressure (warning threshold: systolic >160 or diastolic >100)
        if vital_data.blood_pressure_systolic and vital_data.blood_pressure_systolic > 160:
            # Include both systolic and diastolic in trigger value for context
            bp_display = f"{vital_data.blood_pressure_systolic}/{vital_data.blood_pressure_diastolic or 'N/A'} mmHg"
            logger.warning(f"High blood pressure alert for user {user_id}: {bp_display}")
            
            new_alerts.append(Alert(
                user_id=user_id,
                alert_type=AlertType.HIGH_BLOOD_PRESSURE.value,
                severity=SeverityLevel.WARNING.value,
                title="Elevated Blood Pressure",
                message=f"Systolic blood pressure of {vital_data.blood_pressure_systolic} mmHg exceeds threshold",
                action_required="Monitor blood pressure and consult healthcare provider if elevated readings persist.",
                trigger_value=bp_display,
                threshold_value="160/100 mmHg",
                acknowledged=False,
                is_sent_to_user=True,
                is_sent_to_clinician=True
            ))
        
        # Bulk insert all alerts in a single transaction
        if new_alerts:
            db.add_all(new_alerts)
            db.commit()
            logger.info(f"Created {len(new_alerts)} alert(s) for user {user_id}")
            
    finally:
        # Only close session if we created it
        if not session_provided:
            db.close()


# =============================================
# CALCULATE_VITALS_SUMMARY - Aggregates stats over date range
# Used by: Summary endpoints, dashboard charts
# Returns: VitalSignsSummary with avg/min/max HR, SpO2, alert count
# =============================================
def calculate_vitals_summary(
    db: Session,
    user_id: int,
    start_date: datetime,
    end_date: datetime
) -> VitalSignsSummary:
    """
    Calculate summary statistics for vital signs over a date range.
    
    Args:
        db: Database session
        user_id: User ID
        start_date: Start of period
        end_date: End of period
        
    Returns:
        Summary statistics
    """
    # Query valid readings in the date range
    vitals = db.query(VitalSignRecord).filter(
        VitalSignRecord.user_id == user_id,
        VitalSignRecord.timestamp >= start_date,
        VitalSignRecord.timestamp <= end_date,
        VitalSignRecord.is_valid == True
    ).all()
    
    if not vitals:
        return VitalSignsSummary(
            date=start_date.strftime("%Y-%m-%d"),
            total_readings=0,
            valid_readings=0,
            alerts_triggered=0
        )
    
    # Calculate statistics
    heart_rates = [v.heart_rate for v in vitals]
    spo2_values = [v.spo2 for v in vitals if v.spo2 is not None]
    hrv_values = [v.hrv for v in vitals if v.hrv is not None]
    
    # Count alerts triggered in the same date range
    alerts_count = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.created_at >= start_date,
        Alert.created_at <= end_date
    ).count()
    
    summary = VitalSignsSummary(
        date=start_date.strftime("%Y-%m-%d"),
        avg_heart_rate=sum(heart_rates) / len(heart_rates) if heart_rates else None,
        min_heart_rate=min(heart_rates) if heart_rates else None,
        max_heart_rate=max(heart_rates) if heart_rates else None,
        avg_spo2=sum(spo2_values) / len(spo2_values) if spo2_values else None,
        min_spo2=min(spo2_values) if spo2_values else None,
        avg_hrv=sum(hrv_values) / len(hrv_values) if hrv_values else None,
        total_readings=len(vitals),
        valid_readings=len(vitals),
        alerts_triggered=alerts_count
    )
    
    return summary


def _parse_edge_timestamp(value: Optional[str]) -> datetime:
    """Parse ISO timestamp sent by mobile edge payloads."""
    if not value:
        return datetime.now(timezone.utc)

    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.now(timezone.utc)


# =============================================
# _RUN_CLOUD_ML_ON_BATCH - Background task: cloud ML re-analysis of a batch-sync payload
# Used by: submit_vitals_batch_sync (background task)
# Returns: None (stores RiskAssessment records + creates alerts in DB)
# WHY: Edge AI is fast but runs without medical history context.
#      Cloud ML re-analyzes each batch item with the patient's full profile
#      so the clinician sees a server-validated risk score alongside the edge result.
# =============================================
def _run_cloud_ml_on_batch(user_id: int, batch_items: list) -> None:
    """
    Background task: run cloud ML risk prediction on each item in a batch-sync payload.

    Args:
        user_id: Patient user ID.
        batch_items: List of EdgeBatchItem objects from EdgeBatchSyncRequest.batch.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return

        if not is_model_loaded():
            logger.warning("Cloud ML batch re-analysis skipped — model not loaded.")
            return

        # Use patient profile for context; fall back to population averages if not set
        age = user.age or 45
        baseline_hr = user.baseline_hr or 70
        max_safe_hr = user.max_safe_hr or max(160, 220 - age)

        new_assessments = []
        new_alerts = []

        for item in batch_items:
            vitals = item.vitals if hasattr(item, "vitals") else (item.get("vitals") or {})

            hr_raw = vitals.get("heart_rate") if isinstance(vitals, dict) else None
            try:
                hr = int(hr_raw)
            except (TypeError, ValueError):
                continue
            if hr < 30 or hr > 250:
                continue

            spo2_raw = vitals.get("spo2") if isinstance(vitals, dict) else None
            try:
                spo2_int = int(float(spo2_raw)) if spo2_raw is not None else 98
            except (TypeError, ValueError):
                spo2_int = 98

            try:
                ml_result = predict_risk(
                    age=age,
                    baseline_hr=baseline_hr,
                    max_safe_hr=max_safe_hr,
                    avg_heart_rate=hr,
                    peak_heart_rate=hr,
                    min_heart_rate=hr,
                    avg_spo2=spo2_int,
                    duration_minutes=5,
                    recovery_time_minutes=2,
                    activity_type="monitoring",
                )
            except Exception as exc:
                logger.warning(f"Cloud ML prediction failed for one batch item (user {user_id}): {exc}")
                continue

            cloud_level = ml_result.get("risk_level", "low")
            cloud_score = float(ml_result.get("risk_score", 0.0))

            # Log any edge-vs-cloud disagreement for audit purposes
            prediction_dict = (
                item.prediction if hasattr(item, "prediction") else (item.get("prediction") or {})
            )
            edge_level = (prediction_dict.get("risk_level") if prediction_dict else None)
            if edge_level and edge_level != cloud_level:
                logger.info(
                    f"Cloud/edge disagreement — user {user_id}: "
                    f"edge={edge_level}, cloud={cloud_level}, HR={hr}"
                )

            import json as _json
            _drivers = build_drivers_from_vitals(user, hr, float(spo2_int))
            _conf = compute_confidence_score(
                ml_confidence=ml_result.get("confidence") or 0.5,
                user=user,
                db=db,
            )
            new_assessments.append(
                RiskAssessment(
                    user_id=user_id,
                    risk_level=cloud_level,
                    risk_score=cloud_score,
                    assessment_type="batch_cloud",
                    generated_by="cloud_ml",
                    input_heart_rate=hr,
                    input_spo2=float(spo2_int),
                    model_name="RandomForest (cloud)",
                    model_version="1.0",
                    confidence=_conf,
                    alert_triggered=(cloud_level in {"high", "critical"}),
                    risk_factors_json=_json.dumps(_drivers),
                )
            )

            # Create an alert if cloud ML flags elevated risk
            if cloud_level in {"high", "critical"}:
                since = datetime.now(timezone.utc) - timedelta(minutes=30)
                recent = db.query(Alert).filter(
                    Alert.user_id == user_id,
                    Alert.alert_type == AlertType.ABNORMAL_ACTIVITY.value,
                    Alert.created_at >= since,
                ).first()
                if not recent:
                    severity = (
                        SeverityLevel.CRITICAL.value
                        if cloud_level == "critical"
                        else SeverityLevel.WARNING.value
                    )
                    new_alerts.append(
                        Alert(
                            user_id=user_id,
                            alert_type=AlertType.ABNORMAL_ACTIVITY.value,
                            severity=severity,
                            title="Elevated Cardiac Risk — Cloud Analysis",
                            message=(
                                f"Cloud ML analysis of your recent readings flagged {cloud_level} risk "
                                f"(score: {cloud_score:.0%}, HR={hr} BPM)."
                            ),
                            action_required="Review with your clinician.",
                            trigger_value=f"{cloud_score:.2f}",
                            threshold_value="0.50",
                            acknowledged=False,
                            is_sent_to_clinician=True,
                            is_sent_to_user=True,
                        )
                    )

        if new_assessments:
            db.add_all(new_assessments)
        if new_alerts:
            db.add_all(new_alerts)
        if new_assessments or new_alerts:
            db.commit()
            logger.info(
                f"Cloud ML batch analysis — user {user_id}: "
                f"{len(new_assessments)} assessments, {len(new_alerts)} alert(s) created"
            )

    except Exception as exc:
        logger.error(f"_run_cloud_ml_on_batch failed for user {user_id}: {exc}")
        db.rollback()
    finally:
        db.close()


# =============================================
# _DETECT_BATCH_ANOMALIES - Background task: trend and anomaly detection on batch-sync
# Used by: submit_vitals_batch_sync (background task, runs in parallel with cloud ML)
# Returns: None (creates trend-alert records in DB)
# WHY: Fixed threshold alerts miss slow deterioration. Trend checks catch it.
#      Three checks: (1) avg HR > 20% above personal baseline,
#                   (2) SpO2 downward trend across the batch,
#                   (3) 3+ consecutive readings > 160 BPM.
# =============================================
def _detect_batch_anomalies(user_id: int, batch_items: list) -> None:
    """
    Background task: detect HR/SpO2 anomalies and trends in a synced batch.

    Args:
        user_id: Patient user ID.
        batch_items: List of EdgeBatchItem objects from EdgeBatchSyncRequest.batch.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # Extract valid (HR, SpO2) pairs from the batch
        readings: List[tuple] = []
        for item in batch_items:
            vitals = item.vitals if hasattr(item, "vitals") else (item.get("vitals") or {})
            if not isinstance(vitals, dict):
                continue
            hr_raw = vitals.get("heart_rate")
            try:
                hr = int(hr_raw)
            except (TypeError, ValueError):
                continue
            if hr < 30 or hr > 250:
                continue
            spo2_raw = vitals.get("spo2")
            try:
                spo2 = float(spo2_raw) if spo2_raw is not None else None
            except (TypeError, ValueError):
                spo2 = None
            readings.append((hr, spo2))

        if len(readings) < 2:
            return  # Not enough data for trend detection

        hrs = [r[0] for r in readings]
        spo2s = [r[1] for r in readings if r[1] is not None]

        # Compute this patient's personal 7-day HR/SpO2 baseline
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        baseline_rows = (
            db.query(VitalSignRecord)
            .filter(
                VitalSignRecord.user_id == user_id,
                VitalSignRecord.timestamp >= seven_days_ago,
                VitalSignRecord.is_valid == True,
            )
            .all()
        )
        baseline_hrs = [r.heart_rate for r in baseline_rows if r.heart_rate]

        new_alerts = []
        dedup_window = datetime.now(timezone.utc) - timedelta(minutes=30)

        # ---- Check 1: Batch avg HR > 20% above personal 7-day baseline ----
        if baseline_hrs:
            personal_avg_hr = sum(baseline_hrs) / len(baseline_hrs)
            batch_avg_hr = sum(hrs) / len(hrs)
            if batch_avg_hr > personal_avg_hr * 1.20:
                recent = db.query(Alert).filter(
                    Alert.user_id == user_id,
                    Alert.alert_type == "elevated_hr_trend",
                    Alert.created_at >= dedup_window,
                ).first()
                if not recent:
                    new_alerts.append(
                        Alert(
                            user_id=user_id,
                            alert_type="elevated_hr_trend",
                            severity=SeverityLevel.WARNING.value,
                            title="Elevated Heart Rate Trend",
                            message=(
                                f"Your average heart rate over the last sync period "
                                f"({batch_avg_hr:.0f} BPM) is more than 20% above your "
                                f"7-day personal baseline ({personal_avg_hr:.0f} BPM)."
                            ),
                            action_required="Monitor for symptoms. Rest if you feel discomfort.",
                            trigger_value=f"{batch_avg_hr:.0f} BPM",
                            threshold_value=f"{personal_avg_hr * 1.20:.0f} BPM",
                            acknowledged=False,
                            is_sent_to_clinician=True,
                            is_sent_to_user=True,
                        )
                    )

        # ---- Check 2: SpO2 downward trend across the batch ----
        if len(spo2s) >= 4:
            mid = len(spo2s) // 2
            first_half_avg = sum(spo2s[:mid]) / mid
            second_half_avg = sum(spo2s[mid:]) / (len(spo2s) - mid)
            if first_half_avg - second_half_avg > 2.0:
                recent = db.query(Alert).filter(
                    Alert.user_id == user_id,
                    Alert.alert_type == "spo2_declining",
                    Alert.created_at >= dedup_window,
                ).first()
                if not recent:
                    new_alerts.append(
                        Alert(
                            user_id=user_id,
                            alert_type="spo2_declining",
                            severity=SeverityLevel.WARNING.value,
                            title="Declining Blood Oxygen Trend",
                            message=(
                                f"Blood oxygen saturation appears to be declining across this sync period "
                                f"({first_half_avg:.1f}% → {second_half_avg:.1f}%). "
                                "This may indicate early respiratory difficulty."
                            ),
                            action_required=(
                                "Monitor closely. Seek medical attention if SpO2 drops below 94%."
                            ),
                            trigger_value=f"{second_half_avg:.1f}%",
                            threshold_value="2 pp drop",
                            acknowledged=False,
                            is_sent_to_clinician=True,
                            is_sent_to_user=True,
                        )
                    )

        # ---- Check 3: 3+ consecutive readings > 160 BPM ----
        consecutive = 0
        max_consecutive = 0
        for hr in hrs:
            if hr > 160:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        if max_consecutive >= 3:
            recent = db.query(Alert).filter(
                Alert.user_id == user_id,
                Alert.alert_type == "sustained_high_hr",
                Alert.created_at >= dedup_window,
            ).first()
            if not recent:
                new_alerts.append(
                    Alert(
                        user_id=user_id,
                        alert_type="sustained_high_hr",
                        severity=SeverityLevel.WARNING.value,
                        title="Sustained High Heart Rate",
                        message=(
                            f"Heart rate exceeded 160 BPM for {max_consecutive} consecutive "
                            "readings in this sync period."
                        ),
                        action_required="Reduce activity intensity. Rest and monitor.",
                        trigger_value=f"{max_consecutive} readings > 160 BPM",
                        threshold_value="3 consecutive",
                        acknowledged=False,
                        is_sent_to_clinician=True,
                        is_sent_to_user=True,
                    )
                )

        if new_alerts:
            db.add_all(new_alerts)
            db.commit()
            logger.info(
                f"Anomaly detection — user {user_id}: {len(new_alerts)} trend alert(s) created"
            )

    except Exception as exc:
        logger.error(f"_detect_batch_anomalies failed for user {user_id}: {exc}")
        db.rollback()
    finally:
        db.close()


# =============================================================================
# Vital Signs Endpoints
# =============================================================================

# --- ENDPOINTS: PATIENT SUBMITS VITALS ---

# =============================================
# SUBMIT_VITALS - Patient submits single reading from wearable
# Used by: Mobile app syncing from Fitbit/Apple Watch
# Returns: VitalSignResponse with recorded data
# Roles: PATIENT (own data only)
# =============================================
@router.post("/vitals", response_model=VitalSignResponse)
@limiter.limit("60/minute")
async def submit_vitals(
    request: Request,
    vital_data: VitalSignCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a single vital signs reading from wearable device.
    
    DESIGN RATIONALE:
    - Accepts readings from Fitbit, Apple Watch, Oura Ring, etc.
    - Validates data quality BEFORE storing (prevents garbage data)
    - Runs alert checking in BACKGROUND (doesn't block user response)
    - Stores with confidence_score for future ML feature engineering
    
    VALIDATION STRATEGY:
    - Heart rate 30-250 BPM (physiologically impossible outside this range)
    - SpO2 70-100% (below 70% is critical, above 100% is sensor error)
    - Blood pressure checked against typical ranges
    - Why not accept invalid data: Garbage in → garbage out for ML models
    
    BACKGROUND ALERTS:
    - Async task checks vitals for thresholds (high HR, low SpO2)
    - Doesn't wait for completion (user gets immediate response)
    - Allows notifications to be sent without blocking API
    
    Mobile app sends data here after collecting from wearable.
    
    Request body example:
    {
        "heart_rate": 75,
        "spo2": 98,
        "blood_pressure_systolic": 120,
        "blood_pressure_diastolic": 80,
        "device_id": "fitbit_charge_6_abc123",
        "timestamp": "2026-01-15T14:30:00Z"
    }
    """
    logger.info(
        "[DIAG][VITALS_POST] backend=%s host=%s path=%s user=%s db=%s",
        _backend_instance_id(),
        request.headers.get("host"),
        request.url.path,
        current_user.user_id,
        _db_target(db),
    )

    # Validate heart rate is physiologically possible
    # WHY: Wearables sometimes send erroneous values (motion artifacts, sensor loss)
    # 30 BPM = severe bradycardia (requires medical attention but possible)
    # 250 BPM = impossible without severe tachycardia (sensor error)
    if vital_data.heart_rate < 30 or vital_data.heart_rate > 250:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heart rate out of valid range (30-250 BPM)"
        )
    
    # Validate blood oxygen saturation
    # WHY: Critical vital for cardiac patients (oxygen delivery indicator)
    # Below 70%: Medical emergency, requires immediate intervention
    # Above 100%: Impossible (sensor malfunction), reject
    if vital_data.spo2 and (vital_data.spo2 < 70 or vital_data.spo2 > 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blood oxygen saturation out of valid range (70-100%)"
        )
    
    # Create vital signs record (column names match Massoud's AWS schema)
    # Stores with system-generated timestamp defaults
    new_vital = VitalSignRecord(
        user_id=current_user.user_id,
        heart_rate=vital_data.heart_rate,
        spo2=vital_data.spo2,
        systolic_bp=vital_data.blood_pressure_systolic,
        diastolic_bp=vital_data.blood_pressure_diastolic,
        hrv=vital_data.hrv,
        source_device=vital_data.source_device,
        device_id=vital_data.device_id,
        timestamp=vital_data.timestamp or datetime.now(timezone.utc),
        is_valid=True,
        confidence_score=1.0
    )
    
    db.add(new_vital)
    db.commit()
    db.refresh(new_vital)
    
    # Check for alerts in background
    background_tasks.add_task(check_vitals_for_alerts, current_user.user_id, vital_data)
    
    logger.info(
        "[DIAG][VITALS_POST_STORED] backend=%s user=%s hr=%s ts=%s db=%s",
        _backend_instance_id(),
        current_user.user_id,
        vital_data.heart_rate,
        new_vital.timestamp,
        _db_target(db),
    )
    
    return new_vital


# =============================================
# SUBMIT_VITALS_BATCH - Patient submits multiple readings at once
# Used by: Mobile app bulk sync (offline data, historical imports)
# Returns: Count of records successfully created
# Roles: PATIENT (own data only)
# =============================================
@router.post("/vitals/batch")
@limiter.limit("10/minute")
async def submit_vitals_batch(
    request: Request,
    batch_data: VitalSignBatchCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit multiple vital signs readings in batch.
    
    Useful for syncing historical data or bulk uploads.
    """
    if not batch_data.vitals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No vital signs data provided"
        )
    
    if len(batch_data.vitals) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size limited to 1000 records"
        )
    
    records_created = 0
    
    for vital_data in batch_data.vitals:
        # Basic validation
        if vital_data.heart_rate < 30 or vital_data.heart_rate > 250:
            continue  # Skip invalid records
        
        new_vital = VitalSignRecord(
            user_id=current_user.user_id,
            heart_rate=vital_data.heart_rate,
            spo2=vital_data.spo2,
            systolic_bp=vital_data.blood_pressure_systolic,
            diastolic_bp=vital_data.blood_pressure_diastolic,
            hrv=vital_data.hrv,
            source_device=vital_data.source_device,
            device_id=vital_data.device_id,
            timestamp=vital_data.timestamp or datetime.now(timezone.utc),
            is_valid=True,
            confidence_score=1.0
        )
        
        db.add(new_vital)
        records_created += 1
    
    db.commit()
    
    # Check for alerts on the batch
    for vital_data in batch_data.vitals:
        background_tasks.add_task(check_vitals_for_alerts, current_user.user_id, vital_data)
    
    logger.info(f"Batch vitals recorded for user {current_user.user_id}: {records_created} records")
    
    return {
        "message": f"Successfully created {records_created} vital signs records",
        "records_created": records_created
    }


@router.post("/vitals/batch-sync")
@limiter.limit("10/minute")
async def submit_vitals_batch_sync(
    request: Request,
    sync_payload: EdgeBatchSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync edge-generated payloads from mobile to cloud backend.

    WHY THIS ENDPOINT EXISTS:
    - Mobile edge AI queues predictions + vitals offline.
    - CloudSyncService flushes that queue periodically.
    - Without this route, periodic sync attempts get 404 and data is dropped.
    """
    if not sync_payload.batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sync items provided"
        )

    records_created = 0
    assessments_created = 0
    skipped = 0

    for item in sync_payload.batch:
        vitals = item.vitals or {}

        heart_rate_raw = vitals.get("heart_rate")
        if heart_rate_raw is None:
            skipped += 1
            continue

        try:
            heart_rate = int(heart_rate_raw)
        except (TypeError, ValueError):
            skipped += 1
            continue

        if heart_rate < 30 or heart_rate > 250:
            skipped += 1
            continue

        spo2_raw = vitals.get("spo2")
        try:
            spo2 = float(spo2_raw) if spo2_raw is not None else None
        except (TypeError, ValueError):
            spo2 = None

        systolic_raw = vitals.get("blood_pressure_systolic", vitals.get("bp_systolic"))
        diastolic_raw = vitals.get("blood_pressure_diastolic", vitals.get("bp_diastolic"))

        try:
            systolic_bp = int(systolic_raw) if systolic_raw is not None else None
        except (TypeError, ValueError):
            systolic_bp = None

        try:
            diastolic_bp = int(diastolic_raw) if diastolic_raw is not None else None
        except (TypeError, ValueError):
            diastolic_bp = None

        reading_timestamp = _parse_edge_timestamp(
            vitals.get("timestamp") or item.timestamp
        )

        new_vital = VitalSignRecord(
            user_id=current_user.user_id,
            heart_rate=heart_rate,
            spo2=spo2,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            hrv=vitals.get("hrv"),
            source_device="edge_ai_sync",
            device_id=vitals.get("device_id", "edge_mobile"),
            timestamp=reading_timestamp,
            is_valid=True,
            confidence_score=1.0,
            processed_by_edge_ai=True,
        )
        db.add(new_vital)
        records_created += 1

        prediction = item.prediction or {}
        logger.info(f"[EDGE_SYNC] user={current_user.user_id} prediction={prediction}")
        risk_score_raw = prediction.get("risk_score")
        risk_level_raw = prediction.get("risk_level")

        if risk_score_raw is not None and risk_level_raw in {"low", "moderate", "high", "critical"}:
            try:
                risk_score = float(risk_score_raw)
            except (TypeError, ValueError):
                risk_score = None

            if risk_score is not None:
                import json as _json
                _hrv_val = vitals.get("hrv")
                try:
                    _hrv = float(_hrv_val) if _hrv_val is not None else None
                except (TypeError, ValueError):
                    _hrv = None
                _spo2_val = spo2 if spo2 is not None else 98.0
                _drivers = build_drivers_from_vitals(
                    current_user, heart_rate, _spo2_val,
                    systolic_bp=systolic_bp, diastolic_bp=diastolic_bp, hrv=_hrv,
                )
                _conf_es = compute_confidence_score(
                    ml_confidence=prediction.get("confidence") or 0.5,
                    user=current_user,
                    db=db,
                )
                new_assessment = RiskAssessment(
                    user_id=current_user.user_id,
                    risk_level=str(risk_level_raw),
                    risk_score=risk_score,
                    assessment_type="edge_sync",
                    generated_by="edge_ai",
                    input_heart_rate=heart_rate,
                    input_spo2=spo2,
                    input_blood_pressure_sys=systolic_bp,
                    input_blood_pressure_dia=diastolic_bp,
                    input_hrv=_hrv,
                    model_name="Edge RandomForest",
                    model_version=str(prediction.get("model_version", "unknown")),
                    confidence=_conf_es,
                    inference_time_ms=prediction.get("inference_time_ms"),
                    risk_factors_json=_json.dumps(_drivers),
                    alert_triggered=bool(item.alerts),
                )
                db.add(new_assessment)
                assessments_created += 1

    db.commit()

    # Fire cloud ML re-analysis and trend detection as background tasks so the
    # HTTP response returns immediately while deeper analysis runs in parallel.
    # Both tasks open their own DB sessions to avoid session-sharing issues.
    background_tasks.add_task(
        _run_cloud_ml_on_batch, current_user.user_id, list(sync_payload.batch)
    )
    background_tasks.add_task(
        _detect_batch_anomalies, current_user.user_id, list(sync_payload.batch)
    )

    logger.info(
        f"Edge sync ingested for user {current_user.user_id}: "
        f"records={records_created}, assessments={assessments_created}, skipped={skipped}"
    )

    return {
        "message": "Edge batch sync processed",
        "source": sync_payload.source,
        "records_created": records_created,
        "assessments_created": assessments_created,
        "skipped": skipped,
        "received": len(sync_payload.batch),
    }


# =============================================
# POST_CRITICAL_ALERT - Immediate critical reading push (bypasses 15-min queue)
# Used by: Mobile app when edge AI detects high/critical risk
# Returns: Confirmation + cloud ML result
# WHY: Normal batch-sync fires every 15 min — too slow for life-threatening events.
#      This endpoint stores the vital, runs cloud ML and creates the alert inside
#      the same HTTP request so the SSE stream picks it up within 1 second.
# =============================================
@router.post("/vitals/critical-alert")
@limiter.limit("20/minute")
async def push_critical_alert(
    request: Request,
    payload: EdgeBatchItem,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Immediately store a single critical vital reading and create a cloud alert.

    WHY THIS ENDPOINT EXISTS:
    - Normal batch sync fires every 15 min — unacceptable for critical events.
    - When edge AI detects high/critical risk, mobile calls this endpoint directly.
    - Vital is stored, cloud ML runs, and the alert is written — all before this
      response returns. The SSE stream (/alerts/stream) picks it up within 1 second.
    """
    vitals = payload.vitals or {}

    hr_raw = vitals.get("heart_rate")
    if hr_raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="heart_rate is required",
        )

    try:
        hr = int(hr_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="heart_rate must be a number",
        )

    if hr < 30 or hr > 250:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="heart_rate out of valid range (30\u2013250 BPM)",
        )

    spo2_raw = vitals.get("spo2")
    try:
        spo2 = float(spo2_raw) if spo2_raw is not None else None
    except (TypeError, ValueError):
        spo2 = None

    systolic_raw = vitals.get("blood_pressure_systolic", vitals.get("bp_systolic"))
    diastolic_raw = vitals.get("blood_pressure_diastolic", vitals.get("bp_diastolic"))
    try:
        systolic_bp = int(systolic_raw) if systolic_raw is not None else None
    except (TypeError, ValueError):
        systolic_bp = None
    try:
        diastolic_bp = int(diastolic_raw) if diastolic_raw is not None else None
    except (TypeError, ValueError):
        diastolic_bp = None

    reading_ts = _parse_edge_timestamp(vitals.get("timestamp") or payload.timestamp)

    # 1. Store the vital record immediately
    new_vital = VitalSignRecord(
        user_id=current_user.user_id,
        heart_rate=hr,
        spo2=spo2,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        source_device="edge_ai_critical",
        device_id=vitals.get("device_id", "edge_mobile"),
        timestamp=reading_ts,
        is_valid=True,
        confidence_score=1.0,
        processed_by_edge_ai=True,
    )
    db.add(new_vital)

    # 2. Run cloud ML re-analysis synchronously so the result is in the alert message
    cloud_level = "unknown"
    cloud_score: Optional[float] = None

    if is_model_loaded():
        try:
            age = current_user.age or 45
            baseline_hr_val = current_user.baseline_hr or 70
            max_safe_hr_val = current_user.max_safe_hr or max(160, 220 - age)
            spo2_int = int(spo2) if spo2 is not None else 98

            ml_result = predict_risk(
                age=age,
                baseline_hr=baseline_hr_val,
                max_safe_hr=max_safe_hr_val,
                avg_heart_rate=hr,
                peak_heart_rate=hr,
                min_heart_rate=hr,
                avg_spo2=spo2_int,
                duration_minutes=5,
                recovery_time_minutes=2,
                activity_type="monitoring",
            )
            cloud_level = ml_result.get("risk_level", "unknown")
            cloud_score = float(ml_result.get("risk_score", 0.0))

            import json as _json
            _hrv_raw = vitals.get("hrv")
            try:
                _hrv_cp = float(_hrv_raw) if _hrv_raw is not None else None
            except (TypeError, ValueError):
                _hrv_cp = None
            _spo2_cp = float(spo2) if spo2 is not None else 98.0
            _drivers_cp = build_drivers_from_vitals(
                current_user, hr, _spo2_cp,
                systolic_bp=systolic_bp, diastolic_bp=diastolic_bp, hrv=_hrv_cp,
            )
            _conf_cp = compute_confidence_score(
                ml_confidence=ml_result.get("confidence") or 0.5,
                user=current_user,
                db=db,
            )
            db.add(
                RiskAssessment(
                    user_id=current_user.user_id,
                    risk_level=cloud_level,
                    risk_score=cloud_score,
                    assessment_type="critical_push",
                    generated_by="cloud_ml",
                    input_heart_rate=hr,
                    input_spo2=spo2,
                    input_blood_pressure_sys=systolic_bp,
                    input_blood_pressure_dia=diastolic_bp,
                    input_hrv=_hrv_cp,
                    model_name="RandomForest (cloud)",
                    model_version="1.0",
                    confidence=_conf_cp,
                    alert_triggered=True,
                    risk_factors_json=_json.dumps(_drivers_cp),
                )
            )
        except Exception as exc:
            logger.warning(
                f"Cloud ML skipped during critical push for user {current_user.user_id}: {exc}"
            )

    # 3. Create the alert immediately — no dedup window for critical-push events
    edge_prediction = payload.prediction or {}
    edge_level = edge_prediction.get("risk_level", "high")

    alert_message = (
        f"Edge AI detected {edge_level} risk (HR={hr} BPM"
        + (f", SpO2={spo2:.0f}%" if spo2 is not None else "")
        + ")"
        + (
            f". Cloud ML confirms {cloud_level} risk ({cloud_score:.0%})."
            if cloud_score is not None
            else " \u2014 cloud verification pending."
        )
    )

    db.add(
        Alert(
            user_id=current_user.user_id,
            alert_type=AlertType.ABNORMAL_ACTIVITY.value,
            severity=SeverityLevel.CRITICAL.value,
            title="Critical Risk Reading \u2014 Immediate Review Required",
            message=alert_message,
            action_required="Immediate clinician review required.",
            trigger_value=(
                f"HR={hr}, edge={edge_level}"
                + (f", cloud={cloud_level}" if cloud_score is not None else "")
            ),
            threshold_value="edge risk_level=high/critical",
            acknowledged=False,
            is_sent_to_user=True,
            is_sent_to_caregiver=True,
            is_sent_to_clinician=True,
        )
    )

    db.commit()

    logger.warning(
        f"Critical alert pushed \u2014 user {current_user.user_id}, "
        f"HR={hr}, edge={edge_level}, cloud={cloud_level}"
    )

    return {
        "message": "Critical alert stored and flagged for clinician review",
        "note": "SSE dashboard updated within 1 second",
        "vital_recorded": True,
        "edge_risk_level": edge_level,
        "cloud_risk_level": cloud_level,
        "cloud_risk_score": cloud_score,
    }


# --- ENDPOINTS: PATIENT READS OWN VITALS ---

# =============================================
# GET_LATEST_VITALS - Patient's most recent reading
# Used by: Mobile app home screen (heart rate ring display)
# Returns: VitalSignResponse with HR, SpO2, BP, timestamp
# Roles: PATIENT (own data)
# =============================================
@router.get("/vitals/latest", response_model=VitalSignResponse)
async def get_latest_vitals(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's most recent vital signs reading.
    
    Used by mobile app home screen and doctor dashboard.
    """
    logger.info(
        "[DIAG][VITALS_GET_LATEST] backend=%s host=%s path=%s user=%s db=%s",
        _backend_instance_id(),
        request.headers.get("host"),
        request.url.path,
        current_user.user_id,
        _db_target(db),
    )

    latest = db.query(VitalSignRecord)\
               .filter(VitalSignRecord.user_id == current_user.user_id)\
               .order_by(VitalSignRecord.timestamp.desc())\
               .first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vital signs found"
        )
    
    return latest


# =============================================
# GET_VITALS_SUMMARY - Aggregated stats for time period
# Used by: Mobile app dashboard cards, trend indicators
# Returns: Avg/min/max HR, SpO2, alert count
# Roles: PATIENT (own data)
# =============================================
@router.get("/vitals/summary")
async def get_vitals_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vital signs summary for the specified period.
    
    Returns aggregated statistics for dashboard charts.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    summary = calculate_vitals_summary(db, current_user.user_id, start_date, end_date)
    
    return summary


# =============================================
# GET_VITALS_HISTORY - Time-series data for charts
# Used by: Mobile app trend graphs, dashboard analytics
# Returns: Paginated list of VitalSignResponse + summary
# Roles: PATIENT (own data)
# =============================================
@router.get("/vitals/history", response_model=VitalSignsHistoryResponse)
async def get_vitals_history(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=1000, description="Records per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get historical vital signs data for trend graphs.
    
    Used by mobile app graphs and doctor dashboard analytics.
    """
    logger.info(
        "[DIAG][VITALS_GET_HISTORY] backend=%s host=%s path=%s user=%s days=%s page=%s per_page=%s db=%s",
        _backend_instance_id(),
        request.headers.get("host"),
        request.url.path,
        current_user.user_id,
        days,
        page,
        per_page,
        _db_target(db),
    )

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Query vitals in date range
    query = db.query(VitalSignRecord)\
              .filter(
                  VitalSignRecord.user_id == current_user.user_id,
                  VitalSignRecord.timestamp >= start_date,
                  VitalSignRecord.timestamp <= end_date
              )\
              .order_by(VitalSignRecord.timestamp.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    vitals = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Calculate summary for the period
    summary = calculate_vitals_summary(db, current_user.user_id, start_date, end_date)
    
    return VitalSignsHistoryResponse(
        vitals=vitals,
        summary=summary,
        total=total,
        page=page,
        per_page=per_page
    )


# =============================================================================
# Clinician/Admin Endpoints
# =============================================================================

# =============================================
# GET_USER_LATEST_VITALS - Clinician view of patient's latest reading
# Used by: Clinician dashboard patient detail view
# Returns: VitalSignResponse with most recent values
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/vitals/user/{user_id}/latest", response_model=VitalSignResponse)
async def get_user_latest_vitals(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get latest vital signs for a specific user.
    
    Clinician/Admin access only.
    """
    logger.info(
        "[DIAG][VITALS_GET_USER_LATEST] backend=%s host=%s path=%s clinician=%s patient=%s db=%s",
        _backend_instance_id(),
        request.headers.get("host"),
        request.url.path,
        current_user.user_id,
        user_id,
        _db_target(db),
    )

    # Check access permissions
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    check_clinician_phi_access(current_user, user)
    
    latest = db.query(VitalSignRecord)\
               .filter(VitalSignRecord.user_id == user_id)\
               .order_by(desc(VitalSignRecord.timestamp))\
               .first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vital signs found for this user"
        )
    
    return latest


# =============================================
# GET_USER_VITALS_SUMMARY - Clinician view of patient stats
# Used by: Clinician dashboard, patient summary cards
# Returns: Aggregated min/max/avg for each vital type
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/vitals/user/{user_id}/summary")
async def get_user_vitals_summary(
    user_id: int,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get vital signs summary for a specific user.
    
    Clinician/Admin access only.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    check_clinician_phi_access(current_user, user)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    summary = calculate_vitals_summary(db, user_id, start_date, end_date)
    
    return summary


# =============================================
# GET_USER_VITALS_HISTORY - Clinician view of patient trends
# Used by: Clinician dashboard charts, detailed patient analysis
# Returns: Paginated VitalSignsHistoryResponse
# Roles: DOCTOR, ADMIN (PHI access required)
# =============================================
@router.get("/vitals/user/{user_id}/history", response_model=VitalSignsHistoryResponse)
async def get_user_vitals_history(
    user_id: int,
    request: Request,
    days: int = Query(7, ge=1, le=90),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get historical vital signs for a specific user.
    
    Clinician/Admin access only.
    """
    logger.info(
        "[DIAG][VITALS_GET_USER_HISTORY] backend=%s host=%s path=%s clinician=%s patient=%s days=%s page=%s per_page=%s db=%s",
        _backend_instance_id(),
        request.headers.get("host"),
        request.url.path,
        current_user.user_id,
        user_id,
        days,
        page,
        per_page,
        _db_target(db),
    )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    check_clinician_phi_access(current_user, user)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    query = db.query(VitalSignRecord)\
              .filter(
                  VitalSignRecord.user_id == user_id,
                  VitalSignRecord.timestamp >= start_date,
                  VitalSignRecord.timestamp <= end_date
              )\
              .order_by(VitalSignRecord.timestamp.desc())
    
    total = query.count()
    vitals = query.offset((page - 1) * per_page).limit(per_page).all()
    
    summary = calculate_vitals_summary(db, user_id, start_date, end_date)
    
    return VitalSignsHistoryResponse(
        vitals=vitals,
        summary=summary,
        total=total,
        page=page,
        per_page=per_page
    )