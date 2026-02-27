"""
=============================================================================
ADAPTIV HEALTH - Message Model
=============================================================================
SQLAlchemy model for patient-clinician messaging with REST polling support.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# CLASS: Message (SQLAlchemy Model)
#   - Primary Key...................... Line 35  (message_id)
#   - Foreign Keys..................... Line 40  (sender_id, receiver_id)
#   - Message Content.................. Line 55  (content, is_read)
#   - Timestamps....................... Line 70  (sent_at)
#   - Indexes.......................... Line 85  (user/time indexes)
#
# BUSINESS CONTEXT:
# - Patient-clinician messaging via REST polling (industry-standard)
# - Text conversations for care coordination
# - Production feature with support for future WebSocket upgrade
# =============================================================================
"""

from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class Message(Base):
    """
    Message model for patient-clinician conversations.
    
    Supports basic text messages with read/unread state.
    """

    __tablename__ = "messages"

    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------
    sender_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    receiver_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Message Content (encrypted)
    # -------------------------------------------------------------------------
    content = Column(Text, nullable=False)
    # Encrypted content stored for persistence (AES-256-GCM)
    encrypted_content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    sent_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_messages_sender_receiver", "sender_id", "receiver_id"),
        Index("idx_messages_receiver_sender", "receiver_id", "sender_id"),
        Index("idx_messages_sender_time", "sender_id", "sent_at"),
        Index("idx_messages_receiver_time", "receiver_id", "sent_at"),
        Index("idx_messages_pair_time", "sender_id", "receiver_id", "sent_at"),
        {"extend_existing": True}
    )

    def __repr__(self):
        return (
            f"<Message(message_id={self.message_id}, sender_id={self.sender_id}, "
            f"receiver_id={self.receiver_id}, is_read={self.is_read})>"
        )
