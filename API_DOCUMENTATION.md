# AdaptivHealth – API Reference

Complete inventory of every API endpoint defined in the FastAPI backend and how each is consumed by the **React web dashboard** and **Flutter mobile app**.

**Base URL**: `http://localhost:8000`
**API Prefix**: `/api/v1`
**Auth**: JWT Bearer tokens (`Authorization: Bearer <token>`)
**Auto-generated docs**: Swagger UI at `/docs`, ReDoc at `/redoc`

---

## Table of Contents

1. [Health Check Endpoints](#1-health-check-endpoints)
2. [Authentication Endpoints](#2-authentication-endpoints)
3. [User Management Endpoints](#3-user-management-endpoints)
4. [Vital Signs Endpoints](#4-vital-signs-endpoints)
5. [Activity / Session Endpoints](#5-activity--session-endpoints)
6. [Alert Endpoints](#6-alert-endpoints)
7. [AI Risk Prediction Endpoints](#7-ai-risk-prediction-endpoints)
8. [Frontend Usage Summary](#8-frontend-usage-summary)
9. [API Methods Defined but Not Yet Used by UI](#9-api-methods-defined-but-not-yet-used-by-ui)

---

## 1. Health Check Endpoints

Defined directly in `app/main.py` (no `/api/v1` prefix).

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `GET` | `/` | `root()` | Root welcome message |
| `GET` | `/health` | `health_check()` | Application health status |
| `GET` | `/health/db` | `database_health_check()` | Database connectivity check |

**Web dashboard usage** – `api.ts` defines `getHealth()` and `getDatabaseHealth()` but neither page calls them.
**Mobile app usage** – `ai_api.dart` defines `getHealth()` but no screen calls it directly.

---

## 2. Authentication Endpoints

Defined in `app/api/auth.py` · Mounted at `/api/v1` · Tag: *Authentication*

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `POST` | `/api/v1/register` | `register_user()` | Create a new user account |
| `POST` | `/api/v1/login` | `login()` | Authenticate with email + password, returns JWT |
| `POST` | `/api/v1/refresh` | `refresh_token()` | Exchange a refresh token for a new access token |
| `GET` | `/api/v1/me` | `get_current_user_info()` | Return the authenticated user's profile |
| `POST` | `/api/v1/reset-password` | `request_password_reset()` | Request a password-reset token (1-hour expiry) |
| `POST` | `/api/v1/reset-password/confirm` | `confirm_password_reset()` | Confirm password reset with token + new password |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `POST /login` | ✅ `LoginPage` | ✅ `LoginScreen`, `AiApi` |
| `POST /register` | ✅ `api.ts` (defined) | ✅ `api_client.dart` (defined) |
| `POST /refresh` | — | — |
| `GET /me` | — (uses `/users/me`) | — (uses `/users/me`) |
| `POST /reset-password` | — | — |
| `POST /reset-password/confirm` | — | — |

---

## 3. User Management Endpoints

Defined in `app/api/user.py` · Mounted at `/api/v1/users` · Tag: *User Management*

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| `GET` | `/api/v1/users/me` | `get_my_profile()` | Any | Get own profile |
| `PUT` | `/api/v1/users/me` | `update_my_profile()` | Any | Update own profile (whitelisted fields: name, age, gender, phone) |
| `PUT` | `/api/v1/users/me/medical-history` | `update_medical_history()` | Any | Update own medical history |
| `GET` | `/api/v1/users/` | `list_users()` | Admin/Clinician | Paginated list of all users |
| `GET` | `/api/v1/users/{user_id}` | `get_user()` | Any | Get user by ID |
| `PUT` | `/api/v1/users/{user_id}` | `update_user()` | Admin | Update any user |
| `POST` | `/api/v1/users/` | `create_user()` | Admin | Create a new user |
| `DELETE` | `/api/v1/users/{user_id}` | `deactivate_user()` | Admin | Soft-delete / deactivate user |
| `GET` | `/api/v1/users/{user_id}/medical-history` | `get_user_medical_history()` | Any | Get a user's medical history |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `GET /users/me` | ✅ `LoginPage`, `DashboardPage`, `PatientDetailPage` | ✅ `HomeScreen`, `AiApi` |
| `PUT /users/me` | ✅ `api.ts` (defined) | ✅ `ai_api.dart` (defined) |
| `GET /users/` | ✅ `api.ts` (defined, `getAllUsers`) | — |
| `GET /users/{id}` | ✅ `api.ts` (defined, `getUserById`) | — |
| `PUT /users/me/medical-history` | — | — |
| `PUT /users/{id}` | — | — |
| `POST /users/` | — | — |
| `DELETE /users/{id}` | — | — |
| `GET /users/{id}/medical-history` | — | — |

---

## 4. Vital Signs Endpoints

Defined in `app/api/vital_signs.py` · Mounted at `/api/v1` · Tag: *Vital Signs*

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| `POST` | `/api/v1/vitals` | `submit_vitals()` | Any | Submit a single vital-sign reading (triggers alert checks) |
| `POST` | `/api/v1/vitals/batch` | `submit_vitals_batch()` | Any | Submit multiple readings at once |
| `GET` | `/api/v1/vitals/latest` | `get_latest_vitals()` | Any | Latest reading for current user |
| `GET` | `/api/v1/vitals/summary` | `get_vitals_summary()` | Any | Summary stats over N days (default 7) |
| `GET` | `/api/v1/vitals/history` | `get_vitals_history()` | Any | Paginated history for current user |
| `GET` | `/api/v1/vitals/user/{user_id}/latest` | `get_user_latest_vitals()` | Clinician/Admin | Latest reading for a specific patient |
| `GET` | `/api/v1/vitals/user/{user_id}/summary` | `get_user_vitals_summary()` | Clinician/Admin | Summary for a specific patient |
| `GET` | `/api/v1/vitals/user/{user_id}/history` | `get_user_vitals_history()` | Clinician/Admin | History for a specific patient |

### Alert Thresholds (auto-generated on `POST /vitals`)

| Metric | Condition | Severity |
|--------|-----------|----------|
| Heart Rate | > 180 BPM | CRITICAL |
| SpO2 | < 90% | CRITICAL |
| Systolic BP | > 160 mmHg | WARNING |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `POST /vitals` | ✅ `api.ts` (defined) | ✅ `api_client.dart`, `AiApi` |
| `POST /vitals/batch` | — | — |
| `GET /vitals/latest` | ✅ `api.ts` (defined) | ✅ `HomeScreen`, `AiApi` |
| `GET /vitals/summary` | ✅ `api.ts` (defined) | — |
| `GET /vitals/history` | ✅ `api.ts` (defined) | ✅ `api_client.dart`, `AiApi` |
| `GET /vitals/user/{id}/latest` | — | — |
| `GET /vitals/user/{id}/summary` | — | — |
| `GET /vitals/user/{id}/history` | — | — |

---

## 5. Activity / Session Endpoints

Defined in `app/api/activity.py` · Mounted at `/api/v1` · Tag: *Activities*

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| `POST` | `/api/v1/activities/start` | `start_activity_session()` | Any | Start a workout / recovery session |
| `POST` | `/api/v1/activities/end/{session_id}` | `end_activity_session()` | Any | End a running session |
| `GET` | `/api/v1/activities` | `get_my_activities()` | Any | List own activities (limit, offset, type filter) |
| `GET` | `/api/v1/activities/user/{user_id}` | `get_user_activities()` | Clinician/Admin | List activities for a patient |
| `GET` | `/api/v1/activities/{session_id}` | `get_activity_session()` | Any | Get a single session by ID |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `POST /activities/start` | ✅ `api.ts` (defined) | ✅ `WorkoutScreen`, `AiApi` |
| `POST /activities/end/{id}` | ✅ `api.ts` (defined) | ✅ `WorkoutScreen`, `AiApi` |
| `GET /activities` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `GET /activities/{id}` | ✅ `api.ts` (defined) | — |
| `GET /activities/user/{id}` | — | — |
| `PATCH /activities/{id}` | ✅ `api.ts` (defined) | ✅ `AiApi` |

> **Note**: The web dashboard `api.ts` defines `PATCH /activities/{sessionId}` (`updateActivity`) but the backend only exposes `GET /activities/{session_id}` — there is no `PATCH` route in `activity.py`. This is a mismatch.

---

## 6. Alert Endpoints

Defined in `app/api/alert.py` · Mounted at `/api/v1` · Tag: *Alerts*

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| `GET` | `/api/v1/alerts` | `get_my_alerts()` | Any | Paginated list of own alerts (filter: acknowledged, severity) |
| `POST` | `/api/v1/alerts` | `create_alert()` | Any | Manually create an alert |
| `GET` | `/api/v1/alerts/stats` | `get_alert_statistics()` | Any | Alert counts over N days (default 7) |
| `PATCH` | `/api/v1/alerts/{alert_id}/acknowledge` | `acknowledge_alert()` | Any | Mark alert as acknowledged |
| `PATCH` | `/api/v1/alerts/{alert_id}/resolve` | `resolve_alert()` | Any | Mark alert as resolved |
| `GET` | `/api/v1/alerts/user/{user_id}` | `get_user_alerts()` | Clinician/Admin | Alerts for a specific patient |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `GET /alerts` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `POST /alerts` | — | — |
| `GET /alerts/stats` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `PATCH /alerts/{id}/acknowledge` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `PATCH /alerts/{id}/resolve` | ✅ `api.ts` (defined) | — |
| `GET /alerts/user/{id}` | — | — |

---

## 7. AI Risk Prediction Endpoints

Defined in `app/api/predict.py` · Mounted at `/api/v1` · Tag: *AI Risk Prediction*

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| `GET` | `/api/v1/predict/status` | `check_model_status()` | Any | Check if ML model is loaded |
| `POST` | `/api/v1/predict/risk` | `predict_risk()` | Any | Run risk prediction on supplied metrics |
| `GET` | `/api/v1/predict/user/{user_id}/risk` | `predict_user_risk_from_latest_session()` | Clinician/Admin | Predict risk from patient's latest session |
| `GET` | `/api/v1/predict/my-risk` | `get_my_risk_history()` | Any | Own risk assessment history (limit=10) |
| `POST` | `/api/v1/risk-assessments/compute` | `compute_my_risk_assessment()` | Any | Compute and store risk assessment |
| `POST` | `/api/v1/patients/{user_id}/risk-assessments/compute` | `compute_patient_risk_assessment()` | Clinician/Admin | Compute risk for a patient |
| `GET` | `/api/v1/risk-assessments/latest` | `get_my_latest_risk_assessment()` | Any | Latest stored risk assessment |
| `GET` | `/api/v1/patients/{user_id}/risk-assessments/latest` | `get_patient_latest_risk_assessment()` | Clinician/Admin | Latest risk for a patient |
| `GET` | `/api/v1/recommendations/latest` | `get_my_latest_recommendation()` | Any | Latest exercise recommendation |
| `GET` | `/api/v1/patients/{user_id}/recommendations/latest` | `get_patient_latest_recommendation()` | Clinician/Admin | Latest recommendation for a patient |

### Usage

| Endpoint | Web Dashboard | Mobile App |
|----------|:---:|:---:|
| `GET /predict/status` | — | — |
| `POST /predict/risk` | ✅ `api.ts` (defined) | ✅ `HomeScreen`, `AiApi` |
| `GET /predict/user/{id}/risk` | — | — |
| `GET /predict/my-risk` | — | — |
| `POST /risk-assessments/compute` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `POST /patients/{id}/risk-assessments/compute` | — | — |
| `GET /risk-assessments/latest` | ✅ `api.ts` (defined) | ✅ `AiApi` |
| `GET /patients/{id}/risk-assessments/latest` | — | — |
| `GET /recommendations/latest` | ✅ `api.ts` (defined) | ✅ `api_client.dart`, `AiApi` |
| `GET /patients/{id}/recommendations/latest` | — | — |

---

## 8. Frontend Usage Summary

### Web Dashboard (React / TypeScript)

The API client (`web-dashboard/src/services/api.ts`) defines **28 methods** covering every endpoint category. However, only **2 methods** are actively called from page components:

| API Method | Called From |
|-----------|-----------|
| `login(email, password)` | `LoginPage.tsx` |
| `getCurrentUser()` | `LoginPage.tsx`, `DashboardPage.tsx`, `PatientDetailPage.tsx` |

> **PatientsPage.tsx** uses hardcoded mock data and does not call any API.
> **PatientDetailPage.tsx** uses mock data for vitals and risk; only calls `getCurrentUser()`.

All other `api.ts` methods (`getLatestVitalSigns`, `getAlerts`, `computeRiskAssessment`, etc.) are **defined and ready** but not yet wired into UI components.

### Mobile App (Flutter / Dart)

Two API client files exist:

| File | Methods | Actively Called |
|------|---------|:---:|
| `lib/services/api_client.dart` | 10 methods | ✅ `LoginScreen`, `HomeScreen`, `WorkoutScreen` |
| `lib/features/ai/ai_api.dart` | 20+ methods | ✅ via `AiStore` → `AiHomeScreen`, `AiPlanScreen` |

**Endpoints actively called from screens**:

| Endpoint | Screen |
|----------|--------|
| `POST /login` | `LoginScreen` |
| `GET /users/me` | `HomeScreen` |
| `GET /vitals/latest` | `HomeScreen` |
| `POST /predict/risk` | `HomeScreen` |
| `POST /activities/start` | `WorkoutScreen` |
| `POST /activities/end/{id}` | `WorkoutScreen` |

> **RecoveryScreen** uses demo/local data only — no live API calls.

---

## 9. API Methods Defined but Not Yet Used by UI

The following backend endpoints have **no frontend consumer** in either the web dashboard pages or mobile app screens. They are fully implemented and available via `/docs` but await UI integration.

| Endpoint | Notes |
|----------|-------|
| `POST /api/v1/refresh` | Token refresh (interceptors could auto-call) |
| `GET /api/v1/me` | Overlaps with `/users/me` |
| `POST /api/v1/reset-password` | No password-reset UI built |
| `POST /api/v1/reset-password/confirm` | No password-reset UI built |
| `PUT /api/v1/users/me/medical-history` | No medical-history edit UI |
| `PUT /api/v1/users/{id}` | Admin user edit UI pending |
| `POST /api/v1/users/` | Admin user creation UI pending |
| `DELETE /api/v1/users/{id}` | Admin user deactivation UI pending |
| `GET /api/v1/users/{id}/medical-history` | No medical-history view UI |
| `POST /api/v1/vitals/batch` | Batch upload UI pending |
| `GET /api/v1/vitals/user/{id}/latest` | Clinician patient-detail UI uses mock data |
| `GET /api/v1/vitals/user/{id}/summary` | Clinician patient-detail UI uses mock data |
| `GET /api/v1/vitals/user/{id}/history` | Clinician patient-detail UI uses mock data |
| `GET /api/v1/activities/user/{id}` | Clinician view pending |
| `POST /api/v1/alerts` | Manual alert creation UI pending |
| `GET /api/v1/alerts/user/{id}` | Clinician alert view pending |
| `GET /api/v1/predict/status` | ML model status UI pending |
| `GET /api/v1/predict/user/{id}/risk` | Clinician risk view pending |
| `GET /api/v1/predict/my-risk` | Risk history UI pending |
| `POST /api/v1/patients/{id}/risk-assessments/compute` | Clinician risk compute pending |
| `GET /api/v1/patients/{id}/risk-assessments/latest` | Clinician risk view pending |
| `GET /api/v1/patients/{id}/recommendations/latest` | Clinician recommendation view pending |

---

## Quick Test with cURL

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","name":"Test User"}'

# 2. Login (returns access_token + refresh_token)
curl -X POST http://localhost:8000/api/v1/login \
  -d "username=test@example.com&password=password123"

# 3. Get profile (replace <TOKEN>)
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <TOKEN>"

# 4. Submit vitals
curl -X POST http://localhost:8000/api/v1/vitals \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"heart_rate":75,"spo2":98,"systolic_bp":120,"diastolic_bp":80}'

# 5. Get latest vitals
curl http://localhost:8000/api/v1/vitals/latest \
  -H "Authorization: Bearer <TOKEN>"

# 6. Run risk prediction
curl -X POST http://localhost:8000/api/v1/predict/risk \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"heart_rate":75,"spo2":98,"systolic_bp":120,"diastolic_bp":80}'

# 7. Health check
curl http://localhost:8000/health
```

---

## Configuration Reference

| Setting | Env Variable | Default |
|---------|-------------|---------|
| Database | `DATABASE_URL` | `sqlite:///./adaptivhealth.db` |
| JWT Secret | `SECRET_KEY` | *(required)* |
| JWT Algorithm | — | `HS256` |
| Access Token Expiry | — | 30 minutes |
| Refresh Token Expiry | — | 7 days |
| CORS Origins | — | `localhost:3000`, `localhost:5173`, `localhost:5000` |
| Max Login Attempts | — | 3 |
| Lockout Duration | — | 5 minutes |
| PHI Encryption Key | `PHI_ENCRYPTION_KEY` | *(optional, base64)* |

---

**Total backend endpoints**: 40+
**Actively called from web dashboard UI**: 2 (`login`, `getCurrentUser`)
**Actively called from mobile app UI**: 6+ (login, profile, vitals, prediction, activities)
**Defined in frontend API clients but not yet wired to pages**: 20+
**Backend-only (no frontend method exists)**: 12+
