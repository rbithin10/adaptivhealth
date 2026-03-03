# MASTER_CHECKLIST.md

> **Purpose**: Human-facing project summary — outstanding tasks and known issues only.
> Synced with `ARCHITECT_CHECKLIST.md` (detailed working board).
> **Last updated**: March 3, 2026

## Backend

- [x] **P0** Remove `"*"` from TrustedHostMiddleware `allowed_hosts`; add AWS ALB hostname instead
- [x] **P0** Expand SlowAPI rate limits to cover `/login`, `/register`, and vitals submission endpoints (keep existing reset-password protection)
- [x] **P0** Guard password reset dev-token logging so it cannot run in production
- [x] **P1** Extract shared `_compute_risk_assessment()` helper to deduplicate 130+ lines in `predict.py`
- [x] **P1** Restrict CORS `allow_methods`/`allow_headers` from wildcard `["*"]` to specific values
- [x] **P1** Add dedicated tests for medication reminders (currently no test references found)
- [x] **P1** Expand nutrition.py tests (currently only 5 basic → now 21 tests)
- [x] **P1** Expand rehab.py tests (currently only 2 basic → now 6 tests)
- [x] **P1** Reduce broad `except Exception` usage in PHI-sensitive code paths (prioritise `medical_history.py`)
- [x] **P0** NL risk insights now use Gemini-generated output only (removed dashboard-side fallback summaries)
- [x] **P2** Verify whether `celery`, `redis`, and `boto3` are used; remove if unused — removed
- [x] **P2** Refactor `chat_service.py` 186-line elif chain to dict-based dispatcher
- [x] **P2** Migrate from `python-jose` to `PyJWT` (more actively maintained)
- [x] **P1** Stabilize Gemini key loading for document extraction by accepting GEMINI_API_KEY and GOOGLE_API_KEY aliases
- [x] **P1** Add authenticated medical extraction readiness endpoint (`GET /api/v1/medical-extraction/status`) for Gemini diagnostics
- [x] **P1** Add patient-document storage integrity flags (empty vs missing) and clinician warning banner for missing uploaded files
- [x] **P0** Add real-time clinician alert SSE stream endpoint (`GET /api/v1/alerts/stream`) for instant dashboard updates

## Mobile App

- [x] **P0** Replace empty `catch (_) {}` blocks with logged/handled failures (no silent error swallowing)
- [x] **P0** Remove hard-coded `age = 35` in workout logic; use onboarding/profile value (fetches from API, 35 as fallback)
- [x] **P1** Replace hard-coded nutrition goals with explicit defaults or personalised goals (Mifflin-St Jeor TDEE)
- [x] **P1** Remove or gate debug `print`/`debugPrint` calls behind `kDebugMode`
- [x] **P1** Decide: wire routes for `AiHomeScreen`/`AiPlanScreen`/`ActivityDetailScreen` or remove unused screens — removed
- [x] **P1** Add Flutter widget tests (login, onboarding, home screen at minimum)
- [x] **P2** Remove unused `go_router` from `pubspec.yaml` (app uses Navigator.push)
- [x] **P2** Add more Provider classes (AuthProvider, ChatProvider) to reduce StatefulWidget state
- [x] **P2** **Edge AI runtime stabilization** — syncNow(), lastSyncTime, full state tracking implemented
- [x] **P2** **Top Navigation Drawer** — Added Notifications, Health Insights (backend-backed only)

## Web Dashboard

- [x] **P0** Fix `getRecommendationById()` and `updateRecommendation()` to call correct ID-based endpoints
- [x] **P0** Replace browser `alert()` calls with MUI Snackbar/Alert patterns
- [x] **P1** Remove `Promise<any>` and reduce `any` usage in `api.ts` by introducing typed responses
- [x] **P1** Split `PatientDetailPage` into sub-components/panels (VitalsPanel, RiskAssessmentPanel, MedicalProfilePanel, AlertsPanel, AdvancedMLPanel)
- [x] **P1** Add React component tests (LoginPage, AdminPage, PatientsPage)
- [x] **P2** Remove `console.log` from DashboardPage and PatientsPage
- [x] **P2** Remove demo credentials from LoginPage before production
- [x] **P2** Upgrade TypeScript from `^4.9.5` to `^5.6.3`
- [x] **P2** Verify whether `@reduxjs/toolkit` / `react-redux` are used; remove if unused — already absent
- [x] **P2** Upgrade MUI from v5 to v6 (`^6.4.12`)
- [x] **P1** Patients table medical-record UX: show `empty` only when truly unavailable and open uploaded medical document directly from list button
- [x] **P0** Remove/retire unused shim API wrappers (`getRiskAssessmentsForUser`, `getRecommendations`, `getRecommendationById`, `updateRecommendation`, `updateActivity`)
- [x] **P0** Complete alerts flow wiring in patient detail (acknowledge + resolve)
- [x] **P0** Enforce route-level RBAC in `App.tsx` for admin/clinician-only routes
- [x] **P0** Disable public dashboard registration route (`/register` redirects to `/login`)
- [~] **P1** Continue breaking down `PatientDetailPage.tsx` monolith (still large; extracted `SessionHistoryPanel` and `PredictionExplainabilityPanel`)
- [x] **P1** Expand dashboard test coverage (now includes `MessagingPage`, `DashboardPage`, `PatientDetailPage`, `RegisterPage`, `ResetPasswordPage`, and route/RBAC tests in `App.test.tsx`)

## Docs & Demo

- [x] **P1** Prepare deployment checklist and production walkthrough — `docs/DEPLOYMENT_CHECKLIST.md`
- [x] **P1** Add `.gitignore` entries for mobile service config and signing keys (`google-services.json`, `GoogleService-Info.plist`, `*.jks`, `*.keystore`), `node_modules/` (root), and `.dart_tool/`
- [x] **P2** Move university documents (`.docx`, `.pdf`) into `docs/university/`
- [x] **P2** Move root utility scripts into `scripts/`
- [x] **P2** Add migration version tracking (`_applied_migrations` table + updated `scripts/apply_migrations.py`)
- [x] **P1** Align dashboard QA/README backend target notes with ALB-default + local `REACT_APP_API_URL` override
- [x] **P0** Align NL architecture docs with implementation: NL-first interpretation layer, Gemini as optional gap-fill/enhancement (`docs/NL_AI_COACH_API.md`)

---

## BLE (Bluetooth Low Energy) — Heart Rate Monitor Integration

### Core layer: `lib/services/ble/` — solid foundations
- [x] `ble_service.dart` — Singleton, Heart Rate Service 0x180D scan + 0x2A37 subscribe, auto-reconnect (exponential backoff 2/4/8s), persist last device via SharedPreferences
- [x] `ble_health_parser.dart` — Correct BLE Heart Rate Measurement parsing (Uint8/Uint16, sensor contact, energy expended, RR intervals for HRV)
- [x] `ble_permission_handler.dart` — Android 12+ (BLUETOOTH_SCAN + BLUETOOTH_CONNECT) and Android < 12 (locationWhenInUse)

### Platform configuration — complete
- [x] `AndroidManifest.xml` — All BLE permissions declared (BLUETOOTH_SCAN, BLUETOOTH_CONNECT, BLUETOOTH, BLUETOOTH_ADMIN with maxSdkVersion, FOREGROUND_SERVICE_CONNECTED_DEVICE)
- [x] `AndroidManifest.xml` — `uses-feature android.hardware.bluetooth_le` with `required="false"`
- [x] `Info.plist` — `NSBluetoothAlwaysUsageDescription` set
- [x] `Info.plist` — `UIBackgroundModes` includes `bluetooth-central`
- [x] `pubspec.yaml` — `flutter_blue_plus: ^1.35.0` and `permission_handler: ^11.3.0` present

### Integration gaps — require fixes
- [x] **P0 BLE–Workout disconnect**: `ActiveWorkoutScreen` now subscribes to `VitalsProvider.vitalsStream` for live BLE/HealthKit HR; falls back to simulation only when source is mock
- [x] **P0 DevicePairing → VitalsProvider disconnect**: `DevicePairingScreen._connect()` now calls `VitalsProvider.connectBle()` via Provider so the unified vitals pipeline receives real data
- [x] **P1 No Bluetooth adapter state check**: `BleService.isBluetoothOn()` + `requestBluetoothOn()` added; `DevicePairingScreen._startScan()` shows "Enable Bluetooth" dialog before scanning
- [x] **P1 Stream controllers not closed in `BleService.dispose()`**: All three broadcast StreamControllers (`_scanResultsController`, `_connectionStateController`, `_heartRateController`) now closed in `dispose()`
- [x] **P2 Silent failure on startup reconnect**: `_attemptReconnectFromSavedDevice()` now checks `isBluetoothOn()` first and logs failures via `debugPrint` in debug mode
- [ ] **P2 Health screen has no real-time BLE vitals**: `health_screen.dart` only shows API-fetched data — no subscription to live BLE/VitalsProvider readings (low priority: health screen is an overview, not real-time monitor)
- [ ] **P2 iOS Podfile missing**: Not generated yet (Windows dev environment) — needs `flutter pub get` on macOS before iOS build
- [x] **P2 No BT on/off monitoring**: `BleService._monitorAdapterState()` added — detects BT off (graceful disconnect) and BT on (auto-reconnect to last saved device)

### Additional hardening (implemented)
- [x] **P1 iOS BLE permissions**: `BlePermissionHandler` now handles iOS `Permission.bluetooth` request proactively + `hasPermissions()` check for silent reconnect
- [x] **P2 forgetSavedDevice()**: New `BleService.forgetSavedDevice()` method for logout cleanup

---

## Known Issues

- [x] ~~Edge AI sync state can still misreport offline/pending (Mobile, Medium)~~ — resolved with sync stabilization
- [x] ~~Central deployment checklist/walkthrough not finalised (Ops, Medium)~~ — `docs/DEPLOYMENT_CHECKLIST.md` created
- [ ] SMTP production rollout not yet verified in-repo (Backend/Ops, Low)
