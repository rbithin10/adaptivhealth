# tests/ — Automated Test Suite

All automated tests for the Python backend. The suite is organized by feature area, with focused unit-style files plus one backend integration suite.

## How to Run

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run a specific test file
pytest tests/test_auth.py
```

## Test Files

| File | What It Tests |
|------|-------------|
| `conftest.py` | Shared test setup — creates a test database, test client, and sample users |
| `helpers.py` | Reusable helper functions for tests (e.g. create a logged-in user) |
| `test_activity.py` | Activity logging and retrieval endpoints |
| `test_advanced_ml.py` | Advanced ML insights — risk timelines, feature importance |
| `test_alerts.py` | Clinical alert creation, deduplication, and statistics |
| `test_auth.py` | Registration, login flows, token refresh, password reset, and password hashing |
| `test_database.py` | Database connection, table creation, session handling |
| `test_integration.py` | Full backend integration workflow against a running server |
| `test_exercise_library.py` | Exercise library data and lookup |
| `test_food_analysis.py` | Food photo upload and AI nutritional analysis |
| `test_main.py` | App startup, health check, CORS configuration |
| `test_medical_history.py` | Patient medical history and medication self-service endpoints |
| `test_medication_reminders.py` | Medication reminder scheduling and adherence tracking |
| `test_messages.py` | Messaging threads, inbox, read receipts, and compatibility routes |
| `test_models.py` | SQLAlchemy model creation and relationships |
| `test_nl.py` | Natural-language summaries, chat, and image-chat endpoints |
| `test_nutrition.py` | Nutrition logging and daily summaries |
| `test_predict.py` | Risk prediction endpoints, helper functions, and assessment workflows |
| `test_rbac_consent.py` | Role-based access control and consent management |
| `test_rehab.py` | Rehab programme creation, phase management, progress |
| `test_schemas.py` | Pydantic schema validation — valid and invalid inputs |
| `test_services.py` | Service-layer unit tests — ML, encryption, email, etc. |
| `test_users.py` | User profile viewing, admin management, and clinician assignment |
| `test_vital_signs.py` | Vital signs recording and retrieval |

## Structure Notes

- Files are named after product areas rather than coverage targets.
- One integration file is kept for full backend flow validation.
- Coverage-chasing files and one-off line-target tests should stay out of this folder.
