# Adaptiv Health Patient App - Implementation Roadmap

## Overview
Transform the current build from bulky card layouts into a professional, compact fitness app (Zepp/SnapFitness style) with all essential backend integrations.

---

## Phase 1: UI/UX Redesign (Foundation)
**Timeline: Week 1-2 | Priority: CRITICAL**

### Goals:
- Replace oversized card blocks with compact, information-dense layouts
- Implement modern design system (spacing, typography, colors)
- Prepare component structure for all backend data types

### Key Changes:

#### Home Screen Redesign
- **Current Issue:** Giant HR display takes half the screen
- **New Approach:** 
  - Compact vital signs grid (4 cards: HR, SpO2, BP, HRV)
  - Each card shows current value + mini trend line
  - Color-coded status (green/yellow/red based on risk_level)
  - Quick action buttons below vitals

#### Navigation Structure
- Replace simple bottom nav with tab-based system:
  - **Home** - Vitals & status
  - **Fitness** - Plans, sessions, recommendations
  - **Recovery** - Post-workout insights, breathing exercises
  - **Health** - Chatbot, messages, resources
  - **Profile** - User settings, data sharing

#### Design System Reference Points
- **Zepp App:** Minimalist cards, color-coded zones, metric grids
- **SnapFitness:** Compact summaries, action-focused UI, progress rings
- **Adaptiv Requirements:** Medical alert styling, HIPAA-compliant aesthetics

---

## Phase 2: Fitness Plans & Suggestions Module
**Timeline: Week 2-3 | Backend Integration: /recommendations endpoint**

### What Backend Provides:
```
- title: "Light Walking Session"
- suggested_activity: "walking"
- intensity_level: "low" | "moderate" | "high"
- duration_minutes: 30
- target_heart_rate_min: 92
- target_heart_rate_max: 120
- description: "Detailed guidance"
- warnings: "Safety notes"
- confidence_score: 0.95
- is_completed: boolean
```

### Implementation:

#### New Screen: "Fitness Plans"
1. **Today's Recommended Workout**
   - Card showing today's AI recommendation
   - Activity type with icon
   - Duration & target HR zone
   - "Start Session" button

2. **This Week's Plan**
   - 7-day view with suggested activities
   - Completed activities checked off
   - Ability to swap/reschedule activities

3. **Personalized Suggestions**
   - Based on:
     - risk_score from ML model
     - recovery_score from last session
     - activity_phase (resting/active/recovering)
   - Display multiple options with intensity levels
   - Show confidence scores (transparent AI)

#### Integration Points:
```python
# Fetch recommendations based on user state
GET /recommendations?user_id={id}&days=7&include_forecast=true

# Recommendation ranking (A/B tested best variants)
GET /recommendation-ranking?session_history={recent_sessions}

# Post completion
POST /activity-sessions
{
  activity_type: "walking",
  avg_heart_rate: 105,
  peak_heart_rate: 120,
  duration_minutes: 28,
  feeling_before: "Good",
  feeling_after: "Refreshed"
}
```

#### UI Components:
- **WorkoutCard** - Compact display of single recommendation
- **TargetZoneIndicator** - Visual HR zone (green/yellow/red)
- **CompletionToggle** - Mark workout as done
- **ConfidenceScore** - Small badge showing ML confidence

---

## Phase 3: Diet & Nutrition Module
**Timeline: Week 3-4 | Backend Integration: New endpoint needed**

### Current Gap:
Backend doesn't have dedicated nutrition endpoint yet. Needs implementation:

```python
# Proposed endpoint (coordinate with backend team)
GET /nutrition/recommendations?user_id={id}&date={date}
{
  meals: [
    {
      meal_type: "breakfast|lunch|dinner|snack",
      suggested_items: ["oatmeal", "berries", "yogurt"],
      calories_target: 500,
      suggested_recipes: [...],
      benefits: "Heart-healthy",
      nutritionist_notes: "Based on your recovery phase"
    }
  ],
  daily_nutrition_goals: {
    calories: 2000,
    potassium_mg: 3500,
    water_liters: 2.5
  },
   restrictions: ["saturated_fats"],
  assigned_nutritionist: "Dr. Amanda White"
}
```

### Implementation:

#### New Screen: "Nutrition"
1. **Daily Nutrition Summary**
   - Progress rings: Calories, Water intake
   - Status indicators (on track/caution/over limit)

2. **Meal Suggestions**
   - Breakfast/Lunch/Dinner/Snacks
   - Recipe cards with:
     - Ingredients list
     - Prep time
     - Nutritional info
     - Heart-health benefits

3. **Nutrition Log**
   - Quick add buttons for common foods
   - Nutritional calculation
   - Daily total tracking

4. **Contact Nutritionist**
   - Link to messaging with assigned nutritionist
   - View past nutrition advice
   - Schedule nutrition consultation

#### Design Pattern:
- Similar to fitness cards but with food focus
- Color-code macros (proteins/carbs/fats)
- Show alignment with cardiovascular guidelines

---

## Phase 4: AI Health Chatbot
**Timeline: Week 4-5 | Backend Integration: /alerts/natural-language endpoint**

### What Backend Provides:
```
# LLM-generated human-readable alerts
GET /alerts/natural-language?alert_type={type}
Response: "Your heart rate was elevated for 15 minutes during walking. 
This is within safe limits, but consider taking a 5-minute rest break 
next time to optimize recovery."

# Risk summary explanation
GET /risk-summary/natural-language?include_recommendations=true
Response: Plain English risk explanation + next steps

# Model explanation (SHAP feature importance)
GET /predict/explain?session_id={id}
Response: "Your elevated heart rate (92%) and moderate HRV (45%) 
contributed to a moderate risk score today. Continue current activity."
```

### Implementation:

#### New Screen: "Health Coach"
1. **Chat Interface**
   - Patient asks health questions
   - Chatbot provides cardiovascular-specific guidance
   - Uses backend NLP endpoints for responses

2. **Quick Questions**
   - "Should I exercise today?" → Checks risk_score
   - "Why was my alert triggered?" → Uses /predict/explain
   - "What can I do better?" → Combines recommendations + trends

3. **Daily Insights**
   - Morning briefing on:
     - Today's risk level
     - Recommended activities
     - Nutritional focus
   - Evening summary of:
     - Session performance
     - Recovery metrics
     - Tomorrow's forecast

#### System Architecture:
```python
# Patient question
POST /chat/message
{
  user_id: "user123",
  message: "Why was my heart rate so high yesterday?",
  context: {
    latest_session_id: "sess456",
    latest_vital_signs: {...}
  }
}

# Response combines:
# 1. Natural language alert explanation
# 2. Risk factors from predict/explain
# 3. Recommendations for improvement
# 4. Trend context from user history

Response: "Your elevated heart rate yesterday (peak 145 BPM) was 
primarily driven by high activity intensity. However, your recovery 
was good. Today I'd recommend a lighter session to maintain balance."
```

#### UI Components:
- **ChatBubble** - Message display
- **QuickReplyButtons** - Common questions
- **InsightCard** - Formatted health insight
- **MetricContext** - Show relevant vital in explanation

---

## Phase 5: Doctor Direct Messaging
**Timeline: Week 5-6 | Backend Integration: New endpoint needed**

### Current Gap:
Backend has Care Team info but needs messaging endpoint:

```python
# Proposed endpoint (coordinate with backend)
GET /messaging/conversations?user_id={id}
[
  {
    conversation_id: "conv123",
    clinician: {
      name: "Dr. Emily Rodriguez",
      role: "Cardiologist",
      email: "e.rodriguez@adaptihealth.com",
      availability_status: "Available"
    },
    last_message: {...},
    unread_count: 2
  }
]

GET /messaging/conversations/{conversation_id}/messages?limit=50

POST /messaging/send
{
  conversation_id: "conv123",
  message: "I had some chest discomfort during my workout yesterday",
  attachments: ["vital_summary_2024_02_15"]
}

# Real-time updates via WebSocket
WS /messaging/stream?user_id={id}&conversation_id={conv_id}
```

### Implementation:

#### New Screen: "Messages"
1. **Clinician List**
   - All assigned care team members
   - Status indicator (Available/Busy/Offline)
   - Role badges (Cardiologist/Nurse/Nutritionist)
   - Unread message count

2. **Conversation Thread**
   - Message history with care team member
   - Timestamps & read receipts
   - Ability to attach vital sign reports
   - Quick action: Schedule appointment

3. **Message Composition**
   - Rich text editor
   - Attach vital summaries/activity sessions
   - Medical terminology suggestions (non-invasive)
   - Send & schedule options

#### Design Pattern:
- Healthcare messaging standard (clear, professional)
- Distinguish system messages from user/clinician messages
- Highlight urgent/priority messages

---

## Phase 6: Enhanced Recovery Screen
**Timeline: Week 6 | Backend Integration: Activity sessions + trend-forecast**

### Current State:
Basic recovery score display. Enhance with:

#### New Features:
1. **Recovery Quality Metrics**
   - Breathing exercises (from recovery module)
   - HRV recovery trend (graph of HR variability)
   - Sleep quality correlation (if available)

2. **Post-Session Analysis**
   - Session summary from activity_sessions data:
     - Avg/peak/min HR
     - Time in target zone
     - Calories burned
     - Recovery time to baseline

3. **Trend Forecast**
   ```python
   GET /trend-forecast?days=7
   Returns: Predicted vital trends for next 7 days
   Display: Line graphs showing expected HR, HRV, recovery patterns
   ```

4. **Breathing Exercises**
   - Guided breathing routines
   - Interactive animations
   - Post-exercise recovery protocols
   - 2-5 minute sessions

---

## Phase 7: Activity History Enhancement
**Timeline: Week 7 | Backend Integration: Activity sessions list**

### Current State:
"No Activity Yet" placeholder. Implement:

#### Features:
1. **Session History Timeline**
   ```python
   GET /activity-sessions?user_id={id}&days=30
   Returns: List of all completed activities with full metrics
   ```

2. **Session Detail View**
   - Activity type + duration
   - HR graph during session (avg/peak/min)
   - SpO2 during activity
   - Calories burned
   - Recovery metrics
   - Risk score during session
   - User feeling before/after

3. **Statistics Dashboard**
   - This week's activity summary
   - Total time exercised
   - Average intensity
   - Personal records (peak HR, longest session, etc.)

4. **Filter & Search**
   - By activity type
   - By date range
   - By intensity level

---

## Phase 8: Smart Alerts & Notifications
**Timeline: Week 8 | Backend Integration: Alerts endpoint**

### Backend Provides:
```
- alert_type: high_heart_rate | low_spo2 | high_blood_pressure | irregular_rhythm
- severity: info | warning | critical | emergency
- title: "Heart Rate High"
- message: "Your heart rate reached 145 BPM. Consider slowing down."
- action_required: "Reduce intensity" | "Check medication" | etc.
- trigger_value: 145
- threshold_value: 140
- natural_language_explanation: Available via /alerts/natural-language
```

### Implementation:

#### Alert Display Strategy:
1. **In-App Notifications**
   - Real-time banners at top of screen
   - Color-coded by severity
   - Auto-dismiss safe alerts, persistent for critical

2. **Push Notifications**
   - Critical/Emergency alerts immediately
   - Warning alerts within 1 minute
   - Info alerts as daily digest

3. **Alert History**
   - Chronological view of all alerts
   - Mark as reviewed/acknowledged
   - See what action was taken

4. **Smart Context**
   - Alert explanation using natural-language endpoint
   - Suggested next actions
   - When to contact doctor

---

## Data Flow Architecture

```
┌─────────────────────┐
│   Wearable Device   │
│  (HR, SpO2, BP)     │
└──────────┬──────────┘
           │ BLE
           ▼
┌─────────────────────────────────────────────────┐
│        Flutter Mobile App (Patient)             │
├─────────────────────────────────────────────────┤
│ ├─ Home Screen (Vitals Grid)                   │
│ ├─ Fitness Plans (Recommendations)             │
│ ├─ Nutrition (Diet Guidance)                   │
│ ├─ Health Coach (AI Chatbot)                   │
│ ├─ Messages (Doctor Communication)             │
│ ├─ Recovery (Post-Workout Insights)            │
│ ├─ Activity History (Session Logs)             │
│ └─ Alerts & Notifications                      │
└──────────┬──────────────────────────────────────┘
           │ HTTPS REST API
           ▼
┌─────────────────────────────────────────────────┐
│   FastAPI Backend (AWS EC2)                     │
├─────────────────────────────────────────────────┤
│ ├─ /vital-signs (Real-time data)              │
│ ├─ /risk-assessment (ML predictions)          │
│ ├─ /alerts (Alert management)                 │
│ ├─ /activity-sessions (Workout logs)          │
│ ├─ /recommendations (Fitness/Diet plans)      │
│ ├─ /messaging (Doctor communication)          │
│ ├─ /trend-forecast (Future predictions)       │
│ ├─ /anomaly-detection (Unusual patterns)      │
│ └─ /alerts/natural-language (LLM responses)   │
└──────────┬──────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│  AWS RDS (PostgreSQL) + ML Models (TensorFlow) │
│  HIPAA-Encrypted Data Storage                  │
└─────────────────────────────────────────────────┘
```

---

## Component Structure (Flutter)

```
lib/
├── screens/
│   ├── home/
│   │   ├── home_screen.dart
│   │   ├── widgets/vitals_grid.dart
│   │   ├── widgets/risk_card.dart
│   │   └── widgets/status_indicator.dart
│   ├── fitness/
│   │   ├── fitness_plans_screen.dart
│   │   ├── widgets/recommendation_card.dart
│   │   ├── widgets/target_zone_indicator.dart
│   │   └── workout_session_screen.dart
│   ├── nutrition/
│   │   ├── nutrition_screen.dart
│   │   ├── widgets/meal_card.dart
│   │   └── widgets/nutrition_progress.dart
│   ├── health_coach/
│   │   ├── chatbot_screen.dart
│   │   ├── widgets/chat_bubble.dart
│   │   └── widgets/insight_card.dart
│   ├── messages/
│   │   ├── messages_screen.dart
│   │   ├── conversation_screen.dart
│   │   └── widgets/message_thread.dart
│   ├── recovery/
│   │   ├── recovery_screen.dart
│   │   ├── widgets/breathing_exercise.dart
│   │   └── widgets/recovery_metrics.dart
│   ├── history/
│   │   ├── activity_history_screen.dart
│   │   ├── session_detail_screen.dart
│   │   └── widgets/session_card.dart
│   └── profile/
│       ├── profile_screen.dart
│       └── settings_screen.dart
├── models/
│   ├── vital_signs.dart
│   ├── risk_assessment.dart
│   ├── recommendation.dart
│   ├── activity_session.dart
│   ├── alert.dart
│   └── message.dart
├── services/
│   ├── api_service.dart (REST calls)
│   ├── websocket_service.dart (Real-time messaging)
│   ├── local_storage_service.dart (Offline data)
│   └── encryption_service.dart (HIPAA compliance)
├── providers/ (State Management)
│   ├── vital_signs_provider.dart
│   ├── recommendation_provider.dart
│   ├── activity_provider.dart
│   ├── messaging_provider.dart
│   └── alert_provider.dart
└── utils/
    ├── constants.dart
    ├── validators.dart
    └── formatting.dart
```

---

## API Integration Checklist

### Phase 1-2: Core Vitals & Fitness
- [ ] `GET /vital-signs` - Real-time vitals display
- [ ] `GET /recommendations` - Fitness plan suggestions
- [ ] `GET /recommendation-ranking` - A/B tested best workouts
- [ ] `POST /activity-sessions` - Log completed workouts
- [ ] `GET /activity-sessions` - History retrieval
- [ ] `GET /anomaly-detection` - Unusual pattern warnings

### Phase 3: Nutrition (New Backend Endpoint)
- [ ] `GET /nutrition/recommendations` - Daily meal suggestions
- [ ] `GET /nutrition/recipes` - Recipe database
- [ ] `POST /nutrition/logs` - Log meals eaten

### Phase 4: AI Chatbot
- [ ] `POST /chat/message` - Send question to chatbot
- [ ] `GET /alerts/natural-language` - Explain alerts in plain English
- [ ] `GET /risk-summary/natural-language` - Daily risk summary
- [ ] `GET /predict/explain` - SHAP explanations

### Phase 5: Messaging (New Backend Endpoint)
- [ ] `GET /messaging/conversations` - List all chats
- [ ] `GET /messaging/conversations/{id}/messages` - Load chat history
- [ ] `POST /messaging/send` - Send message
- [ ] `WS /messaging/stream` - Real-time message updates

### Phase 6-8: Enhancements
- [ ] `GET /trend-forecast` - Predict future vital trends
- [ ] `GET /alerts` - Alert history & management
- [ ] `GET /user/profile` - User data & medical history
- [ ] `GET /baseline-optimization` - Personalized HR baseline

---

## Key Technical Decisions

### State Management
- Use Provider package for clean architecture
- Cache vital signs locally for offline access
- Real-time updates via WebSocket for messages/alerts

### Data Security
- Encrypt sensitive data at rest (HIPAA compliance)
- All API calls over HTTPS
- JWT token management with refresh logic
- Biometric auth for app unlock

### Performance
- Lazy load screens to reduce initial load time
- Cache vital sign history locally (last 30 days)
- Compress images for nutrition/recovery modules
- Optimize graph rendering for activity history

### Offline Capability
- Store last vital readings locally
- Queue messages to send when back online
- Cache recommendations for offline view
- Sync on reconnection

---

## Success Metrics

1. **UI/UX Quality**
   - Compact layouts with 30% less whitespace vs current
   - Load times under 2 seconds per screen
   - Professional fitness app aesthetic (Zepp-comparable)

2. **Feature Completeness**
   - All backend data types displayed meaningfully
   - Zero broken API integrations
   - Natural language explanations for all alerts

3. **Patient Engagement**
   - Fitness plans completed 80%+ of the time
   - Doctor messages responded to within 24 hours
   - Chatbot used 3+ times per week

4. **Clinical Safety**
   - Critical alerts displayed within 100ms
   - No missed anomaly detections
   - 100% HIPAA compliance in data handling

---

## Next Steps

1. **Immediate (This Week):**
   - Approve design mockups for each screen
   - Finalize backend API specifications for nutrition/messaging
   - Set up Flutter project structure

2. **Short Term (Next 2 Weeks):**
   - Complete UI/UX redesign (Phase 1)
   - Integrate vital signs display (Phase 2 foundation)
   - Build recommendation card components

3. **Medium Term (Next 4 Weeks):**
   - Complete fitness plans module
   - Implement nutrition tracking
   - Add AI chatbot integration

4. **Long Term (Next 6-8 Weeks):**
   - Build messaging system
   - Enhance recovery module
   - Complete activity history

---

**Document Version:** 1.0
**Last Updated:** February 15, 2026
**Team:** Adaptiv Health (Backend, Frontend, ML, Security)
