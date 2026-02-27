# Natural Language AI Coach API

## Overview

Four FastAPI endpoints that provide patient-friendly natural-language summaries for the AI coach feature. All endpoints follow the same pattern: accept query parameters, return structured data + `nl_summary` text field.

**Base path**: `/api/v1/nl`

---

## Endpoints

### 1. Risk Summary
**GET** `/api/v1/nl/risk-summary`

Returns encouraging, patient-safe risk assessment summary.

**Query Parameters:**
- `user_id` (UUID, required) - User identifier
- `time_window_hours` (int, optional, default=24) - Time window for analysis

**Response:** `RiskSummaryResponse`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "time_window_hours": 24,
  "risk_level": "LOW",
  "risk_score": 0.23,
  "key_factors": {
    "avg_heart_rate": 72,
    "max_heart_rate": 95,
    "avg_spo2": 98,
    "alert_count": 0
  },
  "safety_status": "SAFE",
  "nl_summary": "Over the past 24 hours, your health readings look stable and within safe ranges. Your average heart rate was 72 BPM (peak: 95 BPM), and oxygen levels averaged 98%. No alerts were triggered, which is great. You're okay for light to moderate activities, just listen to your body."
}
```

---

### 2. Today's Workout
**GET** `/api/v1/nl/todays-workout`

Returns encouraging workout recommendation with safety guidance.

**Query Parameters:**
- `user_id` (UUID, required) - User identifier
- `date` (date, optional, default=today) - Target date

**Response:** `TodaysWorkoutResponse`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2026-02-21",
  "activity_type": "WALKING",
  "intensity_level": "LIGHT",
  "duration_minutes": 20,
  "target_hr_min": 85,
  "target_hr_max": 110,
  "risk_level": "LOW",
  "nl_summary": "Today's recommendation: Try a light walk for 20 minutes at a comfortable, easy pace. Aim to keep your heart rate between 85-110 BPM during the activity. If you feel any discomfort, chest pain, or severe breathlessness, stop and rest. Otherwise, enjoy your workout!"
}
```

---

### 3. Alert Explanation
**GET** `/api/v1/nl/alert-explanation`

Returns calm, clear explanation of health alert with recommended action.

**Query Parameters:**
- `user_id` (UUID, required) - User identifier
- `alert_id` (UUID, optional) - Specific alert ID (defaults to latest)

**Response:** `AlertExplanationResponse`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "alert_id": "123e4567-e89b-12d3-a456-426614174000",
  "alert_type": "HIGH_HEART_RATE",
  "severity_level": "MEDIUM",
  "alert_time": "2026-02-21T14:30:00Z",
  "context": {
    "during_activity": true,
    "activity_type": "walking",
    "heart_rate": 145,
    "spo2": 97
  },
  "recommended_action": "SLOW_DOWN",
  "nl_summary": "At 02:30 PM, your heart rate reached 145 BPM during walking. This requires attention—it's outside your typical safe range. Slow down the pace—ease up on intensity and see if your readings stabilize."
}
```

**Recommended Actions:**
- `CONTINUE` - Safe to continue activity
- `SLOW_DOWN` - Reduce intensity
- `STOP_AND_REST` - Stop and rest 10-15 minutes
- `CONTACT_DOCTOR` - Contact care team
- `EMERGENCY` - Seek immediate medical attention

---

### 4. Progress Summary
**GET** `/api/v1/nl/progress-summary`

Returns motivational progress summary comparing current and previous periods.

**Query Parameters:**
- `user_id` (UUID, required) - User identifier
- `range` (string, optional, default="7d") - Time range ("7d" or "30d")

**Response:** `ProgressSummaryResponse`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "range": "7d",
  "current_period": {
    "start": "2026-02-14T00:00:00Z",
    "end": "2026-02-21T00:00:00Z",
    "workout_count": 5,
    "total_active_minutes": 110,
    "avg_risk_level": "LOW",
    "time_in_safe_zone_minutes": 95,
    "time_above_safe_zone_minutes": 15,
    "alert_count": 1
  },
  "previous_period": {
    "start": "2026-02-07T00:00:00Z",
    "end": "2026-02-14T00:00:00Z",
    "workout_count": 3,
    "total_active_minutes": 75,
    "avg_risk_level": "LOW",
    "time_in_safe_zone_minutes": 65,
    "time_above_safe_zone_minutes": 10,
    "alert_count": 2
  },
  "trend": {
    "workout_frequency": "IMPROVING",
    "alerts": "IMPROVING",
    "risk": "STABLE",
    "overall": "IMPROVING"
  },
  "nl_summary": "Over the past 7 days, you completed 5 workouts totaling 110 active minutes. That's 2 more workouts than the previous period and 1 fewer alert. Excellent progress! Your consistency is paying off. Keep up the great work—try to maintain at least this many sessions going forward."
}
```

**Trend Values:**
- `IMPROVING` - Metrics getting better
- `STABLE` - Metrics consistent
- `WORSENING` - Metrics declining (caring, non-blaming tone)

---

## Implementation Details

### Architecture
- **Schemas**: `app/schemas/nl.py` - Pydantic models for requests/responses
- **Builders**: `app/services/nl_builders.py` - NL text generation functions
- **Routes**: `app/api/nl_endpoints.py` - FastAPI endpoint handlers
- **Tests**: `tests/test_nl_endpoints.py` - Unit tests for builders

### Current State
All endpoints use **dummy data** and are ready for database integration. Each route has a `TODO` comment marking where to add real DB queries:

```python
# TODO: Real DB query
# risk_assessment = db.query(RiskAssessment).filter(...).first()
# vitals = db.query(VitalSignRecord).filter(...).all()
```

### Tone Guidelines
- **Risk Summary**: Encouraging, not scary
- **Workout**: Motivational with safety cues
- **Alert**: Calm and clear, only urgent for EMERGENCY actions
- **Progress**: 
  - IMPROVING: Supportive and proud
  - STABLE: Calm and encouraging
  - WORSENING: Caring and cautious, no blame

### Integration with Mobile App
The mobile app's `FloatingChatbot` currently calls `GET /api/v1/risk-summary/natural-language` (from `advanced_ml.py`). Consider migrating to use these new NL endpoints for richer functionality:

```dart
// Current: getRiskSummaryNL() → /api/v1/risk-summary/natural-language
// Future: Can expand to use /api/v1/nl/* endpoints for different contexts
```

---

## Testing

Run tests:
```bash
pytest tests/test_nl_endpoints.py -v
```

Test coverage:
- ✅ Route registration
- ✅ Risk summary builder
- ✅ Workout builder
- ✅ Alert explanation builder
- ✅ Progress summary builder
- ✅ Trend computation logic

---

## Next Steps

1. **Database Integration**: Replace dummy data with real queries:
   - `RiskAssessment` - Latest risk for user
   - `VitalSignRecord` - Aggregate vitals in time window
   - `ExerciseRecommendation` - Active recommendation for date
   - `Alert` - Latest or specific alert by ID
   - `ActivitySession` - Aggregate sessions in period

2. **Authentication**: Add `Depends(get_current_user)` to ensure users can only access their own data

3. **Mobile Integration**: Update `FloatingChatbot` to use new endpoints for richer responses

4. **A/B Testing**: Track which NL summaries lead to better engagement/outcomes

5. **LLM Enhancement**: Consider replacing rule-based builders with LLM generation (GPT-4, Claude, etc.) for more natural language
