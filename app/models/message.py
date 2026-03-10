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
    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Unique ID for each message

    # -------------------------------------------------------------------------
    # Foreign Keys — who sent and who received the message
    # -------------------------------------------------------------------------
    sender_id = Column(  # The user who wrote and sent this message
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    receiver_id = Column(  # The user who should receive this message
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Message Content (encrypted for privacy)
    # -------------------------------------------------------------------------
    content = Column(Text, nullable=False)  # The actual text of the message
    encrypted_content = Column(Text, nullable=True)  # Same message but encrypted for secure storage
    is_read = Column(Boolean, default=False, nullable=False)  # Has the receiver opened and read this message?
    read_at = Column(DateTime(timezone=True), nullable=True)  # The exact time the receiver read the message

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    sent_at = Column(  # When the message was sent
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # -------------------------------------------------------------------------
    # Indexes — speed up searching messages between users
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("idx_messages_sender_receiver", "sender_id", "receiver_id"),  # Find conversations between two people
        Index("idx_messages_receiver_sender", "receiver_id", "sender_id"),  # Same but looking from the receiver's side
        Index("idx_messages_sender_time", "sender_id", "sent_at"),  # Find messages sent by someone, sorted by time
        Index("idx_messages_receiver_time", "receiver_id", "sent_at"),  # Find messages received by someone, sorted by time
        Index("idx_messages_pair_time", "sender_id", "receiver_id", "sent_at"),  # Full conversation history in order
        {"extend_existing": True}
    )

    def __repr__(self):
        return (
            f"<Message(message_id={self.message_id}, sender_id={self.sender_id}, "
            f"receiver_id={self.receiver_id}, is_read={self.is_read})>"
        )
