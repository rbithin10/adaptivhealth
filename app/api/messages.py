"""
Message API endpoints.

Patient-clinician messaging with REST polling support.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 25
#
# ENDPOINTS - PATIENT/CLINICIAN (own threads)
#   - GET /messages/thread/{id}........ Line 45  (Fetch thread)
#   - POST /messages................... Line 105 (Send message)
#   - POST /messages/{id}/read......... Line 160 (Mark message read)
#
# BUSINESS CONTEXT:
# - Production text conversations between patients and clinicians
# - REST polling (industry-standard for healthcare apps)
# =============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, asc
from typing import List
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageResponse, InboxSummaryResponse
from app.api.auth import get_current_user
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Message Endpoints
# =============================================================================

# =============================================
# GET_THREAD - Fetch conversation with another user
# Used by: Mobile app doctor messaging screen
# Returns: List[MessageResponse] ordered by sent_at ascending
# Roles: ALL authenticated users (own threads only)
# =============================================
@router.get("/messages/thread/{other_user_id}", response_model=List[MessageResponse])
async def get_message_thread(
    other_user_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Max messages to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get message thread between the current user and another user.
    
    Messages are ordered by sent_at ascending (oldest first).
    
    Args:
        other_user_id: The other participant's user ID
        limit: Max number of messages to return (default 50)
        current_user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        List of messages between the two users
    
    Raises:
        404: Other user not found
    """
    other_user = db.query(User).filter(User.user_id == other_user_id).first()
    if other_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(
                    Message.sender_id == current_user.user_id,
                    Message.receiver_id == other_user_id
                ),
                and_(
                    Message.sender_id == other_user_id,
                    Message.receiver_id == current_user.user_id
                )
            )
        )
        .order_by(asc(Message.sent_at))
        .limit(limit)
        .all()
    )

    logger.info(
        f"Message thread fetched: current_user={current_user.user_id}, "
        f"other_user={other_user_id}, count={len(messages)}"
    )

    return messages


# =============================================
# SEND_MESSAGE - Create a new message
# Used by: Mobile app messaging screen
# Returns: MessageResponse
# Roles: ALL authenticated users
# =============================================
@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to another user.
    
    Args:
        message_data: MessageCreate payload with receiver_id and content
        current_user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        Created message
    
    Raises:
        404: Receiver not found
    """
    receiver = db.query(User).filter(User.user_id == message_data.receiver_id).first()
    if receiver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )

    # Encrypt message content
    try:
        encrypted_content = encryption_service.encrypt_text(message_data.content)
    except Exception as e:
        logger.warning(f"Message encryption failed: {e}, storing unencrypted")
        encrypted_content = None

    message = Message(
        sender_id=current_user.user_id,
        receiver_id=message_data.receiver_id,
        content=message_data.content,  # Store plain text for immediate use
        encrypted_content=encrypted_content,  # Store encrypted for security at rest
        sent_at=datetime.now(timezone.utc),
        is_read=False
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info(
        f"Message sent: id={message.message_id}, "
        f"sender={current_user.user_id}, receiver={message_data.receiver_id}"
    )

    return message


# =============================================
# MARK_READ - Mark message as read
# Used by: Mobile app messaging screen
# Returns: MessageResponse
# Roles: Receiver only
# =============================================
@router.post("/messages/{message_id}/read", response_model=MessageResponse)
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a message as read (receiver only).
    
    Args:
        message_id: ID of the message to mark read
        current_user: Authenticated user from JWT token
        db: Database session
    
    Returns:
        Updated message
    
    Raises:
        404: Message not found or user not authorized
    """
    message = db.query(Message).filter(Message.message_id == message_id).first()
    if message is None or message.receiver_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)

    logger.info(
        f"Message marked read: id={message.message_id}, receiver={current_user.user_id}"
    )

    return message


# =============================================
# GET_INBOX - Fetch clinician's message inbox
# Used by: Web dashboard messaging section
# Returns: List[InboxSummaryResponse] ordered by most recent first
# Roles: Clinicians only
# =============================================
@router.get("/messages/inbox", response_model=List[InboxSummaryResponse])
async def get_messaging_inbox(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get message inbox for clinician.
    
    Returns list of patients with unread messages, ordered by most recent.
    Shows latest message from each patient + unread count.
    
    Args:
        current_user: Authenticated clinician from JWT token
        db: Database session
    
    Returns:
        List of inbox summaries for each patient with messages
    
    Raises:
        403: Current user is not a clinician
    """
    from app.models.user import UserRole
    
    if current_user.role != UserRole.CLINICIAN and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can view messaging inbox"
        )
    
    # Get all unique patients who have messaged this clinician
    # (either they sent messages to us, or we sent to them)
    subquery = (
        db.query(Message)
        .filter(
            or_(
                Message.receiver_id == current_user.user_id,
                Message.sender_id == current_user.user_id
            )
        )
        .with_entities(
            Message.sender_id,
            Message.receiver_id,
            Message.content,
            Message.sent_at,
            Message.is_read,
            Message.message_id
        )
        .order_by(Message.sent_at.desc())
    )
    
    # Group by conversation partner and get summary
    conversations = {}
    for msg_rec in subquery.all():
        msg_sender_id, msg_receiver_id, content, sent_at, is_read, msg_id = msg_rec
        
        # Determine who the "other" person is in this conversation
        other_user_id = msg_sender_id if msg_receiver_id == current_user.user_id else msg_receiver_id
        
        if other_user_id not in conversations:
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            if other_user:
                conversations[other_user_id] = {
                    'patient_id': other_user_id,
                    'patient_name': other_user.full_name or f"Patient {other_user_id}",
                    'last_message_content': content,
                    'last_message_sender_id': msg_sender_id,
                    'last_message_sent_at': sent_at,
                    'unread_count': 0
                }
        
        # Count unread messages from this patient to clinician
        if msg_sender_id == other_user_id and msg_receiver_id == current_user.user_id and not is_read:
            conversations[other_user_id]['unread_count'] += 1
    
    # Convert to response list, sorted by most recent first
    inbox_list = list(conversations.values())
    inbox_list.sort(key=lambda x: x['last_message_sent_at'], reverse=True)
    
    logger.info(
        f"Messaging inbox fetched: clinician={current_user.user_id}, "
        f"conversation_count={len(inbox_list)}"
    )
    
    return inbox_list
