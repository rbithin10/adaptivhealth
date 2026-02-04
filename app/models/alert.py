"""
=============================================================================
ADAPTIV HEALTH - Alert Model
=============================================================================
Records emergency and warning notifications triggered by abnormal readings.
Implements REQ-1.3: Emergency Alert System from SRS.

Requirements:
- Emergency alerts must be issued within 3 seconds
- Automatic notification to caregivers/clinicians
- Full audit trail for HIPAA compliance
=============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import json


class AlertType(str, enum.Enum):
    """
    Types of alerts the system can generate.
    Based on SRS REQ-1.3 and Design Doc Section 5.
    """
    # Heart Rate Alerts
    HIGH_HEART_RATE = "high_heart_rate"           # HR exceeds safe threshold
    LOW_HEART_RATE = "low_heart_rate"             # HR below safe threshold (bradycardia)
    RAPID_HR_INCREASE = "rapid_hr_increase"       # Sudden HR spike
    
    # Oxygen Alerts
    LOW_OXYGEN = "low_oxygen"                      # SpO2 below 90%
    CRITICAL_OXYGEN = "critical_oxygen"            # SpO2 below 85%
    
    # Rhythm Alerts
    IRREGULAR_RHYTHM = "irregular_rhythm"          # HRV anomaly detected
    ARRHYTHMIA_SUSPECTED = "arrhythmia_suspected"  # Potential arrhythmia
    
    # Blood Pressure Alerts
    HIGH_BLOOD_PRESSURE = "high_blood_pressure"    # BP spike (>140/90)
    HYPERTENSIVE_CRISIS = "hypertensive_crisis"   # BP >180/120
    
    # Exertion Alerts
    OVEREXERTION = "overexertion"                 # Combined risk indicators
    PROLONGED_HIGH_INTENSITY = "prolonged_high_intensity"  # Too long in danger zone
    
    # Recovery Alerts
    POOR_RECOVERY = "poor_recovery"               # Slow recovery pattern
    RECOVERY_CONCERN = "recovery_concern"          # HR not dropping post-exercise
    
    # System Alerts
    DEVICE_DISCONNECTED = "device_disconnected"   # Wearable connection lost
    SENSOR_ERROR = "sensor_error"                 # Invalid sensor readings
    SYSTEM = "system"                             # General system alerts


class SeverityLevel(str, enum.Enum):
    """
    Alert severity levels determining urgency and response.
    Maps to UI colors and notification priority.
    """
    INFO = "info"           # Blue - Informational, no action needed
    WARNING = "warning"     # Yellow - Caution, consider adjusting
    CRITICAL = "critical"   # Orange - Immediate action required
    EMERGENCY = "emergency" # Red - Contact emergency services/caregivers


class Alert(Base):
    """
    Alert from Data Dictionary (Section 4.1).
    
    Records safety notifications created when:
    - Vital signs exceed safe thresholds
    - AI detects concerning patterns
    - System identifies emergency situations
    
    Flow:
    1. Edge AI or Cloud AI detects anomaly
    2. Alert record created in database
    3. Push notification sent to user device
    4. If CRITICAL/EMERGENCY, notify caregiver and clinician
    5. Alert tracked until acknowledged/resolved
    """
    
    __tablename__ = "alerts"
    
    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # -------------------------------------------------------------------------
    # Foreign Key
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Alert Classification
    # -------------------------------------------------------------------------
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity_level = Column(Enum(SeverityLevel), default=SeverityLevel.WARNING, nullable=False, index=True)
    
    # -------------------------------------------------------------------------
    # Alert Content
    # -------------------------------------------------------------------------
    title = Column(String(100), nullable=False)  # Short title for notification
    alert_message = Column(String(500), nullable=False)  # User-facing message
    technical_details = Column(Text, nullable=True)  # JSON with detailed data for clinicians
    action_required = Column(String(200), nullable=True)  # What user should do
    
    # -------------------------------------------------------------------------
    # Trigger Values
    # -------------------------------------------------------------------------
    trigger_value = Column(String(100), nullable=True)   # e.g., "HR: 185 BPM"
    threshold_value = Column(String(100), nullable=True) # e.g., "Max safe: 150 BPM"
    trigger_metric = Column(String(50), nullable=True)   # heart_rate, spo2, etc.
    
    # -------------------------------------------------------------------------
    # Related Risk Assessment
    # -------------------------------------------------------------------------
    risk_assessment_id = Column(Integer, nullable=True)
    risk_score = Column(Float, nullable=True)
    
    # -------------------------------------------------------------------------
    # Related Activity Session
    # -------------------------------------------------------------------------
    activity_session_id = Column(Integer, nullable=True)
    
    # -------------------------------------------------------------------------
    # Notification Status
    # -------------------------------------------------------------------------
    # User notification
    is_sent_to_user = Column(Boolean, default=False)
    user_notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_method = Column(String(50), nullable=True)  # push, sms, email
    
    # User acknowledgment
    is_acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(100), nullable=True)  # user, caregiver, clinician
    
    # Caregiver notification
    is_sent_to_caregiver = Column(Boolean, default=False)
    caregiver_notified_at = Column(DateTime(timezone=True), nullable=True)
    caregiver_response = Column(String(200), nullable=True)
    
    # Clinician notification
    is_sent_to_clinician = Column(Boolean, default=False)
    clinician_notified_at = Column(DateTime(timezone=True), nullable=True)
    clinician_id = Column(Integer, nullable=True)  # Which clinician was notified
    clinician_response = Column(Text, nullable=True)
    
    # -------------------------------------------------------------------------
    # Resolution
    # -------------------------------------------------------------------------
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)  # user, system, clinician
    resolution_notes = Column(Text, nullable=True)
    resolution_action = Column(String(100), nullable=True)  # rest_taken, medication, etc.
    
    # Was this a false positive?
    is_false_positive = Column(Boolean, default=False)
    false_positive_reason = Column(String(200), nullable=True)
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    alert_time = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="alerts")
    
    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_alert_user_time', 'user_id', 'alert_time'),
        Index('idx_alert_severity', 'severity_level'),
        Index('idx_alert_unresolved', 'is_resolved', 'is_acknowledged'),
        Index('idx_alert_type_severity', 'alert_type', 'severity_level'),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type.value}, severity={self.severity_level.value})>"
    
    @property
    def requires_immediate_action(self) -> bool:
        """Check if alert requires immediate response."""
        return self.severity_level in [SeverityLevel.CRITICAL, SeverityLevel.EMERGENCY]
    
    @property
    def requires_caregiver_notification(self) -> bool:
        """Check if caregiver should be notified."""
        return self.severity_level in [SeverityLevel.CRITICAL, SeverityLevel.EMERGENCY]
    
    @property
    def requires_clinician_notification(self) -> bool:
        """Check if clinician should be notified."""
        return self.severity_level == SeverityLevel.EMERGENCY
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active (not resolved or acknowledged)."""
        return not self.is_resolved and not self.is_acknowledged
    
    def acknowledge(self, acknowledged_by: str = "user") -> None:
        """
        Mark alert as acknowledged.
        
        Args:
            acknowledged_by: Who acknowledged (user, caregiver, clinician)
        """
        from datetime import datetime, timezone
        self.is_acknowledged = True
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by = acknowledged_by
    
    def resolve(self, resolved_by: str = "user", notes: str = None, action: str = None) -> None:
        """
        Mark alert as resolved.
        
        Args:
            resolved_by: Who resolved (user, system, clinician)
            notes: Resolution notes
            action: Action taken to resolve
        """
        from datetime import datetime, timezone
        self.is_resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        if notes:
            self.resolution_notes = notes
        if action:
            self.resolution_action = action
    
    def mark_false_positive(self, reason: str = None) -> None:
        """Mark this alert as a false positive."""
        self.is_false_positive = True
        self.false_positive_reason = reason
        self.resolve(resolved_by="user", notes="Marked as false positive")
    
    def set_technical_details(self, details: dict) -> None:
        """Store technical details as JSON."""
        self.technical_details = json.dumps(details)
    
    def get_technical_details(self) -> dict:
        """Retrieve technical details from JSON."""
        if self.technical_details:
            return json.loads(self.technical_details)
        return {}
    
    def get_severity_color(self) -> str:
        """Get color code for UI display."""
        colors = {
            SeverityLevel.INFO: "#3B82F6",      # Blue
            SeverityLevel.WARNING: "#F59E0B",   # Yellow/Amber
            SeverityLevel.CRITICAL: "#F97316",  # Orange
            SeverityLevel.EMERGENCY: "#EF4444", # Red
        }
        return colors.get(self.severity_level, "#6B7280")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "alert_type": self.alert_type.value,
            "severity_level": self.severity_level.value,
            "severity_color": self.get_severity_color(),
            "title": self.title,
            "message": self.alert_message,
            "action_required": self.action_required,
            "trigger_value": self.trigger_value,
            "threshold_value": self.threshold_value,
            "is_acknowledged": self.is_acknowledged,
            "is_resolved": self.is_resolved,
            "requires_immediate_action": self.requires_immediate_action,
            "alert_time": self.alert_time.isoformat() if self.alert_time else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }