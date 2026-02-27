# Messaging Quick Start Guide

## For Developers

### Run Verification
```bash
python verify_messaging.py
```

This checks:
- ✅ All files present
- ✅ Database table exists
- ✅ Routes registered
- ✅ Mobile integration complete
- ✅ Basic functionality works

---

## For Testers

### Test the Messaging Feature

#### 1. Start Backend
```bash
python start_server.py
# Backend runs on http://localhost:8080
```

#### 2. Run Mobile App
```bash
cd mobile-app
flutter run -d chrome  # For web testing
# or
flutter run            # For device/emulator
```

#### 3. Test Flow
1. **Login** as patient (test@example.com / password123)
2. **Navigate** to "Doctor Messaging" (Messages tab)
3. **Send message** to clinician (ID: 1)
4. **Refresh** to see messages
5. **Verify** bidirectional conversation works

---

## API Testing with curl

### Login First
```bash
# Login as patient
curl -X POST http://localhost:8080/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"

# Save the access_token from response
TOKEN="eyJ..."
```

### Send Message
```bash
curl -X POST http://localhost:8080/api/v1/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "receiver_id": 1,
    "content": "Hello doctor, I have a question about my workout intensity."
  }'
```

### Get Conversation Thread
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/messages/thread/1?limit=50"
```

### Mark Message as Read
```bash
curl -X POST http://localhost:8080/api/v1/messages/42/read \
  -H "Authorization: Bearer $TOKEN"
```

---

## Run Tests

### All Messaging Tests
```bash
pytest tests/test_messaging.py -v
```

### Specific Test
```bash
pytest tests/test_messaging.py::TestMessaging::test_send_message_success -v
```

### With Coverage
```bash
pytest tests/test_messaging.py --cov=app.api.messages --cov-report=html
```

---

## Database Migration

If `messages` table doesn't exist:

### SQLite (Development)
```bash
sqlite3 adaptiv_health.db < migrations/add_messages.sql
```

### PostgreSQL (Production)
```bash
psql -U username -d adaptiv_health -f migrations/add_messages.sql
```

---

## Mobile App Implementation

The messaging feature is already integrated in Flutter:

**Files:**
- `mobile-app/lib/services/api_client.dart` (lines 678-715)
- `mobile-app/lib/screens/doctor_messaging_screen.dart`

**Usage in mobile app:**
```dart
// Get thread
final messages = await apiClient.getMessageThread(
  clinicianId,
  limit: 50,
);

// Send message
await apiClient.sendMessage(
  receiverId: clinicianId,
  content: "Hello doctor",
);
```

---

## Troubleshooting

### "401 Unauthorized"
- Token expired (30 min TTL)
- Solution: Re-login or use refresh token

### "404 User not found"
- Receiver ID doesn't exist
- Solution: Check `SELECT user_id FROM users` for valid IDs

### "422 Validation error"
- Empty message content
- Content too long (max 1000 chars)
- Solution: Check content validation

### "messages table not found"
- Migration not run
- Solution: Run `sqlite3 adaptiv_health.db < migrations/add_messages.sql`

### Mobile app shows error
- Backend not running
- Solution: Start backend with `python start_server.py`
- Check ApiClient baseUrl matches backend (default: http://localhost:8080)

---

## Documentation

**Full Implementation Guide:**
- [`docs/MESSAGING_IMPLEMENTATION.md`](docs/MESSAGING_IMPLEMENTATION.md)

**API Reference:**
- [`design files/BACKEND_API_SPECIFICATIONS.md`](design%20files/BACKEND_API_SPECIFICATIONS.md)

**Integration Status:**
- [`docs/API_INTEGRATION_STATUS.md`](docs/API_INTEGRATION_STATUS.md)

---

## Implementation Approach & Future Enhancements

**Current Implementation**:
- ✅ REST polling (industry-standard for healthcare apps)
- ✅ Message threading with read status
- ✅ Clinician assignment & access control
- ✅ Real-time mobile notifications

**Future Enhancements** (can be added in future production iterations):
- WebSockets for ultra-low-latency messaging
- Unread count endpoint
- Message editing/deletion
- File attachments
- Web dashboard integration

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/models/message.py` | Database model |
| `app/schemas/message.py` | Request/response schemas |
| `app/api/messages.py` | REST endpoints |
| `migrations/add_messages.sql` | Database migration |
| `tests/test_messaging.py` | Test suite (11 tests) |
| `mobile-app/lib/services/api_client.dart` | HTTP client methods |
| `mobile-app/lib/screens/doctor_messaging_screen.dart` | Chat UI |

---

## Support

For issues or questions:
1. Check [`docs/MESSAGING_IMPLEMENTATION.md`](docs/MESSAGING_IMPLEMENTATION.md)
2. Run `python verify_messaging.py` to diagnose
3. Check backend logs for error details
4. Review test suite: `pytest tests/test_messaging.py -v`
