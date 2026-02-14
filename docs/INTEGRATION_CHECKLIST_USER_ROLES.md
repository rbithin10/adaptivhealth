# Integration Checklist: `copilot/implement-user-roles-access`

**Branch:** `copilot/implement-user-roles-access`  
**Target:** `main`  
**Impact:** 20 files, 1,901 insertions, 37 deletions  
**Risk Level:** HIGH (authentication, RBAC, database schema changes)

---

## PRE-MERGE: CRITICAL FIXES REQUIRED

### ☑️ Fix 1: Make `/register` Admin-Only

**File:** `app/api/auth.py` (line ~238)

**Current:**
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
```

**Change to:**
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
```

**Validation:** Test that `/register` returns 401 without admin token

---

### ☑️ Fix 2: Hardcode Account Lockout to 3 Attempts

**File:** `app/api/auth.py` (line ~95)

**Current:**
```python
if auth_cred.failed_login_attempts >= settings.max_login_attempts:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
```

**Change to:**
```python
if auth_cred.failed_login_attempts >= 3:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
```

**Validation:** Test 3 failed logins → account locked for 15 minutes

---

### ☑️ Fix 3: Remove CAREGIVER Role

**File:** `app/models/user.py` (line ~30)

**Current:**
```python
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"  # ← DELETE THIS LINE
    ADMIN = "admin"
```

**Change to:**
```python
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"
```

**Validation:** No references to CAREGIVER in codebase

---

## DATABASE MIGRATION

### ☑️ Step 1: Backup Production Database

```bash
# SQLite backup
cp adaptiv_health.db adaptiv_health_backup_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL backup (if using AWS RDS)
pg_dump -h <host> -U <user> -d adaptiv_health > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### ☑️ Step 2: Run Schema Migration

**Create migration script:** `migrations/add_rbac_consent_columns.sql`

```sql
-- Add role and status columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'patient';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

-- Add medical data columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS medical_history_encrypted TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(20);

-- Add consent/sharing columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_state VARCHAR(30) DEFAULT 'SHARING_ON';
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_requested_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_requested_by INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_reviewed_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_reviewed_by INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_decision VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_reason VARCHAR(500);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_email_active ON users(email, is_active);
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);

-- Set defaults for existing users
UPDATE users SET role = 'patient' WHERE role IS NULL;
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL;
UPDATE users SET share_state = 'SHARING_ON' WHERE share_state IS NULL;
```

**Run migration:**
```bash
# SQLite
sqlite3 adaptiv_health.db < migrations/add_rbac_consent_columns.sql

# PostgreSQL
psql -h <host> -U <user> -d adaptiv_health -f migrations/add_rbac_consent_columns.sql
```

---

### ☑️ Step 3: Verify Migration

```sql
-- Check new columns exist
PRAGMA table_info(users);  -- SQLite
\d users;                  -- PostgreSQL

-- Verify data integrity
SELECT COUNT(*) FROM users WHERE role IS NULL;              -- Should be 0
SELECT COUNT(*) FROM users WHERE share_state IS NULL;       -- Should be 0
SELECT COUNT(*) FROM users WHERE is_active = TRUE;          -- Should be all
```

---

## CODE INTEGRATION

### ☑️ Step 4: Merge Branch with Fixes

```bash
# Create integration branch
git checkout main
git pull origin main
git checkout -b integration/user-roles-fixed

# Merge the feature branch
git merge origin/copilot/implement-user-roles-access

# Apply the 3 critical fixes manually
# (Fix 1, 2, 3 from above)

# Commit fixes
git add app/api/auth.py app/models/user.py
git commit -m "fix: Apply critical security fixes for RBAC integration

- Make /register admin-only (security requirement)
- Hardcode account lockout to 3 attempts (NIST standard)
- Remove unused CAREGIVER role from enum"

# Push integration branch
git push origin integration/user-roles-fixed
```

---

### ☑️ Step 5: Update Dependencies

```bash
# Backend (if any new packages)
cd c:\Users\hp\Desktop\AdpativHealth
.venv\Scripts\activate
pip install -r requirements.txt

# Web dashboard (if package.json changed)
cd web-dashboard
npm install

# Mobile app (if pubspec.yaml changed)
cd mobile-app
flutter pub get
```

---

## TESTING PHASE

### ☑️ Test 1: Backend Unit Tests

```bash
cd c:\Users\hp\Desktop\AdpativHealth
.venv\Scripts\activate
pytest tests/test_rbac_consent.py -v
```

**Expected:** All 23+ tests pass

---

### ☑️ Test 2: Account Creation Flow

1. **Admin creates patient account:**
   ```bash
   # Login as admin
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=admin@test.com&password=Admin1234"
   
   # Create patient (with admin token)
   curl -X POST http://localhost:8080/api/v1/users/ \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "patient@test.com",
       "password": "TempPass123",
       "name": "Test Patient",
       "role": "patient"
     }'
   ```

2. **Patient logs in:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=patient@test.com&password=TempPass123"
   ```

3. **Verify /register is blocked without admin:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@test.com","password":"Pass1234","name":"Test"}'
   ```
   **Expected:** 401 Unauthorized

---

### ☑️ Test 3: Account Lockout

1. **Attempt 3 failed logins:**
   ```bash
   # Attempt 1
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=patient@test.com&password=WrongPass1"
   
   # Attempt 2
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=patient@test.com&password=WrongPass2"
   
   # Attempt 3
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=patient@test.com&password=WrongPass3"
   ```

2. **Verify lockout:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/login \
     -d "username=patient@test.com&password=TempPass123"
   ```
   **Expected:** 423 Account Locked

3. **Wait 15 minutes or reset in DB:**
   ```sql
   UPDATE auth_credentials 
   SET failed_login_attempts = 0, locked_until = NULL 
   WHERE user_id = (SELECT user_id FROM users WHERE email = 'patient@test.com');
   ```

---

### ☑️ Test 4: Consent Workflow

1. **Patient requests disable:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/consent/disable \
     -H "Authorization: Bearer <patient_token>" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Privacy preference"}'
   ```

2. **Clinician views pending requests:**
   ```bash
   curl -X GET http://localhost:8080/api/v1/consent/pending \
     -H "Authorization: Bearer <clinician_token>"
   ```

3. **Clinician approves:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/consent/review/2 \
     -H "Authorization: Bearer <clinician_token>" \
     -H "Content-Type: application/json" \
     -d '{"decision":"approve","reason":"Patient request honored"}'
   ```

4. **Verify vitals blocked:**
   ```bash
   curl -X GET http://localhost:8080/api/v1/vitals/user/2/latest \
     -H "Authorization: Bearer <clinician_token>"
   ```
   **Expected:** 403 Patient has disabled data sharing

---

### ☑️ Test 5: Admin Panel UI

1. **Open web dashboard:** http://localhost:3000/admin
2. **Verify admin login required**
3. **Test create user form:**
   - Email: test@example.com
   - Password: TestPass123
   - Role: patient
   - Submit → Verify user created
4. **Test password reset:**
   - Select user
   - New password: NewPass456
   - Submit → Verify success
5. **Test deactivate:**
   - Click deactivate on test user
   - Confirm → Verify is_active = False

---

### ☑️ Test 6: Mobile Password Reset

1. **Open mobile app:** http://localhost:5000
2. **Click "Forgot password?"**
3. **Enter email:** patient@test.com
4. **Submit → Check backend logs for reset token**
5. **Copy token from logs**
6. **Use token to reset password via API:**
   ```bash
   curl -X POST http://localhost:8080/api/v1/reset-password/confirm \
     -H "Content-Type: application/json" \
     -d '{"token":"<token_from_logs>","new_password":"NewPass789"}'
   ```
7. **Login with new password**

---

### ☑️ Test 7: Role-Based Access

**Admin blocked from PHI:**
```bash
# Login as admin
curl -X POST http://localhost:8080/api/v1/login \
  -d "username=admin@test.com&password=Admin1234"

# Try to access patient vitals (should fail)
curl -X GET http://localhost:8080/api/v1/vitals/user/2/latest \
  -H "Authorization: Bearer <admin_token>"
```
**Expected:** 403 Admin users cannot access patient health data

---

## DEPLOYMENT

### ☑️ Step 8: Deploy Backend

```bash
# Stop existing service
# (Adjust for your deployment method)

# Pull latest code
git checkout main
git pull origin main

# Activate venv and install deps
.venv\Scripts\activate
pip install -r requirements.txt

# Run migrations (if not done)
python scripts/run_migrations.py

# Restart service
# Example: systemctl restart adaptiv-health-api
```

---

### ☑️ Step 9: Deploy Web Dashboard

```bash
cd web-dashboard
npm install
npm run build

# Deploy build/ folder to hosting
# Example: Copy to nginx web root, or deploy to Vercel/Netlify
```

---

### ☑️ Step 10: Deploy Mobile App

```bash
cd mobile-app
flutter pub get
flutter build web

# Deploy build/web folder
# Example: Firebase Hosting, AWS S3, etc.
```

---

## POST-DEPLOYMENT VALIDATION

### ☑️ Verify 1: Backend Health

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/predict/status
```
**Expected:** Both return 200 OK

---

### ☑️ Verify 2: Database State

```sql
-- Check user roles distribution
SELECT role, COUNT(*) FROM users GROUP BY role;

-- Check consent states
SELECT share_state, COUNT(*) FROM users GROUP BY share_state;

-- Check active accounts
SELECT COUNT(*) FROM users WHERE is_active = TRUE;
```

---

### ☑️ Verify 3: Admin Access

1. Login to admin panel
2. Verify user list loads
3. Create a test account
4. Delete test account

---

### ☑️ Verify 4: Patient Flow

1. Admin creates patient account
2. Patient logs in with temp password
3. Patient views own vitals
4. Patient requests consent disable
5. Clinician approves request
6. Clinician blocked from patient vitals

---

## ROLLBACK PLAN

### If Critical Issues Found

**Step 1: Revert Code**
```bash
git checkout main
git revert <integration_commit_hash>
git push origin main
```

**Step 2: Restore Database**
```bash
# SQLite
cp adaptiv_health_backup_YYYYMMDD_HHMMSS.db adaptiv_health.db

# PostgreSQL
psql -h <host> -U <user> -d adaptiv_health < backup_YYYYMMDD_HHMMSS.sql
```

**Step 3: Redeploy Previous Version**
```bash
git checkout <previous_stable_tag>
# Redeploy backend, web, mobile
```

---

## MONITORING POST-INTEGRATION

### Week 1: Watch for Issues

**Backend Logs:**
- Authentication failures (429, 423)
- Authorization errors (403)
- Consent state transitions
- Admin actions (user creation, password resets)

**Database Queries:**
```sql
-- Failed logins in last 24 hours
SELECT email, failed_login_attempts, locked_until 
FROM users u 
JOIN auth_credentials ac ON u.user_id = ac.user_id 
WHERE failed_login_attempts > 0;

-- Consent state changes today
SELECT COUNT(*), share_state 
FROM users 
WHERE DATE(share_requested_at) = CURRENT_DATE 
GROUP BY share_state;

-- New accounts created today
SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE;
```

**Metrics to Track:**
- Login success rate
- Account lockouts per day
- Consent disable requests
- Admin actions performed
- PHI access denials (403 errors)

---

## DOCUMENTATION UPDATES

### ☑️ Update API Documentation

- Add 8 consent endpoints to Swagger/ReDoc
- Update /register security requirement (admin-only)
- Document role requirements for all endpoints

### ☑️ Update User Guides

- Admin: How to create accounts, reset passwords
- Patient: How to request consent disable
- Clinician: How to review consent requests

### ☑️ Update Developer Docs

- RBAC architecture overview
- Consent state machine diagram
- Migration guide for existing users
- Security best practices

---

## SIGN-OFF CHECKLIST

- [ ] All 3 critical fixes applied
- [ ] Database migration successful
- [ ] All backend tests pass (23+ tests)
- [ ] Manual E2E tests complete
- [ ] Admin panel functional
- [ ] Mobile password reset works
- [ ] Role-based access enforced
- [ ] Consent workflow operational
- [ ] Backup created before deploy
- [ ] Rollback plan tested
- [ ] Monitoring alerts configured
- [ ] Documentation updated
- [ ] Team trained on new features

---

## CONTACTS & SUPPORT

**Integration Lead:** [Your Name]  
**Backend Team:** [Contact]  
**Frontend Team:** [Contact]  
**Database Admin:** [Contact]  

**Rollback Authority:** [Name/Role]  
**Emergency Contact:** [Phone/Email]

---

## COMPLETION

**Integration Date:** _________________  
**Deployed By:** _________________  
**Verified By:** _________________  
**Status:** ☐ Success  ☐ Rolled Back  ☐ Partial (notes):

**Notes:**
