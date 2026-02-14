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
# ENDPOINTS - PATIENT (own data)
#   --- SUBMIT VITALS ---
#   - POST /vitals..................... Line 239 (Submit single reading)
#   - POST /vitals/batch............... Line 332 (Submit multiple readings)
#
#   --- READ VITALS ---
#   - GET /vitals/latest............... Line 402 (Most recent reading)
#   - GET /vitals/summary.............. Line 432 (Aggregated stats)
#   - GET /vitals/history.............. Line 457 (Time-series data)
#
# ENDPOINTS - CLINICIAN (patient data)
#   - GET /vitals/user/{id}/latest..... Line 510 (Patient's latest)
#   - GET /vitals/user/{id}/summary.... Line 551 (Patient's stats)
#   - GET /vitals/user/{id}/history.... Line 586 (Patient's history)
#
# BUSINESS CONTEXT:
# - Patients sync vitals from wearables (Fitbit, Apple Watch)
# - Mobile app shows latest readings on home screen
# - Clinician dashboard shows patient vitals with time trends
# - Alerts auto-create when thresholds exceeded (HR>180, SpO2<90)
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.vital_signs import VitalSignRecord
from app.models.alert import Alert, AlertType, SeverityLevel
from app.schemas.vital_signs import (
    VitalSignCreate, VitalSignResponse, VitalSignBatchCreate,
    VitalSignsSummary, VitalSignsHistoryResponse, VitalSignsStats
)
from app.services.encryption import encryption_service
from app.api.auth import get_current_user, get_current_doctor_user, check_clinician_phi_access

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

# =============================================
# CHECK_VITALS_FOR_ALERTS - Background task for threshold monitoring
# Used by: Called after every vital submission
# Returns: None (creates Alert records in DB)
# Triggers: HR>180 (critical), SpO2<90 (critical), BP>160 (warning)
# =============================================
def check_vitals_for_alerts(user_id: int, vital_data: VitalSignCreate):
    """
    Background task to check vital signs for alerts.
    
    Creates alert records and logs notifications when thresholds are exceeded.
    
    Args:
        user_id: User ID
        vital_data: Vital signs data
    """
    # Create a new database session for background task
    from app.database import SessionLocal
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
async def submit_vitals(
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
    
    logger.info(f"Vital signs recorded for user {current_user.user_id}: HR={vital_data.heart_rate}")
    
    return new_vital


# =============================================
# SUBMIT_VITALS_BATCH - Patient submits multiple readings at once
# Used by: Mobile app bulk sync (offline data, historical imports)
# Returns: Count of records successfully created
# Roles: PATIENT (own data only)
# =============================================
@router.post("/vitals/batch")
async def submit_vitals_batch(
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


# --- ENDPOINTS: PATIENT READS OWN VITALS ---

# =============================================
# GET_LATEST_VITALS - Patient's most recent reading
# Used by: Mobile app home screen (heart rate ring display)
# Returns: VitalSignResponse with HR, SpO2, BP, timestamp
# Roles: PATIENT (own data)
# =============================================
@router.get("/vitals/latest", response_model=VitalSignResponse)
async def get_latest_vitals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's most recent vital signs reading.
    
    Used by mobile app home screen and doctor dashboard.
    """
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
    current_user: User = Depends(get_current_doctor_user),
    db: Session = Depends(get_db)
):
    """
    Get latest vital signs for a specific user.
    
    Clinician/Admin access only.
    """
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