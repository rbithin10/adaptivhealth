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

## Known Issues

- [x] ~~Edge AI sync state can still misreport offline/pending (Mobile, Medium)~~ — resolved with sync stabilization
- [x] ~~Central deployment checklist/walkthrough not finalised (Ops, Medium)~~ — `docs/DEPLOYMENT_CHECKLIST.md` created
- [ ] SMTP production rollout not yet verified in-repo (Backend/Ops, Low)
