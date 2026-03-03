# API ↔ UI Coverage Audit

> **Generated:** June 2025
> **Scope:** Backend API (FastAPI), Web Dashboard (React), Mobile Patient App (Flutter)

---

## A. Backend API Inventory

All paths are relative to the `/api/v1` prefix unless otherwise noted.

### A1. Authentication

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| POST | `/register` | — | — | Create new account |
| POST | `/login` | — | — | Obtain JWT token pair |
| POST | `/refresh` | — | — | Refresh access token |
| GET | `/me` | ✔ | Any | Return current user profile |
| POST | `/reset-password` | — | — | Request password-reset email |
| POST | `/reset-password/confirm` | — | — | Complete password reset |

### A2. User Management (`/users`)

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| GET | `/users/me` | ✔ | Any | Get own profile |
| PUT | `/users/me` | ✔ | Any | Update own profile |
| PUT | `/users/me/medical-history` | ✔ | Any | Update own medical history |
| GET | `/users/` | ✔ | Clinician+ | List all users |
| GET | `/users/{user_id}` | ✔ | Clinician+ | Get user by ID |
| PUT | `/users/{user_id}` | ✔ | Admin | Update any user |
| POST | `/users/` | ✔ | Admin | Create user (admin-provisioned) |
| DELETE | `/users/{user_id}` | ✔ | Admin | Delete user |
| GET | `/users/{user_id}/medical-history` | ✔ | Clinician+ | View patient medical history |

### A3. Vital Signs

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| POST | `/vitals` | ✔ | Any | Submit vital signs |
| POST | `/vitals/batch` | ✔ | Any | Submit batch vitals |
| GET | `/vitals/latest` | ✔ | Any | Get own latest vitals |
| GET | `/vitals/summary` | ✔ | Any | Get own vitals summary |
| GET | `/vitals/history` | ✔ | Any | Get own vitals history |
| GET | `/vitals/user/{user_id}/latest` | ✔ | Clinician+ | Get patient latest vitals |
| GET | `/vitals/user/{user_id}/summary` | ✔ | Clinician+ | Get patient vitals summary |
| GET | `/vitals/user/{user_id}/history` | ✔ | Clinician+ | Get patient vitals history |

### A4. Activities

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| POST | `/activities/start` | ✔ | Any | Start activity session |
| POST | `/activities/end/{session_id}` | ✔ | Any | End activity session |
| GET | `/activities` | ✔ | Any | List own activities |
| GET | `/activities/user/{user_id}` | ✔ | Clinician+ | List patient activities |
| GET | `/activities/{session_id}` | ✔ | Any | Get activity by ID |

### A5. Alerts

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| GET | `/alerts` | ✔ | Any | List own alerts |
| PATCH | `/alerts/{alert_id}/acknowledge` | ✔ | Any | Acknowledge alert |
| PATCH | `/alerts/{alert_id}/resolve` | ✔ | Any | Resolve alert |
| POST | `/alerts` | ✔ | Any | Create alert |
| GET | `/alerts/user/{user_id}` | ✔ | Clinician+ | List patient alerts |
| GET | `/alerts/stats` | ✔ | Clinician+ | Alert statistics |

### A6. AI Risk Prediction

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| GET | `/predict/status` | — | — | ML model health check |
| POST | `/predict/risk` | ✔ | Any | Run risk prediction |
| GET | `/predict/user/{user_id}/risk` | ✔ | Clinician+ | Get patient risk prediction |
| GET | `/predict/my-risk` | ✔ | Any | Get own risk prediction |
| POST | `/risk-assessments/compute` | ✔ | Any | Compute own risk assessment |
| POST | `/patients/{user_id}/risk-assessments/compute` | ✔ | Clinician+ | Compute patient risk assessment |
| GET | `/risk-assessments/latest` | ✔ | Any | Get own latest risk assessment |
| GET | `/patients/{user_id}/risk-assessments/latest` | ✔ | Clinician+ | Get patient risk assessment |
| GET | `/recommendations/latest` | ✔ | Any | Get own latest recommendations |
| GET | `/patients/{user_id}/recommendations/latest` | ✔ | Clinician+ | Get patient recommendations |

### A7. Advanced ML

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| GET | `/anomaly-detection` | ✔ | Any | Detect anomalies in vitals |
| GET | `/trend-forecast` | ✔ | Any | Forecast vitals trends |
| GET | `/baseline-optimization` | ✔ | Any | Get optimized baseline |
| POST | `/baseline-optimization/apply` | ✔ | Any | Apply baseline |
| GET | `/recommendation-ranking` | ✔ | Any | Rank recommendations |
| POST | `/recommendation-ranking/outcome` | ✔ | Any | Report recommendation outcome |
| POST | `/alerts/natural-language` | ✔ | Any | Generate patient-friendly NL alert text (template-based) |
| GET | `/risk-summary/natural-language` | ✔ | Any | NL risk summary (template-first; optional Gemini enhancement via `use_cloud_ai=true`) |
| GET | `/model/retraining-status` | ✔ | Clinician+ | Model retraining status |
| GET | `/model/retraining-readiness` | ✔ | Clinician+ | Model retraining readiness |
| POST | `/predict/explain` | ✔ | Any | Explainability for prediction |

**Total endpoints: 55** (+ 5 new consent endpoints below)

### A8. Consent / Data Sharing *(NEW)*

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| GET | `/consent/status` | ✔ | Any | Get own sharing consent status |
| POST | `/consent/disable` | ✔ | Patient | Request sharing disable (creates pending request) |
| POST | `/consent/enable` | ✔ | Patient | Re-enable sharing (from SHARING_OFF) |
| GET | `/consent/pending` | ✔ | Clinician | List pending disable requests |
| POST | `/consent/{patient_id}/review` | ✔ | Clinician | Approve/reject disable request |

### A9. Admin User Management *(NEW)*

| Method | Path | Auth | Role | Description |
|--------|------|:----:|------|-------------|
| POST | `/users/{user_id}/reset-password` | ✔ | Admin | Set temporary password for user |

---

## B. Frontend Usage Matrix

✅ = called from at least one page &nbsp; ⬜ = wrapper exists but unused &nbsp; — = no wrapper

| Backend Endpoint | Mobile App | Web Dashboard |
|------------------|:----------:|:-------------:|
| **Authentication** | | |
| POST `/register` | ✅ register_screen | ✅ RegisterPage |
| POST `/login` | ✅ login_screen | ✅ LoginPage |
| POST `/refresh` | — | — |
| GET `/me` | ✅ home_screen, profile_screen | ✅ LoginPage, DashboardPage |
| POST `/reset-password` | — | — |
| POST `/reset-password/confirm` | — | — |
| **User Management** | | |
| GET `/users/me` | ✅ (via getCurrentUser) | ✅ (via getCurrentUser) |
| PUT `/users/me` | ✅ profile_screen | ⬜ wrapper only |
| PUT `/users/me/medical-history` | — | — |
| GET `/users/` | — | ✅ DashboardPage, PatientsPage |
| GET `/users/{user_id}` | — | ✅ PatientDetailPage |
| PUT `/users/{user_id}` | — | — |
| POST `/users/` | — | — |
| DELETE `/users/{user_id}` | — | — |
| GET `/users/{user_id}/medical-history` | — | — |
| **Vital Signs** | | |
| POST `/vitals` | ⬜ wrapper only | ⬜ wrapper only |
| POST `/vitals/batch` | — | — |
| GET `/vitals/latest` | ✅ home_screen | ⬜ wrapper only |
| GET `/vitals/summary` | — | ✅ DashboardPage |
| GET `/vitals/history` | ⬜ wrapper only | ⬜ wrapper only |
| GET `/vitals/user/{id}/latest` | — | ✅ PatientDetailPage |
| GET `/vitals/user/{id}/summary` | — | ⬜ wrapper only |
| GET `/vitals/user/{id}/history` | — | ✅ PatientDetailPage |
| **Activities** | | |
| POST `/activities/start` | ✅ workout_screen | ⬜ wrapper only |
| POST `/activities/end/{id}` | ✅ workout_screen | ⬜ wrapper only |
| GET `/activities` | ✅ history_screen | ⬜ wrapper only |
| GET `/activities/user/{user_id}` | — | ✅ PatientDetailPage |
| GET `/activities/{session_id}` | ⬜ wrapper only | ⬜ wrapper only |
| **Alerts** | | |
| GET `/alerts` | — | ✅ DashboardPage |
| PATCH `/alerts/{id}/acknowledge` | — | ⬜ wrapper only |
| PATCH `/alerts/{id}/resolve` | — | ⬜ wrapper only |
| POST `/alerts` | — | — |
| GET `/alerts/user/{user_id}` | — | ✅ PatientDetailPage |
| GET `/alerts/stats` | — | ✅ DashboardPage |
| **Risk / Predictions** | | |
| GET `/predict/status` | — | — |
| POST `/predict/risk` | ✅ home_screen | ⬜ wrapper only |
| GET `/predict/user/{id}/risk` | — | — |
| GET `/predict/my-risk` | — | — |
| POST `/risk-assessments/compute` | — | ⬜ wrapper only |
| POST `/patients/{id}/risk-assessments/compute` | — | ⬜ wrapper only |
| GET `/risk-assessments/latest` | — | ⬜ wrapper only |
| GET `/patients/{id}/risk-assessments/latest` | — | ✅ PatientDetailPage |
| GET `/recommendations/latest` | ⬜ wrapper only | ⬜ wrapper only |
| GET `/patients/{id}/recommendations/latest` | — | ✅ PatientDetailPage |
| **Advanced ML** | | |
| GET `/anomaly-detection` | — | — |
| GET `/trend-forecast` | — | — |
| GET `/baseline-optimization` | — | — |
| POST `/baseline-optimization/apply` | — | — |
| GET `/recommendation-ranking` | — | — |
| POST `/recommendation-ranking/outcome` | — | — |
| POST `/alerts/natural-language` | — | ✅ PatientDetailPage |
| GET `/risk-summary/natural-language` | — | ✅ PatientDetailPage |
| GET `/model/retraining-status` | — | — |
| GET `/model/retraining-readiness` | — | — |
| POST `/predict/explain` | — | — |

**Coverage summary:**

| | Endpoints Used | Wrapper Only | No Wrapper |
|---|:-:|:-:|:-:|
| Mobile App | 9 | 4 | 42 |
| Web Dashboard | 15 | 14 | 26 |

---

## C. Client API Wrapper Methods

### C1. Web Dashboard (`api.ts`)

| Wrapper Method | Backend Endpoint | Called From Page? |
|----------------|------------------|:-:|
| `login()` | POST `/login` | ✅ LoginPage |
| `register()` | POST `/register` | ✅ RegisterPage |
| `getCurrentUser()` | GET `/users/me` | ✅ LoginPage, DashboardPage |
| `updateCurrentUserProfile()` | PUT `/users/me` | ❌ |
| `getAllUsers()` | GET `/users/` | ✅ DashboardPage, PatientsPage |
| `getUserById()` | GET `/users/{id}` | ✅ PatientDetailPage |
| `getLatestVitalSigns()` | GET `/vitals/latest` | ❌ |
| `getLatestVitalSignsForUser()` | GET `/vitals/user/{id}/latest` | ✅ PatientDetailPage |
| `getVitalSignsHistory()` | GET `/vitals/history` | ❌ |
| `getVitalSignsHistoryForUser()` | GET `/vitals/user/{id}/history` | ✅ PatientDetailPage, DashboardPage |
| `getVitalSignsSummary()` | GET `/vitals/summary` | ✅ DashboardPage |
| `getVitalSignsSummaryForUser()` | GET `/vitals/user/{id}/summary` | ❌ |
| `submitVitalSigns()` | POST `/vitals` | ❌ |
| `getLatestRiskAssessment()` | GET `/risk-assessments/latest` | ❌ |
| `getLatestRiskAssessmentForUser()` | GET `/patients/{id}/risk-assessments/latest` | ✅ PatientDetailPage, DashboardPage |
| `computeRiskAssessment()` | POST `/risk-assessments/compute` | ❌ |
| `computeRiskAssessmentForUser()` | POST `/patients/{id}/risk-assessments/compute` | ❌ |
| `predictRisk()` | POST `/predict/risk` | ❌ |
| `getLatestRecommendation()` | GET `/recommendations/latest` | ❌ |
| `getLatestRecommendationForUser()` | GET `/patients/{id}/recommendations/latest` | ✅ PatientDetailPage |
| `getRecommendations()` | GET `/recommendations` | ❌ |
| `getRecommendationById()` | GET `/recommendations/{id}` | ❌ |
| `updateRecommendation()` | PATCH `/recommendations/{id}` | ❌ |
| `getAlerts()` | GET `/alerts` | ✅ DashboardPage |
| `getAlertsForUser()` | GET `/alerts/user/{id}` | ✅ PatientDetailPage |
| `getAlertStats()` | GET `/alerts/stats` | ✅ DashboardPage |
| `acknowledgeAlert()` | PATCH `/alerts/{id}/acknowledge` | ❌ |
| `resolveAlert()` | PATCH `/alerts/{id}/resolve` | ❌ |
| `getActivities()` | GET `/activities` | ❌ |
| `getActivitiesForUser()` | GET `/activities/user/{id}` | ✅ PatientDetailPage |
| `getActivityById()` | GET `/activities/{id}` | ❌ |
| `startActivity()` | POST `/activities/start` | ❌ |
| `endActivity()` | POST `/activities/end/{id}` | ❌ |
| `updateActivity()` | PATCH `/activities/{id}` | ❌ |
| `getHealth()` | GET `/health` | ❌ |
| `getDatabaseHealth()` | GET `/health/db` | ❌ |

**Used: 15 / 36** — 21 wrappers are defined but never called from any page.

### C2. Mobile App (`api_client.dart`)

| Wrapper Method | Backend Endpoint | Called From Screen? |
|----------------|------------------|:-:|
| `login()` | POST `/login` | ✅ login_screen |
| `register()` | POST `/register` | ✅ register_screen |
| `logout()` | — (local token clear) | ❌ |
| `getCurrentUser()` | GET `/users/me` | ✅ profile_screen, home_screen |
| `updateProfile()` | PUT `/users/me` | ✅ profile_screen |
| `getLatestVitals()` | GET `/vitals/latest` | ✅ home_screen |
| `getVitalHistory()` | GET `/vitals/history` | ❌ |
| `submitVitalSigns()` | POST `/vitals` | ❌ |
| `predictRisk()` | POST `/predict/risk` | ✅ home_screen |
| `startSession()` | POST `/activities/start` | ✅ workout_screen |
| `endSession()` | POST `/activities/end/{id}` | ✅ workout_screen |
| `getActivities()` | GET `/activities` | ✅ history_screen |
| `getActivityById()` | GET `/activities/{id}` | ❌ |
| `getRecommendation()` | GET `/recommendations/latest` | ❌ |

**Used: 9 / 14** — 5 wrappers are defined but never called from any screen.

---

## D. Gaps & Decisions

### D1. Missing UI for Existing Backend Features

| # | Gap | Status |
|---|-----|--------|
| 1 | **No password-reset UI.** | ✅ **RESOLVED** — Forgot password flow added to both mobile login screen and dashboard login page. |
| 2 | **No admin user-creation page.** | ✅ **RESOLVED** — AdminPage added with user creation, temp password reset, and deactivation. |
| 3 | **No UI for alert acknowledge/resolve.** Dashboard lists alerts but has no buttons wired to `PATCH /alerts/{id}/acknowledge` or `/resolve`. | Deferred — future work. |
| 4 | **No medical-history UI.** | Deferred — future work (requires HIPAA-compliant form design). |
| 5 | **Advanced ML endpoints have zero frontend consumers.** | Deferred — future work (Phase C/D). |

### D2. Auth & Security Gaps

| # | Gap | Status |
|---|-----|--------|
| 6 | **No logout endpoint on backend.** Both clients clear the local token but do not invalidate it server-side. | Future work — requires token blacklist table. |
| 7 | **No refresh-token retry logic.** | ✅ **RESOLVED** — Both clients now intercept 401, try refresh token once, retry original request, then logout on failure. |
| 8 | **RBAC not fully enforced.** | ✅ **RESOLVED** — Admin blocked from all PHI endpoints (403). Clinician access checks consent state (SHARING_OFF → 403). Role-based routing added to dashboard login. |

### D3. Client Design Issues

| # | Gap | Status |
|---|-----|--------|
| 9 | **Mobile app exposes a registration screen.** | Future work — remove or gate. Per requirements, patients are created by admin. |
| 10 | **Dashboard has no role-based routing.** | ✅ **RESOLVED** — Admin redirected to /admin, clinician to /dashboard. |
| 11 | **Unused wrappers in `api.ts`.** | Future work — wire or prune as needed. |
| 12 | **Unused wrappers in `api_client.dart`.** | Future work — wire or prune as needed. |

### D4. Missing Backend Endpoints

| # | Gap | Status |
|---|-----|--------|
| 13 | **No `POST /logout` or token-blacklist endpoint.** | Future work. |
| 14 | **No consent/data-sharing workflow.** | ✅ **RESOLVED** — Full consent state machine implemented (SHARING_ON → SHARING_DISABLE_REQUESTED → SHARING_OFF). |
| 15 | **`updateActivity` wrapper calls `PATCH /activities/{id}` — no backend route.** | Future work — dead wrapper. |
| 16 | **`getRecommendations`/`getRecommendationById` wrappers — no backend routes.** | Future work — dead wrappers. |

### D5. Summary Heatmap

```
                         Mobile App    Web Dashboard
Authentication              ██████        ██████
User Management              ███           █████
Vital Signs                  ███           █████
Activities                   ████          ██
Alerts                                     ████
Risk / Predictions           ██            ███
Advanced ML                                          (future)
Medical History                                       (future)
Password Reset               ██████        ██████    ← NEW
Admin User Mgmt                            ██████    ← NEW
Consent / Sharing            ████          ████      ← NEW
```

_Filled blocks (█) indicate relative coverage depth._

---

## Appendix: Page → API Call Map

### Web Dashboard

| Page | API Calls |
|------|-----------|
| **LoginPage** | `login()`, `getCurrentUser()`, `requestPasswordReset()` |
| **RegisterPage** | `register()` |
| **DashboardPage** | `getCurrentUser()`, `getAllUsers()`, `getAlertStats()`, `getAlerts()`, `getVitalSignsSummary()`, `getVitalSignsHistoryForUser()`, `getLatestRiskAssessmentForUser()`, `getPendingConsentRequests()`, `reviewConsentRequest()` |
| **AdminPage** *(NEW)* | `getCurrentUser()`, `getAllUsers()`, `createUser()`, `adminResetUserPassword()`, `deactivateUser()` |
| **PatientsPage** | `getAllUsers()` |
| **PatientDetailPage** | `getUserById()`, `getLatestVitalSignsForUser()`, `getVitalSignsHistoryForUser()`, `getActivitiesForUser()`, `getAlertsForUser()`, `getLatestRiskAssessmentForUser()`, `getLatestRecommendationForUser()` |

### Mobile App

| Screen | API Calls |
|--------|-----------|
| **login_screen** | `login()`, `requestPasswordReset()` |
| **register_screen** | `register()` |
| **home_screen** | `getLatestVitals()`, `getCurrentUser()`, `predictRisk()` |
| **workout_screen** | `startSession()`, `endSession()` |
| **profile_screen** | `getCurrentUser()`, `updateProfile()`, `getConsentStatus()`, `requestDisableSharing()`, `enableSharing()` |
| **history_screen** | `getActivities()` |
| **recovery_screen** | _(no API calls — static UI)_ |
