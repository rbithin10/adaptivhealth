"""
=============================================================================
ADAPTIV HEALTH - Exercise Recommendation Model
=============================================================================
Stores AI-generated personalized workout recommendations.
Implements REQ-1.2: Adaptive AI Exercise Feedback from SRS.

The AI system generates recommendations based on:
- Current cardiovascular state
- Recent risk assessments
- Historical performance data
- Recovery patterns
- Medical history
=============================================================================
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, Boolean, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import json


class IntensityLevel(str, enum.Enum):
    """
    Exercise intensity levels for recommendations.
    Based on percentage of maximum heart rate.
    """
    VERY_LIGHT = "very_light"   # <50% max HR - Recovery, gentle movement
    LIGHT = "light"             # 50-60% max HR - Warm up, cool down
    MODERATE = "moderate"       # 60-70% max HR - Fat burning, endurance
    VIGOROUS = "vigorous"       # 70-80% max HR - Cardio training
    HIGH = "high"               # 80-90% max HR - Performance training
    MAXIMUM = "maximum"         # 90-100% max HR - Peak effort (rarely recommended)


class RecommendationType(str, enum.Enum):
    """Types of recommendations the AI can generate."""
    DAILY_WORKOUT = "daily_workout"      # Regular exercise plan
    RECOVERY_DAY = "recovery_day"        # Rest and light activity
    REHABILITATION = "rehabilitation"     # Post-cardiac event rehab program
    BREATHING = "breathing"               # Breathing exercises
    STRETCHING = "stretching"             # Flexibility and mobility
    LIFESTYLE = "lifestyle"               # General health tips
    INTENSITY_ADJUSTMENT = "intensity_adjustment"  # Real-time adjustment during workout
    COOLDOWN = "cooldown"                 # Post-exercise cooldown
    WARMUP = "warmup"                     # Pre-exercise warmup


class RecommendationStatus(str, enum.Enum):
    """Status of a recommendation."""
    PENDING = "pending"        # Generated but not started
    ACTIVE = "active"          # Currently being followed
    COMPLETED = "completed"    # Successfully completed
    SKIPPED = "skipped"        # User skipped
    MODIFIED = "modified"      # User modified the recommendation
    EXPIRED = "expired"        # Validity period passed


class ExerciseRecommendation(Base):
    """
    Exercise Recommendation from Data Dictionary (Section 4.1).
    
    AI-generated personalized workout recommendations that adapt to:
    - User's current cardiovascular condition
    - Recent activity and recovery status
    - Risk assessment results
    - Time of day and user preferences
    
    Requirements:
    - REQ-1.2: Adaptive feedback within 2 seconds
    - Personalized to user's cardiovascular condition
    - Safe intensity within calculated limits
    - Interpretable AI (explain why recommendation was made)
    """
    
    __tablename__ = "exercise_recommendations"
    
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
    # Recommendation Type and Status
    # -------------------------------------------------------------------------
    recommendation_type = Column(
        Enum(RecommendationType),
        default=RecommendationType.DAILY_WORKOUT,
        nullable=False
    )
    status = Column(
        Enum(RecommendationStatus),
        default=RecommendationStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # -------------------------------------------------------------------------
    # Exercise Details
    # -------------------------------------------------------------------------
    title = Column(String(100), nullable=False)  # e.g., "Morning Light Walk"
    suggested_activity = Column(String(100), nullable=False)  # e.g., "Walking"
    intensity_level = Column(Enum(IntensityLevel), default=IntensityLevel.MODERATE, nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Recommended duration
    
    # -------------------------------------------------------------------------
    # Heart Rate Targets
    # -------------------------------------------------------------------------
    target_heart_rate_min = Column(Integer, nullable=True)   # Lower bound of safe zone
    target_heart_rate_max = Column(Integer, nullable=True)   # Upper bound of safe zone
    target_heart_rate_avg = Column(Integer, nullable=True)   # Target average HR
    
    # -------------------------------------------------------------------------
    # Additional Metrics (if applicable)
    # -------------------------------------------------------------------------
    target_distance_km = Column(Float, nullable=True)        # For walking/running/cycling
    target_steps = Column(Integer, nullable=True)            # Step goal
    target_calories = Column(Float, nullable=True)           # Calorie burn target
    sets = Column(Integer, nullable=True)                    # For strength exercises
    reps = Column(Integer, nullable=True)                    # Repetitions per set
    rest_between_sets_seconds = Column(Integer, nullable=True)
    
    # -------------------------------------------------------------------------
    # Detailed Instructions
    # -------------------------------------------------------------------------
    description = Column(Text, nullable=True)      # Full exercise description
    instructions = Column(Text, nullable=True)     # Step-by-step guide (JSON array)
    warmup_instructions = Column(Text, nullable=True)
    cooldown_instructions = Column(Text, nullable=True)
    modifications = Column(Text, nullable=True)    # Easier/harder variations
    warnings = Column(Text, nullable=True)         # Safety warnings
    
    # -------------------------------------------------------------------------
    # Validity Period
    # -------------------------------------------------------------------------
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)  # Suggested time
    
    # -------------------------------------------------------------------------
    # Completion Tracking
    # -------------------------------------------------------------------------
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Float, nullable=True)
    actual_avg_heart_rate = Column(Integer, nullable=True)
    completion_percentage = Column(Float, nullable=True)  # 0-100
    
    # -------------------------------------------------------------------------
    # User Feedback
    # -------------------------------------------------------------------------
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)
    perceived_difficulty = Column(Integer, nullable=True)  # 1-10 scale
    would_do_again = Column(Boolean, nullable=True)
    
    # -------------------------------------------------------------------------
    # AI Generation Info
    # -------------------------------------------------------------------------
    generated_by = Column(String(50), default="cloud_ai")  # edge_ai, cloud_ai, clinician
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)  # AI confidence (0-1)
    
    # -------------------------------------------------------------------------
    # Basis for Recommendation (Interpretable AI)
    # -------------------------------------------------------------------------
    based_on_risk_assessment_id = Column(Integer, nullable=True)
    based_on_recent_sessions = Column(Integer, default=0)  # How many sessions considered
    reasoning_json = Column(Text, nullable=True)  # Why this was recommended
    
    # Factors that influenced the recommendation
    factors_considered = Column(Text, nullable=True)  # JSON array of factors
    
    # -------------------------------------------------------------------------
    # Related Activity Session
    # -------------------------------------------------------------------------
    activity_session_id = Column(Integer, nullable=True)  # If linked to a session
    
    # -------------------------------------------------------------------------
    # Priority and Ordering
    # -------------------------------------------------------------------------
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest
    sequence_order = Column(Integer, nullable=True)  # Order in a workout plan
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="recommendations")
    
    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_rec_user_date', 'user_id', 'created_at'),
        Index('idx_rec_status', 'status'),
        Index('idx_rec_type', 'recommendation_type'),
        Index('idx_rec_valid', 'valid_from', 'valid_until'),
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<ExerciseRecommendation(id={self.id}, activity={self.suggested_activity}, intensity={self.intensity_level.value})>"
    
    @property
    def is_active(self) -> bool:
        """Check if recommendation is currently active and valid."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        if self.status != RecommendationStatus.ACTIVE and self.status != RecommendationStatus.PENDING:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        return True
    
    @property
    def is_expired(self) -> bool:
        """Check if recommendation has expired."""
        from datetime import datetime, timezone
        if self.valid_until:
            return datetime.now(timezone.utc) > self.valid_until
        return False
    
    def mark_completed(self, actual_duration: float = None, actual_hr: int = None) -> None:
        """
        Mark recommendation as completed.
        
        Args:
            actual_duration: Actual duration in minutes
            actual_hr: Actual average heart rate
        """
        from datetime import datetime, timezone
        self.is_completed = True
        self.completed_at = datetime.now(timezone.utc)
        self.status = RecommendationStatus.COMPLETED
        
        if actual_duration:
            self.actual_duration_minutes = actual_duration
            self.completion_percentage = min(100, (actual_duration / self.duration_minutes) * 100)
        
        if actual_hr:
            self.actual_avg_heart_rate = actual_hr
    
    def skip(self) -> None:
        """Mark recommendation as skipped."""
        self.status = RecommendationStatus.SKIPPED
    
    def expire(self) -> None:
        """Mark recommendation as expired."""
        self.status = RecommendationStatus.EXPIRED
    
    def activate(self) -> None:
        """Set recommendation as active."""
        self.status = RecommendationStatus.ACTIVE
    
    def get_heart_rate_zone_description(self) -> str:
        """Get human-readable description of target heart rate zone."""
        if self.target_heart_rate_min and self.target_heart_rate_max:
            return f"Keep your heart rate between {self.target_heart_rate_min} and {self.target_heart_rate_max} BPM"
        elif self.target_heart_rate_avg:
            return f"Aim for around {self.target_heart_rate_avg} BPM"
        return "Heart rate targets not specified"
    
    def set_instructions(self, instructions: list) -> None:
        """Store instructions as JSON array."""
        self.instructions = json.dumps(instructions)
    
    def get_instructions(self) -> list:
        """Retrieve instructions as list."""
        if self.instructions:
            return json.loads(self.instructions)
        return []
    
    def set_reasoning(self, reasoning: dict) -> None:
        """Store AI reasoning as JSON."""
        self.reasoning_json = json.dumps(reasoning)
    
    def get_reasoning(self) -> dict:
        """Retrieve AI reasoning."""
        if self.reasoning_json:
            return json.loads(self.reasoning_json)
        return {}
    
    def get_intensity_description(self) -> str:
        """Get description of intensity level."""
        descriptions = {
            IntensityLevel.VERY_LIGHT: "Very light activity - gentle movement, easy breathing",
            IntensityLevel.LIGHT: "Light activity - can hold a conversation easily",
            IntensityLevel.MODERATE: "Moderate activity - slightly breathless, can talk in short sentences",
            IntensityLevel.VIGOROUS: "Vigorous activity - noticeably breathless, can say a few words",
            IntensityLevel.HIGH: "High intensity - very breathless, minimal talking",
            IntensityLevel.MAXIMUM: "Maximum effort - cannot talk, all-out effort",
        }
        return descriptions.get(self.intensity_level, "Unknown intensity")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "type": self.recommendation_type.value,
            "status": self.status.value,
            "activity": self.suggested_activity,
            "intensity": {
                "level": self.intensity_level.value,
                "description": self.get_intensity_description(),
            },
            "duration_minutes": self.duration_minutes,
            "heart_rate_target": {
                "min": self.target_heart_rate_min,
                "max": self.target_heart_rate_max,
                "description": self.get_heart_rate_zone_description(),
            },
            "instructions": self.get_instructions(),
            "description": self.description,
            "warnings": self.warnings,
            "is_active": self.is_active,
            "is_completed": self.is_completed,
            "confidence_score": self.confidence_score,
            "reasoning": self.get_reasoning(),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }