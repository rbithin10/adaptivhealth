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
from app.api.auth import get_current_user_session_or_bearer
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_conversation_id(conversation_id: str) -> int:
    """Parse conversation identifier into other_user_id.

    Supports both numeric IDs ("12") and prefixed IDs ("conv_12").
    """
    normalized = conversation_id.strip()
    if normalized.lower().startswith("conv_"):
        normalized = normalized[5:]

    try:
        return int(normalized)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation_id format"
        ) from exc


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
    current_user: User = Depends(get_current_user_session_or_bearer),
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
    current_user: User = Depends(get_current_user_session_or_bearer),
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
    current_user: User = Depends(get_current_user_session_or_bearer),
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
    current_user: User = Depends(get_current_user_session_or_bearer),
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


# =============================================
# GET_CONVERSATIONS_COMPAT - Spec-compatible conversations list
# Used by: UI contracts expecting /messaging/conversations
# Returns: Conversation summaries with unread count
# Roles: ALL authenticated users
# =============================================
@router.get("/messaging/conversations")
async def get_messaging_conversations(
    include_unread: bool = Query(default=True, description="Include unread count"),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """List active conversations in a spec-compatible response shape."""
    rows = (
        db.query(Message)
        .filter(
            or_(
                Message.sender_id == current_user.user_id,
                Message.receiver_id == current_user.user_id,
            )
        )
        .order_by(Message.sent_at.desc())
        .all()
    )

    conversations = {}
    for msg in rows:
        other_user_id = msg.sender_id if msg.receiver_id == current_user.user_id else msg.receiver_id
        if other_user_id not in conversations:
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            if not other_user:
                continue

            conversations[other_user_id] = {
                "conversation_id": f"conv_{other_user_id}",
                "participant": {
                    "id": other_user.user_id,
                    "name": other_user.full_name or f"User {other_user.user_id}",
                    "role": str(other_user.role),
                },
                "last_message": {
                    "message_id": msg.message_id,
                    "sender_id": msg.sender_id,
                    "content": msg.content,
                    "timestamp": msg.sent_at,
                    "type": "text",
                },
                "unread_count": 0,
                "updated_at": msg.sent_at,
            }

        if include_unread and msg.sender_id == other_user_id and msg.receiver_id == current_user.user_id and not msg.is_read:
            conversations[other_user_id]["unread_count"] += 1

    items = list(conversations.values())
    items.sort(key=lambda item: item["updated_at"], reverse=True)

    return {
        "user_id": current_user.user_id,
        "conversations": items,
        "total_conversations": len(items),
        "total_unread": sum(item["unread_count"] for item in items),
    }


# =============================================
# GET_CONVERSATION_MESSAGES_COMPAT - Spec-compatible thread history
# Used by: UI contracts expecting /messaging/conversations/{id}/messages
# Returns: Paginated conversation message list
# Roles: ALL authenticated users
# =============================================
@router.get("/messaging/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """Retrieve message history for a conversation in spec-compatible shape."""
    other_user_id = _parse_conversation_id(conversation_id)
    other_user = db.query(User).filter(User.user_id == other_user_id).first()
    if other_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation does not exist")

    base_query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.user_id, Message.receiver_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.receiver_id == current_user.user_id),
        )
    )

    total_messages = base_query.count()
    messages = (
        base_query
        .order_by(asc(Message.sent_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    payload = []
    for msg in messages:
        sender_user = current_user if msg.sender_id == current_user.user_id else other_user
        payload.append({
            "message_id": msg.message_id,
            "sender": {
                "id": msg.sender_id,
                "type": "patient" if str(sender_user.role).lower().endswith("patient") else "clinician",
                "name": sender_user.full_name or f"User {sender_user.user_id}",
            },
            "content": msg.content,
            "timestamp": msg.sent_at,
            "type": "text",
            "read_by_recipient": msg.is_read,
            "read_at": msg.read_at,
        })

    return {
        "conversation_id": f"conv_{other_user_id}",
        "participant": {
            "id": other_user.user_id,
            "name": other_user.full_name or f"User {other_user.user_id}",
            "role": str(other_user.role),
        },
        "messages": payload,
        "pagination": {
            "total_messages": total_messages,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_messages,
        },
    }


# =============================================
# SEND_CONVERSATION_MESSAGE_COMPAT - Spec-compatible send endpoint
# Used by: UI contracts expecting /messaging/conversations/{id}/messages
# Returns: Sent message envelope
# Roles: ALL authenticated users
# =============================================
@router.post("/messaging/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_conversation_message(
    conversation_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """Send a conversation message in a spec-compatible request/response shape."""
    other_user_id = _parse_conversation_id(conversation_id)
    receiver = db.query(User).filter(User.user_id == other_user_id).first()
    if receiver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation does not exist")

    content = str(payload.get("content", "")).strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content is required")

    try:
        encrypted_content = encryption_service.encrypt_text(content)
    except Exception:
        encrypted_content = None

    message = Message(
        sender_id=current_user.user_id,
        receiver_id=other_user_id,
        content=content,
        encrypted_content=encrypted_content,
        sent_at=datetime.now(timezone.utc),
        is_read=False,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "message_id": message.message_id,
        "conversation_id": f"conv_{other_user_id}",
        "sender": {
            "id": current_user.user_id,
            "type": "patient" if str(current_user.role).lower().endswith("patient") else "clinician",
        },
        "content": message.content,
        "timestamp": message.sent_at,
        "type": "text",
        "read_by_recipient": False,
        "status": "sent",
        "attachments": payload.get("attachments", []),
    }


# =============================================
# MARK_CONVERSATION_READ_COMPAT - Mark thread unread messages as read
# Used by: UI contracts expecting /messaging/conversations/{id}/read
# Returns: Count of messages marked read
# Roles: ALL authenticated users
# =============================================
@router.put("/messaging/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    current_user: User = Depends(get_current_user_session_or_bearer),
    db: Session = Depends(get_db),
):
    """Mark all unread incoming messages in a conversation as read."""
    other_user_id = _parse_conversation_id(conversation_id)

    unread_messages = (
        db.query(Message)
        .filter(
            Message.sender_id == other_user_id,
            Message.receiver_id == current_user.user_id,
            Message.is_read.is_(False),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for message in unread_messages:
        message.is_read = True
        message.read_at = now

    db.commit()

    return {
        "conversation_id": f"conv_{other_user_id}",
        "messages_marked_read": len(unread_messages),
        "read_at": now,
    }
