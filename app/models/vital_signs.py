"""
=============================================================================
ADAPTIV HEALTH - Vital Signs Model
=============================================================================
Stores physiological measurements from wearable devices.
Core data for real-time monitoring and AI analysis.

Data Flow: Wearable → BLE → Mobile App → Cloud API → This Table
=============================================================================
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class VitalSignRecord(Base):
    """
    Vital Sign Record from Data Dictionary (Section 4.1).
    
    Stores physiological data captured from wearable sensors:
    - Heart Rate (BPM) - Primary vital for cardiovascular monitoring
    - SpO2 (Blood oxygen saturation) - Critical for safety alerts
    - Blood Pressure (Systolic/Diastolic) - Cardiovascular load indicator
    - HRV (Heart Rate Variability) - Autonomic function and recovery
    
    Requirements Implemented:
    - REQ-1.1: Real-time heart rate monitoring (≤500ms latency)
    - PERF-1.5: Real-time HR and SpO2 updates displayed on mobile
    """
    
    __tablename__ = "vital_sign_records"
    
    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # -------------------------------------------------------------------------
    # Foreign Key - Links to User
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Heart Rate Data
    # -------------------------------------------------------------------------
    heart_rate = Column(Integer, nullable=False)  # BPM (beats per minute), 30-250 valid range
    
    # -------------------------------------------------------------------------
    # Blood Oxygen Saturation
    # -------------------------------------------------------------------------
    spo2 = Column(Float, nullable=True)  # Percentage (0-100), <90% triggers alert
    
    # -------------------------------------------------------------------------
    # Blood Pressure (mmHg)
    # -------------------------------------------------------------------------
    blood_pressure_systolic = Column(Integer, nullable=True)   # Top number (normal: 90-120)
    blood_pressure_diastolic = Column(Integer, nullable=True)  # Bottom number (normal: 60-80)
    
    # -------------------------------------------------------------------------
    # Heart Rate Variability
    # -------------------------------------------------------------------------
    hrv = Column(Float, nullable=True)  # RMSSD in milliseconds, higher = better recovery
    
    # -------------------------------------------------------------------------
    # Device Information
    # -------------------------------------------------------------------------
    source_device = Column(String(100), nullable=True)  # e.g., "Fitbit Charge 6"
    device_id = Column(String(255), nullable=True)      # Unique device identifier
    
    # -------------------------------------------------------------------------
    # Data Quality Flags
    # -------------------------------------------------------------------------
    is_valid = Column(Boolean, default=True, nullable=False)  # True = valid reading
    confidence_score = Column(Float, default=1.0, nullable=False)  # 0-1, AI confidence
    
    # Flag for readings that triggered edge AI processing
    processed_by_edge_ai = Column(Boolean, default=False, nullable=False)
    
    # -------------------------------------------------------------------------
    # Activity Context (optional)
    # -------------------------------------------------------------------------
    activity_session_id = Column(Integer, nullable=True)  # Link to activity if during workout
    activity_phase = Column(String(20), nullable=True)  # resting, active, recovery
    
    # -------------------------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------------------------
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # When record was created in our system (may differ from device timestamp)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="vital_signs")
    
    # -------------------------------------------------------------------------
    # Indexes for Performance
    # -------------------------------------------------------------------------
    __table_args__ = (
        # Composite index for querying user's vitals in time range
        Index('idx_vital_user_timestamp', 'user_id', 'timestamp'),
        # Index for finding abnormal readings
        Index('idx_vital_heart_rate', 'heart_rate'),
        # Index for low oxygen alerts
        Index('idx_vital_spo2', 'spo2'),
        # Index for activity-linked vitals
        Index('idx_vital_activity', 'activity_session_id'),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<VitalSignRecord(id={self.id}, user_id={self.user_id}, hr={self.heart_rate}, ts={self.timestamp})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "blood_pressure": {
                "systolic": self.blood_pressure_systolic,
                "diastolic": self.blood_pressure_diastolic
            } if self.blood_pressure_systolic else None,
            "hrv": self.hrv,
            "source_device": self.source_device,
            "is_valid": self.is_valid,
            "confidence_score": self.confidence_score,
            "activity_phase": self.activity_phase,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    def is_heart_rate_abnormal(self, min_hr: int = 40, max_hr: int = 180) -> bool:
        """
        Check if heart rate is outside normal bounds.
        
        Args:
            min_hr: Minimum acceptable HR (default 40 BPM)
            max_hr: Maximum acceptable HR (default 180 BPM)
            
        Returns:
            True if HR is abnormal
        """
        return self.heart_rate < min_hr or self.heart_rate > max_hr
    
    def is_spo2_low(self, threshold: float = 90.0) -> bool:
        """
        Check if blood oxygen is dangerously low.
        
        Args:
            threshold: SpO2 percentage below which is dangerous
            
        Returns:
            True if SpO2 is below threshold
        """
        if self.spo2 is None:
            return False
        return self.spo2 < threshold
    
    def is_blood_pressure_high(self, sys_threshold: int = 140, dia_threshold: int = 90) -> bool:
        """
        Check if blood pressure is elevated (hypertension stage 2).
        
        Returns:
            True if BP exceeds thresholds
        """
        if self.blood_pressure_systolic is None:
            return False
        return (
            self.blood_pressure_systolic >= sys_threshold or
            self.blood_pressure_diastolic >= dia_threshold
        )
    
    def get_risk_indicators(self) -> list:
        """
        Get list of risk indicators present in this reading.
        
        Returns:
            List of risk indicator strings
        """
        indicators = []
        
        if self.is_heart_rate_abnormal():
            if self.heart_rate < 40:
                indicators.append("bradycardia")
            else:
                indicators.append("tachycardia")
        
        if self.is_spo2_low():
            indicators.append("hypoxemia")
        
        if self.is_blood_pressure_high():
            indicators.append("hypertension")
        
        return indicators