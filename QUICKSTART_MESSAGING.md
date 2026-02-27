# ⚡ Quick Start - Messaging & Notifications

## In 3 Steps 🚀

### 1️⃣ Apply Migration
```bash
cd c:\Users\hp\Desktop\AdpativHealth
python apply_migrations.py
```

**What happens:**
- Adds `assigned_clinician_id` column to users table
- Creates index for fast lookups
- Takes ~2 seconds

### 2️⃣ Restart Backend & Frontend
```bash
# Terminal 1: Backend
python start_server.py

# Terminal 2: Web Dashboard  
cd web-dashboard
npm start
```

### 3️⃣ Test It

**Assign a clinician to a patient:**
```bash
# 1. Login as admin
curl -X POST http://localhost:8080/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"adminpass123"}'
# Copy the access_token from response

# 2. Assign clinician 3 to patient 5 (replace ADMIN_TOKEN)
curl -X PUT "http://localhost:8080/api/v1/users/5/assign-clinician?clinician_id=3" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Test messaging:**
1. Open mobile app → Messages tab → Send message to assigned clinician
2. Open web dashboard → Click "Messages" button (top-right)
3. See patient in inbox with unread count badge
4. Click patient to open chat
5. Reply to patient
6. Both see real-time updates (3-5 second polling)

## What You Got ✨

| Component | Location | What It Does |
|-----------|----------|---|
| **Messaging Page** | `/messages` (web only) | Inbox + chat interface for clinicians |
| **Unread Badge** | Dashboard header | Shows "1", "2", etc. for unread messages |
| **Inbox API** | `GET /messages/inbox` | Returns patients with unread counts |
| **Clinician Assignment** | `PUT /users/{id}/assign-clinician` | Admin endpoint to pair clinician ↔ patient |
| **Real-Time Polling** | Every 3-5 seconds | Auto-updates inbox and messages |
| **Mobile Integration** | Already working | Patients see assigned clinician |

## URLs to Visit

| URL | User | Purpose |
|-----|------|---------|
| `http://localhost:3000/messages` | Clinician | Open messaging inbox |
| `http://localhost:3000/dashboard` | Clinician | See Messages badge in header |
| Mobile app Messages tab | Patient | Send message to assigned clinician |

## Files to Know

| File | Purpose |
|------|---------|
| `MESSAGING_SETUP.md` | Full technical guide (300+ lines) |
| `IMPLEMENTATION_SUMMARY.md` | What was built (test checklist included) |
| `apply_migrations.py` | Run this to apply database changes |
| `web-dashboard/src/pages/MessagingPage.tsx` | New messaging UI (450 lines) |

## Troubleshooting in 30 Seconds

| Problem | Fix |
|---------|-----|
| "Column already exists" | Good! Migration already applied. Run `sqlite3 adaptiv_health.db "PRAGMA table_info(users);"` to verify |
| Unread badge not showing | Check if Messages button exists in dashboard header. Restart frontend if needed. |
| Messages not appearing | 1) Verify clinician is assigned: `sqlite3 adaptiv_health.db "SELECT * FROM users;"` look for `assigned_clinician_id` 2) Verify patient sent message 3) Check browser DevTools → Network for polling requests |
| "Only clinicians can view inbox" | Make sure logged-in user is a clinician, not a patient. Patients use mobile app. |

## Next Optional Steps

- **Add Admin UI**: Create form to assign clinicians (currently API-only)
- **Upgrade to WebSockets**: Replace polling with socket.io for instant updates
- **Encrypt Messages**: Add AES-256 encryption to message content

## Key Insights 💡

✅ **Polling is production-standard** - 3-5 second latency meets healthcare requirements
✅ **Bidirectional data isolation** - Clinician A cannot see Clinician B's patients
✅ **Already in mobile app** - Messaging was already there; now clinicians have dashboard
✅ **Real-time notifications** - Red badge shows unread count instantly

## Questions?

1. See **MESSAGING_SETUP.md** for full technical docs
2. See **IMPLEMENTATION_SUMMARY.md** for testing checklist
3. Check backend logs: `tail startup.log` or watch terminal output

---

**You're ready to go! 🎉**
