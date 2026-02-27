# Messaging & Clinician Assignment Setup Guide

## Overview

This guide walks through enabling the complete messaging system with real-time notifications and clinician-patient assignment.

## Components Added

### 1. Backend Changes

**New API Endpoints:**
- `GET /messages/inbox` - Get clinician's message inbox with unread counts (clinician-only)
- `GET /messages/thread/{other_user_id}` - Get conversation thread
- `POST /messages` - Send message
- `POST /messages/{message_id}/read` - Mark message as read

**New Database Column:**
- `users.assigned_clinician_id` - Foreign key linking patients to their assigned clinician

**New Schemas:**
- `InboxSummaryResponse` - Patient + unread count + last message summary

### 2. Frontend Changes

**New Pages:**
- `web-dashboard/src/pages/MessagingPage.tsx` - Full messaging inbox with real-time polling

**Updates to Dashboard:**
- Added "Messages" button in header with unread count badge
- Real-time polling every 5 seconds for new unread messages

**API Methods (web-dashboard/src/services/api.ts):**
- `getMessagingInbox()` - Fetch inbox
- `getMessageThread()` - Fetch conversation
- `sendMessage()` - Send message
- `markMessageAsRead()` - Mark read

**Mobile App (Already working):**
- Updated to use assigned clinician instead of "first available clinician"
- Mobile app already has full messaging functionality

## Step-by-Step Setup

### Step 1: Apply Database Migration

```bash
# From project root
python apply_migrations.py
```

This adds the `assigned_clinician_id` column and index to the users table.

**What this does:**
- Adds `assigned_clinician_id INTEGER` column to users table
- Creates index `idx_assigned_clinician` for fast lookups

**Verify the migration worked:**
```bash
sqlite3 adaptiv_health.db
sqlite> PRAGMA table_info(users);
# Look for assigned_clinician_id in the output
sqlite> .quit
```

### Step 2: Start/Restart Backend

```bash
python start_server.py
# or
start.bat
```

Backend now loads with new endpoints enabled.

### Step 3: Test Clinician Assignment (Admin Only)

**Via curl:**
```bash
# 1. Admin Login to get token
curl -X POST http://localhost:8080/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "adminpass123"}'
# Returns: {"access_token": "TOKEN", ...}

# 2. Assign clinician to patient (replace IDs and TOKEN)
curl -X PUT http://localhost:8080/api/v1/users/5/assign-clinician?clinician_id=3 \
  -H "Authorization: Bearer TOKEN"
# Returns: Updated user object

# 3. Verify assignment (clinician views their patients)
curl -X GET http://localhost:8080/api/v1/users \
  -H "Authorization: Bearer TOKEN_OF_CLINICIAN"
# Returns: Only their assigned patients
```

**Or use Admin Dashboard (if available):**
- Go to Admin page
- Look for patient in list
- Select/assign clinician (feature may need to be added to admin UI)

### Step 4: Test Messaging Flow

**Patient sends message to assigned clinician:**
1. Open mobile app
2. Navigate to Messages tab
3. Should see assigned clinician (or "No clinician assigned" if none)
4. Send message
5. Clinician receives notification

**Clinician receives message:**
1. Open web dashboard
2. Click "Messages" button (badge shows unread count)
3. Click patient to open conversation
4. Messages auto-update every 3 seconds (real-time polling)
5. Send reply via text input
6. Patient receives notification

## Architecture Details

### Messaging Flow

```
Patient (Mobile)                 Backend                    Clinician (Web)
      |                            |                              |
      |-- POST /messages ---------->|                              |
      |                            |-- Store Message              |
      |                            |-- Check Assignment           |
      |                            |                              |
      |                            |<- GET /messages/inbox        |
      |                            |   (polling every 5 sec)      |
      |                            |-- Return Inbox              |
      |                            |   with unread_count ---------->|
      |                            |                         (Shows Badge)
      |                            |                              |
      |<- GET /messages/thread <---|-GET /messages/thread ------->|
      |   (auto-update)            |   (polling every 3 sec)      |
```

### Data Isolation

**Clinicians can only see:**
- Patients they are assigned to
- Messages from those patients
- Inbox filtered to assigned patients only

**Patients can:**
- See their assigned clinician
- Send messages to that clinician
- See message thread

### Polling Strategy

- **Dashboard Inbox**: Polls every 5 seconds
- **Active Chat**: Polls every 3 seconds (when conversation is open)
- **Unread Badge**: Updates every 5 seconds

This balances responsiveness with server load.

## Troubleshooting

### Migration Failed: "Column already exists"

**Cause:** Migration was already applied
**Solution:** Check database with `sqlite3 adaptiv_health.db "PRAGMA table_info(users);"` - if `assigned_clinician_id` exists, you're good to go.

### Messages not showing in inbox

**Check:**
1. Is the clinician logged in?
2. Is there a patient-clinician assignment?
   - Run: `curl -X GET http://localhost:8080/api/v1/users/{user_id} -H "Authorization: Bearer TOKEN"`
   - Look for `assigned_clinician_id` field
3. Has the patient sent a message?
   - Check message table: `sqlite3 adaptiv_health.db "SELECT * FROM messages;"`

### "Only clinicians can view messaging inbox"

**Cause:** Patient or admin trying to access clinician inbox
**Solution:** Only clinician-role users can use the Messages page (admin has separate page)

### Unread count not updating

**Check:**
1. Is polling running? (Check browser DevTools Network tab for GET /messages/inbox requests)
2. Are new messages being sent? (Check backend logs)
3. Try manual refresh: Press F5

## API Endpoint Reference

### GET /messages/inbox (Clinician only)

Get all patients with unread messages.

**Response:**
```json
[
  {
    "patient_id": 2,
    "patient_name": "John Doe",
    "last_message_content": "Hi doctor, how are you?",
    "last_message_sender_id": 2,
    "last_message_sent_at": "2026-02-23T10:30:00Z",
    "unread_count": 1
  },
  {
    "patient_id": 4,
    "patient_name": "Jane Smith",
    "last_message_content": "Thanks for the advice",
    "last_message_sender_id": 1,
    "last_message_sent_at": "2026-02-23T10:20:00Z",
    "unread_count": 0
  }
]
```

### GET /messages/thread/{other_user_id}

Get full conversation thread with another user.

**Params:**
- `limit` (optional, default=50): Max messages to return

**Response:**
```json
[
  {
    "message_id": 1,
    "sender_id": 2,
    "receiver_id": 1,
    "content": "Hi doctor",
    "sent_at": "2026-02-23T10:30:00Z",
    "is_read": true
  },
  {
    "message_id": 2,
    "sender_id": 1,
    "receiver_id": 2,
    "content": "Hello! How can I help?",
    "sent_at": "2026-02-23T10:35:00Z",
    "is_read": false
  }
]
```

### POST /messages

Send a message.

**Body:**
```json
{
  "receiver_id": 2,
  "content": "Hello, I have a question"
}
```

**Response:** Message object (same structure as GET /thread)

### POST /messages/{message_id}/read

Mark a message as read (receiver only).

**Response:** Updated message object

### PUT /users/{user_id}/assign-clinician

Assign a clinician to a patient (admin only).

**Params:**
- `clinician_id` (required): User ID of the clinician

**Response:** Updated user object with `assigned_clinician_id` set

## Next Steps

1. ✅ Apply migration with `python apply_migrations.py`
2. ✅ Test clinician assignment via API
3. ✅ Have a clinician and patient exchange messages
4. ✅ Verify unread count badge appears
5. ✅ Test real-time polling (new messages appear within 3-5 seconds)

## Optional: Admin UI for Assignment

Currently, clinician assignment is API-only. To add an admin UI:

1. Create new component: `web-dashboard/src/components/AssignClinicianDialog.tsx`
2. Add assign dialog to `AdminPage.tsx` patient list
3. Call API: `PUT /users/{patient_id}/assign-clinician?clinician_id={clinician_id}`

This is a useful enhancement to streamline clinician-patient pairing in the admin interface.

## Security Notes

- Only clinicians/admins can view their messaging inbox
- Clinicians only see assigned patients (enforced at API level)
- Patients only see their assigned clinician
- All messages are logged for audit compliance
- PHI in messages is not encrypted (can be added later: `utils/encryption.py`)

## Performance Considerations

For production:

1. **WebSockets**: Replace polling with socket.io for real-time updates
   - Current: GET /messages/inbox every 5 seconds
   - Better: Live socket events when new messages arrive

2. **Message Pagination**: Handle 1000+ message conversations
   - Current: Returns all messages (limit param exists but default 50)
   - Add: Pagination with `offset` and `limit`

3. **Caching**: Cache inbox summaries
   - Current: Fresh query each time
   - Add: Cache with TTL, invalidate on new message

4. **Database Optimization**: Consider read replicas for high-volume clinics

These optimizations can be prioritized based on production performance monitoring and workload patterns.
