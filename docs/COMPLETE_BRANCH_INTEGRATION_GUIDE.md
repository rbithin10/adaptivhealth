# COMPLETE Integration Guide: `copilot/implement-user-roles-access`

**Branch:** `copilot/implement-user-roles-access`  
**Target:** `main`  
**Scope:** 20 files, 1,901 insertions, 37 deletions  
**Impact:** Authentication, RBAC, Consent Management, Admin UI, Database Schema

---

## OVERVIEW OF ALL CHANGES

### 4 New Files Added
1. `API_UI_COVERAGE.md` (350 lines) - Comprehensive API/UI documentation
2. `app/api/consent.py` (219 lines) - **8 new consent management endpoints**
3. `tests/test_rbac_consent.py` (246 lines) - **Comprehensive test suite**
4. `web-dashboard/src/pages/AdminPage.tsx` (321 lines) - **Admin panel UI**

### 16 Files Modified

#### Backend API Files (Consent enforcement added)
5. `app/api/activity.py` (+11 lines) - Added consent check to `GET /activities/user/{id}`
6. `app/api/alert.py` (+11 lines) - Added consent check to `GET /alerts/user/{id}`
7. `app/api/predict.py` (+16 lines) - Added consent checks to 5 prediction endpoints
8. `app/api/vital_signs.py` (+8 lines) - Added consent checks to 3 vitals endpoints
9. `app/api/auth.py` (+33 lines) - Password reset, lockout logic, register endpoint
10. `app/api/user.py` (+67 lines) - Admin user management, password reset by admin

#### Core Backend Files
11. `app/main.py` (+9 lines) - Registered consent router
12. `app/models/user.py` (+14 lines) - **13 new database columns** + UserRole enum

#### Frontend Files
13. `web-dashboard/src/App.tsx` (+9 lines) - Added /admin route
14. `web-dashboard/src/pages/DashboardPage.tsx` (+91 lines) - Role-based dashboard display
15. `web-dashboard/src/pages/LoginPage.tsx` (+89 lines) - Role display, improved UI
16. `web-dashboard/src/services/api.ts` (+96 lines) - Admin & consent API functions

#### Mobile App Files
17. `mobile-app/lib/screens/login_screen.dart` (+124 lines) - **Forgot password UI**
18. `mobile-app/lib/screens/profile_screen.dart` (+124 lines) - Display role, consent status
19. `mobile-app/lib/services/api_client.dart` (+99 lines) - Password reset API calls

#### Test Files
20. `tests/test_registration.py` (+1 line) - Minor update

---

## DETAILED CHANGE BREAKDOWN

### 1. DATABASE SCHEMA CHANGES

**File:** `app/models/user.py`

#### New Enum
```python
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"  # ⚠️ FIX REQUIRED: Remove this (not implemented)
    ADMIN = "admin"
```

#### 13 New Columns Added to `users` Table
```python
# Role and status
role = Column(Enum(UserRole), default=UserRole.PATIENT)
is_active = Column(Boolean, default=True)
is_verified = Column(Boolean, default=False)

# Medical data (encrypted)
medical_history_encrypted = Column(String)
emergency_contact_name = Column(String(255))
emergency_contact_phone = Column(String(20))

# Consent/sharing state machine (7 columns)
share_state = Column(String(30), default="SHARING_ON")
share_requested_at = Column(DateTime(timezone=True))
share_requested_by = Column(Integer)
share_reviewed_at = Column(DateTime(timezone=True))
share_reviewed_by = Column(Integer)
share_decision = Column(String(20))
share_reason = Column(String(500))
```

**Migration Required:** See section 3 below

---

### 2. AUTHENTICATION & AUTHORIZATION CHANGES

**File:** `app/api/auth.py`

#### A. Password Reset Flow (NEW - 3 endpoints)

**Endpoint:** `POST /api/v1/request-password-reset`
- **Public** (no auth required)
- Input: `{"email": "user@example.com"}`
- Generates reset token, stores in DB
- Returns: `{"message": "Password reset instructions sent"}`

**Endpoint:** `POST /api/v1/reset-password/confirm`
- **Public** (no auth required)
- Input: `{"token": "abc123...", "new_password": "NewPass123"}`
- Validates token, updates password
- Returns: `{"message": "Password reset successful"}`

**Endpoint:** `GET /api/v1/check-reset-token/{token}`
- **Public** (no auth required)
- Validates if reset token is valid
- Returns: `{"valid": true}` or 400 error

#### B. Account Lockout Logic

**Current (branch):**
```python
if auth_cred.failed_login_attempts >= settings.max_login_attempts:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
```

**⚠️ FIX REQUIRED:** Hardcode to 3 attempts:
```python
if auth_cred.failed_login_attempts >= 3:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
```

#### C. Registration Endpoint

**Current (branch):**
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)  # ⚠️ PUBLIC - NO AUTH
):
```

**⚠️ FIX REQUIRED:** Make admin-only:
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
```

#### D. New Permission Helper Function

```python
def check_clinician_phi_access(clinician: User, patient: User):
    """
    Enforces consent for clinician access to patient PHI.
    Raises 403 if:
    - Patient has disabled sharing (share_state != "SHARING_ON")
    - User is ADMIN (admins cannot access PHI, only manage users)
    """
    if clinician.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin users cannot access patient health data"
        )
    
    if patient.share_state != "SHARING_ON":
        raise HTTPException(
            status_code=403,
            detail="Patient has disabled data sharing"
        )
```

---

### 3. USER MANAGEMENT (Admin Features)

**File:** `app/api/user.py`

#### New/Updated Endpoints

**A. Create User (Admin Only)**
```python
POST /api/v1/users/
Auth: Admin only
Input: {
  "email": "patient@example.com",
  "password": "TempPass123",
  "name": "John Doe",
  "age": 45,
  "gender": "M",
  "phone": "+1234567890",
  "role": "patient"
}
```

**B. Reset User Password (Admin Only)**
```python
POST /api/v1/users/{user_id}/reset-password
Auth: Admin only
Input: {"new_password": "NewTempPass456"}
```

**C. Deactivate User (Admin Only)**
```python
POST /api/v1/users/{user_id}/deactivate
Auth: Admin only
Body: {"reason": "Account closed"}
```

**D. Reactivate User (Admin Only)**
```python
POST /api/v1/users/{user_id}/reactivate
Auth: Admin only
```

**E. Get All Users (Admin Only)**
```python
GET /api/v1/users/
Auth: Admin only
Returns: List of all users with role, status, consent state
```

---

### 4. CONSENT MANAGEMENT (8 New Endpoints)

**File:** `app/api/consent.py` (NEW FILE - 219 lines)

#### Consent State Machine
```
SHARING_ON (default)
   ↓ Patient requests disable
SHARING_DISABLE_REQUESTED
   ↓ Clinician approves
SHARING_OFF
   ↓ Patient requests re-enable
SHARING_ENABLE_REQUESTED
   ↓ Clinician approves
SHARING_ON
```

#### Endpoints

**A. Request Disable Sharing (Patient)**
```python
POST /api/v1/consent/disable
Auth: Patient only
Input: {"reason": "Privacy concern"}
Sets: share_state = SHARING_DISABLE_REQUESTED
```

**B. Request Enable Sharing (Patient)**
```python
POST /api/v1/consent/enable
Auth: Patient only
Input: {"reason": "Want to share data again"}
Sets: share_state = SHARING_ENABLE_REQUESTED
```

**C. Get Pending Requests (Clinician)**
```python
GET /api/v1/consent/pending
Auth: Clinician only
Returns: All patients with DISABLE/ENABLE_REQUESTED states
```

**D. Review Request (Clinician)**
```python
POST /api/v1/consent/review/{user_id}
Auth: Clinician only
Input: {
  "decision": "approve",  // or "reject"
  "reason": "Patient request honored"
}
```

**E. Get My Consent Status (Patient)**
```python
GET /api/v1/consent/status
Auth: Patient only
Returns: {
  "share_state": "SHARING_ON",
  "share_requested_at": null,
  "pending_request": false
}
```

**F. Get Patient Consent Status (Clinician)**
```python
GET /api/v1/consent/patient/{user_id}
Auth: Clinician only
Returns: Patient's consent state + history
```

**G. Get Consent Audit Log (Patient)**
```python
GET /api/v1/consent/audit
Auth: Patient only
Returns: History of all consent state changes
```

**H. Get Patient Audit Log (Clinician)**
```python
GET /api/v1/consent/patient/{user_id}/audit
Auth: Clinician only
Returns: Patient's consent audit log
```

---

### 5. PHI ACCESS PROTECTION (Consent Enforcement)

All patient data endpoints now check consent before returning PHI:

#### `app/api/vital_signs.py` (3 endpoints)
- `GET /api/v1/vitals/user/{user_id}/latest` → Add consent check
- `GET /api/v1/vitals/user/{user_id}/summary` → Add consent check
- `GET /api/v1/vitals/user/{user_id}/history` → Add consent check

#### `app/api/activity.py` (1 endpoint)
- `GET /api/v1/activities/user/{user_id}` → Add consent check

#### `app/api/alert.py` (1 endpoint)
- `GET /api/v1/alerts/user/{user_id}` → Add consent check

#### `app/api/predict.py` (5 endpoints)
- `GET /api/v1/predict/user/{user_id}/risk` → Add consent check
- `POST /api/v1/predict/patient/{user_id}/risk-assessment` → Add consent check
- `GET /api/v1/predict/patient/{user_id}/risk-assessment/latest` → Add consent check
- `GET /api/v1/predict/patient/{user_id}/recommendation/latest` → Add consent check
- `POST /api/v1/predict/patient/{user_id}/recommendation` → Add consent check

**Implementation Pattern (same for all):**
```python
# Before accessing patient data
patient = db.query(User).filter(User.user_id == user_id).first()
if not patient:
    raise HTTPException(status_code=404, detail="User not found")
check_clinician_phi_access(current_user, patient)  # ← NEW

# Then proceed with data access
```

---

### 6. WEB DASHBOARD CHANGES

#### A. New Admin Page (`web-dashboard/src/pages/AdminPage.tsx` - 321 lines)

**Features:**
1. **Create User Form**
   - Fields: email, password, name, age, gender, phone, role
   - Calls `POST /api/v1/users/`

2. **User List Table**
   - Displays: ID, name, email, role, status, consent state
   - Actions: Reset password, deactivate/reactivate
   - Fetches `GET /api/v1/users/`

3. **Reset Password Dialog**
   - Admin enters new password for user
   - Calls `POST /api/v1/users/{id}/reset-password`

4. **Deactivate User**
   - Calls `POST /api/v1/users/{id}/deactivate`

**Access:** Only visible to users with role=ADMIN

#### B. Updated App Router (`web-dashboard/src/App.tsx`)

```typescript
// New route added
<Route path="/admin" element={<AdminPage />} />
```

#### C. Enhanced Dashboard (`web-dashboard/src/pages/DashboardPage.tsx` +91 lines)

**New Features:**
- Display user role badge (Patient/Clinician/Admin)
- Consent status indicator for patients
- Role-specific navigation (admins see "Admin Panel" link)
- Improved patient/clinician data displays

#### D. Updated Login Page (`web-dashboard/src/pages/LoginPage.tsx` +89 lines)

**New Features:**
- Display logged-in user's role
- Better error messages
- "Forgot Password?" link (opens modal)
- Improved UI/UX

#### E. API Service Layer (`web-dashboard/src/services/api.ts` +96 lines)

**New API Functions:**
```typescript
// Admin functions
export const createUser = (userData: UserCreateRequest) => {...}
export const getAllUsers = () => {...}
export const resetUserPassword = (userId: number, password: string) => {...}
export const deactivateUser = (userId: number, reason: string) => {...}
export const reactivateUser = (userId: number) => {...}

// Consent functions
export const requestDisableSharing = (reason: string) => {...}
export const requestEnableSharing = (reason: string) => {...}
export const getPendingConsentRequests = () => {...}
export const reviewConsentRequest = (userId: number, decision: string, reason: string) => {...}
export const getMyConsentStatus = () => {...}
export const getPatientConsentStatus = (userId: number) => {...}

// Password reset
export const requestPasswordReset = (email: string) => {...}
export const confirmPasswordReset = (token: string, password: string) => {...}
export const checkResetToken = (token: string) => {...}
```

---

### 7. MOBILE APP CHANGES

#### A. Login Screen (`mobile-app/lib/screens/login_screen.dart` +124 lines)

**New "Forgot Password" View:**
- User enters email
- Calls `apiClient.requestPasswordReset(email)`
- Shows success message
- Backend sends reset token (currently logged, not emailed)

**Flow:**
1. User clicks "Forgot Password?"
2. Enters email → Submits
3. Receives confirmation
4. (In production: Email with reset link)
5. User enters token + new password
6. Calls `confirmPasswordReset(token, password)`

#### B. Profile Screen (`mobile-app/lib/screens/profile_screen.dart` +124 lines)

**New Display Fields:**
- User role badge (Patient/Clinician/Admin)
- Consent status:
  - "Data Sharing: ON" (green)
  - "Data Sharing: OFF" (red)
  - "Data Sharing: Pending Review" (yellow)
- Button: "Request to Disable Sharing" or "Request to Enable Sharing"

**New Actions:**
- Request disable sharing → Calls `apiClient.requestDisableSharing(reason)`
- Request enable sharing → Calls `apiClient.requestEnableSharing(reason)`
- View consent history → Calls `apiClient.getConsentAudit()`

#### C. API Client (`mobile-app/lib/services/api_client.dart` +99 lines)

**New Methods:**
```dart
// Password reset
Future<void> requestPasswordReset(String email)
Future<void> confirmPasswordReset(String token, String newPassword)
Future<bool> checkResetToken(String token)

// Consent management
Future<void> requestDisableSharing(String reason)
Future<void> requestEnableSharing(String reason)
Future<Map<String, dynamic>> getConsentStatus()
Future<List<dynamic>> getConsentAudit()

// Clinician consent actions
Future<List<dynamic>> getPendingConsentRequests()
Future<void> reviewConsentRequest(int userId, String decision, String reason)
Future<Map<String, dynamic>> getPatientConsentStatus(int userId)
```

---

### 8. TESTING

**File:** `tests/test_rbac_consent.py` (NEW - 246 lines)

**Test Coverage (23+ tests):**

1. **Role-Based Access Control (8 tests)**
   - Patient can access own data
   - Clinician can access patient data (when sharing ON)
   - Admin cannot access patient PHI
   - Unauthorized access attempts blocked

2. **Consent Workflow (7 tests)**
   - Patient requests disable sharing
   - Clinician sees pending request
   - Clinician approves/rejects request
   - State transitions correctly
   - PHI blocked when sharing OFF

3. **Admin User Management (5 tests)**
   - Admin creates user account
   - Admin resets user password
   - Admin deactivates/reactivates user
   - Non-admin cannot access admin endpoints

4. **Account Lockout (3 tests)**
   - 3 failed logins lock account
   - Locked account returns 423
   - Lockout expires after 15 minutes

**Run Tests:**
```bash
pytest tests/test_rbac_consent.py -v
```

---

### 9. DOCUMENTATION

**File:** `API_UI_COVERAGE.md` (NEW - 350 lines)

**Contents:**
- Complete API endpoint reference (all 8 consent endpoints)
- UI implementation status (web dashboard + mobile app)
- Frontend component mapping
- Test scenario descriptions
- Integration checklist

---

## CRITICAL FIXES REQUIRED BEFORE MERGE

### ⚠️ Fix 1: Remove CAREGIVER Role

**File:** `app/models/user.py` (line ~30)

**Current:**
```python
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"  # ← DELETE THIS
    ADMIN = "admin"
```

**Fixed:**
```python
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"
```

---

### ⚠️ Fix 2: Hardcode Account Lockout to 3 Attempts

**File:** `app/api/auth.py` (line ~95)

**Current:**
```python
if auth_cred.failed_login_attempts >= settings.max_login_attempts:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
```

**Fixed:**
```python
if auth_cred.failed_login_attempts >= 3:
    auth_cred.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
```

---

### ⚠️ Fix 3: Make /register Admin-Only

**File:** `app/api/auth.py` (line ~238)

**Current:**
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)  # ← PUBLIC
):
```

**Fixed:**
```python
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),  # ← ADMIN ONLY
    db: Session = Depends(get_db)
):
```

---

## DATABASE MIGRATION

### Step 1: Backup Database

```bash
# SQLite
cp adaptiv_health.db adaptiv_health_backup_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL
pg_dump -h <host> -U <user> -d adaptiv_health > backup.sql
```

### Step 2: Create Migration SQL

**File:** `migrations/add_rbac_consent.sql`

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
CREATE INDEX IF NOT EXISTS idx_user_share_state ON users(share_state);

-- Set defaults for existing users
UPDATE users SET role = 'patient' WHERE role IS NULL;
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL;
UPDATE users SET share_state = 'SHARING_ON' WHERE share_state IS NULL;
```

### Step 3: Run Migration

```bash
# SQLite
sqlite3 adaptiv_health.db < migrations/add_rbac_consent.sql

# PostgreSQL
psql -h <host> -U <user> -d adaptiv_health -f migrations/add_rbac_consent.sql
```

### Step 4: Verify Migration

```sql
-- Check columns exist
PRAGMA table_info(users);  -- SQLite
\d users;                  -- PostgreSQL

-- Verify data
SELECT COUNT(*) FROM users WHERE role IS NULL;         -- Should be 0
SELECT COUNT(*) FROM users WHERE share_state IS NULL;  -- Should be 0
SELECT role, COUNT(*) FROM users GROUP BY role;
```

---

## INTEGRATION STEPS

### 1. Checkout and Merge

```bash
# Fetch latest
git fetch origin

# Create integration branch
git checkout main
git pull origin main
git checkout -b integration/user-roles-complete

# Merge feature branch
git merge origin/copilot/implement-user-roles-access

# Check for conflicts
git status
```

### 2. Apply Critical Fixes

Apply fixes 1, 2, 3 from above manually:
- Remove CAREGIVER from UserRole enum
- Hardcode lockout to 3 attempts
- Make /register admin-only

```bash
# Commit fixes
git add app/models/user.py app/api/auth.py
git commit -m "fix: Apply 3 critical security/config fixes for RBAC

- Remove unused CAREGIVER role (only 3 roles needed)
- Hardcode account lockout to 3 attempts (NIST standard)
- Make /register admin-only (per security requirements)"
```

### 3. Update Dependencies

```bash
# Backend
cd c:\Users\hp\Desktop\AdpativHealth
.venv\Scripts\activate
pip install -r requirements.txt

# Web dashboard
cd web-dashboard
npm install

# Mobile app
cd mobile-app
flutter pub get
```

### 4. Run Database Migration

```bash
# Run migration SQL (see section above)
sqlite3 adaptiv_health.db < migrations/add_rbac_consent.sql
```

### 5. Run Tests

```bash
cd c:\Users\hp\Desktop\AdpativHealth
.venv\Scripts\activate
pytest tests/test_rbac_consent.py -v
pytest tests/test_registration.py -v
```

### 6. Manual Testing

Start all services:
```bash
# Terminal 1: Backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080

# Terminal 2: Web Dashboard
cd web-dashboard
npm start

# Terminal 3: Mobile App
cd mobile-app
flutter run -d chrome --web-port=5000
```

Test scenarios:
1. ✅ Admin creates patient account
2. ✅ Patient logs in with temp password
3. ✅ Patient requests consent disable
4. ✅ Clinician reviews and approves
5. ✅ Clinician blocked from patient PHI
6. ✅ Admin cannot access PHI
7. ✅ 3 failed logins lock account
8. ✅ Password reset flow works
9. ✅ /register blocked without admin token

### 7. Deploy

```bash
# Push integration branch
git push origin integration/user-roles-complete

# Create PR for review
# After approval, merge to main
git checkout main
git merge integration/user-roles-complete
git push origin main

# Deploy to production
# (Follow your deployment process)
```

---

## COMPLETE FILE-BY-FILE SUMMARY

| File | Status | Lines | Key Changes |
|------|--------|-------|-------------|
| API_UI_COVERAGE.md | NEW | +350 | API/UI documentation |
| app/api/activity.py | MODIFIED | +11 | Consent check in get_user_activities |
| app/api/alert.py | MODIFIED | +11 | Consent check in get_user_alerts |
| app/api/auth.py | MODIFIED | +33 | Password reset (3 endpoints), lockout logic ⚠️ |
| app/api/consent.py | NEW | +219 | 8 consent management endpoints |
| app/api/predict.py | MODIFIED | +16 | Consent checks in 5 prediction endpoints |
| app/api/user.py | MODIFIED | +67 | Admin user mgmt (create, reset pwd, deactivate) |
| app/api/vital_signs.py | MODIFIED | +8 | Consent checks in 3 vitals endpoints |
| app/main.py | MODIFIED | +9 | Register consent router |
| app/models/user.py | MODIFIED | +14 | 13 new columns, UserRole enum ⚠️ |
| mobile-app/lib/screens/login_screen.dart | MODIFIED | +124 | Forgot password UI |
| mobile-app/lib/screens/profile_screen.dart | MODIFIED | +124 | Role & consent status display |
| mobile-app/lib/services/api_client.dart | MODIFIED | +99 | Password reset & consent API calls |
| tests/test_rbac_consent.py | NEW | +246 | 23+ tests for RBAC, consent, admin |
| tests/test_registration.py | MODIFIED | +1 | Minor update |
| web-dashboard/src/App.tsx | MODIFIED | +9 | /admin route |
| web-dashboard/src/pages/AdminPage.tsx | NEW | +321 | Complete admin panel UI |
| web-dashboard/src/pages/DashboardPage.tsx | MODIFIED | +91 | Role display, consent status |
| web-dashboard/src/pages/LoginPage.tsx | MODIFIED | +89 | Forgot password link, role display |
| web-dashboard/src/services/api.ts | MODIFIED | +96 | Admin & consent API functions |

**Total: 20 files, 1,901 insertions, 37 deletions**

---

## ROLLBACK PLAN

If issues found after deployment:

```bash
# 1. Revert code
git checkout main
git revert <merge_commit_hash>
git push origin main

# 2. Restore database
cp adaptiv_health_backup_YYYYMMDD.db adaptiv_health.db
# or
psql < backup.sql

# 3. Redeploy previous version
git checkout <previous_stable_tag>
# Redeploy backend, web, mobile
```

---

## POST-INTEGRATION MONITORING

### Week 1 Metrics
- Login success/failure rates
- Account lockouts per day
- Consent disable/enable requests
- Admin actions (user creation, password resets)
- 403 errors (PHI access denied)
- 423 errors (account locked)

### SQL Queries
```sql
-- Failed logins today
SELECT email, failed_login_attempts, locked_until 
FROM users u JOIN auth_credentials ac ON u.user_id = ac.user_id 
WHERE failed_login_attempts > 0;

-- Consent requests today
SELECT COUNT(*), share_state FROM users 
WHERE DATE(share_requested_at) = CURRENT_DATE 
GROUP BY share_state;

-- New users created today
SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE;

-- Role distribution
SELECT role, COUNT(*) FROM users GROUP BY role;
```

---

## CHECKLIST

Integration Preparation:
- [ ] All 3 critical fixes applied
- [ ] Database backup created
- [ ] Migration SQL tested on dev DB
- [ ] Dependencies updated (pip, npm, flutter)

Testing:
- [ ] All 246 unit tests pass
- [ ] Manual E2E tests complete (9 scenarios)
- [ ] Admin panel functional
- [ ] Mobile password reset works
- [ ] Consent workflow operational
- [ ] PHI access blocked when sharing OFF

Deployment:
- [ ] Integration branch merged to main
- [ ] Production DB migration successful
- [ ] Backend deployed
- [ ] Web dashboard deployed
- [ ] Mobile app deployed
- [ ] All services health checks pass

Documentation:
- [ ] API docs updated
- [ ] User guides updated (admin, patient, clinician)
- [ ] Team trained on new features
- [ ] Runbook updated with rollback steps

Monitoring:
- [ ] Alerts configured for 403/423 errors
- [ ] Dashboard for consent requests
- [ ] Admin action audit log enabled

---

## CONTACTS

**Integration Lead:** _________________  
**Backend Team:** _________________  
**Frontend Team:** _________________  
**Database Admin:** _________________  
**Rollback Authority:** _________________  

---

## SIGN-OFF

**Integration Date:** _________________  
**Deployed By:** _________________  
**Verified By:** _________________  
**Status:** ☐ Success  ☐ Rolled Back  ☐ Partial

**Notes:**

