# Data Pipeline — Gap Closure Checklist

Covers the three gaps identified from the pipeline analysis (paste.txt lines 1–13).

---

## What Already Works (Confirmed)

- 15-min batch sync: `CloudSyncService` → `POST /vitals/batch-sync`
- Batch-sync ingests vitals + edge risk assessments into DB
- SSE alert stream: `GET /alerts/stream` polls DB every 1 s, pushes to dashboard
- Dashboard SSE client: `DashboardPage.tsx` connects to `EventSource` on load
- GPS emergencies: prioritised at front of sync queue

---

## Gaps to Close

### Gap 1 — Cloud ML never auto-runs after batch sync

- [x] **1a.** Add `_run_cloud_ml_on_batch()` background task in `app/api/vital_signs.py`  
  — called at end of `POST /vitals/batch-sync`  
  — calls `predict_risk()` per batch item using patient's `age`, `baseline_hr`, `max_safe_hr`  
  — stores results as `RiskAssessment(generated_by="cloud_ml", assessment_type="batch_cloud")`  
  — creates alert if cloud ML level is `high` or `critical`

### Gap 2 — Critical edge alerts don't push immediately

- [x] **2a.** Add `POST /vitals/critical-alert` endpoint in `app/api/vital_signs.py`  
  — stores single vital record  
  — immediately creates alert (skips 5-min dedup window for critical severity)  
  — runs synchronous cloud ML re-analysis and stores result  
  — responds in < 500 ms so SSE picks it up within the next 1-s poll

- [x] **2b.** Add `pushCriticalAlertNow()` method to `CloudSyncService` (Dart)  
  — calls `POST /vitals/critical-alert` directly  
  — does not touch the queue  
  — returns true/false so caller can fall back to queue on failure

- [x] **2c.** In `CloudSyncService.queuePrediction()`, detect `risk_level == "high"` or `"critical"`  
  — call `pushCriticalAlertNow()` immediately  
  — still queue the item normally so batch-sync also has the record

### Gap 3 — No anomaly / trend detection on batch data

- [x] **3a.** Add `_detect_batch_anomalies()` background task in `app/api/vital_signs.py`  
  — called at end of `POST /vitals/batch-sync` (parallel with cloud ML task)  
  — computes patient's 7-day personal baseline (avg HR, avg SpO2) from DB  
  — flags batch avg HR > 20 % above personal baseline → creates `elevated_hr_trend` warning alert  
  — flags SpO2 downward trend across batch (first-half avg vs second-half avg > 2 pp drop) → creates `spo2_declining` warning alert  
  — flags 3+ consecutive readings with HR > 160 → creates `sustained_high_hr` warning alert  
  — deduplicated with a 30-min window (not 5-min) to avoid spamming on long batches

---

## Implementation Order

1. ~~Gap 2a → backend endpoint (unblocks immediate push)~~ ✓
2. ~~Gap 2b + 2c → mobile wiring (uses 2a)~~ ✓
3. ~~Gap 1a → cloud ML background task on batch (uses existing `predict_risk`)~~ ✓
4. ~~Gap 3a → anomaly/trend detection on batch (last, lowest risk)~~ ✓

---

## All gaps closed. Files changed:

| File | Change |
|------|--------|
| `app/api/vital_signs.py` | Added `_run_cloud_ml_on_batch()`, `_detect_batch_anomalies()`, `POST /vitals/critical-alert`; wired background tasks into `POST /vitals/batch-sync`; **bug fix**: added `EdgeBatchItem` to schema imports (was causing `NameError` at startup) |
| `mobile-app/lib/services/cloud_sync_service.dart` | Added `pushCriticalAlertNow()`; updated `queuePrediction()` to fire it on high/critical risk |
| `tests/test_vital_signs.py` | Added `TestCriticalAlert` class — 5 tests covering success, DB record creation, missing HR, invalid HR, and no-auth |

---

## Post-implementation audit notes

### Bug fixed
- `EdgeBatchItem` was missing from `from app.schemas.vital_signs import (...)` in `vital_signs.py`. FastAPI evaluates type annotations at module load, so this would have raised `NameError` on server startup and prevented the endpoint from registering.

### Mock pipeline trace (verified working)
```
MockVitalsService (emergency scenario, HR 181-200)
  → _edgeAiStore.processVitals()   [edge_ai_store.dart:266]
  → _syncService.queuePrediction() [edge_ai_store.dart:266]
  → if riskLevel == 'high'/'critical':
      → pushCriticalAlertNow()     [cloud_sync_service.dart:150]
      → POST /vitals/critical-alert [backend]
      → alert written synchronously → SSE stream in ≤1 s
```
The emergency mock scenario correctly exercises the full new pipeline end-to-end.

### Mock data inventory

| Location | Type | Status |
|----------|------|--------|
| `mobile-app/lib/services/mock_vitals_service.dart` | 4 physiological scenarios (rest/workout/sleep/emergency) with Gaussian noise, 90-tick cycles, all 3 alert thresholds | Production-quality dev tool — correctly wired to EdgeAiStore + CloudSyncService |
| `mobile-app/lib/screens/profile_screen.dart` | Dropdown to select mock scenario | Wired to `MockVitalsService.setScenario()` |
| `design files/ClinicalDashboard.jsx` | `mockPatientData`, `mockAlerts`, `mockTrendData` — static arrays | Design/prototype file only, NOT used in production `DashboardPage.tsx` |
| `web-dashboard/src/pages/DashboardPage.tsx` | No mock data — reads from SSE + REST API | Production-ready |
| `tests/test_vital_signs.py` | Inline test payloads | Correct — now includes `TestCriticalAlert` |
