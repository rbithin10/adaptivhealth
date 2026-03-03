# AdaptivHealth — Project Audit Report

> **Initial audit**: June 2025
> **Updated**: March 2, 2026
> **Scope**: Full-stack audit across backend (FastAPI), mobile (Flutter), and web dashboard (React/TypeScript).
> **Purpose**: Identify gaps, risks, and recommendations before capstone submission.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Repository Hygiene](#2-repository-hygiene)
3. [Code Style Compliance](#3-code-style-compliance)
4. [Backend Architecture](#4-backend-architecture)
5. [Mobile App Architecture](#5-mobile-app-architecture)
6. [Web Dashboard Architecture](#6-web-dashboard-architecture)
7. [End-to-End Data Flows](#7-end-to-end-data-flows)
8. [Dead Code, Unused Files & Logic Rabbit Holes](#8-dead-code-unused-files--logic-rabbit-holes)
9. [Testing Coverage](#9-testing-coverage)
10. [Security Posture](#10-security-posture)
11. [Dependency Health](#11-dependency-health)
12. [Recommendations and Prioritised Action Items](#12-recommendations-and-prioritised-action-items)

---

## 1. Executive Summary

AdaptivHealth is a clinical-grade cardiovascular monitoring platform with three components (FastAPI backend, Flutter mobile app, React web dashboard). The codebase demonstrates **strong engineering fundamentals**: all 14 API routers are registered, RBAC is enforced across 3 roles, PHI encryption uses AES-256-GCM, consent gating is applied to 16+ endpoints, and copilot instructions compliance is excellent (5/5 files checked pass all conventions).

**Key strengths:** Comprehensive backend with 81+ endpoints, proper JWT auth with refresh tokens, ML risk prediction with medical adjustments (prior MI, HF, beta-blockers), edge AI on mobile with pure-Dart RF, structured BLE pipeline, 150+ test functions covering core APIs, well-organized Pydantic V2 schemas, and no hardcoded API keys found in any source files.

**Critical issues requiring immediate attention:**

| # | Issue | Severity |
|---|-------|----------|
| 1 | Wildcard `"*"` in TrustedHostMiddleware defeats host validation in production | **Critical** |
| 2 | Only 1/81 endpoints is rate-limited (password reset) — login, register, and vitals submission are unprotected | **High** |
| 3 | 130+ lines copy-pasted between patient/clinician risk compute in `predict.py` | **High** |
| 4 | 7 empty catch blocks in mobile app silently swallow errors | **High** |
| 5 | Root-level university documents and utility scripts clutter the repository | **Medium** |
| 6 | Medication reminders have 0 dedicated tests | **Medium** |
| 7 | No Flutter or React test suites | **Medium** |

---

## 2. Repository Hygiene

### 2.1 Root Directory Clutter

The project root contains files that should be relocated or removed:

| File / Folder | Issue | Recommendation |
|---|---|---|
| `paste.txt` | 349-line implementation plan document — not source code | Delete |
| `adaptiv_health.db` | SQLite artefact; project now enforces PostgreSQL only | Delete; already in `.gitignore` |
| `SRS Doc.docx`, `Proposal Document.docx`, `Design document .docx` | University documents mixed with source code | Move to `docs/university/` |
| `CSIT321_Subject Outline_AUT_WIN 2025.docx`, `uow225651 grade descriptor.pdf` | Administrative documents | Move to `docs/university/` or remove |
| `deployment.drawio.png`, `SecurityArch.drawio.png` | Architecture diagrams loose at root | Move to `docs/diagrams/` or `images/` |
| `design files/` | Design specs mixed at root | Rename to `docs/design/` for consistency |
| `images/` | Unclear purpose at root level | Move into `docs/images/` |
| `apply_migrations.py`, `create_admin.py`, `init_db.py`, `reset_database.py`, `seed_patient.py` | Utility scripts at root | Move to `scripts/` |
| `run_coverage.py`, `quick_install.bat`, `start.bat`, `start_server.py`, `deploy.sh` | Dev convenience scripts at root | Move to `scripts/` |
| `ARCHITECT_CHECKLIST.md`, `ROADMAP.md` | Planning docs at root | Acceptable, but consider `docs/` |

**Previously deleted files (confirmed NOT on disk):**
`push_repo.py`, `check_db_accounts.py`, `run_migration.py`, `test_imports.py`, `test_minimal.py`, `test_ml_load.py`, `update_admin_password.py`, `verify_branch_coverage.py`, `verify_messaging.py`, `coverage.json`, `new`, `adaptiv_health_design_analysis.jsx` — all properly deleted.

### 2.2 .gitignore Coverage

**Well covered**: `.env`, `__pycache__/`, `*.db`, `*.sqlite`, `uploads/`, `.vscode/`, `.idea/`, `build/`, `htmlcov/`, `startup.log`, `coverage.json`.

**Gaps identified**:

| Missing Entry | Risk |
|---|---|
| `google-services.json` | Mobile service config could be committed |
| `GoogleService-Info.plist` | Mobile service config could be committed |
| `*.jks` / `*.keystore` | Android signing keys |
| `node_modules/` | MISSING at root level — relies on web-dashboard having its own |
| `.dart_tool/` | MISSING — Flutter build artifacts not covered |
| `web-dashboard/.env` | Dashboard-specific env vars (currently only root `.env` is covered) |
| `mobile-app/.env` | Future mobile env file |

### 2.3 Secrets Scan

| Finding | File | Severity |
|---------|------|----------|
| `.env` file exists on disk (gitignored) | `.env` (root) | Low |
| Web dashboard .env exists | `web-dashboard/.env` — only `REACT_APP_API_URL=http://localhost:8080` | Low |
| `.env.example` properly documented | `.env.example` — placeholder values only, no real secrets | GOOD |
| Dev token logging flag | `app/config.py:88` — `password_reset_dev_token_logging` defaults to False | Medium |
| Demo credentials in UI | `web-dashboard/src/pages/LoginPage.tsx:203` — `test@example.com / Pass1234` | Low |

**No hardcoded API keys (`sk-`, `SG.`, `AKIA`) found in any source files.**

### 2.4 Migration Files

11 SQL migration files exist in `migrations/`. These are raw SQL `ALTER TABLE` statements, not managed by Alembic. This is acceptable for the capstone but should be noted:

```
add_clinician_assignment.sql    add_message_encryption.sql
add_lifestyle_fields.sql        add_message_read_at.sql
add_medical_history_medications.sql  add_messages.sql
add_medication_reminders.sql    add_nutrition_entries.sql
add_rbac_consent.sql            add_rehab_phase.sql
add_rehab_tables.sql
```

**Risk**: No migration ordering or version tracking. Running migrations out of order or re-running them could fail silently.

---

## 3. Code Style Compliance

### 3.1 Python Backend

| Convention | Status | Notes |
|---|---|---|
| `snake_case` functions/variables | **Pass** | Consistent across all modules |
| `PascalCase` classes | **Pass** | Models, schemas, services all compliant |
| Type hints on all functions | **Mostly Pass** | Core API and service functions are typed; some internal helpers may lack return types |
| Triple-quoted docstrings | **Mostly Pass** | All service classes and major endpoints have docstrings |
| File map comment blocks (lines 5-30) | **5/5 Pass** | All sampled files have FILE MAP with line refs and BUSINESS CONTEXT |
| Import order (external → internal) | **Pass** | Consistent 4-5 tier organization |
| TODO/FIXME/HACK comments | **None found** | Clean codebase |
| Logging via `logger = logging.getLogger(__name__)` | **Pass** | Structured logging throughout |

### 3.2 Flutter Mobile

| Convention | Status | Notes |
|---|---|---|
| `snake_case.dart` filenames | **Pass** | All screen, service, and model files compliant |
| `PascalCase` classes | **Pass** | Consistent |
| `camelCase` methods/variables | **Pass** | Consistent |
| `_` prefix for private members | **Pass** | Observed in state classes |
| Widget organisation (constructor → state → lifecycle → handlers → build) | **Pass** | Onboarding and other screens follow this pattern |
| Flutter singleton services | **Pass** | BleService, HealthService use `_internal()` pattern |
| Provider state management | **Pass** | EdgeAiStore, VitalsProvider, ChatStore in MultiProvider |
| TODO/FIXME comments | **None found** | Search returned only false positives (`.toDouble()`) |

### 3.3 React Dashboard

| Convention | Status | Notes |
|---|---|---|
| `PascalCase.tsx` for components/pages | **Pass** | All 9 pages follow this |
| `camelCase.ts` for services/utils | **Pass** | `api.ts`, `colors.ts` compliant |
| Props interfaces as `[Name]Props` | **Pass** | `ProtectedRouteProps` observed |
| Import order (React → pages → styles) | **Pass** | Consistent in App.tsx |
| React MUI components | **Pass** | All pages use MUI (Box, Paper, Typography, etc.) |
| localStorage auth | **Pass** | Token stored/retrieved from localStorage |
| `eslint-disable` suppressions | **5 instances** | All are `react-hooks/exhaustive-deps` in page components |

### 3.4 Code Style Violations

| File | Line | Violation | Severity |
|------|------|-----------|----------|
| `web-dashboard/src/services/api.ts` | 56 | `normalizeUser(data: any)` — untyped parameter | Medium |
| `web-dashboard/src/services/api.ts` | 277, 284 | `getVitalSignsSummary()` returns `Promise<any>` | Medium |
| `web-dashboard/src/services/api.ts` | 730-794 | 8 admin/consent methods return `Promise<any>` | Medium |
| `web-dashboard/src/pages/AdminPage.tsx` | 119, 136, 149, 180, 200 | `catch (err: any)` — untyped error catches | Low |
| `web-dashboard/src/pages/DashboardPage.tsx` | 71, 116, 799 | `useState<any[]>` and `(user as any).role` | Low |
| `web-dashboard/src/pages/LoginPage.tsx` | 50 | `(user as any).role` — type assertion bypass | Low |
| `web-dashboard/src/pages/PatientDetailPage.tsx` | 464 | `(u as any).assigned_clinician_id` | Low |
| `web-dashboard/src/pages/PatientDashboardPage.tsx` | 58 | `useState<any[]>([])` for vital history | Low |
| `mobile-app/lib/main.dart` | 150-178 | `go_router` imported but unused; uses Navigator.push | Low |

---

## 4. Backend Architecture

### 4.1 Router Registry

All 14 API routers properly registered in `app/main.py` (lines 222-316). **No orphan routers.**

| Router | Prefix | Tags |
|--------|--------|------|
| `auth.router` | `/api/v1` | Authentication |
| `user.router` | `/api/v1/users` | User Management |
| `vital_signs.router` | `/api/v1` | Vital Signs |
| `activity.router` | `/api/v1` | Activities |
| `alert.router` | `/api/v1` | Alerts |
| `predict.router` | `/api/v1` | AI Risk Prediction |
| `advanced_ml.router` | `/api/v1` | Advanced ML |
| `consent.router` | `/api/v1` | Consent / Data Sharing |
| `nl_endpoints.router` | `/api/v1/nl` | AI Coach NL |
| `nutrition.router` | `/api/v1` | Nutrition |
| `messages.router` | `/api/v1` | Messages |
| `medical_history.router` | `/api/v1` | Medical Profile |
| `medication_reminder.router` | `/api/v1` | Medication Reminders |
| `rehab.router` | `/api/v1` | Rehab Programs |

### 4.2 Endpoint Inventory (81+ endpoints)

Key endpoints with auth and rate-limit status:

| Method | Path | Auth Dependency | Rate Limit | Notes |
|--------|------|-----------------|------------|-------|
| POST | `/register` | None | No | **Should add rate limit** |
| POST | `/login` | None | No | **Should add rate limit** |
| POST | `/reset-password` | None | **3/15min** | Only rate-limited endpoint |
| POST | `/admin/register` | `get_current_admin_user` | No | OK |
| POST | `/refresh` | None | No | OK |
| GET | `/me` | `get_current_user` | No | OK |
| GET/PUT | `/users/me` | `get_current_user` | No | Returns heart rate zones |
| GET/PUT/POST/DELETE | `/users/{user_id}` | `get_current_admin_user` | No | Admin-only CRUD |
| GET | `/users/{user_id}/medical-history` | `get_current_doctor_user` | No | Consent gated |
| POST | `/vitals` | `get_current_user` | No | HR 30-250, SpO2 70-100 validation |
| POST | `/vitals/batch` | `get_current_user` | No | Max 1000 records |
| POST | `/vitals/batch-sync` | `get_current_user` | No | Edge AI + vitals |
| GET | `/vitals/user/{user_id}/*` | `get_current_doctor_user` | No | All consent gated |
| POST | `/predict/risk` | `get_current_user` | No | ML prediction |
| POST | `/risk-assessments/compute` | `get_current_user` | No | Medical adjustments wired |
| POST | `/patients/{id}/risk-assessments/compute` | `get_current_doctor_user` | No | Consent gated |
| GET/POST/PUT/DELETE | `/patients/{id}/medical-history/*` | `get_current_doctor_user` | No | All consent gated |
| GET/POST/PUT/DELETE | `/patients/{id}/medications/*` | `get_current_doctor_user` | No | All consent gated |

*All remaining endpoints follow the same auth patterns with proper RBAC.*

### 4.3 Model-Schema Alignment

All 13 SQLAlchemy models have corresponding Pydantic schemas. No mismatches. Schemas use Pydantic V2 with `model_validate()`. Encryption handled at API layer.

**Models** (12 in `app/models/`):
`user`, `vital_signs`, `alert`, `activity`, `auth_credential`, `medical_history`, `medication_adherence`, `message`, `nutrition`, `recommendation`, `rehab`, `risk_assessment`

**Schemas** (12 in `app/schemas/`):
`user`, `vital_signs`, `alert`, `activity`, `medical_history`, `medication_reminder`, `message`, `nl`, `nutrition`, `recommendation`, `rehab`, `risk_assessment`

**Services** (15 in `app/services/`):
`auth_service`, `ml_prediction`, `encryption`, `chat_service`, `document_extraction`, `email_service`, `anomaly_detection`, `baseline_optimization`, `explainability`, `natural_language_alerts`, `nl_builders`, `recommendation_ranking`, `rehab_service`, `retraining_pipeline`, `trend_forecasting`

### 4.4 PHI Encryption

`app/services/encryption.py` — AES-256-GCM via `cryptography` library:
- `encrypt_phi()`/`decrypt_phi()` in `medical_history.py` (lines 113, 134, 219, 274)
- `encryption_service.encrypt_json()` in `user.py` (lines 267-268)
- Message encryption via `encryption_service` in `messages.py`

### 4.5 RBAC & Consent

3 roles (PATIENT, CLINICIAN, ADMIN) enforced via 5 auth dependencies. `check_clinician_phi_access()` applied to **16+ endpoints**. Clinicians see only assigned patients (`user.py:358`).

### 4.6 Exception Handling

**33 broad `except Exception` blocks** found across the backend:

| File | Count | Severity |
|---|---|---|
| `api/medical_history.py` | 9 | High — most exception-heavy file |
| `services/chat_service.py` | 3 | Medium — external API calls justify broad catches |
| `services/document_extraction.py` | 2 | Medium — external API calls |
| `api/nutrition.py` | 3 | Medium |
| `api/predict.py` | 2 | Medium |
| `main.py` | 3 | Low — startup/lifespan handlers |
| `services/retraining_pipeline.py` | 2 | Low — background task |
| Others (9 files) | 1 each | Low |

### 4.7 Backend Issues Summary

| Severity | Issue | Location |
|----------|-------|----------|
| **Critical** | Wildcard `"*"` in TrustedHostMiddleware | `app/main.py:124` |
| **High** | Only 1/81 endpoints rate-limited | Only `/reset-password` has `3/15min` (`auth.py:630`) |
| **High** | 130+ lines duplicated between risk compute functions | `app/api/predict.py:606-728` vs `737-850` |
| **Medium** | Dev token logging flag in production code | `app/api/auth.py:684,695` gated by `app/config.py:91-92` |
| **Medium** | CORS allows `["*"]` methods and headers | `app/main.py:110-111` |
| **Low** | `EdgeBatchItem` class defined but never used | `app/api/vital_signs.py:64-71` |

---

## 5. Mobile App Architecture

### 5.1 Screen Inventory (20 screens)

| Screen | Loading | Error | Empty | Status |
|--------|---------|-------|-------|--------|
| HomeScreen (`home_screen.dart`) | YES | YES (retry) | YES | Active |
| LoginScreen (`login_screen.dart`) | YES (button) | YES (SnackBar) | N/A | Active |
| RegisterScreen (`register_screen.dart`) | YES (button) | YES (dialog) | N/A | Active |
| OnboardingScreen (`onboarding_screen.dart`) | YES | YES | N/A | Active — 7 steps |
| ProfileScreen (`profile_screen.dart`) | YES | YES | YES | Active |
| HealthScreen (`health_screen.dart`) | YES | **NO** | YES | Active — missing error UI |
| DoctorMessagingScreen (`doctor_messaging_screen.dart`) | YES | YES (retry) | YES | Active |
| DevicePairingScreen (`device_pairing_screen.dart`) | YES | YES (SnackBar) | YES | Active |
| FitnessPlansScreen (`fitness_plans_screen.dart`) | YES | **NO** | YES | Active — missing error UI |
| RecoveryScreen (`recovery_screen.dart`) | YES | YES (text) | N/A | Active |
| NutritionScreen (`nutrition_screen.dart`) | YES | YES (retry) | YES | Active |
| RehabProgramScreen (`rehab_program_screen.dart`) | YES | YES (retry) | YES | Active |
| WorkoutScreen (`workout_screen.dart`) | YES | Partial | N/A | Active |
| HistoryScreen (`history_screen.dart`) | YES | YES | YES | Active |
| NotificationsScreen (`notifications_screen.dart`) | YES | YES | YES | Active |
| AiHomeScreen (`ai_home_screen.dart`) | YES | — | — | **ORPHAN** — no route |
| AiPlanScreen (`ai_plan_screen.dart`) | YES | — | — | **ORPHAN** — no route |
| ActivityDetailScreen (`activity_detail_screen.dart`) | — | — | — | **ORPHAN** — imported but unused |

### 5.2 Service Layer

| Service | Singleton | Error Handling | Uses ApiClient |
|---------|-----------|----------------|----------------|
| `api_client.dart` (Dio) | N/A | YES (interceptors) | Self |
| `edge_ai_store.dart` (ChangeNotifier) | Provider | YES | Via CloudSync |
| `edge_ml_service.dart` (Pure-Dart RF) | Class | YES | No (local) |
| `cloud_sync_service.dart` | Class | **Partial** (empty catch line 427) | YES |
| `ble/ble_service.dart` | YES (`_internal()`) | YES | No |
| `health/health_service.dart` | YES (`_internal()`) | YES | No |
| `notification_service.dart` | YES (`._instance`) | YES | No |
| `medication_reminder_service.dart` | YES (`init()`) | YES | YES |
| `alert_polling_service.dart` | Class | YES | YES |
| `chat_store.dart` | Class | YES | No |
| `gps_location_service.dart` | Class | YES | No |
| `mock_vitals_service.dart` | Class | N/A | No |

### 5.3 BLE Pipeline

Full chain verified: `DevicePairingScreen → BleService.startScan() [180D] → connectToDevice → _subscribeToHeartRate [2A37] → BleHealthParser → heartRateStream → VitalsProvider → EdgeAiStore.processVitals() → CloudSyncService → POST /vitals/batch-sync`

**Status: PASS** — pipeline complete.

### 5.4 Health Package & Edge AI

- `health: ^13.3.1` — current, uses `Health()` (NOT deprecated `HealthFactory`)
- EdgeMLService: pure-Dart RF (100 trees), `scaler_params.json` + `tree_ensemble.json` embedded
- No deprecated BLE APIs found

### 5.5 Permissions

**Android:** All required — BLUETOOTH_SCAN, BLUETOOTH_CONNECT, POST_NOTIFICATIONS, FOREGROUND_SERVICE, Health Connect read permissions.
**iOS:** All required — NSBluetoothAlwaysUsageDescription, NSHealthShareUsageDescription, UIBackgroundModes: bluetooth-central.

### 5.6 State Management

| Provider | Purpose |
|---|---|
| `vitals_provider.dart` | Central vitals state — connects BLE, Health, Edge AI, and sync |

Only one Provider found. Other screens manage state locally via `StatefulWidget`. Acceptable for the project scope but limits data sharing between screens.

### 5.7 Mobile Issues Summary

| Severity | Issue | Location |
|----------|-------|----------|
| **High** | 7 empty `catch (_) {}` blocks | `home_screen:550,724,1729`; `health_screen:318`; `workout_screen:478,561`; `cloud_sync:427` |
| **High** | 28 debug print/debugPrint statements | `main.dart`, `onboarding`, `profile`, `medication_reminder`, `notifications` |
| **Medium** | 3 orphan screens (no navigation route) | `ai_home_screen.dart`, `ai_plan_screen.dart`, `activity_detail_screen.dart` |
| **Medium** | `go_router: ^17.1.0` imported but unused | `pubspec.yaml` — app uses Navigator.push |
| **Medium** | Hard-coded `age = 35` | `workout_screen.dart:36` — should derive from profile |
| **Medium** | Hard-coded nutrition goals | `nutrition_screen.dart:25-28` — should be personalised |
| **Medium** | 2 screens missing error UI | `health_screen.dart`, `fitness_plans_screen.dart` |

---

## 6. Web Dashboard Architecture

### 6.1 Page Inventory (9 pages)

| Page | Route | Lines | Loading | Error | Empty |
|------|-------|-------|---------|-------|-------|
| LoginPage.tsx | `/login` (Public) | 211 | YES | YES (Alert) | N/A |
| RegisterPage.tsx | `/register` (Public) | 235 | YES | YES (Alert + validation) | N/A |
| ResetPasswordPage.tsx | `/reset-password` (Public) | 178 | YES | YES (multi-source) | YES (invalidLink) |
| DashboardPage.tsx | `/dashboard` (Clinician) | 900+ | YES | YES (dataWarning) | Partial |
| PatientDashboardPage.tsx | `/dashboard` (Patient) | 400+ | YES | YES | Partial |
| AdminPage.tsx | `/admin` (Protected) | 660 | YES | YES (per-operation) | YES |
| PatientsPage.tsx | `/patients` (Protected) | 400+ | YES | YES (alert) | YES |
| PatientDetailPage.tsx | `/patients/:patientId` (Protected) | 3600+ | YES | YES (errorMessage) | YES |
| MessagingPage.tsx | `/messages` (Protected) | 500+ | YES | YES | YES |

### 6.2 Route Protection

- `ProtectedRoute` component checks `localStorage.getItem('token')` and redirects to `/login` if missing.
- `DashboardWrapper` performs role-based routing: patients see `PatientDashboardPage`, clinicians see `DashboardPage`.
- Default route `/` redirects to `/dashboard`.
- All routes correct. ResetPasswordPage extracts token from URL query param (line 25).

### 6.3 API Client Coverage

`api.ts` — **88+ methods** covering all backend endpoints.

**11 methods returning `Promise<any>` (should be typed):** `getVitalSignsSummary` (277), `getVitalSignsSummaryForUser` (284), `getConsentStatus` (730), `getPendingConsentRequests` (735), `reviewConsentRequest` (740), `adminResetUserPassword` (756), `createUser` (763), `deactivateUser` (776), `updateUser` (781), `assignClinicianToPatient` (794), `normalizeUser` param (56).

**Broken methods:** `getRecommendationById()` (line 407) ignores ID parameter; `updateRecommendation()` (line 414) always returns latest instead of updating by ID.

### 6.4 Admin Page — Full CRUD Verified

CREATE (users), READ (list with pagination), UPDATE (profile fields), DELETE (soft deactivate), password reset, clinician assignment.

### 6.5 Patient Detail Page — All Panels Functional

Current vitals, risk assessment with "Run AI Assessment", HR history chart, vitals summary, risk factors, recommendations, alerts, activities, anomaly detection, trend forecast, baseline optimization, recommendation ranking, NL risk summary, retraining status, prediction explainability, medical profile CRUD, document upload with extraction review.

### 6.6 Component Structure

```
src/
├── components/
│   ├── cards/       # Stat cards, metric cards
│   └── common/      # StatusBadge, shared components
├── services/
│   └── api.ts       # Axios client with interceptors (88+ methods)
├── theme/
│   ├── colors.ts    # ISO 3864 clinical colour palette
│   └── typography.ts
└── types/           # TypeScript interfaces
```

### 6.7 Dashboard Issues Summary

| Severity | Issue | Location |
|----------|-------|----------|
| **Medium** | 11 API methods return `Promise<any>` | `api.ts:56,277,284,730-794` |
| **Medium** | 7 browser `alert()` calls | `AdminPage:150`, `PatientDetailPage:892,905,1081,3546,3548`, `PatientsPage:38` |
| **Medium** | PatientDetailPage 3600+ lines (monolithic) | Should split into VitalsPanel, RiskPanel, MedicalProfilePanel, etc. |
| **Medium** | 2 broken API methods (ignore ID param) | `api.ts:407` `getRecommendationById()`, `api.ts:414` `updateRecommendation()` |
| **Low** | `console.log` in production | `DashboardPage:163`, `PatientsPage:34` |
| **Low** | Demo credentials shown | `LoginPage:203` |

---

## 7. End-to-End Data Flows

### Flow Verification Summary

| # | Flow | Status |
|---|------|--------|
| 1 | User registration → login → JWT → protected endpoint | **PASS** |
| 2 | Vitals submission → alert threshold → alert creation → notification | **PASS** |
| 3 | BLE → VitalsProvider → EdgeAiStore → risk → CloudSync → backend | **PASS** |
| 4 | Password reset request → email → token → reset confirmation | **PASS** |
| 5 | Document upload → PDF extraction → Gemini → review → save | **PASS** |
| 6 | Risk compute → medical adjustment → adjusted score → recommendations | **PASS** |
| 7 | Clinician views patient → consent check → PHI access | **PASS** |

### 7.1 Registration → Onboarding → Profile Complete

```
RegisterScreen ──POST /api/v1/register──→ Backend creates User + AuthCredential
    │
    └─→ OnboardingScreen (7 steps)
           ├─ Step 1: Name, Gender
           ├─ Step 2: Age
           ├─ Step 3: Fitness & Rehab (activity level, exercise limitations, rehab phase)
           ├─ Step 4: Goals & Wellbeing (primary goal, stress, sleep)
           ├─ Step 5: Health Profile (conditions, baseline HR, max safe HR)
           ├─ Step 6: Emergency Contact
           └─ Step 7: All Set Summary
                │
                ├─ PUT /api/v1/me (health profile + age)
                ├─ PUT /api/v1/me (emergency contact)
                └─ PUT /api/v1/me (lifestyle data)
                       │
                       └─→ Navigate to HomeScreen
```

### 7.2 BLE → Vitals → Edge AI → Cloud Sync

```
BLE Device (HR monitor)
    │
    └─→ ble_service.dart (scan + connect + subscribe 0x2A37)
           │
           └─→ ble_health_parser.dart (parse HR, RR-interval)
                  │
                  └─→ VitalsProvider (update state)
                         │
                         ├─→ edge_ml_service.dart (predict risk, ~10ms)
                         │     └─→ edge_ai_store.dart (cache result)
                         │
                         ├─→ edge_alert_service.dart
                         │     └─→ notification_service.dart (if threshold violated)
                         │
                         └─→ cloud_sync_service.dart (queue for batch upload)
                               └─→ POST /api/v1/vitals/batch-sync (every 15 min or on-demand)
                                      │
                                      └─→ Backend: check_vitals_for_alerts() (background task)
                                            └─→ Alert model (HR > 180 CRITICAL, SpO2 < 90 CRITICAL)
```

### 7.3 Login → JWT → Authenticated Requests

```
LoginScreen ──POST /api/v1/login──→ Backend validates credentials
    │                                    │
    │                                    ├─→ Check account lockout (locked_until)
    │                                    ├─→ Verify password (PBKDF2-SHA256, 200k rounds)
    │                                    └─→ Return {access_token, refresh_token}
    │
    └─→ Store tokens (flutter_secure_storage / localStorage)
           │
           └─→ Dio/Axios interceptor adds Authorization: Bearer <token>
                  │
                  └─→ On 401: attempt POST /api/v1/refresh with refresh_token
                         │
                         ├─→ Success: update stored tokens, retry request
                         └─→ Failure: redirect to login
```

### 7.4 ML Risk Prediction (Backend)

```
POST /api/v1/predictions/risk
    │
    ├─→ get_current_user (JWT validation)
    ├─→ engineer_features() (17 derived features from raw vitals)
    ├─→ scaler.transform() (StandardScaler normalisation)
    ├─→ model.predict_proba() (RandomForest, 100 trees)
    └─→ Return {risk_score: 0.0-1.0, risk_level, confidence}

Risk adjustment chain (predict.py):
    ├─→ +0.10 prior MI
    ├─→ +0.05–0.20 HF (by NYHA class)
    ├─→ +0.05 anticoagulant
    └─→ beta-blocker HR adjustment
```

### 7.5 Clinician-Patient Messaging

```
Mobile: DoctorMessagingScreen ──POST /api/v1/messages──→ Backend
                                                            │
                                                            └─→ Message model (encrypted at rest)
                                                                   │
Web: MessagingPage ──GET /api/v1/messages/{conversation_id}──→ Decrypt and return
```

### 7.6 Document Extraction (Medical History)

```
POST /api/v1/medical-history/extract-document
    │
    ├─→ Upload PDF/image
    ├─→ document_extraction.py → Gemini 2.0 Flash API
    │     └─→ Extract structured medical data
    ├─→ encryption_service.encrypt_text() (AES-256-GCM)
    └─→ Store in MedicalHistory model
```

### 7.7 AI Chat Coach

```
Mobile: AiHomeScreen ──POST /api/v1/chat──→ chat_service.py
                                               │
                                               ├─→ Rate limit check (10 req/min per user)
                                               ├─→ Build context from user vitals + history
                                               ├─→ Gemini 2.0 Flash API (15 RPM global limit)
                                               └─→ Return AI response
```

---

## 8. Dead Code, Unused Files & Logic Rabbit Holes

### 8.1 Root-Level Scripts (Should Be in `scripts/`)

| File | Used? | Action |
|---|---|---|
| `apply_migrations.py` | Rarely — manual migration runner | Move to `scripts/` |
| `create_admin.py` | One-time admin seeder | Move to `scripts/` |
| `init_db.py` | DB initialisation | Move to `scripts/` |
| `reset_database.py` | DEV ONLY — destructive | Move to `scripts/`, mark clearly |
| `seed_patient.py` | Test data seeder | Move to `scripts/` |
| `run_coverage.py` | Dev utility | Move to `scripts/` |
| `quick_install.bat` | Windows dev setup | Move to `scripts/` |
| `start.bat` / `start_server.py` | Dev launchers | Acceptable at root |
| `deploy.sh` | Deploy script | Move to `scripts/` |

### 8.2 Mobile App Root Clutter

The `mobile-app/` directory contains 16 markdown and 2 `.dart` files that are documentation, not source code:

```
COMPLETE_CHANGE_LOG.md          DARK_MODE_BEST_PRACTICES.dart
DARK_MODE_GUIDE.md              DARK_MODE_IMPLEMENTATION.md
DARK_MODE_INTEGRATION_COMPLETE.md  DARK_MODE_QUICK_REFERENCE.md
DELIVERY_SUMMARY.md             DESIGN_PATTERNS.md
FINAL_DELIVERABLES.md           FLUTTER_AI_INTEGRATION.md
HCI_PRINCIPLES.md               IMPLEMENTATION_SUMMARY.md
ONBOARDING_TESTING.md           TESTING_CHECKLIST.md
THEME_INTEGRATION_EXAMPLE.dart  UI_ENHANCEMENTS.md
UI_VISUAL_GUIDE.md
```

**Recommendation**: Move all `.md` files to `mobile-app/docs/` and delete or move `.dart` example files.

### 8.3 Incomplete Implementations

| File | Line | Type | Description |
|------|------|------|-------------|
| `mobile-app/lib/screens/ai_home_screen.dart` | — | Orphan screen | No navigation route in main.dart |
| `mobile-app/lib/screens/ai_plan_screen.dart` | — | Orphan screen | Referenced only from orphan ai_home_screen |
| `mobile-app/lib/screens/activity_detail_screen.dart` | — | Orphan screen | Imported but unused in navigation |
| `web-dashboard/src/services/api.ts` | 407 | Broken method | `getRecommendationById()` ignores ID |
| `web-dashboard/src/services/api.ts` | 414 | Broken method | `updateRecommendation()` returns latest |
| `app/api/vital_signs.py` | 64-71 | Unused class | `EdgeBatchItem` never referenced |
| `mobile-app/lib/screens/workout_screen.dart` | 36 | Hard-coded | `age = 35` not from profile |
| `mobile-app/lib/screens/nutrition_screen.dart` | 25-28 | Hard-coded | Daily goals not personalised |
| `mobile-app/lib/screens/health_screen.dart` | — | Missing UI | No error state on failure |
| `mobile-app/lib/screens/fitness_plans_screen.dart` | — | Missing UI | No error state on failure |

### 8.4 Unwanted Code Patterns

| File | Line | Category | Severity | Description |
|------|------|----------|----------|-------------|
| `app/main.py` | 124 | Security | Critical | Wildcard `"*"` in TrustedHostMiddleware |
| `app/api/auth.py` | 684, 695 | Security | High | Dev token logging via `logger.info()` |
| `app/api/vital_signs.py` | 64-71 | Dead code | Low | `EdgeBatchItem` defined but unused |
| `mobile-app/lib/screens/home_screen.dart` | 550, 724, 1729 | Empty catch | Medium | `catch (_) {}` — errors silenced |
| `mobile-app/lib/screens/health_screen.dart` | 318 | Empty catch | Medium | `catch (_) {}` — error silenced |
| `mobile-app/lib/screens/workout_screen.dart` | 478, 561 | Empty catch | Medium | `catch (_) {}` — errors silenced |
| `mobile-app/lib/services/cloud_sync_service.dart` | 427 | Empty catch | Medium | `catch (_) {}` — queue persistence error |
| `mobile-app/lib/main.dart` | 93-171 | Debug | Medium | 10 print/debugPrint statements |
| `mobile-app/lib/services/medication_reminder_service.dart` | 67-196 | Debug | Low | 8 debugPrint calls |
| `mobile-app/lib/screens/onboarding_screen.dart` | Various | Debug | Low | 6 print statements |
| `mobile-app/lib/screens/doctor_messaging_screen.dart` | Various | Debug | Low | 2 print statements |
| `mobile-app/lib/screens/profile_screen.dart` | 216, 245 | Debug | Low | 2 debugPrint calls |
| `web-dashboard/src/pages/DashboardPage.tsx` | 163 | Debug | Low | `console.log(...)` |
| `web-dashboard/src/pages/PatientsPage.tsx` | 34 | Debug | Low | `console.log(...)` |
| `app/main.py` | 51, 67, 157 | Error handling | Medium | Broad `except Exception` |
| `app/services/chat_service.py` | 429, 502, 541 | Error handling | Medium | Broad `except Exception` |

### 8.5 Logic Rabbit Holes

These areas have overgrown complexity and should be refactored:

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| `app/api/predict.py` | 606-850 | 130+ lines duplicated between patient/clinician risk compute | Extract `_compute_risk_assessment()` shared helper |
| `app/services/chat_service.py` | 69-310 | 186-line function with 7 elif branches | Dict-based dispatcher pattern |
| `app/api/auth.py` | 1-774 | 774-line file mixing many concerns | Split into auth_core, auth_reset, auth_dependencies |
| `app/api/predict.py` | 1-1008 | 1008-line file | Split into predict, risk_assessment, recommendation endpoints |
| `web-dashboard/src/pages/PatientDetailPage.tsx` | 1-3600 | 3600+ line monolithic component | Split into VitalsPanel, RiskPanel, MedicalProfilePanel, etc. |

### 8.6 Backend Services — Usage Verification Needed

| Service | Concern |
|---|---|
| `email_service.py` | No email provider configured in requirements |
| `baseline_optimization.py` | May only be called by advanced_ml endpoints |
| `recommendation_ranking.py` | May only be called by advanced_ml endpoints |
| `trend_forecasting.py` | May only be called by advanced_ml endpoints |
| `retraining_pipeline.py` | Background task — verify it is actually triggered |

### 8.7 Test Files — Coverage-Boosting Artifacts

| File | Concern |
|---|---|
| `test_100_percent_coverage.py` | Name suggests coverage padding |
| `test_coverage_gaps.py` | Name suggests coverage padding |
| `test_coverage_gaps2.py` | Name suggests coverage padding |
| `test_final_coverage.py` | Name suggests coverage padding |
| `test_last_7_lines.py` | Name suggests coverage padding |

**Recommendation**: Review these files. If they test real functionality, rename to reflect what they test. If trivial assertions, remove them.

---

## 9. Testing Coverage

### 9.1 Test File Inventory (27 files, 150+ functions)

| File | Functions | Domain |
|---|---|---|
| `conftest.py` | — | Shared fixtures (DB setup, test client, auth helpers) |
| `helpers.py` | — | Shared test utilities |
| `test_registration.py` | — | User registration flow |
| `test_auth_extended.py` | 20+ | Login, register, refresh, password reset, lockout |
| `test_user_api.py` | 35+ | Profile CRUD, clinician assignment |
| `test_vital_signs.py` | 45+ | Submit, batch, query, history, summary |
| `test_predict_api.py` | 50+ | ML status, predict, risk assessment |
| `test_alert_api.py` | 10+ | Create, acknowledge, resolve, dedup |
| `test_activity.py` | 19+ | Session start, end, query |
| `test_messages.py` / `test_messaging.py` | 20+ | Thread, send, read |
| `test_rbac_consent.py` | 5+ | RBAC, consent gating |
| `test_advanced_ml.py` | 10+ | Anomaly, forecast, baseline |
| `test_nl_endpoints.py` | 4+ | NL risk summary |
| `test_nutrition.py` | 5 | Basic CRUD |
| `test_final_coverage.py` | 2+ | Rehab basic |
| `test_predict_807.py` | — | Specific prediction edge case |
| `test_models.py` | — | ORM model unit tests |
| `test_schemas.py` | — | Pydantic schema validation |
| `test_services.py` | — | Service layer unit tests |
| `test_database.py` | — | Database connection and session |
| `test_main.py` | — | App startup and middleware |
| `test_e2e_integration.py` | — | End-to-end integration flows |
| `test_exercise_library.py` | — | Exercise/activity library |
| `test_100_percent_coverage.py` | — | Coverage gap filler |
| `test_coverage_gaps.py` | — | Coverage gap filler |
| `test_coverage_gaps2.py` | — | Coverage gap filler |
| `test_last_7_lines.py` | — | Coverage gap filler |

### 9.2 Coverage Gaps

| API Module | Status | Gap |
|-----------|--------|-----|
| `medication_reminder.py` | **NOT TESTED** | 0 tests — all 4 endpoints untested |
| `nutrition.py` | MINIMAL | 5 tests — recommendations untested |
| `rehab.py` | MINIMAL | 2 tests — progression untested |
| `nl_endpoints.py` | MINIMAL | 4 tests — AI summaries untested |
| `medical_history.py` | PARTIAL | Limited endpoint coverage |
| `encryption_service.py` | **NOT TESTED** | Critical for PHI |
| `chat_service.py` | **NOT TESTED** | No dedicated tests |
| `document_extraction.py` | **NOT TESTED** | No dedicated tests |
| Flutter mobile app | **NONE** | No Dart test files |
| React web dashboard | **NONE** | Testing libs installed but no custom tests |

**Recommendation**: Add dedicated test files for `medical_history`, `medication_reminder`, `rehab`, `encryption`, and `chat_service`. Add widget tests for Flutter and component tests for React.

---

## 10. Security Posture

### 10.1 Critical Issues

| ID | Issue | Location | Severity |
|---|---|---|---|
| SEC-01 | **TrustedHostMiddleware has `"*"` wildcard** | `app/main.py` line ~124 | **CRITICAL** |

The `allowed_hosts` list includes `"*"` alongside specific domains. This negates the entire purpose of the middleware — any host header is accepted.

**Fix**: Remove `"*"` from the list. Add the AWS ALB hostname instead:
```python
allowed_hosts=[
    "api.adaptivhealth.com",
    "adaptivhealth.com",
    "dashboard.adaptivhealth.com",
    "adaptivhealth-alb-1498103672.me-central-1.elb.amazonaws.com",
    "localhost",
    "127.0.0.1",
]
```

### 10.2 High/Medium Issues

| ID | Issue | Location | Severity |
|---|---|---|---|
| SEC-02 | Only 1/81 endpoints rate-limited (password reset `3/15min`) | `app/rate_limiter.py`, `app/api/auth.py:630` | **HIGH** |
| SEC-03 | Dev token logging flag in production code | `app/api/auth.py:684,695`, `app/config.py:91-92` | **HIGH** |
| SEC-04 | CORS `allow_methods/headers=["*"]` | `app/main.py:110-111` | **MEDIUM** |
| SEC-05 | 33 broad `except Exception` blocks could swallow security-relevant errors | See Section 4.6 heatmap | **MEDIUM** |
| SEC-06 | Mobile token stored via `flutter_secure_storage` but fallback to in-memory `static String? _authToken` exists | `api_client.dart` | **LOW** |
| SEC-07 | Demo credentials in UI | `LoginPage.tsx:203` | **LOW** |

**Recommended rate limits**: login 5/min, register 3/min, vitals 60/min.

### 10.3 Good Practices Already in Place

| Control | Status | Location |
|---|---|---|
| JWT authentication (access + refresh tokens) | **Implemented** | `app/api/auth.py`, `app/services/auth_service.py` |
| PBKDF2-SHA256 password hashing (200k rounds) | **Implemented** | `app/services/auth_service.py` |
| Password strength validation (8+ chars, digit, letter) | **Implemented** | `app/schemas/user.py` |
| Account lockout (3 failed attempts → 15 min lock) | **Implemented** | `app/api/auth.py` |
| PHI encryption (AES-256-GCM) | **Implemented** | `app/services/encryption.py` |
| CORS regex (localhost only for dev) | **Implemented** | `app/main.py` |
| Rate limiting (SlowAPI) | **Implemented** | `app/main.py` (1 endpoint) |
| Role-based access (patient/clinician/admin) | **Implemented** | `app/api/auth.py` |
| Consent-based PHI access | **Implemented** | `app/api/consent.py` |
| No SQL injection (SQLAlchemy ORM) | **Confirmed** | Throughout backend |
| No XSS (`dangerouslySetInnerHTML`) | **Confirmed** | Grep found zero matches |
| No hardcoded API keys | **Confirmed** | No `sk-`, `SG.`, `AKIA` patterns found |
| JWT properly configured | **Confirmed** | HS256, 30min access / 7day refresh |
| `.env` in `.gitignore` | **Confirmed** | Root `.env` covered |

### 10.4 HIPAA Compliance Checklist

| Requirement | Status |
|---|---|
| PHI encrypted at rest | **Yes** — AES-256-GCM via `encryption.py` |
| PHI encrypted in transit | **Partial** — HTTPS required in production; development uses HTTP |
| Access controls (RBAC) | **Yes** — patient/clinician/admin roles |
| Audit logging | **Partial** — `logger.info()` on vitals submission and alerts; no dedicated audit trail table |
| Minimum necessary access | **Yes** — patients see own data; clinicians need consent |
| Session timeout | **Yes** — 30-minute access token expiry |
| Account lockout | **Yes** — 3 attempts → 15-minute lockout |

---

## 11. Dependency Health

### 11.1 Backend (Python) — `requirements.txt`

| Package | Version Spec | Notes |
|---|---|---|
| `fastapi` | `>=0.115` | Current, well-maintained |
| `uvicorn[standard]` | `>=0.30` | Current |
| `sqlalchemy` | `>=2.0.30` | Current, using 2.0 async-compatible style |
| `pydantic` | `>=2.7` | Current v2 |
| `python-jose[cryptography]` | `>=3.3.0` | Maintained but low activity; consider `PyJWT` long-term |
| `passlib[bcrypt]` | `>=1.7.4` | Low maintenance activity; consider direct `bcrypt` |
| **`scikit-learn`** | **`==1.8.0`** | **Pinned exact** — required for model compatibility |
| `psycopg[binary]` | `>=3.2.1` | Modern async PostgreSQL driver |
| `cryptography` | `>=44.0` | Active, well-maintained |
| `google-generativeai` | `>=0.8.0` | Gemini SDK |
| ~~`celery`~~ | — | Removed (unused) |
| ~~`redis`~~ | — | Removed (unused) |
| ~~`boto3`~~ | — | Removed (unused — AWS infra managed via CLI/deploy scripts, not app code) |
| `structlog` | `>=24.2` | Structured logging |

### 11.2 Mobile (Flutter) — `pubspec.yaml`

| Package | Version | Notes |
|---|---|---|
| `flutter_blue_plus` | `^1.35.0` | BLE — actively maintained |
| `health` | `^13.3.1` | HealthKit/Google Fit — actively maintained |
| `dio` | `^5.4.0` | HTTP client — actively maintained |
| `flutter_secure_storage` | `^10.0.0` | Keychain/Keystore — actively maintained |
| `go_router` | `^17.1.0` | Navigation — **unused** (app uses Navigator.push) |
| `provider` | `^6.1.0` | State management — stable |
| `google_fonts` | `^8.0.2` | DM Sans typography |
| `fl_chart` | `^1.1.1` | Charts — actively maintained |
| `geolocator` | `^14.0.2` | GPS location |
| `permission_handler` | `^11.3.0` | Runtime permissions |
| `flutter_local_notifications` | `^18.0.1` | Local push notifications |
| `shared_preferences` | `^2.2.2` | Theme preference storage |

**SDK constraint**: `>=3.0.0 <4.0.0` — current Dart 3.x. Lock files: `pubspec.lock` exists.

### 11.3 Web Dashboard (React) — `package.json`

| Package | Version | Notes |
|---|---|---|
| `react` | `^18.2.0` | Current stable |
| `react-dom` | `^18.2.0` | Current stable |
| `react-router-dom` | `^6.21.3` | Current v6 |
| `axios` | `^1.6.5` | HTTP client — actively maintained |
| `@mui/material` | `^5.15.6` | MUI v5 — consider v6 long-term |
| `recharts` | `^2.12.0` | Charting — actively maintained |
| `typescript` | `^4.9.5` | Consider upgrading to TS 5.x |
| `@reduxjs/toolkit` | `^2.0.1` | **Possibly unused** — no Redux store found |
| `react-redux` | `^9.1.0` | **Possibly unused** — no Redux store found |
| `lucide-react` | `^0.563.0` | Icons |
| `date-fns` | `^3.2.0` | Date utilities |

Lock files: `package-lock.json` exists.

---

## 12. Recommendations and Prioritised Action Items

### Critical — Must Fix

| # | Severity | Area | Issue | Recommended Fix | Effort |
|---|----------|------|-------|-----------------|--------|
| 1 | **Critical** | Security | Wildcard `"*"` in TrustedHostMiddleware | Remove from `app/main.py:124`; add ALB hostname | 5 min |
| 2 | **High** | Security | Only 1/81 endpoints rate-limited | Add limits: login 5/min, register 3/min, vitals 60/min | 30 min |
| 3 | **High** | Security | Dev token logging in auth.py | Guard with environment check at `auth.py:684` | 10 min |
| 4 | **High** | Code Quality | 130+ lines duplicated in predict.py | Extract shared `_compute_risk_assessment()` helper | 1 hr |
| 5 | **High** | Mobile | 7 empty catch blocks | Add error logging at each location | 30 min |

### High Priority — Strongly Recommended

| # | Severity | Area | Issue | Recommended Fix | Effort |
|---|----------|------|-------|-----------------|--------|
| 6 | **Medium** | Security | CORS wildcard methods/headers | Restrict to specific values in `main.py:110-111` | 10 min |
| 7 | **Medium** | Testing | medication_reminder.py: 0 tests | Create dedicated test file | 1 hr |
| 8 | **Medium** | Testing | nutrition.py: only 5 tests | Expand coverage | 1 hr |
| 9 | **Medium** | Testing | rehab.py: only 2 tests | Expand coverage | 1 hr |
| 10 | **Medium** | Testing | No Flutter or React tests | Add widget/component tests | 4-6 hr |
| 11 | **Medium** | Repo | University docs in repo root | Move to `docs/university/` | 5 min |
| 12 | **Medium** | Repo | Utility scripts in root | Move to `scripts/` | 10 min |
| 13 | **Medium** | Repo | .gitignore gaps | Add `node_modules`, `.dart_tool`, `google-services.json`, `GoogleService-Info.plist`, `*.jks` | 5 min |
| 14 | **Medium** | Dashboard | 11 methods return `Promise<any>` | Add TypeScript types | 1 hr |
| 15 | **Medium** | Dashboard | 7 browser `alert()` calls | Replace with MUI Snackbar | 30 min |
| 16 | **Medium** | Dashboard | PatientDetailPage 3600+ lines | Split into sub-components | 3-4 hr |
| 17 | **Medium** | Dashboard | 2 broken API methods (ignore ID) | Fix `getRecommendationById` and `updateRecommendation` | 15 min |
| 18 | **Medium** | Mobile | 3 orphan screens | Remove or integrate into navigation | 30 min |
| 19 | **Medium** | Mobile | Hard-coded age and nutrition goals | Derive from profile/onboarding values | 30 min |
| 20 | **Medium** | Backend | Broad `except Exception` blocks (33 total) | Catch specific types, prioritise `medical_history.py` | 1-2 hr |

### Low Priority — Future Enhancements

| # | Severity | Area | Issue | Recommended Fix | Effort |
|---|----------|------|-------|-----------------|--------|
| 21 | **Low** | Mobile | 28 debug print statements | Remove or gate behind `kDebugMode` | 30 min |
| 22 | **Low** | Mobile | `go_router` unused | Remove from `pubspec.yaml` | 5 min |
| 23 | **Low** | Dependencies | celery, redis, redux possibly unused | Verify and remove | 30 min |
| 24 | **Low** | Backend | chat_service 186-line elif chain | Dict dispatcher pattern | 1 hr |
| 25 | **Low** | Dashboard | console.log in production | Remove | 5 min |
| 26 | **Low** | Dashboard | Demo credentials shown | Remove from prod | 5 min |
| 27 | **Low** | Dashboard | TypeScript `^4.9.5` | Upgrade to `^5.x` | 30 min |
| 28 | **Low** | Backend | `python-jose` low maintenance | Migrate to `PyJWT` | 1 hr |
| 29 | **Low** | Backend | No migration version tracking | Add `_applied_migrations` table or Alembic | 1-2 hr |
| 30 | **Low** | Mobile | Only 1 Provider class | Add AuthProvider, ChatProvider | 3-5 hr |
| 31 | **Low** | Dashboard | MUI v5 | Upgrade to v6 | 2-4 hr |

---

## Appendix A: File Counts Summary

| Component | Type | Count |
|---|---|---|
| Backend | API routers | 14 |
| Backend | Models | 12 |
| Backend | Schemas | 12 |
| Backend | Services | 15 |
| Backend | Test files | 27 |
| Backend | Migration files | 11 |
| Backend | Endpoints | 81+ |
| Mobile | Screens | 20 (3 orphan) |
| Mobile | Services | 13+ |
| Mobile | Providers | 1 |
| Dashboard | Pages | 9 |
| Dashboard | API methods | 88+ |
| Dashboard | Component dirs | 2 (cards, common) |

## Appendix B: Backend Exception Handling Heatmap

```
medical_history.py   ████████████████████  9
nutrition.py         ██████████            3
chat_service.py      ██████████            3
main.py              ██████████            3
document_extraction  ██████                2
predict.py           ██████                2
retraining_pipeline  ██████                2
database.py          ██████                2
auth_service.py      ███                   1
encryption.py        ███                   1
auth.py              ███                   1
user.py              ███                   1
vital_signs.py       ███                   1
messages.py          ███                   1
ml_prediction.py     ███                   1
                                    Total: 33
```
