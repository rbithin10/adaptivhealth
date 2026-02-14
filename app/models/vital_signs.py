"""
=============================================================================
ADAPTIV HEALTH - Vital Signs Model
=============================================================================
SQLAlchemy model mapped to Massoud's AWS RDS 'vital_signs' table.
50,000 rows of cardiac patient vital sign readings.

Data Flow: Wearable → BLE → Mobile App → Cloud API → This Table

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CLASS: VitalSignRecord (SQLAlchemy Model)
#   - Primary Key...................... Line 35  (reading_id)
#   - Foreign Key...................... Line 40  (user_id → users)
#   - Vital Sign Columns............... Line 50  (heart_rate, spo2, etc.)
#   - Metadata Columns................. Line 75  (device_type, source, etc.)
#   - Timestamps....................... Line 95  (timestamp, created_at)
#   - Relationships.................... Line 105 (user)
#   - Indexes.......................... Line 115 (composite indexes)
#
# BUSINESS CONTEXT:
# - 50k+ rows of wearable sensor data
# - Critical for ML risk prediction
# - Real-time sync from mobile app
# =============================================================================
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class VitalSignRecord(Base):
    """
    Maps to Massoud's 'vital_signs' table on AWS RDS.
    Column names match exactly what's in the database.
    """

    __tablename__ = "vital_signs"

    # -------------------------------------------------------------------------
    # Primary Key - matches Massoud's reading_id
    # -------------------------------------------------------------------------
    reading_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Foreign Key - matches Massoud's user_id reference
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Massoud's original columns (already in AWS RDS - 50K rows)
    # -------------------------------------------------------------------------
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    heart_rate = Column(Integer, nullable=False)
    spo2 = Column(Float, nullable=True)  # Changed to Float to support decimal values (e.g., 97.5%)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    hrv = Column(Float, nullable=True)
    activity_type = Column(String(50), nullable=True)
    is_anomaly = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # -------------------------------------------------------------------------
    # Bithin's extra columns (to be added via ALTER TABLE)
    # -------------------------------------------------------------------------
    source_device = Column(String(100), nullable=True)
    device_id = Column(String(255), nullable=True)
    is_valid = Column(Boolean, default=True, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=True)
    processed_by_edge_ai = Column(Boolean, default=False, nullable=True)
    activity_phase = Column(String(20), nullable=True)

    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="vital_signs")

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_vital_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_vital_heart_rate', 'heart_rate'),
        {'extend_existing': True}
    )

    # -------------------------------------------------------------------------
    # Convenience properties for API compatibility
    # -------------------------------------------------------------------------
    @property
    def id(self):
        """Alias for reading_id."""
        return self.reading_id

    @property
    def blood_pressure_systolic(self):
        """Alias for systolic_bp."""
        return self.systolic_bp

    @property
    def blood_pressure_diastolic(self):
        """Alias for diastolic_bp."""
        return self.diastolic_bp

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<VitalSign(reading_id={self.reading_id}, user_id={self.user_id}, hr={self.heart_rate})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.reading_id,
            "user_id": self.user_id,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "blood_pressure": {
                "systolic": self.systolic_bp,
                "diastolic": self.diastolic_bp
            } if self.systolic_bp else None,
            "hrv": self.hrv,
            "activity_type": self.activity_type,
            "source_device": self.source_device,
            "is_anomaly": self.is_anomaly,
            "is_valid": self.is_valid,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def is_heart_rate_abnormal(self, min_hr: int = 40, max_hr: int = 180) -> bool:
        """Check if heart rate is outside normal bounds."""
        return self.heart_rate < min_hr or self.heart_rate > max_hr

    def is_spo2_low(self, threshold: float = 90.0) -> bool:
        """Check if blood oxygen is dangerously low."""
        if self.spo2 is None:
            return False
        return self.spo2 < threshold

    def get_risk_indicators(self) -> list:
        """Get list of risk indicators in this reading."""
        indicators = []
        if self.is_heart_rate_abnormal():
            indicators.append("bradycardia" if self.heart_rate < 40 else "tachycardia")
        if self.is_spo2_low():
            indicators.append("hypoxemia")
        return indicators
