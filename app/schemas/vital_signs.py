"""
Vital signs data validation.

Defines what heart rate, blood pressure, and other vital sign data
looks like when sent to the API. Checks that all numbers are reasonable
(like heart rate is between 30 and 250 BPM).

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# REQUEST SCHEMAS
#   - VitalSignBase.................... Line 35  (Common fields)
#   - VitalSignCreate.................. Line 60  (Single reading input)
#   - VitalSignBatchCreate............. Line 75  (Batch sync input)
#
# RESPONSE SCHEMAS
#   - VitalSignResponse................ Line 90  (Single reading output)
#   - VitalSignsSummary................ Line 115 (Aggregated stats)
#   - VitalSignsHistoryResponse........ Line 135 (Paginated history)
#   - VitalSignsStats.................. Line 150 (Min/max/avg per metric)
#   - RealTimeVitals................... Line 170 (WebSocket format)
#
# UTILITY SCHEMAS
#   - VitalSignsExportRequest.......... Line 185 (Data export params)
#
# BUSINESS CONTEXT:
# - Field ranges match medical validity
# - Batch sync for offline data
# =============================================================================
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# =============================================================================
# Vital Signs Base Schema
# =============================================================================

class VitalSignBase(BaseModel):
    """
    Base schema for vital sign measurements.
    Core cardiovascular metrics from wearable devices.
    """
    heart_rate: int = Field(..., ge=30, le=250, description="Heart rate in BPM")
    spo2: Optional[float] = Field(None, ge=0, le=100, description="Blood oxygen saturation percentage")
    blood_pressure_systolic: Optional[int] = Field(None, ge=70, le=250, description="Systolic blood pressure (mmHg)")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150, description="Diastolic blood pressure (mmHg)")
    hrv: Optional[float] = Field(None, ge=0, description="Heart rate variability (RMSSD in ms)")
    source_device: Optional[str] = Field(None, max_length=100, description="Wearable device name (e.g., 'Fitbit Charge 6')")
    device_id: Optional[str] = Field(None, max_length=255, description="Unique device identifier")
    timestamp: Optional[datetime] = Field(None, description="Measurement timestamp (UTC)")
    
    @field_validator('blood_pressure_systolic', 'blood_pressure_diastolic')
    def validate_blood_pressure(cls, v):
        # Blood pressure must be positive.
        if v is not None and v <= 0:
            raise ValueError('Blood pressure must be positive')
        return v
    
    @field_validator('spo2')
    def validate_spo2(cls, v):
        # SpO2 must be between 0 and 100.
        if v is not None and (v < 0 or v > 100):
            raise ValueError('SpO2 must be between 0 and 100')
        return v


# =============================================================================
# Vital Sign Creation Schema
# =============================================================================

class VitalSignCreate(VitalSignBase):
    """
    Schema for submitting new vital sign measurements.
    Used by mobile app to send data from wearables.
    """
    pass  # Inherits all fields from base


# =============================================================================
# Vital Sign Batch Upload Schema
# =============================================================================

class VitalSignBatchCreate(BaseModel):
    """
    Schema for batch uploading multiple vital sign records.
    Useful for syncing historical data or bulk imports.
    """
    vitals: List[VitalSignCreate] = Field(..., description="List of vital sign records")


# =============================================================================
# Vital Sign Response Schema
# =============================================================================

class VitalSignResponse(BaseModel):
    """
    Schema for vital sign data in API responses.
    Includes system-generated fields and decrypted data.
    """
    id: int = Field(..., description="Record ID")
    user_id: int = Field(..., description="User ID")
    heart_rate: int = Field(..., description="Heart rate in BPM")
    spo2: Optional[float] = Field(None, description="Blood oxygen saturation percentage")
    blood_pressure: Optional[dict] = Field(None, description="Blood pressure as {'systolic': int, 'diastolic': int}")
    hrv: Optional[float] = Field(None, description="Heart rate variability")
    source_device: Optional[str] = Field(None, description="Wearable device name")
    is_valid: bool = Field(..., description="Data validity flag")
    confidence_score: Optional[float] = Field(None, description="AI confidence score")
    activity_phase: Optional[str] = Field(None, description="Activity phase (resting, active, etc.)")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    class Config:
        from_attributes = True


# =============================================================================
# Vital Signs Summary Schema
# =============================================================================

class VitalSignsSummary(BaseModel):
    """
    Schema for daily/weekly vital signs summaries.
    Aggregated statistics for dashboard visualization.
    """
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    avg_heart_rate: Optional[float] = Field(None, description="Average heart rate")
    min_heart_rate: Optional[int] = Field(None, description="Minimum heart rate")
    max_heart_rate: Optional[int] = Field(None, description="Maximum heart rate")
    avg_spo2: Optional[float] = Field(None, description="Average SpO2")
    min_spo2: Optional[float] = Field(None, description="Minimum SpO2")
    avg_hrv: Optional[float] = Field(None, description="Average HRV")
    total_readings: int = Field(..., description="Total number of readings")
    valid_readings: int = Field(..., description="Number of valid readings")
    alerts_triggered: int = Field(..., description="Number of alerts triggered")


# =============================================================================
# Vital Signs History Response
# =============================================================================

class VitalSignsHistoryResponse(BaseModel):
    """
    Schema for vital signs history with trends.
    Used for charts and graphs in mobile app and dashboard.
    """
    vitals: List[VitalSignResponse] = Field(..., description="List of vital sign records")
    summary: Optional[VitalSignsSummary] = Field(None, description="Period summary")
    total: int = Field(..., description="Total records")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Records per page")


# =============================================================================
# Vital Signs Statistics Schema
# =============================================================================

class VitalSignsStats(BaseModel):
    """
    Schema for comprehensive vital signs statistics.
    Used for dashboard analytics and clinician reports.
    """
    period: str = Field(..., description="Time period (daily, weekly, monthly)")
    heart_rate: dict = Field(..., description="HR statistics")
    spo2: dict = Field(..., description="SpO2 statistics")
    blood_pressure: dict = Field(..., description="BP statistics")
    hrv: dict = Field(..., description="HRV statistics")
    activity_distribution: dict = Field(..., description="Activity phase distribution")
    device_usage: dict = Field(..., description="Device usage statistics")
    alerts_summary: dict = Field(..., description="Alerts summary")


# =============================================================================
# Real-time Vital Signs Schema
# =============================================================================

class RealTimeVitals(BaseModel):
    """
    Schema for real-time vital signs streaming.
    Lightweight format for live monitoring.
    """
    heart_rate: int = Field(..., description="Current heart rate")
    spo2: Optional[float] = Field(None, description="Current SpO2")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    activity_phase: Optional[str] = Field(None, description="Current activity phase")
    risk_level: Optional[str] = Field(None, description="Current risk level (low, moderate, high)")


# =============================================================================
# Vital Signs Export Schema
# =============================================================================

class VitalSignsExportRequest(BaseModel):
    """
    Schema for requesting vital signs data export.
    Supports CSV and PDF formats for compliance.
    """
    start_date: datetime = Field(..., description="Start date for export")
    end_date: datetime = Field(..., description="End date for export")
    format: str = Field(default="csv", description="Export format (csv, pdf)")
    include_raw_data: bool = Field(default=True, description="Include raw measurements")
    include_summaries: bool = Field(default=True, description="Include summary statistics")
    
    @field_validator('format')
    def validate_format(cls, v):
        allowed = ['csv', 'pdf', 'json']
        if v not in allowed:
            raise ValueError(f'Format must be one of: {allowed}')
        return v
    
    @field_validator('end_date')
    def validate_date_range(cls, v):
        # Note: In pydantic v2, cross-field validation is done with @model_validator
        # For now, basic validation
        return v