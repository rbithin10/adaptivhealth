# Adaptiv Health - Backend API Specifications
## Missing Endpoints & Complete Integration Guide

---

## Overview

This document specifies the **new backend endpoints** required to support the complete Adaptiv Health app. The existing core endpoints (vitals, alerts, activities, and risk/recommendations) are already implemented under `/api/v1`. This focuses on **Nutrition** and **Messaging** modules.

---

## 1. Nutrition API Endpoints

**Status note (current backend):** Nutrition logging is implemented via `/api/v1/nutrition`, `/api/v1/nutrition/recent`, and `/api/v1/nutrition/{entry_id}`. The recommendations endpoint below is **planned/TODO** and not yet implemented.

### 1.1 Get Daily Nutrition Recommendations

**Endpoint:** `GET /nutrition/recommendations`

**Purpose:** Get personalized meal suggestions based on user's cardiovascular status, recovery phase, and health goals.

**Request:**
```python
GET /nutrition/recommendations?user_id={user_id}&date={YYYY-MM-DD}&include_recipes=true

# Example:
GET /nutrition/recommendations?user_id=user123&date=2026-02-15&include_recipes=true
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | Patient ID |
| date | string | No | Date in YYYY-MM-DD format (defaults to today) |
| include_recipes | boolean | No | Include detailed recipe data (default: false) |

**Response (200 OK):**
```json
{
  "date": "2026-02-15",
  "user_id": "user123",
  "daily_nutrition_goals": {
    "calories_target": 2000,
    "potassium_mg": 3500,
    "water_liters": 2.5,
    "fiber_grams": 25,
    "protein_grams": 75
  },
  "meal_restrictions": [
    "saturated_fats",
    "processed_foods"
  ],
  "assigned_nutritionist": {
    "id": "doc456",
    "name": "Dr. Amanda White",
    "email": "a.white@adaptihealth.com",
    "phone": "+1-555-0156"
  },
  "meals": [
    {
      "meal_type": "breakfast",
      "meal_id": "meal_b1",
      "suggested_items": [
        "oatmeal",
        "berries",
        "low-fat yogurt",
        "honey"
      ],
      "portion_sizes": {
        "oatmeal": "1/2 cup dry",
        "berries": "1 cup mixed",
        "yogurt": "6 oz",
        "honey": "1 tbsp"
      },
      "nutritional_info": {
        "calories": 320,
        "potassium_mg": 450,
        "protein_grams": 12,
        "fiber_grams": 8,
        "saturated_fat_grams": 1.5
      },
      "benefits": "High fiber, omega-3 rich, supports heart health",
      "cardiovascular_notes": "Berries contain antioxidants beneficial for blood vessel health",
      "recipe_id": "recipe_001",
      "prep_time_minutes": 5,
      "difficulty": "easy",
      "instructions": [
        "Cook oatmeal according to package directions",
        "Top with fresh berries",
        "Add yogurt on the side",
        "Drizzle with honey"
      ]
    },
    {
      "meal_type": "lunch",
      "meal_id": "meal_l1",
      "suggested_items": [
        "grilled chicken breast",
        "brown rice",
        "steamed broccoli",
        "olive oil"
      ],
      "portion_sizes": {
        "chicken": "4 oz",
        "rice": "1 cup cooked",
        "broccoli": "2 cups",
        "olive_oil": "1 tbsp"
      },
      "nutritional_info": {
        "calories": 520,
        "potassium_mg": 650,
        "protein_grams": 35,
        "fiber_grams": 5,
        "saturated_fat_grams": 2
      },
      "benefits": "Lean protein, whole grains, rich in vitamins",
      "cardiovascular_notes": "Minimally processed preparation supports blood pressure management",
      "recipe_id": "recipe_002",
      "prep_time_minutes": 20,
      "difficulty": "easy"
    },
    {
      "meal_type": "snack",
      "meal_id": "meal_s1",
      "suggested_items": ["almonds", "apple"],
      "portion_sizes": {
        "almonds": "1 oz (23 nuts)",
        "apple": "1 medium"
      },
      "nutritional_info": {
        "calories": 180,
        "potassium_mg": 195,
        "protein_grams": 6,
        "fiber_grams": 4,
        "saturated_fat_grams": 1
      },
      "benefits": "Healthy fats, natural sugars, sustained energy"
    },
    {
      "meal_type": "dinner",
      "meal_id": "meal_d1",
      "suggested_items": [
        "baked salmon",
        "sweet potato",
        "asparagus"
      ],
      "portion_sizes": {
        "salmon": "5 oz",
        "sweet_potato": "1 medium",
        "asparagus": "1 cup"
      },
      "nutritional_info": {
        "calories": 480,
        "potassium_mg": 800,
        "protein_grams": 32,
        "fiber_grams": 6,
        "saturated_fat_grams": 1.5
      },
      "benefits": "Omega-3 rich, supports cardiovascular health",
      "cardiovascular_notes": "Salmon omega-3s promote healthy heart function and reduce inflammation"
    }
  ],
  "daily_summary": {
    "total_calories": 1500,
    "total_potassium_mg": 2095,
    "total_protein_grams": 85,
    "total_fiber_grams": 23,
    "total_saturated_fat_grams": 6
  },
  "status_vs_goals": {
    "potassium": "60% of recommended daily intake",
    "water": "Track throughout the day (2.5 liters goal)",
    "notes": "Excellent for cardiovascular recovery. Focus on hydration."
  },
  "nutritionist_note": "Based on your moderate risk level yesterday, I've focused on anti-inflammatory foods. Continue hydration protocol.",
  "confidence_score": 0.88,
  "last_updated": "2026-02-15T08:00:00Z"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid date format. Use YYYY-MM-DD",
  "status": 400
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "User not found",
  "status": 404
}
```

---

### 1.2 Log Meal Consumption

**Endpoint:** `POST /nutrition/logs`

**Purpose:** Record a meal eaten by the user. Used to track actual consumption vs. recommendations.

**Request:**
```python
POST /nutrition/logs
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "user_id": "user123",
  "meal_type": "breakfast",
  "meal_id": "meal_b1",  # From recommendations endpoint
  "items": [
    {
      "food_name": "oatmeal",
      "portion": "0.5 cup dry",
      "calories": 150
    },
    {
      "food_name": "berries",
      "portion": "1 cup mixed",
      "calories": 85
    }
  ],
  "total_calories": 235,
  "timestamp": "2026-02-15T08:30:00Z",
  "notes": "Prepared as suggested, tasty!",
  "satisfaction_rating": 8  # 1-10 scale
}
```

**Response (201 Created):**
```json
{
  "log_id": "log_b1_20260215",
  "user_id": "user123",
  "meal_type": "breakfast",
  "timestamp": "2026-02-15T08:30:00Z",
  "total_calories": 235,
  "adherence_to_recommendation": 0.95,  # How well it matched suggestion
  "feedback": "Excellent choice! High fiber and nutrient-dense.",
  "status": "logged"
}
```

---

### 1.3 Get Nutrition Progress

**Endpoint:** `GET /nutrition/progress`

**Purpose:** Get user's nutrition tracking summary for a date range.

**Request:**
```python
GET /nutrition/progress?user_id={user_id}&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}

# Example: Last 7 days
GET /nutrition/progress?user_id=user123&start_date=2026-02-08&end_date=2026-02-15
```

**Response:**
```json
{
  "period": {
    "start_date": "2026-02-08",
    "end_date": "2026-02-15",
    "days_tracked": 8
  },
  "daily_summaries": [
    {
      "date": "2026-02-15",
      "meals_logged": 4,
      "total_calories": 1500,
      "adherence_score": 0.92,
      "notes": "Good day, followed recommendations"
    },
    {
      "date": "2026-02-14",
      "meals_logged": 3,
      "total_calories": 1450,
      "adherence_score": 0.85,
      "notes": "Slightly heavy dinner portions"
    }
  ],
  "weekly_average": {
    "calories_per_day": 1500,
    "adherence_to_recommendations": 0.89,
    "consistency": "Good - 6/7 days logged"
  },
  "trends": {
    "calorie_trend": "Stable",
    "recommendation_adherence": "Improving"
  },
  "goals_status": {
    "hydration": "Below target (avg 1.8L/day, goal 2.5L)",
    "recommendation": "Increase water intake by 700ml daily"
  }
}
```

---

## 2. Messaging API Endpoints

**Status note (current backend):** Messaging is implemented via REST polling with the following endpoints:
- `GET /api/v1/messages/thread/{other_user_id}`
- `POST /api/v1/messages`
- `POST /api/v1/messages/{message_id}/read`

The `/messaging/conversations` and WebSocket endpoints below are **planned/TODO** and not yet implemented.

### 2.1 Get Care Team Conversations

**Endpoint:** `GET /messaging/conversations`

**Purpose:** List all active messaging conversations between patient and care team members.

**Request:**
```python
GET /messaging/conversations?user_id={user_id}&include_unread=true

# Example:
GET /messaging/conversations?user_id=user123&include_unread=true
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | Patient ID |
| include_unread | boolean | No | Include unread count (default: true) |

**Response (200 OK):**
```json
{
  "user_id": "user123",
  "conversations": [
    {
      "conversation_id": "conv_123",
      "clinician": {
        "id": "doc_001",
        "name": "Dr. Emily Rodriguez",
        "role": "Cardiologist",
        "email": "e.rodriguez@adaptihealth.com",
        "phone": "+1-555-0100",
        "photo_url": "https://api.adaptihealth.com/photos/doc_001.jpg",
        "availability": {
          "status": "available",  # available | busy | offline
          "last_seen": "2026-02-15T14:30:00Z",
          "response_time_average_hours": 0.5
        }
      },
      "last_message": {
        "message_id": "msg_456",
        "sender_id": "doc_001",
        "content": "Continue with light cardio 2-3x per week. Monitor your heart rate.",
        "timestamp": "2026-02-15T10:30:00Z",
        "type": "text"
      },
      "unread_count": 1,
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-02-15T10:30:00Z",
      "pinned": false
    },
    {
      "conversation_id": "conv_124",
      "clinician": {
        "id": "doc_002",
        "name": "Lisa Chang",
        "role": "Cardiac Nurse",
        "email": "l.chang@adaptihealth.com",
        "phone": "+1-555-0101",
        "availability": {
          "status": "busy",
          "last_seen": "2026-02-15T12:00:00Z",
          "response_time_average_hours": 1.5
        }
      },
      "last_message": {
        "message_id": "msg_457",
        "sender_id": "user123",
        "content": "I had chest discomfort during my walk yesterday. Should I be worried?",
        "timestamp": "2026-02-14T15:00:00Z",
        "type": "text"
      },
      "unread_count": 0,
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2026-02-14T15:00:00Z",
      "pinned": false
    },
    {
      "conversation_id": "conv_125",
      "clinician": {
        "id": "doc_003",
        "name": "Dr. Amanda White",
        "role": "Nutritionist",
        "email": "a.white@adaptihealth.com",
        "phone": "+1-555-0102",
        "availability": {
          "status": "offline",
          "last_seen": "2026-02-14T17:00:00Z",
          "response_time_average_hours": 4
        }
      },
      "last_message": {
        "message_id": "msg_458",
        "sender_id": "doc_003",
        "content": "Focus on minimally processed foods and balanced meals. Stay hydrated.",
        "timestamp": "2026-02-13T11:00:00Z",
        "type": "text"
      },
      "unread_count": 0,
      "created_at": "2025-11-01T12:00:00Z",
      "updated_at": "2026-02-13T11:00:00Z",
      "pinned": false
    }
  ],
  "total_conversations": 3,
  "total_unread": 1
}
```

---

### 2.2 Get Conversation Messages

**Endpoint:** `GET /messaging/conversations/{conversation_id}/messages`

**Purpose:** Retrieve message history for a specific conversation with a clinician.

**Request:**
```python
GET /messaging/conversations/{conversation_id}/messages?limit=50&offset=0

# Example:
GET /messaging/conversations/conv_123/messages?limit=50&offset=0
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| conversation_id | string | Yes | Conversation ID (in path) |
| limit | int | No | Messages to retrieve (default: 50, max: 100) |
| offset | int | No | Pagination offset (default: 0) |

**Response (200 OK):**
```json
{
  "conversation_id": "conv_123",
  "clinician": {
    "id": "doc_001",
    "name": "Dr. Emily Rodriguez",
    "role": "Cardiologist"
  },
  "messages": [
    {
      "message_id": "msg_450",
      "sender": {
        "id": "user123",
        "type": "patient",
        "name": "Sarah Patient"
      },
      "content": "I completed the walking session you recommended. Heart rate stayed in the target zone the entire time!",
      "timestamp": "2026-02-15T14:00:00Z",
      "type": "text",
      "read_by_recipient": true,
      "read_at": "2026-02-15T14:15:00Z"
    },
    {
      "message_id": "msg_451",
      "sender": {
        "id": "doc_001",
        "type": "clinician",
        "name": "Dr. Emily Rodriguez"
      },
      "content": "Excellent work! This shows great progress in your cardiovascular recovery. Keep maintaining this pace.",
      "timestamp": "2026-02-15T14:30:00Z",
      "type": "text",
      "read_by_recipient": true,
      "read_at": "2026-02-15T14:32:00Z"
    },
    {
      "message_id": "msg_452",
      "sender": {
        "id": "user123",
        "type": "patient",
        "name": "Sarah Patient"
      },
      "content": "Should I increase the intensity next week?",
      "timestamp": "2026-02-15T14:35:00Z",
      "type": "text",
      "attachments": [
        {
          "attachment_id": "att_001",
          "type": "session_summary",
          "name": "Walking_Session_Feb15.pdf",
          "url": "https://api.adaptihealth.com/attachments/att_001"
        }
      ],
      "read_by_recipient": true,
      "read_at": "2026-02-15T14:37:00Z"
    },
    {
      "message_id": "msg_453",
      "sender": {
        "id": "doc_001",
        "type": "clinician",
        "name": "Dr. Emily Rodriguez"
      },
      "content": "You can gradually increase intensity. Look for activities in the 'Moderate' range starting next week. I'll update your recommendations.",
      "timestamp": "2026-02-15T14:50:00Z",
      "type": "text",
      "read_by_recipient": true,
      "read_at": "2026-02-15T14:52:00Z"
    }
  ],
  "pagination": {
    "total_messages": 47,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

### 2.3 Send Message

**Endpoint:** `POST /messaging/conversations/{conversation_id}/messages`

**Purpose:** Send a new message to a clinician in a conversation.

**Request:**
```python
POST /messaging/conversations/conv_123/messages
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "user_id": "user123",
  "content": "I experienced some chest tightness during my workout today. Should I reduce intensity?",
  "type": "text",
  "attachments": [
    {
      "type": "session_summary",
      "session_id": "sess_789"
    }
  ]
}
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | Patient ID |
| content | string | Yes | Message text (max 2000 chars) |
| type | enum | Yes | "text" - primary message type |
| attachments | array | No | Session summaries, vital reports |
| schedule_send | datetime | No | Send at specific time |

**Response (201 Created):**
```json
{
  "message_id": "msg_999",
  "conversation_id": "conv_123",
  "sender": {
    "id": "user123",
    "type": "patient"
  },
  "content": "I experienced some chest tightness during my workout today.",
  "timestamp": "2026-02-15T15:00:00Z",
  "type": "text",
  "read_by_recipient": false,
  "status": "sent",
  "attachments": [
    {
      "attachment_id": "att_002",
      "type": "session_summary",
      "name": "Workout_Feb15_Session.json",
      "url": "https://api.adaptihealth.com/attachments/att_002"
    }
  ]
}
```

---

### 2.4 Mark Messages as Read

**Endpoint:** `PUT /messaging/conversations/{conversation_id}/read`

**Purpose:** Mark all messages in a conversation as read.

**Request:**
```python
PUT /messaging/conversations/conv_123/read
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "user_id": "user123"
}
```

**Response (200 OK):**
```json
{
  "conversation_id": "conv_123",
  "messages_marked_read": 5,
  "read_at": "2026-02-15T15:05:00Z"
}
```

---

### 2.5 WebSocket Real-Time Messaging (Optional but Recommended)

**Endpoint:** `WS /messaging/stream`

**Purpose:** Establish a WebSocket connection for real-time message delivery and presence awareness.

**Connection:**
```python
# Connect
WS ws://api.adaptihealth.com/messaging/stream?user_id=user123&token={jwt_token}

# Receive new message notification
{
  "type": "new_message",
  "message": {
    "message_id": "msg_999",
    "conversation_id": "conv_123",
    "sender": {
      "id": "doc_001",
      "name": "Dr. Emily Rodriguez"
    },
    "content": "Great progress! Let's schedule a follow-up call.",
    "timestamp": "2026-02-15T15:30:00Z"
  }
}

# Receive typing indicator
{
  "type": "typing",
  "conversation_id": "conv_123",
  "user_id": "doc_001",
  "user_name": "Dr. Emily Rodriguez"
}

# Receive presence update
{
  "type": "presence_update",
  "user_id": "doc_001",
  "status": "online"  # online | away | offline
}
```

**Client to Server (Send):**
```python
# Send message via WebSocket
{
  "action": "send_message",
  "conversation_id": "conv_123",
  "content": "Thank you for the advice",
  "type": "text"
}

# Indicate user is typing
{
  "action": "typing",
  "conversation_id": "conv_123"
}
```

---

## 3. Integration with Existing Endpoints

### Data Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  Existing Endpoints (Working)               │
├─────────────────────────────────────────────────────────────┤
│ GET /api/v1/vitals/latest                                   │
│ GET /api/v1/risk-assessments/latest                          │
│ GET /api/v1/alerts                                          │
│ GET /api/v1/activities                                      │
│ POST /api/v1/activities/start                               │
│ GET /api/v1/recommendations/latest                          │
│ GET /api/v1/anomaly-detection                               │
│ GET /api/v1/trend-forecast                                  │
│ POST /api/v1/alerts/natural-language                        │
│ GET /api/v1/risk-summary/natural-language                   │
│ POST /api/v1/predict/explain                                │
│ GET /api/v1/users/me                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               NEW Endpoints (To Implement)                  │
├─────────────────────────────────────────────────────────────┤
│ GET /nutrition/recommendations        ← NEW PRIORITY 1     │
│ POST /nutrition/logs                  ← NEW PRIORITY 1     │
│ GET /nutrition/progress               ← NEW PRIORITY 2     │
│                                                             │
│ GET /messaging/conversations          ← NEW PRIORITY 1     │
│ GET /messaging/conversations/{id}/... ← NEW PRIORITY 1     │
│ POST /messaging/conversations/{id}/.. ← NEW PRIORITY 1     │
│ WS /messaging/stream                  ← NEW PRIORITY 2     │
└─────────────────────────────────────────────────────────────┘
```

**Deprecated legacy paths (do not use):**
- `GET /vital-signs` → use `/api/v1/vitals/history` or `/api/v1/vitals/latest`
- `GET /risk-assessment` → use `/api/v1/risk-assessments/latest`
- `GET /recommendations` → use `/api/v1/recommendations/latest`
- `GET /activity-sessions` / `POST /activity-sessions` → use `/api/v1/activities` and `/api/v1/activities/start`
- `GET /user/profile` → use `/api/v1/users/me`

### Current FastAPI Routes (Authoritative, /api/v1)

#### Auth
- `POST /register` — Admin-only create user. Body: `email`, `name`, `password`, `role`, optional `age`, `gender`, `phone`. Response: `UserResponse`.
- `POST /login` — OAuth2 form: `username`, `password`. Response: `TokenResponse` (`access_token`, `refresh_token`, `token_type`, `expires_in`, `user`).
- `POST /refresh` — Body: `refresh_token`. Response: `TokenResponse`.
- `GET /me` — Current user (`UserResponse`).
- `POST /reset-password` — Body: `email`. Response: `{message}`.
- `POST /reset-password/confirm` — Body: `token`, `new_password`. Response: `{message}`.

#### Users (`/users`)
- `GET /users/me` — `UserProfileResponse` (includes `baseline_heart_rate`, `max_heart_rate`, `heart_rate_zones`).
- `PUT /users/me` — Body: `name`, `age`, `gender`, `phone`. Response: `UserResponse`.
- `PUT /users/me/medical-history` — Body: `conditions`, `medications`, `allergies`, `surgeries`, `notes`. Response: `{message}`.
- `GET /users` — Query: `page`, `per_page`, optional `role`, `search`. Response: `UserListResponse`.
- `GET /users/{user_id}` — `UserResponse`.
- `PUT /users/{user_id}` — Body: `UserUpdate`. Response: `{message, user}`.
- `POST /users` — Body: `UserCreateAdmin` (`email`, `name`, `password`, `role`, `is_active`, `is_verified`, optional demographics). Response: `{message, user}`.
- `DELETE /users/{user_id}` — Response: `{message}`.
- `POST /users/{user_id}/reset-password` — Body: `new_password`. Response: `{message}`.
- `GET /users/{user_id}/medical-history` — Response: `{medical_history}` or `{message}`.

#### Vital Signs
- `POST /vitals` — Body: `heart_rate`, optional `spo2`, `blood_pressure_systolic`, `blood_pressure_diastolic`, `hrv`, `source_device`, `device_id`, `timestamp`. Response: `VitalSignResponse`.
- `POST /vitals/batch` — Body: `{vitals: VitalSignCreate[]}`. Response: `{message, records_created}`.
- `GET /vitals/latest` — `VitalSignResponse`.
- `GET /vitals/summary` — Query: `days`. Response: `VitalSignsSummary` (avg/min/max HR, avg/min SpO2, avg HRV, total readings, alerts).
- `GET /vitals/history` — Query: `days`, `page`, `per_page`. Response: `VitalSignsHistoryResponse` (vitals + summary).
- `GET /vitals/user/{user_id}/latest` — `VitalSignResponse`.
- `GET /vitals/user/{user_id}/summary` — `VitalSignsSummary`.
- `GET /vitals/user/{user_id}/history` — `VitalSignsHistoryResponse`.

#### Activities
- `POST /activities/start` — Body: `start_time`, optional `end_time`, `activity_type`, HR metrics, `duration_minutes`, `calories_burned`, `recovery_time_minutes`, `feeling_before`, `user_notes`. Response: `ActivitySessionResponse`.
- `POST /activities/end/{session_id}` — Body: `ActivitySessionUpdate` (end metrics, `status`, notes). Response: `ActivitySessionResponse`.
- `GET /activities` — Query: `limit`, `offset`, optional `activity_type`. Response: `ActivitySessionResponse[]`.
- `GET /activities/{session_id}` — `ActivitySessionResponse`.
- `GET /activities/user/{user_id}` — Query: `limit`, `offset`. Response: `ActivitySessionResponse[]`.

#### Alerts
- `GET /alerts` — Query: `page`, `per_page`, optional `acknowledged`, `severity`. Response: `AlertListResponse`.
- `PATCH /alerts/{alert_id}/acknowledge` — Response: `AlertResponse`.
- `PATCH /alerts/{alert_id}/resolve` — Body: `AlertUpdate` (`acknowledged`, `resolved_at`, `resolved_by`, `resolution_notes`). Response: `AlertResponse`.
- `POST /alerts` — Body: `AlertCreate` (`user_id`, `alert_type`, `severity`, `message`, optional metadata). Response: `AlertResponse`.
- `GET /alerts/user/{user_id}` — Query: `page`, `per_page`. Response: `AlertListResponse`.
- `GET /alerts/stats` — Query: `days`. Response: `{period_days, severity_breakdown, unacknowledged_count, generated_at}`.

#### Predict / Risk
- `GET /predict/status` — ML model status (`status`, `model_loaded`, `features_count`).
- `POST /predict/risk` — Body: `age`, `baseline_hr`, `max_safe_hr`, `avg_heart_rate`, `peak_heart_rate`, `min_heart_rate`, `avg_spo2`, `duration_minutes`, `recovery_time_minutes`, optional `activity_type`. Response: `RiskPredictionResponse`.
- `GET /predict/user/{user_id}/risk` — Response: `{user_id, user_name, session_id, session_date, prediction{risk_score,risk_level,high_risk,confidence,recommendation}, inference_time_ms}`.
- `GET /predict/my-risk` — Response: `{user_id, user_name, assessment_count, risk_assessments[]}`.
- `POST /risk-assessments/compute` — Response: `RiskAssessmentComputeResponse` (`risk_score`, `risk_level`, `drivers`, `based_on`).
- `POST /patients/{user_id}/risk-assessments/compute` — Response: `RiskAssessmentComputeResponse`.
- `GET /risk-assessments/latest` — Latest assessment summary with `drivers`.
- `GET /patients/{user_id}/risk-assessments/latest` — Latest assessment summary (clinician view).
- `GET /recommendations/latest` — Latest recommendation (single object).
- `GET /patients/{user_id}/recommendations/latest` — Latest recommendation (clinician view).

**Planned/TODO (not implemented yet):** list-all and by-id endpoints for risk assessments and recommendations.

#### Consent / Data Sharing
- `GET /consent/status` — `ConsentStatusResponse` (`share_state`, `requested_at`, `reviewed_at`, `decision`, `reason`).
- `POST /consent/disable` — Body: `{reason?}`. Response: `{message}`.
- `POST /consent/enable` — Response: `{message}`.
- `GET /consent/pending` — Response: `{pending_requests: [{user_id,email,full_name,requested_at,reason}]}`.
- `POST /consent/{patient_id}/review` — Body: `{decision, reason?}`. Response: `{message}`.

#### Nutrition
- `POST /nutrition` — Body: `meal_type`, `description?`, `calories`, `protein_grams?`, `carbs_grams?`, `fat_grams?`. Response: `NutritionResponse`.
- `GET /nutrition/recent` — Query: `limit`. Response: `NutritionListResponse`.
- `DELETE /nutrition/{entry_id}` — Response: 204 No Content.

#### Messages
- `GET /messages/thread/{other_user_id}` — Query: `limit`. Response: `MessageResponse[]`.
- `POST /messages` — Body: `receiver_id`, `content`. Response: `MessageResponse`.
- `POST /messages/{message_id}/read` — Response: `MessageResponse`.

#### AI Coach (Natural Language)
- `GET /nl/risk-summary` — `RiskSummaryResponse`.
- `GET /nl/todays-workout` — `TodaysWorkoutResponse`.
- `GET /nl/alert-explanation` — `AlertExplanationResponse`.
- `GET /nl/progress-summary` — `ProgressSummaryResponse`.

#### Advanced ML
- `GET /anomaly-detection` — Query: `hours`, `z_threshold`.
- `GET /trend-forecast` — Query: `days`, `forecast_days`.
- `GET /baseline-optimization` — Query: `days`.
- `POST /baseline-optimization/apply` — Apply computed baseline.
- `GET /recommendation-ranking` — Query: `risk_level`, optional `variant`.
- `POST /recommendation-ranking/outcome` — Body: `experiment_id`, `variant`, `outcome`, `outcome_value?`.
- `POST /alerts/natural-language` — Body: `alert_type`, `severity`, optional trigger/threshold + risk fields.
- `GET /risk-summary/natural-language` — Plain-language risk summary.
- `GET /model/retraining-status` — Retraining status metadata.
- `GET /model/retraining-readiness` — Retraining readiness summary.
- `POST /predict/explain` — Body: same fields as `/predict/risk`.

### Risk Assessment & Exercise Recommendation (Current Behavior)

**Current endpoints are latest-only:**
- `GET /risk-assessments/latest` (current user)
- `GET /patients/{id}/risk-assessments/latest` (clinician view)
- `GET /recommendations/latest` (current user)
- `GET /patients/{id}/recommendations/latest` (clinician view)

**Planned/TODO (not implemented yet):**
- List-all and by-id endpoints for risk assessments and recommendations.

**Frontend note:** the React dashboard wraps `latest` responses in a singleton array for list-shaped UI components.

### Recommended Implementation Order

**Week 1:** Nutrition Core
- [ ] `GET /nutrition/recommendations`
- [ ] `POST /nutrition/logs`

**Week 2:** Messaging Core
- [ ] `GET /messaging/conversations`
- [ ] `GET /messaging/conversations/{id}/messages`
- [ ] `POST /messaging/conversations/{id}/messages`

**Week 3:** Enhancements
- [ ] `GET /nutrition/progress`
- [ ] `PUT /messaging/conversations/{id}/read`
- [ ] `WS /messaging/stream` (WebSocket)

---

## 4. Error Handling

All endpoints should return consistent error responses:

```json
// 400 Bad Request
{
  "error": "Invalid request",
  "details": {
    "field": "date",
    "message": "Date must be in YYYY-MM-DD format"
  },
  "status": 400,
  "timestamp": "2026-02-15T15:00:00Z"
}

// 401 Unauthorized
{
  "error": "Authentication required",
  "message": "Invalid or expired token",
  "status": 401,
  "timestamp": "2026-02-15T15:00:00Z"
}

// 403 Forbidden
{
  "error": "Access denied",
  "message": "You don't have permission to access this conversation",
  "status": 403,
  "timestamp": "2026-02-15T15:00:00Z"
}

// 404 Not Found
{
  "error": "Resource not found",
  "message": "Conversation conv_999 does not exist",
  "status": 404,
  "timestamp": "2026-02-15T15:00:00Z"
}

// 429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "retry_after_seconds": 60,
  "status": 429,
  "timestamp": "2026-02-15T15:00:00Z"
}

// 500 Internal Server Error
{
  "error": "Internal server error",
  "request_id": "req_12345",
  "status": 500,
  "timestamp": "2026-02-15T15:00:00Z"
}
```

---

## 5. Authentication & Security

### Headers Required
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
X-Request-ID: {unique_id}
```

### Data Security for Nutrition Endpoints
- All food/meal data is non-PHI (not Protected Health Information)
- User preferences stored encrypted
- Nutritionist assignments encrypted
- Recommendations cached locally after retrieval

### Data Security for Messaging Endpoints
- Messages encrypted end-to-end (recommended)
- Message history encrypted at rest
- Conversation metadata encrypted
- WebSocket connection over WSS (WebSocket Secure)

---

## 6. Rate Limits

```
Nutrition Endpoints:
- GET /nutrition/recommendations: 100 req/hour per user
- POST /nutrition/logs: 50 req/hour per user
- GET /nutrition/progress: 30 req/hour per user

Messaging Endpoints:
- GET /messaging/conversations: 100 req/hour per user
- GET /messaging/.../messages: 200 req/hour per user
- POST /messaging/.../messages: 100 req/hour per user
- WS /messaging/stream: 1 connection per user (no limit on messages)
```

---

## 7. Testing Checklist

### Nutrition API Testing
- [ ] GET /nutrition/recommendations returns valid meal data
- [ ] POST /nutrition/logs correctly records meals
- [ ] Potassium recommendations increase during cardiac recovery
- [ ] Nutritionist assignments properly linked
- [ ] Offline data caching works for recommendations
- [ ] Meal logging works without internet, syncs on reconnect

### Messaging API Testing
- [ ] GET /messaging/conversations lists all active chats
- [ ] Unread counts accurate
- [ ] Message history loads correctly
- [ ] POST /messaging creates message with timestamp
- [ ] Messages marked as read correctly
- [ ] Attachments (session summaries) attach properly
- [ ] WebSocket connects and receives real-time updates
- [ ] Presence updates work correctly
- [ ] Typing indicators appear/disappear properly
- [ ] Rate limits enforced
- [ ] Old messages can be retrieved (pagination)

---

## 8. Frontend Integration Example (Flutter)

```dart
// Example: Get nutrition recommendations
import 'package:dio/dio.dart';

class NutritionService {
  final Dio _dio;
  
  Future<NutritionResponse> getDailyRecommendations({
    required String userId,
    DateTime? date,
    bool includeRecipes = false,
  }) async {
    try {
      final response = await _dio.get(
        '/nutrition/recommendations',
        queryParameters: {
          'user_id': userId,
          'date': date?.toString().split(' ')[0], // YYYY-MM-DD
          'include_recipes': includeRecipes,
        },
        options: Options(
          headers: {'Authorization': 'Bearer $_token'},
        ),
      );
      
      return NutritionResponse.fromJson(response.data);
    } catch (e) {
      throw NutritionException('Failed to fetch recommendations: $e');
    }
  }
}

// Example: Send message to clinician
class MessagingService {
  final Dio _dio;
  
  Future<Message> sendMessage({
    required String conversationId,
    required String content,
    List<Attachment>? attachments,
  }) async {
    try {
      final response = await _dio.post(
        '/messaging/conversations/$conversationId/messages',
        data: {
          'user_id': _userId,
          'content': content,
          'type': 'text',
          if (attachments != null)
            'attachments': attachments.map((a) => a.toJson()).toList(),
        },
        options: Options(
          headers: {'Authorization': 'Bearer $_token'},
        ),
      );
      
      return Message.fromJson(response.data);
    } catch (e) {
      throw MessagingException('Failed to send message: $e');
    }
  }
}
```

---

**Document Version:** 1.0
**Created:** February 15, 2026
**Status:** Ready for Backend Implementation
**Priority:** CRITICAL for Production Release

---

## Next Steps for Backend Team

1. **Nutrition API (Week 1)**
   - Design database schema for meals/recipes
   - Implement ML-based meal recommendation engine
   - Create nutritionist assignment logic
   - Build logging system with adherence tracking

2. **Messaging API (Week 2)**
   - Implement conversation management
   - Set up message encryption
   - Build clinician availability logic
   - Optional: WebSocket server setup

3. **Testing & Deployment (Week 3)**
   - Unit tests for all endpoints
   - Integration tests with mobile app
   - Load testing (rate limits)
   - Security audit (PHI handling)
   - Staging deployment
   - Production deployment

