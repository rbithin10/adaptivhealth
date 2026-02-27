# Read Receipts Implementation Guide

**Status**: ✅ COMPLETE (Backend + Mobile)  
**Date**: December 2024  
**Feature**: Message read receipts with timestamp tracking

---

## Overview

Implemented full read receipt functionality for patient-clinician messaging system:

**Backend (FastAPI)**:
- Added `read_at` timestamp column to messages table
- Updated MessageResponse schema to include read_at field
- Modified POST /messages/{id}/read endpoint to set read_at when marking message read
- Created database migration script

**Mobile (Flutter)**:
- Added automatic message read marking when patient views thread
- Implemented visual read indicators (double checkmark icons)
- Added auto-refresh every 10 seconds for real-time updates
- Improved timestamp formatting (Today, Yesterday, day names)
- Added pull-to-refresh UI pattern

---

## Database Migration

### Required Step: Apply Migration

Before testing, you **MUST** run the migration to add the `read_at` column:

```bash
# SQLite (Development)
sqlite3 adaptiv_health.db < migrations/add_message_read_at.sql

# PostgreSQL (Production)
psql -U username -d adaptiv_health -f migrations/add_message_read_at.sql
```

**Migration Contents** (`migrations/add_message_read_at.sql`):
```sql
-- Add read_at timestamp for message read receipts
ALTER TABLE messages
ADD COLUMN read_at TIMESTAMP NULL;

-- Index for efficient querying of read times
CREATE INDEX IF NOT EXISTS idx_messages_read_at
ON messages (read_at);
```

### Verify Migration Success

```bash
# SQLite
sqlite3 adaptiv_health.db "PRAGMA table_info(messages);"

# PostgreSQL
psql -U username -d adaptiv_health -c "\d messages"
```

You should see `read_at` column (TIMESTAMP, nullable).

---

## Backend Changes

### 1. Message Model (`app/models/message.py`)

**Added field**:
```python
read_at = Column(DateTime(timezone=True), nullable=True)
```

- Stores exact UTC timestamp when message was marked read
- NULL for unread messages
- Indexed for efficient queries

### 2. Message Schema (`app/schemas/message.py`)

**Updated MessageResponse**:
```python
from typing import Optional

class MessageResponse(BaseModel):
    message_id: int
    sender_id: int
    receiver_id: int
    content: str
    sent_at: datetime
    is_read: bool = False
    read_at: Optional[datetime] = None  # NEW
    
    class Config:
        from_attributes = True
```

### 3. Messages API (`app/api/messages.py`)

**Updated mark message read endpoint**:
```python
@router.post("/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = db.query(Message).filter(
        Message.message_id == message_id,
        Message.receiver_id == current_user.user_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Update both is_read flag and read_at timestamp
    message.is_read = True
    message.read_at = datetime.now(timezone.utc)  # NEW
    
    db.commit()
    db.refresh(message)
    return message
```

---

## Mobile Changes

### 1. API Client (`mobile-app/lib/services/api_client.dart`)

**Added method**:
```dart
/// Mark a message as read
Future<Map<String, dynamic>> markMessageRead(int messageId) async {
  try {
    final response = await _dio.post('/messages/$messageId/read');
    return response.data as Map<String, dynamic>;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

### 2. Messaging Screen (`mobile-app/lib/screens/doctor_messaging_screen.dart`)

#### 2.1 Auto-Refresh Timer

**Added timer in initState**:
```dart
Timer? _autoRefreshTimer;

@override
void initState() {
  super.initState();
  _loadClinicianAndThread();
  
  // Auto-refresh every 10 seconds
  _autoRefreshTimer = Timer.periodic(
    const Duration(seconds: 10),
    (_) => _refreshThreadSilently(),
  );
}

@override
void dispose() {
  _autoRefreshTimer?.cancel();  // Clean up timer
  _messageController.dispose();
  _scrollController.dispose();
  super.dispose();
}
```

**Silent refresh method**:
```dart
/// Refresh thread without showing loading indicator (for auto-refresh)
Future<void> _refreshThreadSilently() async {
  if (_clinicianId == null || _isLoading || _isSending) {
    return;
  }

  try {
    final messages = await widget.apiClient.getMessageThread(
      _clinicianId!,
      limit: 50,
    );

    if (!mounted) return;
    
    // Only update if we have new messages
    if (messages.length != _messages.length) {
      setState(() {
        _messages = messages;
      });
      _scrollToBottom();
      _markUnreadMessagesAsRead();
    }
  } catch (e) {
    // Silently ignore errors during auto-refresh
    print('Auto-refresh failed: $e');
  }
}
```

#### 2.2 Auto-Mark Messages Read

**Mark unread messages when viewing thread**:
```dart
/// Mark all unread messages from clinician as read
Future<void> _markUnreadMessagesAsRead() async {
  if (_currentUserId == null || _clinicianId == null) return;

  for (final message in _messages) {
    final isRead = message['is_read'] as bool? ?? false;
    final senderId = message['sender_id'] as int?;
    final messageId = message['message_id'] as int?;

    // Mark as read if:
    // 1. Message is not read
    // 2. Message is from clinician (not sent by us)
    // 3. We have a valid message ID
    if (!isRead && senderId == _clinicianId && messageId != null) {
      try {
        await widget.apiClient.markMessageRead(messageId);
        // Update local state
        message['is_read'] = true;
        message['read_at'] = DateTime.now().toIso8601String();
      } catch (e) {
        print('Failed to mark message $messageId as read: $e');
      }
    }
  }
}
```

**Call after loading thread**:
```dart
Future<void> _loadThread() async {
  // ... load messages ...
  
  _scrollToBottom();
  _markUnreadMessagesAsRead();  // Auto-mark on view
}
```

#### 2.3 Visual Read Indicators

**Updated message bubble UI**:
```dart
Widget _buildMessageBubble(Map<String, dynamic> message) {
  final isSent = _isSentByCurrentUser(message);
  final content = message['content'] as String? ?? '';
  final sentAt = message['sent_at'] as String?;
  final isRead = message['is_read'] as bool? ?? false;
  final readAt = message['read_at'] as String?;
  
  final timestamp = sentAt != null ? DateTime.tryParse(sentAt) : null;
  final timeLabel = _formatTimestamp(timestamp);

  return Align(
    alignment: isSent ? Alignment.centerRight : Alignment.centerLeft,
    child: Container(
      // ... styling ...
      child: Column(
        crossAxisAlignment: isSent ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Text(content, style: ...),
          const SizedBox(height: 4),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(timeLabel, style: ...),
              if (isSent) ...[
                const SizedBox(width: 4),
                Icon(
                  isRead ? Icons.done_all : Icons.done,  // Double checkmark for read
                  size: 14,
                  color: isRead ? AdaptivColors.stable : AdaptivColors.primaryLight,
                ),
              ],
            ],
          ),
        ],
      ),
    ),
  );
}
```

**Checkmark indicators**:
- Single checkmark (Icons.done): Message sent but not read
- Double checkmark (Icons.done_all): Message read by recipient
- Green color: Read message confirmation
- White/light color: Unread message

#### 2.4 Better Timestamp Formatting

**Import intl package** (already in pubspec.yaml):
```dart
import 'dart:async';
import 'package:intl/intl.dart';
```

**Format timestamp function**:
```dart
String _formatTimestamp(DateTime? timestamp) {
  if (timestamp == null) return '';
  
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final messageDate = DateTime(timestamp.year, timestamp.month, timestamp.day);
  
  if (messageDate == today) {
    // Today: show time only
    return DateFormat('HH:mm').format(timestamp);
  } else if (messageDate == today.subtract(const Duration(days: 1))) {
    // Yesterday
    return 'Yesterday ${DateFormat('HH:mm').format(timestamp)}';
  } else if (now.difference(timestamp).inDays < 7) {
    // Last 7 days: show day name
    return DateFormat('EEE HH:mm').format(timestamp);
  } else {
    // Older: show date
    return DateFormat('MMM d, HH:mm').format(timestamp);
  }
}
```

**Examples**:
- Today at 2:45 PM → "14:45"
- Yesterday at 9:30 AM → "Yesterday 09:30"
- Last Monday → "Mon 16:20"
- Older → "Nov 28, 10:15"

#### 2.5 Pull-to-Refresh UI

**Wrapped ListView with RefreshIndicator**:
```dart
return RefreshIndicator(
  onRefresh: _loadThread,
  child: ListView.builder(
    controller: _scrollController,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    itemCount: _messages.length,
    itemBuilder: (context, index) {
      final message = _messages[index];
      return _buildMessageBubble(message);
    },
  ),
);
```

User can pull down to manually refresh messages.

#### 2.6 Improved Empty State

**Better empty message UI**:
```dart
if (_messages.isEmpty) {
  return Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 64,
            color: AdaptivColors.text400,
          ),
          const SizedBox(height: 16),
          Text(
            'No messages yet',
            style: AdaptivTypography.sectionTitle,
          ),
          const SizedBox(height: 8),
          Text(
            'Start a conversation with your clinician',
            style: AdaptivTypography.body.copyWith(
              color: AdaptivColors.text600,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    ),
  );
}
```

---

## Testing Steps

### 1. Apply Database Migration

**Run migration script**:
```bash
sqlite3 adaptiv_health.db < migrations/add_message_read_at.sql
```

**Verify**:
```bash
sqlite3 adaptiv_health.db "SELECT sql FROM sqlite_master WHERE name='messages';"
```

### 2. Start Backend

```bash
python start_server.py
# Backend runs on http://localhost:8080
```

### 3. Test with Mobile App

```bash
cd mobile-app
flutter run
```

### 4. Test Read Receipt Flow

#### Test Scenario 1: Patient Views Messages

1. **Login as patient** (e.g., test@example.com)
2. **Navigate to Messages tab**
3. **Observe**:
   - Screen loads clinician and message thread
   - Unread messages from clinician are automatically marked read
   - Auto-refresh triggers every 10 seconds
4. **Send a message** to clinician
5. **Check sent message bubble**:
   - Should show single checkmark (not read yet)
   - Timestamp shows "14:35" (or "Yesterday 09:20", etc.)

#### Test Scenario 2: Clinician Reads Message

1. **Login as clinician** via web dashboard or another device
2. **Open conversation** with the patient
3. **Read the patient's message**
4. **Return to patient app**:
   - Within 10 seconds (auto-refresh), sent message should update
   - Single checkmark → double green checkmark
   - Indicates clinician read the message

#### Test Scenario 3: Pull-to-Refresh

1. **In mobile Messages screen**
2. **Pull down** from top of message list
3. **Observe**:
   - Loading spinner appears
   - Thread refreshes with latest messages
   - Read states update

#### Test Scenario 4: Timestamp Formatting

1. **Send messages at different times**
2. **Verify timestamps**:
   - Recent messages: "14:45"
   - Yesterday: "Yesterday 09:30"
   - Last week: "Mon 16:20"
   - Older: "Nov 28, 10:15"

---

## API Contract

### POST /api/v1/messages/{message_id}/read

**Request**:
```http
POST /api/v1/messages/123/read
Authorization: Bearer <jwt_token>
```

**Response** (200 OK):
```json
{
  "message_id": 123,
  "sender_id": 5,
  "receiver_id": 2,
  "content": "How are you feeling today?",
  "sent_at": "2024-12-18T10:30:00Z",
  "is_read": true,
  "read_at": "2024-12-18T14:45:32Z"
}
```

**Error Cases**:
- 404: Message not found or user is not receiver
- 401: Unauthorized (invalid token)

---

## Database Schema

### messages table (after migration)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| message_id | INTEGER | NO | Primary key |
| sender_id | INTEGER | NO | User who sent message |
| receiver_id | INTEGER | NO | User who receives message |
| content | TEXT | NO | Message plaintext |
| encrypted_content | TEXT | YES | AES-256-GCM encrypted content |
| sent_at | TIMESTAMP | NO | When message was sent |
| is_read | BOOLEAN | NO | Read flag (legacy) |
| **read_at** | **TIMESTAMP** | **YES** | **When message was marked read** |

**Indexes**:
- `idx_messages_sender_receiver` - (sender_id, receiver_id) for thread queries
- `idx_messages_read_at` - (read_at) for analytics

---

## Known Limitations

1. **No delivery confirmation**: Single checkmark means "sent to server", not "delivered to recipient device"
2. **No typing indicators**: Not implemented in this phase
3. **No offline read marking**: If patient is offline when viewing messages, they won't be marked read until online
4. **Read state is one-way**: Patient sees when clinician reads their messages, but clinician doesn't see read receipts from patient (can be added later)

---

## Future Enhancements

### Optional Next Steps

1. **Bidirectional read receipts**: Show clinician when patient reads their messages
2. **Read by timestamp in UI**: Show "Read at 2:45 PM" tooltip on double checkmark
3. **WebSocket real-time updates**: Replace polling with WebSocket for instant updates
4. **Typing indicators**: Show "Dr. Smith is typing..." when clinician is composing
5. **Message reactions**: Allow patient to react with emoji (👍, ❤️, etc.)
6. **Message search**: Search through conversation history
7. **Unread message counter**: Show badge count on Messages tab icon

---

## Troubleshooting

### Issue: Migration fails with "duplicate column"

**Symptom**: `ALTER TABLE messages ADD COLUMN read_at` fails

**Solution**:
```bash
# Check if column already exists
sqlite3 adaptiv_health.db "PRAGMA table_info(messages);"

# If read_at exists, migration already applied (safe to skip)
```

### Issue: Messages not auto-marking as read

**Symptom**: Patient views thread but messages stay unread

**Debug steps**:
1. Check backend logs for POST /messages/{id}/read errors
2. Verify patient is authenticated (valid JWT token)
3. Check `_markUnreadMessagesAsRead()` is being called
4. Add print statements:
   ```dart
   print('Marking message $messageId as read...');
   await widget.apiClient.markMessageRead(messageId);
   print('Successfully marked read');
   ```

### Issue: Checkmarks not updating

**Symptom**: Sent messages always show single checkmark

**Debug steps**:
1. Check auto-refresh is working (should run every 10 seconds)
2. Verify backend returns `is_read: true` and `read_at` fields
3. Check `_buildMessageBubble()` logic:
   ```dart
   final isRead = message['is_read'] as bool? ?? false;
   print('Message ${message['message_id']}, isRead: $isRead');
   ```

### Issue: Timestamps show incorrectly

**Symptom**: All timestamps show raw ISO strings instead of formatted

**Solution**:
- Ensure `intl` package is in `pubspec.yaml` dependencies
- Run `flutter pub get`
- Import: `import 'package:intl/intl.dart';`
- Check `DateTime.tryParse()` successfully parses timestamp

---

## Documentation

- **API Spec**: See `BACKEND_API_SPECIFICATIONS.md` section 7.5
- **Mobile Integration**: See `MESSAGING_MVP_IMPLEMENTATION.md`
- **Setup Guide**: See `CLINICIAN_ASSIGNMENT_COMPLETE_GUIDE.md`

---

## Summary

✅ **Backend**: Added `read_at` timestamp column, updated schema, set timestamp on mark-read API  
✅ **Mobile**: Added markMessageRead method, auto-mark on view, visual indicators, auto-refresh, better timestamps  
✅ **Migration**: Created `add_message_read_at.sql` migration script  
✅ **UI/UX**: Double checkmarks, color coding, pull-to-refresh, improved empty state  

**Next Steps**:
1. Apply migration: `sqlite3 adaptiv_health.db < migrations/add_message_read_at.sql`
2. Restart backend: `python start_server.py`
3. Test mobile app: Follow test scenarios above
4. Optional: Add clinician-side read receipts (show when patient reads clinician messages)
