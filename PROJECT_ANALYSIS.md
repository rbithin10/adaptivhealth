# AdaptivHealth — CSIT321 Project Analysis

## Executive Summary

AdaptivHealth is a medical-grade cardiovascular health monitoring platform with
three components: a **FastAPI backend**, a **React web dashboard**, and a
**Flutter mobile app**. The project demonstrates strong software engineering
fundamentals including HIPAA-compliant architecture, role-based access control,
ML-powered risk prediction, and a well-structured codebase with clear
separation of concerns.

---

## Grading Assessment (CSIT321 Criteria)

| Category | Score | Notes |
|---|---|---|
| **Architecture & Design** | 9/10 | Excellent 3-tier architecture (API ↔ Dashboard ↔ Mobile). Separate auth credentials table for HIPAA. ML integration is well-structured. |
| **Backend Implementation** | 8/10 | 10 API endpoints, JWT auth, RBAC, alert system, ML prediction. Several critical bugs found and fixed (see below). |
| **Frontend (React)** | 7/10 | 4 pages with professional design system. Uses mock data instead of real API calls. Missing charts integration. |
| **Mobile App (Flutter)** | 6/10 | 4 screens with theming. Navigation and state management incomplete. No real API integration. |
| **Database Design** | 9/10 | 7 well-normalised tables. Proper foreign keys, indexes, and relationship modelling. |
| **Security** | 8/10 | JWT + PBKDF2 + AES-256-GCM + account lockout. Several vulnerabilities found and fixed. |
| **Testing** | 4/10 | No test suite existed before this review. 32 tests added covering auth, users, and vital signs. |
| **Documentation** | 9/10 | Excellent README, ROADMAP, and inline comments. API documentation via Swagger. |
| **ML Integration** | 8/10 | Random Forest classifier (96.9% accuracy). Feature engineering pipeline. Model files included. |
| **Code Quality** | 7/10 | Clean structure and docstrings. Some bugs found in queries and field references. |
| **Overall** | **75/100** | Strong MVP with professional architecture. Main gaps: testing, frontend integration, and a few critical bugs. |

---

## Bugs Found & Fixed

### Critical Bugs

1. **Password Reset Crash** (`app/api/auth.py`)
   - `timedelta` was not imported at module level, only inside `authenticate_user`.
     The `request_password_reset` endpoint used `timedelta(hours=1)` without an
     import in scope, causing a `NameError` at runtime.
   - **Fix:** Added `timedelta` to the top-level `from datetime import` statement.

2. **Wrong Field Name in Password Reset** (`app/api/auth.py:470`)
   - `auth_cred.account_locked_until = None` referenced a non-existent field.
     The correct field is `locked_until` (defined in `AuthCredential` model).
   - **Fix:** Changed to `auth_cred.locked_until = None`.

3. **Broken User Queries — `User.id` Property** (7 occurrences)
   - `User.id` is a Python `@property` alias for `user_id`, not a SQLAlchemy
     column. Using it in `db.query(User).filter(User.id == x)` silently fails
     because Python evaluates `property_object == x` as `False` at class level.
   - **Affected endpoints:** `get_user`, `update_user`, `deactivate_user`,
     `get_user_medical_history`, `get_user_latest_vitals`,
     `get_user_vitals_summary`, `get_user_vitals_history`.
   - **Fix:** Changed all 7 occurrences to `User.user_id == user_id`.

4. **Admin Create User Crash** (`app/api/user.py`)
   - `User(hashed_password=...)` passed a column that doesn't exist on the `User`
     model (passwords are stored in the separate `AuthCredential` table).
   - **Fix:** Changed to create `User` and `AuthCredential` separately, matching
     the pattern used by the register endpoint.

5. **Missing `max_heart_rate` Setter** (`app/models/user.py`)
   - `max_heart_rate` was a read-only `@property`. The `update_my_profile`
     endpoint called `current_user.max_heart_rate = ...` which raised
     `AttributeError`.
   - **Fix:** Added `@max_heart_rate.setter` to write to `max_safe_hr`.

### Security Fixes

6. **Privilege Escalation via `setattr()`** (`app/api/user.py`)
   - Both `update_my_profile` and admin `update_user` iterated over all
     user-submitted fields and set them with `setattr()`. An attacker could
     include `"role": "admin"` or `"is_active": true` in the request body to
     escalate privileges.
   - **Fix:** Added a whitelist of allowed fields: `{"name", "age", "gender", "phone"}`.

7. **Weak PBKDF2 Rounds** (`app/services/auth_service.py`)
   - Used 200,000 rounds while OWASP recommends ≥ 600,000 for PBKDF2-SHA256.
   - **Fix:** Increased to 600,000 rounds.

---

## Existing Strengths

### Architecture
- **Clean 3-tier separation**: API → Database → Frontend
- **HIPAA-compliant data isolation**: Auth credentials in separate table from PHI
- **Background task processing**: Alert checks run asynchronously
- **Dependency injection**: FastAPI's `Depends()` used consistently

### Security
- NIST-approved PBKDF2-SHA256 password hashing
- JWT access + refresh token pattern
- AES-256-GCM encryption for medical data
- Account lockout after failed login attempts
- CORS and TrustedHost middleware
- SQL injection prevention via SQLAlchemy ORM
- Consistent use of generic error messages (prevents user enumeration on login)

### Code Quality
- Comprehensive docstrings on all endpoints
- Consistent file structure and naming
- Pydantic validation on all API inputs
- Proper HTTP status codes and error handling

### Documentation
- 440+ line README with architecture diagrams, API docs, and setup guide
- Development ROADMAP tracking completion
- Inline code comments explaining design decisions

---

## Remaining Improvements (Priority Order)

### Priority 1 — Testing & CI/CD
- [x] Add pytest test suite (32 tests added)
- [x] Add GitHub Actions CI workflow
- [ ] Add test coverage reporting (target: 80%+)
- [ ] Add frontend tests (React Testing Library, Flutter widget tests)

### Priority 2 — Frontend Integration
- [ ] Replace mock data in React dashboard with real API calls
- [ ] Implement Recharts data visualisation (currently placeholder text)
- [ ] Complete Flutter navigation with go_router
- [ ] Add Flutter state management with Provider
- [ ] Connect Flutter app to backend API

### Priority 3 — Security Hardening
- [ ] Add rate limiting middleware (e.g., `slowapi`)
- [ ] Implement CSRF protection for web dashboard
- [ ] Move JWT storage from localStorage to HttpOnly cookies
- [ ] Add input sanitisation for medical history notes
- [ ] Implement caregiver-patient assignment table (currently all caregivers access all patients)

### Priority 4 — Production Readiness
- [ ] Add Alembic database migrations
- [ ] Implement email service for password reset
- [ ] Add WebSocket support for real-time alerts
- [ ] Add API response pagination on all list endpoints
- [ ] Configure Celery background task workers
- [ ] Add Dockerfile for containerised deployment
- [ ] Add health check for ML model availability
- [ ] Add structured logging with structlog

### Priority 5 — Code Quality
- [ ] Replace deprecated Pydantic `class Config` with `ConfigDict`
- [ ] Replace `model.dict()` with `model.model_dump()`
- [ ] Add type hints to all service methods
- [ ] Extract reusable React components (Header, VitalCard, AlertBanner)
- [ ] Add API error response standardisation

---

## Test Coverage Summary

| Module | Tests | Status |
|---|---|---|
| `AuthService` (password hashing, JWT) | 5 | ✅ All pass |
| `AuthCredential` (lockout logic) | 4 | ✅ All pass |
| Registration endpoint | 3 | ✅ All pass |
| Login endpoint | 3 | ✅ All pass |
| Protected endpoints | 2 | ✅ All pass |
| User profile (GET/PUT) | 3 | ✅ All pass |
| Admin user management | 4 | ✅ All pass |
| Vital signs submission | 5 | ✅ All pass |
| Vital signs retrieval | 2 | ✅ All pass |
| Auth denied | 1 | ✅ All pass |
| **Total** | **32** | **32/32 passing** |

---

## How to Run Tests

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest httpx

# Run tests
SECRET_KEY="your-secret-key-min-32-chars" \
PHI_ENCRYPTION_KEY="dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE=" \
DEBUG=true \
python -m pytest tests/ -v
```

---

## Conclusion

AdaptivHealth demonstrates solid software engineering for a CSIT321 project. The
architecture is well-designed, the codebase is clean, and the documentation is
excellent. The main areas for improvement are: (1) testing coverage, (2) frontend
API integration, and (3) a few critical bugs that were discovered and fixed during
this review. With the fixes applied and 32 tests added, the project is in a
significantly stronger position for both grading and future development.
