"""
=============================================================================
ADAPTIV HEALTH - Activity Session Model
=============================================================================
Tracks workout and activity sessions with performance metrics.
Used for adaptive exercise recommendations and recovery analysis.
=============================================================================
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ActivityType(str, enum.Enum):
    """Types of physical activities tracked by the system."""
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength"
    YOGA = "yoga"
    STRETCHING = "stretching"
    CARDIO = "cardio"
    HIIT = "hiit"
    REHAB = "rehab"           # Cardiac rehabilitation exercises
    BREATHING = "breathing"   # Breathing exercises
    OTHER = "other"


class ActivityPhase(str, enum.Enum):
    """
    Activity phases from SegmentActivityPhase algorithm (Design Doc Section 5).
    Used to classify user's current cardiovascular state during monitoring.
    
    Detection Logic:
    - RESTING: current_HR < baseline_HR + 10
    - ACTIVE: baseline_HR + 10 <= current_HR <= baseline_HR + 45
    - HIGH_INTENSITY: current_HR > baseline_HR + 45
    - RECOVERY: HR dropping for 30+ seconds
    """
    RESTING = "resting"
    WARMUP = "warmup"
    ACTIVE = "active"
    HIGH_INTENSITY = "high_intensity"
    COOLDOWN = "cooldown"
    RECOVERY = "recovery"


class SessionStatus(str, enum.Enum):
    """Status of an activity session."""
    SCHEDULED = "scheduled"    # Planned but not started
    IN_PROGRESS = "in_progress"  # Currently active
    PAUSED = "paused"          # Temporarily paused
    COMPLETED = "completed"    # Finished normally
    CANCELLED = "cancelled"    # User cancelled
    INTERRUPTED = "interrupted"  # Stopped due to alert/safety


class ActivitySession(Base):
    """
    Activity Session from Data Dictionary (Section 4.1).
    
    Records individual workout or activity sessions with:
    - Duration and timing
    - Activity type and intensity
    - Heart rate statistics
    - Recovery metrics
    - AI risk analysis results
    
    Used for:
    - Post-session summaries (REQ-1.4)
    - AI model training and personalization
    - Progress tracking and trend analysis
    - Exercise recommendation refinement
    """
    
    __tablename__ = "activity_sessions"
    
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
    # Session Timing
    # -------------------------------------------------------------------------
    scheduled_start = Column(DateTime(timezone=True), nullable=True)  # If pre-scheduled
    start_time = Column(DateTime(timezone=True), nullable=True)  # Actual start
    end_time = Column(DateTime(timezone=True), nullable=True)    # Actual end
    duration_minutes = Column(Float, nullable=True)  # Calculated from start/end
    
    # -------------------------------------------------------------------------
    # Activity Information
    # -------------------------------------------------------------------------
    activity_type = Column(Enum(ActivityType), default=ActivityType.OTHER, nullable=False)
    activity_name = Column(String(100), nullable=True)  # Custom name like "Morning Walk"
    description = Column(Text, nullable=True)  # Additional details
    
    # -------------------------------------------------------------------------
    # Session Status
    # -------------------------------------------------------------------------
    status = Column(Enum(SessionStatus), default=SessionStatus.SCHEDULED, nullable=False)
    
    # -------------------------------------------------------------------------
    # Heart Rate Statistics
    # -------------------------------------------------------------------------
    baseline_heart_rate = Column(Integer, nullable=True)  # User's baseline at session start
    average_heart_rate = Column(Integer, nullable=True)   # Session average
    peak_heart_rate = Column(Integer, nullable=True)      # Highest recorded
    min_heart_rate = Column(Integer, nullable=True)       # Lowest recorded
    
    # -------------------------------------------------------------------------
    # Time in Heart Rate Zones (minutes)
    # -------------------------------------------------------------------------
    time_in_rest_zone = Column(Float, default=0)      # <50% max HR
    time_in_light_zone = Column(Float, default=0)     # 50-60% max HR
    time_in_moderate_zone = Column(Float, default=0)  # 60-70% max HR (fat burn)
    time_in_vigorous_zone = Column(Float, default=0)  # 70-80% max HR (cardio)
    time_in_high_zone = Column(Float, default=0)      # 80-90% max HR (performance)
    time_in_max_zone = Column(Float, default=0)       # >90% max HR (peak)
    
    # Color-coded zones for UI (simplified)
    time_in_safe_zone = Column(Float, default=0)      # Green zone
    time_in_caution_zone = Column(Float, default=0)   # Yellow zone
    time_in_danger_zone = Column(Float, default=0)    # Red zone
    
    # -------------------------------------------------------------------------
    # Recovery Metrics
    # -------------------------------------------------------------------------
    recovery_time_seconds = Column(Integer, nullable=True)  # Time for HR to return to baseline
    recovery_heart_rate_1min = Column(Integer, nullable=True)  # HR at 1 min post-exercise
    recovery_heart_rate_2min = Column(Integer, nullable=True)  # HR at 2 min post-exercise
    recovery_score = Column(Float, nullable=True)  # 0-100 recovery quality score
    
    # -------------------------------------------------------------------------
    # Performance Metrics
    # -------------------------------------------------------------------------
    calories_burned = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)  # If applicable (walking, running, cycling)
    steps = Column(Integer, nullable=True)  # If step tracking available
    intensity_score = Column(Float, nullable=True)  # 0-10 overall intensity
    
    # -------------------------------------------------------------------------
    # AI Analysis Results
    # -------------------------------------------------------------------------
    session_risk_score = Column(Float, nullable=True)  # Overall risk during session (0-1)
    max_risk_score = Column(Float, nullable=True)  # Highest risk point during session
    alerts_triggered = Column(Integer, default=0)  # Number of safety alerts
    recommendation_followed = Column(Boolean, nullable=True)  # Did user follow AI advice?
    
    # -------------------------------------------------------------------------
    # User Feedback
    # -------------------------------------------------------------------------
    user_rating = Column(Integer, nullable=True)  # 1-5 star rating
    perceived_exertion = Column(Integer, nullable=True)  # RPE scale 1-10
    user_notes = Column(Text, nullable=True)  # User comments
    feeling_before = Column(String(20), nullable=True)  # good, okay, tired
    feeling_after = Column(String(20), nullable=True)  # better, same, worse
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="activity_sessions")
    
    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_activity_user_date', 'user_id', 'start_time'),
        Index('idx_activity_status', 'status'),
        Index('idx_activity_type', 'activity_type'),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<ActivitySession(id={self.id}, user_id={self.user_id}, type={self.activity_type.value}, status={self.status.value})>"
    
    def calculate_duration(self) -> float:
        """Calculate and update session duration in minutes."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = delta.total_seconds() / 60
            return self.duration_minutes
        return 0.0
    
    def start_session(self) -> None:
        """Mark session as started."""
        from datetime import datetime, timezone
        self.status = SessionStatus.IN_PROGRESS
        self.start_time = datetime.now(timezone.utc)
    
    def end_session(self) -> None:
        """Mark session as completed and calculate duration."""
        from datetime import datetime, timezone
        self.status = SessionStatus.COMPLETED
        self.end_time = datetime.now(timezone.utc)
        self.calculate_duration()
    
    def pause_session(self) -> None:
        """Pause the session."""
        self.status = SessionStatus.PAUSED
    
    def resume_session(self) -> None:
        """Resume a paused session."""
        self.status = SessionStatus.IN_PROGRESS
    
    def cancel_session(self) -> None:
        """Cancel the session."""
        self.status = SessionStatus.CANCELLED
    
    def interrupt_session(self) -> None:
        """Mark session as interrupted (due to safety alert)."""
        from datetime import datetime, timezone
        self.status = SessionStatus.INTERRUPTED
        self.end_time = datetime.now(timezone.utc)
        self.calculate_duration()
    
    def get_zone_summary(self) -> dict:
        """Get time spent in each heart rate zone."""
        return {
            "rest": self.time_in_rest_zone,
            "light": self.time_in_light_zone,
            "moderate": self.time_in_moderate_zone,
            "vigorous": self.time_in_vigorous_zone,
            "high": self.time_in_high_zone,
            "max": self.time_in_max_zone,
        }
    
    def calculate_recovery_score(self) -> float:
        """
        Calculate recovery score based on HR recovery data.
        Better recovery = faster HR drop after exercise.
        
        Returns:
            Score from 0-100
        """
        if not self.peak_heart_rate or not self.recovery_heart_rate_1min:
            return 0.0
        
        # Calculate HR drop in first minute
        hr_drop = self.peak_heart_rate - self.recovery_heart_rate_1min
        
        # Score based on recovery (>30 BPM drop in 1 min = excellent)
        if hr_drop >= 30:
            score = 100
        elif hr_drop >= 20:
            score = 80
        elif hr_drop >= 12:
            score = 60
        else:
            score = max(0, hr_drop * 5)
        
        self.recovery_score = score
        return score