# Backend Loose Ends Checklist

Last updated: 2026-03-03

## Done

- [x] Fix schema exports in `app/schemas/__init__.py`
  - Removed/avoided ghost export mismatch (`VitalSignListResponse`)
  - Added missing exports for nutrition recommendation/log schemas
  - Added missing exports for inbox, rehab, medical history, medication reminders, food analysis, NL schemas
- [x] Fix router exports in `app/api/__init__.py`
  - Added missing router exports for NL, medical history, medication reminder, rehab, food analysis
- [x] Move edge sync request schemas to `app/schemas/vital_signs.py`
  - `EdgeBatchItem` and `EdgeBatchSyncRequest` now live in schema layer and are imported by vitals API
- [x] Implement compatibility endpoint `POST /api/v1/nutrition/logs`
- [x] Add/confirm tests for:
  - Food analysis endpoints
  - Messages inbox endpoint
  - NL chat endpoints
  - Nutrition logs endpoint
  - Medical history API endpoint coverage file exists
- [x] Add compatibility messaging conversation endpoints (spec-aligned wrappers)
  - `GET /api/v1/messaging/conversations`
  - `GET /api/v1/messaging/conversations/{conversation_id}/messages`
  - `POST /api/v1/messaging/conversations/{conversation_id}/messages`
  - `PUT /api/v1/messaging/conversations/{conversation_id}/read`
- [x] Implement `GET /api/v1/nutrition/progress` (date-range progress summary)
- [x] Add tests for the new compatibility wrappers and progress endpoint
  - Added conversation compatibility endpoint tests in `tests/test_messages.py`
  - Added progress endpoint tests in `tests/test_nutrition.py`
- [x] Validate changed backend files for diagnostics errors
  - Checked `app/api/messages.py`, `app/api/nutrition.py`, `tests/test_messages.py`, `tests/test_nutrition.py`

## Remaining

- [ ] Run targeted backend tests for changed files with `pytest`
  - `pytest tests/test_messages.py -q`
  - `pytest tests/test_nutrition.py -q`

## Working On Now

- [ ] Waiting for manual `pytest` execution in local terminal (tooling here cannot execute terminal commands)
