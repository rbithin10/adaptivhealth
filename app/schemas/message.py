"""
Message Schemas for API validation and responses.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# SCHEMAS
#   - MessageCreate..................... Line 25  (Create message input)
#   - MessageResponse................... Line 45  (Full message output)
#
# BUSINESS CONTEXT:
# - Patient-clinician text messaging with REST polling
# - Production implementation with secure message threading
# =============================================================================
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class MessageCreate(BaseModel):
    """
    Schema for creating a new message.
    
    Sender is inferred from authentication.
    """
    receiver_id: int = Field(..., description="User ID of the message receiver")  # Who should receive this message
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")  # The actual text of the message (1-1000 characters)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


class MessageResponse(BaseModel):
    """
    Schema for message response.
    
    Includes sender, receiver, content, timestamps, and read state.
    """
    message_id: int = Field(..., description="Unique message ID")  # Unique number for this message
    sender_id: int = Field(..., description="User ID of sender")  # Who wrote this message
    receiver_id: int = Field(..., description="User ID of receiver")  # Who should see this message
    content: str = Field(..., description="Message content")  # The actual text that was sent
    sent_at: datetime = Field(..., description="When the message was sent")  # Date and time the message was sent
    is_read: bool = Field(..., description="Whether the message has been read")  # Has the receiver opened/read it yet?
    read_at: Optional[datetime] = Field(None, description="When the message was marked as read")  # When they read it (empty if unread)

    class Config:
        from_attributes = True


class InboxSummaryResponse(BaseModel):
    """
    Schema for inbox summary (used by clinicians).
    
    Shows patients with new/recent messages and unread count.
    """
    patient_id: int = Field(..., description="Patient user ID")  # The patient's unique ID
    patient_name: str = Field(..., description="Patient full name")  # The patient's name
    last_message_content: str = Field(..., description="Content of last message")  # What the most recent message said
    last_message_sender_id: int = Field(..., description="Who sent the last message")  # Who sent that last message
    last_message_sent_at: datetime = Field(..., description="When last message was sent")  # When the last message was sent
    unread_count: int = Field(..., description="Number of unread messages from patient")  # How many messages the clinician hasn't read yet

    class Config:
        from_attributes = True
