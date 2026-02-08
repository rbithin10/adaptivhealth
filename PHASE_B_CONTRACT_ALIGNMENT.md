# Phase B: Contract Alignment Documentation

## Overview

Phase B ensures that the mobile app (Flutter), web dashboard (React/TypeScript), and backend API (FastAPI) have synchronized endpoint paths, request/response schemas, and authentication patterns.

## Backend API Structure

**Base URL:** `http://api.adaptivhealth.com/api/v1`

All endpoints are prefixed with `/api/v1` for API versioning.

## Authentication

### Token-Based (Bearer Authentication)

All authenticated endpoints require an `Authorization` header:
```
Authorization: Bearer {access_token}
```

### Token Flow

1. **Login** → `POST /login` with username/password (OAuth2 password grant)
2. **Response** → Receive `access_token` and `token_type: "bearer"`
3. **Storage** → Clients store token securely:
   - **Mobile:** `flutter_secure_storage` plugin
   - **Web:** `localStorage` with secure flags
4. **Expiration** → Both clients refresh tokens before expiration
5. **Logout** → Clear token from storage

### 401 Unauthorized Response

If API returns 401:
- **Mobile:** `AiApi` raises exception, `AiStore` catches and navigates to login
- **Web:** `ApiService` interceptor clears token and redirects to `/login`

## Endpoint Categories

### 1. Health Checks (Public, No Auth Required)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic API health check |
| `/health/db` | GET | Database connectivity check |

**Response Example** (`/health`):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": 1707422400
}
```

---

### 2. Authentication

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/login` | POST | No | Submit email/password credential |
| `/register` | POST | No | Create new user account |
| `/refresh` | POST | Yes | Refresh access token |
| `/logout` | POST | Yes | Logout and invalidate token |

**POST /login - Request:**
```
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePass123
```

**POST /login - Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**POST /register - Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "age": 35,
  "gender": "male",
  "phone": "+1234567890"
}
```

---

### 3. User Management

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/users/me` | GET | Yes | Get current user profile |
| `/users/me` | PUT | Yes | Update current user profile |
| `/users/me/medical-history` | PUT | Yes | Update medical history (encrypted) |
| `/users` | GET | Yes* | List all users (admin/clinician) |
| `/users/{user_id}` | GET | Yes* | Get specific user (admin/clinician) |

**GET /users/me - Response:**
```json
{
  "user_id": 42,
  "email": "user@example.com",
  "full_name": "John Doe",
  "age": 35,
  "gender": "male",
  "phone": "+1234567890",
  "baseline_hr": 68,
  "max_safe_hr": 185,
  "is_active": true,
  "is_verified": true,
  "user_role": "patient",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-02-08T14:22:00Z"
}
```

**PUT /users/me - Request:**
```json
{
  "full_name": "John Doe Updated",
  "age": 36,
  "gender": "male",
  "phone": "+1234567890"
}
```

**Note:** Field whitelist enforced on backend; only `full_name`, `age`, `gender`, `phone` can be updated.

---

### 4. Vital Signs

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/vitals` | POST | Yes | Submit new vital sign reading |
| `/vitals/latest` | GET | Yes | Get user's most recent vital reading |
| `/vitals/history` | GET | Yes | Get paginated vital sign history |
| `/vitals/summary` | GET | Yes | Get daily/period summary |

**POST /vitals - Request:**
```json
{
  "heart_rate": 72,
  "spo2": 98,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "hrv": 45.2,
  "source_device": "Fitbit Charge 6",
  "device_id": "FITBIT_ABC123",
  "timestamp": "2024-02-08T14:22:00Z"
}
```

**GET /vitals/latest - Response:**
```json
{
  "id": 1024,
  "user_id": 42,
  "heart_rate": 72,
  "spo2": 98,
  "blood_pressure": {
    "systolic": 120,
    "diastolic": 80
  },
  "hrv": 45.2,
  "source_device": "Fitbit Charge 6",
  "is_valid": true,
  "confidence_score": 0.94,
  "timestamp": "2024-02-08T14:22:00Z",
  "created_at": "2024-02-08T14:22:30Z"
}
```

**GET /vitals/history - Response:**
```json
{
  "vitals": [
    { "id": 1024, "heart_rate": 72, ... },
    { "id": 1023, "heart_rate": 70, ... }
  ],
  "summary": {
    "date": "2024-02-08",
    "avg_heart_rate": 71.5,
    "min_heart_rate": 68,
    "max_heart_rate": 78,
    "avg_spo2": 97.8,
    "total_readings": 15,
    "valid_readings": 15,
    "alerts_triggered": 0
  },
  "total": 142,
  "page": 1,
  "per_page": 50
}
```

---

### 5. Risk Assessment (AI Core)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/risk-assessments/compute` | POST | Yes | Compute risk for current user using latest vitals |
| `/risk-assessments/latest` | GET | Yes | Get user's latest risk assessment |
| `/predict/risk` | POST | Yes | Predict risk from explicit metrics |
| `/predict/status` | GET | No | Check if ML model is loaded |

**POST /risk-assessments/compute - Response:**
```json
{
  "assessment_id": 512,
  "user_id": 42,
  "risk_score": 0.3456,
  "risk_level": "moderate",
  "confidence": 0.92,
  "inference_time_ms": 45.3,
  "drivers": [
    "Heart rate elevated 10 BPM above baseline",
    "Recovery efficiency below optimal",
    "Session duration moderate"
  ],
  "based_on": {
    "age": 35,
    "baseline_hr": 68,
    "avg_heart_rate": 78,
    "peak_heart_rate": 115,
    "avg_spo2": 97,
    "duration_minutes": 45,
    "hr_pct_of_max": 0.62,
    "activity_intensity": 2
  }
}
```

**GET /risk-assessments/latest - Response:**
```json
{
  "assessment_id": 512,
  "user_id": 42,
  "risk_level": "moderate",
  "risk_score": 0.3456,
  "confidence": 0.92,
  "inference_time_ms": 45.3,
  "alert_triggered": false,
  "created_at": "2024-02-08T14:22:00Z"
}
```

---

### 6. Recommendations

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/recommendations/latest` | GET | Yes | Get latest recommendation |
| `/recommendations` | GET | Yes | List paginated recommendations |
| `/recommendations/{id}` | GET | Yes | Get specific recommendation |
| `/recommendations/{id}` | PATCH | Yes | Update recommendation (mark complete, etc.) |

**GET /recommendations/latest - Response:**
```json
{
  "recommendation_id": 127,
  "user_id": 42,
  "title": "Moderate Intensity Walking",
  "suggested_activity": "walking",
  "intensity_level": "moderate",
  "duration_minutes": 30,
  "target_heart_rate_min": 100,
  "target_heart_rate_max": 130,
  "description": "Walk at steady pace for cardiovascular benefit",
  "warnings": "Stop immediately if chest pain or dizziness occurs",
  "status": "pending",
  "is_completed": false,
  "confidence_score": 0.89,
  "created_at": "2024-02-08T14:22:00Z",
  "valid_until": "2024-02-09T14:22:00Z"
}
```

**PATCH /recommendations/{id} - Request:**
```json
{
  "is_completed": true,
  "user_feedback": "Felt good, completed as recommended"
}
```

---

### 7. Alerts

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/alerts` | GET | Yes | List paginated alerts |
| `/alerts/stats` | GET | Yes | Get alert statistics (count by severity, type) |
| `/alerts/{id}/acknowledge` | PATCH | Yes | Mark alert as acknowledged |
| `/alerts/{id}/resolve` | PATCH | Yes | Mark alert as resolved |

**GET /alerts - Response:**
```json
{
  "alerts": [
    {
      "alert_id": 89,
      "user_id": 42,
      "alert_type": "high_heart_rate",
      "severity": "warning",
      "title": "High Heart Rate",
      "message": "Heart rate exceeded 140 BPM",
      "acknowledged": false,
      "created_at": "2024-02-08T14:25:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 50
}
```

**GET /alerts/stats - Response:**
```json
{
  "total": 42,
  "by_severity": {
    "info": 5,
    "warning": 25,
    "critical": 10,
    "emergency": 2
  },
  "by_type": {
    "high_heart_rate": 15,
    "low_spo2": 8,
    "irregular_rhythm": 12,
    "other": 7
  },
  "unacknowledged_count": 18
}
```

**Deduplication:** Alerts with same type/user within 5 minutes are deduplicated (only latest stored).

---

### 8. Activities

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/activities/start` | POST | Yes | Start new activity session |
| `/activities/end/{session_id}` | POST | Yes | End activity session |
| `/activities` | GET | Yes | List paginated activity sessions |
| `/activities/{session_id}` | GET | Yes | Get specific activity details |
| `/activities/{session_id}` | PATCH | Yes | Update activity metrics |

**POST /activities/start - Request:**
```json
{
  "activity_type": "walking"
}
```

**POST /activities/start - Response:**
```json
{
  "session_id": 256,
  "user_id": 42,
  "activity_type": "walking",
  "start_time": "2024-02-08T14:30:00Z",
  "status": "active",
  "created_at": "2024-02-08T14:30:00Z"
}
```

**POST /activities/end/{session_id} - Response:**
```json
{
  "session_id": 256,
  "user_id": 42,
  "activity_type": "walking",
  "start_time": "2024-02-08T14:30:00Z",
  "end_time": "2024-02-08T15:00:00Z",
  "duration_minutes": 30,
  "status": "completed"
}
```

**PATCH /activities/{session_id} - Request:**
```json
{
  "avg_heart_rate": 95,
  "peak_heart_rate": 125,
  "min_heart_rate": 85,
  "calories_burned": 150,
  "feeling_after": "energized",
  "user_notes": "Great workout, felt strong"
}
```

---

## Error Handling

All endpoints follow consistent error response format:

**400 Bad Request (Validation Error):**
```json
{
  "error": {
    "code": 400,
    "message": "Validation error",
    "type": "validation_error",
    "details": "heart_rate must be between 30 and 250"
  }
}
```

**401 Unauthorized:**
```json
{
  "error": {
    "code": 401,
    "message": "Invalid credentials or token expired",
    "type": "unauthorized"
  }
}
```

**403 Forbidden:**
```json
{
  "error": {
    "code": 403,
    "message": "Insufficient permissions",
    "type": "forbidden"
  }
}
```

**404 Not Found:**
```json
{
  "error": {
    "code": 404,
    "message": "Resource not found",
    "type": "not_found"
  }
}
```

**500 Server Error:**
```json
{
  "error": {
    "code": 500,
    "message": "Internal server error",
    "type": "server_error"
  }
}
```

---

## Client Implementation Guides

### Flutter Mobile App

**Setup:**
```dart
// main_with_ai.dart
final apiClient = ApiClient(
  tokenStorage: tokenStorage,
  baseUrl: 'http://YOUR_BACKEND_IP:8000/api/v1',
);
final aiApi = AiApi(apiClient.dio);
```

**Example: Compute Risk Assessment**
```dart
try {
  final response = await aiApi.computeMyRiskAssessment();
  final riskScore = response['risk_score'];
  final riskLevel = response['risk_level'];
  final drivers = List<String>.from(response['drivers'] ?? []);
  
  // Update UI with results
  print('Risk Level: $riskLevel ($riskScore)');
  print('Drivers: $drivers');
} on DioException catch (e) {
  if (e.response?.statusCode == 401) {
    // Handle token expired - navigate to login
  } else {
    // Handle other errors
    print('Error: ${e.message}');
  }
}
```

### Web Dashboard (React/TypeScript)

**Setup:**
```typescript
// services/api.ts
const api = new ApiService();
// Uses localStorage for token, auto-refreshes on 401

// In any React component:
import { api } from '../services/api';

const MyComponent = () => {
  const [risk, setRisk] = useState<RiskAssessmentComputeResponse | null>(null);
  
  const computeRisk = async () => {
    try {
      const response = await api.computeRiskAssessment();
      setRisk(response);
    } catch (error) {
      // ApiService interceptor handles 401 and redirects to /login
      console.error('Error:', error);
    }
  };
  
  return <button onClick={computeRisk}>Compute Risk</button>;
};
```

---

## Testing Contracts

### Manual Testing Checklist

- [ ] Login endpoint returns valid token
- [ ] Token persists across app restart (mobile)
- [ ] 401 redirect to login works on both clients
- [ ] Compute risk assessment returns drivers list
- [ ] Vitals history pagination works
- [ ] Alert deduplication prevents duplicates
- [ ] Activity start/end correctly calculates duration
- [ ] Recommendation status updates persist
- [ ] User profile update enforces whitelist

### Example cURL Commands

```bash
# Login
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePass123"

# Get current user (with token)
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Compute risk assessment
curl -X POST http://localhost:8000/api/v1/risk-assessments/compute \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get vitals history with pagination
curl -X GET "http://localhost:8000/api/v1/vitals/history?page=1&per_page=50" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Summary

Phase B ensures:
- ✅ Unified endpoint paths across mobile and web
- ✅ TypeScript interfaces match Pydantic backend schemas
- ✅ Authentication tokens flow correctly through middleware
- ✅ Error responses are consistent and informative
- ✅ Pagination works uniformly across all list endpoints
- ✅ Field validation enforced on backend (no direct model assignment)

Next phase: Production deployment and monitoring.
