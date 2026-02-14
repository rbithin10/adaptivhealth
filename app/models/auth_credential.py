"""
=============================================================================
ADAPTIV HEALTH - Authentication Credentials Model
=============================================================================
Separate table for authentication credentials (passwords, login attempts).
Keeps sensitive auth data isolated from PHI (health information).

HIPAA Compliance: Segregates authentication data from medical records.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CLASS: AuthCredential (SQLAlchemy Model)
#   - Primary Key...................... Line 40  (credential_id)
#   - Foreign Key...................... Line 45  (user_id → users)
#   - Password......................... Line 50  (hashed_password)
#   - Login Tracking................... Line 55  (last_login, failed_attempts)
#   - Account Security................. Line 65  (locked_until, password_changed)
#   - Relationships.................... Line 85  (user)
#   - Methods.......................... Line 95  (is_locked, record_failed_login)
#
# BUSINESS CONTEXT:
# - HIPAA: Auth data separate from PHI
# - Account lockout after 5 failed attempts
# - Password change tracking for audits
# =============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuthCredential(Base):
    """
    Stores authentication credentials separately from user PHI.
    
    This table contains only:
    - Hashed passwords (never plain text)
    - Login attempts and lockout info
    - Password change tracking
    - Last login timestamp
    
    PHI (health data) stays in the users table and related tables.
    """

    __tablename__ = "auth_credentials"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    credential_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Foreign Key to Users (one-to-one relationship)
    # -------------------------------------------------------------------------
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One credential per user
        index=True
    )

    # -------------------------------------------------------------------------
    # Authentication Fields
    # -------------------------------------------------------------------------
    # Password (always hashed with bcrypt, never plain text)
    hashed_password = Column(String(255), nullable=False)

    # -------------------------------------------------------------------------
    # Account Security / HIPAA Compliance
    # -------------------------------------------------------------------------
    # Failed login attempts (for account lockout)
    failed_login_attempts = Column(Integer, default=0, nullable=False)

    # Account lockout timestamp (NULL = not locked)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Last successful login
    last_login = Column(DateTime(timezone=True), nullable=True)

    # When password was last changed
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # -------------------------------------------------------------------------
    # Audit Trail
    # -------------------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # -------------------------------------------------------------------------
    # Relationship to User
    # -------------------------------------------------------------------------
    user = relationship("User", back_populates="auth_credential")

    # -------------------------------------------------------------------------
    # Indexes for Performance
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index('idx_auth_user_id', 'user_id'),
        Index('idx_auth_locked_until', 'locked_until'),
        Index('idx_auth_last_login', 'last_login'),
    )

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<AuthCredential(user_id={self.user_id}, locked={self.locked_until is not None})>"

    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone
        # Handle both naive and aware datetimes
        now = datetime.now(timezone.utc)
        locked = self.locked_until
        # If locked_until is naive, assume UTC
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return locked > now

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "credential_id": self.credential_id,
            "user_id": self.user_id,
            "failed_login_attempts": self.failed_login_attempts,
            "is_locked": self.is_locked(),
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
