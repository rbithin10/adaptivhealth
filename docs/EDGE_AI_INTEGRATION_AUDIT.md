# Edge AI Coach Integration Audit
## Complete Frontend & Backend Review

**Audit Date:** February 23, 2026  
**Status:** Partially Integrated - Several Loose Ends Identified

---

## EXECUTIVE SUMMARY

### Overall Status: ⚠️ INCOMPLETE

The Edge AI Coach ("Floating AI Coach") is **partially integrated** across mobile and web:

| Component | Mobile App | Web Dashboard | Backend |
|-----------|-----------|---------------|---------|
| AI Coach UI | ✅ Implemented | ❌ Missing | N/A |
| API Endpoints | ✅ 4/4 endpoints ready | ✅ 4/4 endpoints ready | ✅ All registered |
| API Client Methods | ⚠️ Partial (1/4) | ⚠️ Partial (1/4) | N/A |
| State Management | ⚠️ Partial (AiStore) | N/A | N/A |
| Integration Tests | ❌ None | ❌ None | ⚠️ Dummy data |

---

## 1. BACKEND STATUS - READY ✅

### NL Endpoints Registered
**File:** `app/main.py` (lines 253-257)

```python
app.include_router(
    nl_endpoints.router,
    prefix="/api/v1/nl",
    tags=["AI Coach Natural Language"]
)
```

### Available Endpoints (All Implementation-Ready)

| Endpoint | Status | Data | Notes |
|----------|--------|------|-------|
| `GET /api/v1/nl/risk-summary` | ✅ Live | Dummy | Used by mobile AI chat |
| `GET /api/v1/nl/todays-workout` | ✅ Live | Dummy | **NOT CALLED** by mobile/web |
| `GET /api/v1/nl/alert-explanation` | ✅ Live | Dummy | **NOT CALLED** by mobile/web |
| `GET /api/v1/nl/progress-summary` | ✅ Live | Dummy | **NOT CALLED** by mobile/web |
| `GET /api/v1/risk-summary/natural-language` | ✅ Live | Dummy | Legacy endpoint (advanced_ml.py) |

**Implementation Status:**
- All endpoints return **dummy data** with `# TODO: Real DB query` comments
- Feature builders working: `nl_builders.py` handles text generation
- Ready for integration when DB queries are added

---

## 2. MOBILE APP STATUS - PARTIALLY INTEGRATED ⚠️

### AI Coach UI - IMPLEMENTED ✅

**File:** `mobile-app/lib/widgets/floating_chatbot.dart`

**Features:**
- ✅ FloatingActionButton with AI icon
- ✅ Bottom sheet modal interface
- ✅ Chat message UI with user/bot distinction
- ✅ Text input & send functionality
- ✅ "Typing..." indicator
- ✅ Error handling

**Integration Points:**
```dart
// In home_screen.dart (line 218)
floatingActionButton: FloatingChatbot(apiClient: widget.apiClient),

// Mobile app has dedicated screens:
// - screens/ai_home_screen.dart (alternative entry point)
// - features/ai/ai_store.dart (Provider state management)
```

### API Integration - PARTIAL ⚠️

**File:** `mobile-app/lib/services/api_client.dart` (line 625)

Currently calling **ONLY 1 of 4** natural language endpoints:

```dart
Future<String> getRiskSummaryNL() async {
  try {
    final response = await _dio.get('/risk-summary/natural-language');
    // ^^ LEGACY endpoint from advanced_ml.py
    if (response.data is Map && response.data['plain_summary'] != null) {
      return response.data['plain_summary'] as String;
    }
    return 'Your health data is looking stable.';
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

### LOOSE END #1: Missing API Methods

**Problem:** Mobile app only calls `getRiskSummaryNL()` - missing 3 other NL endpoints

**Missing Methods Needed:**

```dart
// TODO: Add these methods to ApiClient
Future<String> getTodaysWorkoutNL() async {
  // GET /nl/todays-workout
}

Future<String> getAlertExplanationNL(String? alertId) async {
  // GET /nl/alert-explanation
}

Future<String> getProgressSummaryNL(String range = '7d') async {
  // GET /nl/progress-summary  (range: '7d' or '30d')
}
```

**Impact:** 
- Floating chatbot can only show risk summaries
- Cannot show workout recommendations
- Cannot explain specific alerts
- Cannot show progress motivational messages

### Chatbot Logic - LIMITED COVERAGE ⚠️

**File:** `floating_chatbot.dart` (lines 109-145)

```dart
Future<String> _getAIResponse(String userMessage) async {
  final lowerMessage = userMessage.toLowerCase();
  
  // Only ONE backend call implemented:
  if (lowerMessage.contains('heart') || lowerMessage.contains('health') /*...*/) {
    try {
      return await widget.apiClient.getRiskSummaryNL();  // ← Uses legacy endpoint
    } catch (e) {
      return "I can access your health data...";
    }
  }
  
  // Rest are hardcoded responses:
  if (lowerMessage.contains('workout')) {
    return "Check the Fitness tab...";  // ← Hardcoded, not from backend
  }
  // ... more hardcoded responses
}
```

**Issue:** Most AI responses are **hardcoded strings** instead of calling backend NL endpoints.

### State Management - PARTIAL ⚠️

**Files:**
- `mobile-app/lib/features/ai/ai_store.dart` - ChangeNotifier for home screen
- `mobile-app/lib/features/ai/ai_api.dart` - API wrapper

**Current Implementation:**

```dart
class AiStore extends ChangeNotifier {
  final AiApi api;
  
  Map<String, dynamic>? latestVitals;
  Map<String, dynamic>? latestRisk;
  Map<String, dynamic>? latestRecommendation;
  
  Future<void> loadHome() async {
    // Only loads vitals, risk, and recommendation
    // Doesn't load AI coach summaries
  }
}
```

**Missing:** No methods for NL endpoints integration in AiStore.

### LOOSE END #2: Deprecated Entry Points Still Present

**File:** `mobile-app/lib/screens/chatbot_screen.dart` (DEPRECATED)

```dart
/// This screen has been retired.
/// 
/// Duplicate UX with FloatingChatbot which is now backed by 
/// GET /api/v1/risk-summary/natural-language
/// 
/// Use FloatingChatbot instead - it's accessible from all screens 
/// via the floating action button.
```

**Issue:** Old chatbot screen still exists but is not used. Could cause confusion. Should be deleted or marked for removal.

---

## 3. WEB DASHBOARD STATUS - NO AI COACH ❌

### Current State

**AI Coach Features on Web Dashboard:** NONE

The web dashboard has **no floating AI coach** or AI chat interface, unlike the mobile app.

### What's Missing

**UI Component:** 
- ❌ No floating action button for AI chat
- ❌ No modal/bottom sheet for chat interface
- ❌ No chat message display component
- ❌ No AI coach widget anywhere

**API Integration:**

Web dashboard API service (`web-dashboard/src/services/api.ts`) has:

```typescript
// ✅ Some AI/NL methods exist:
async getNaturalLanguageRiskSummary(userId: number)
async generateNaturalLanguageAlert(userId: number, ...)
async getRetrainingStatus()
async explainPrediction(params)

// ❌ BUT:
// - No method for todays-workout endpoint
// - No method for alert-explanation endpoint  
// - No method for progress-summary endpoint
// - No methods for NL endpoints (they use /nl/ prefix, not /alerts/natural-language)
// - No UI component to display these
```

**Current Use:** The `generateNaturalLanguageAlert()` is used for **alert summaries** (different from AI Coach).

### LOOSE END #3: Web Dashboard Missing AI Coach Entirely

**To Add:**

1. **Create AI Coach Component**
   ```typescript
   // web-dashboard/src/components/FloatingAiCoach.tsx
   - Floating button (fixed position)
   - Modal/drawer chat interface
   - Message display
   - Input field
   ```

2. **Add to Main Pages**
   ```typescript
   // In App.tsx or main layout
   <FloatingAiCoach />
   ```

3. **Add API Methods to ApiService**
   ```typescript
   async getNLRiskSummary(userId: number)
   async getNLTodaysWorkout(userId: number, date?: string)
   async getNLAlertExplanation(userId: number, alertId?: string)
   async getNLProgressSummary(userId: number, range?: string)
   ```

---

## 4. API ENDPOINT PROBLEMS

### Problem A: Dual Endpoints for Risk Summary

**Two different endpoints return similar data:**

1. **Legacy Endpoint** (advanced_ml.py)
   ```
   GET /api/v1/risk-summary/natural-language
   Returns: {"user_id": ..., "plain_summary": "..."}
   ```

2. **New Endpoint** (nl_endpoints.py)
   ```
   GET /api/v1/nl/risk-summary
   Returns: {"user_id": ..., "risk_score": ..., "nl_summary": "..."}
   ```

**Issue:** Mobile app uses legacy endpoint. Should migrate to new `/nl/*` endpoints for consistency.

**Resolution:**
- Mobile app should update `getRiskSummaryNL()` to use `/nl/risk-summary`
- Deprecate `/risk-summary/natural-language` endpoint
- Update response parsing to use `nl_summary` field

### Problem B: Dummy Data in All NL Endpoints

**Files:** `app/api/nl_endpoints.py` (lines 40-95)

All 4 NL endpoints have:

```python
# TODO: Real DB query
# risk_assessment = db.query(RiskAssessment).filter(...).first()
# vitals = db.query(VitalSignRecord).filter(...).all()

# Currently returns dummy data:
risk_level = "LOW"
risk_score = 0.23
avg_heart_rate = 72
# ... etc
```

**Impact:**
- AI Coach responses are **always the same** for every user
- No personalization based on actual health data
- Good for testing UI, but not production-ready

**Needs:** Database integration to queries to pull real user data.

### Problem C: Missing User ID Handling

**File:** `floating_chatbot.dart`

```dart
_getAIResponse(String userMessage) async {
  // ... tries to call backend
  return await widget.apiClient.getRiskSummaryNL();
  // ^^ No user_id parameter!
}
```

**Backend Expects:**
```
GET /api/v1/nl/risk-summary?user_id=123&time_window_hours=24
```

**Issue:** Mobile app doesn't pass `user_id` to API calls. Backend might return wrong user's data or 400 error.

**Resolution:** Modify all NL API calls to include authenticated user context via JWT token (already done via ApiClient interceptor).

---

## 5. MISSING INTEGRATION POINTS

### Missing Test Coverage

**Test Status:** ❌ NO TESTS

No integration tests for:
- Mobile FloatingChatbot widget
- NL endpoint responses
- API method coverage
- AI Coach E2E flows

**Suggested Tests:**
```bash
tests/test_nl_endpoints.py        # Backend NL endpoints
mobile-app/test/floating_chatbot_test.dart  # Mobile widget
web-dashboard/src/__tests__/FloatingAiCoach.test.tsx  # Web component
```

### Missing Documentation

**Missing Docs:**
- How to use AI Coach on mobile vs web
- API integration guide for frontends
- Chatbot intent mapping (what user says → what API to call)
- Error handling & timeout behavior

---

## INTEGRATION CHECKLIST

### Priority 1: CRITICAL (Blocks full integration)

- [ ] **Add missing API methods to mobile ApiClient**
  - `getTodaysWorkoutNL()`
  - `getAlertExplanationNL(alertId)`
  - `getProgressSummaryNL(range)`
  - Update `getRiskSummaryNL()` to use new `/nl/risk-summary` endpoint

- [ ] **Fix user context in NL endpoint calls**
  - Ensure user_id is passed (via JWT token)
  - Test with multiple users to verify data isolation

- [ ] **Remove deprecated chatbot screen**
  - Delete `mobile-app/lib/screens/chatbot_screen.dart`
  - Update any remaining references

### Priority 2: HIGH (Adds complete feature parity)

- [ ] **Create web dashboard AI Coach component**
  - Floating action button
  - Chat modal
  - Message display
  - Input field

- [ ] **Add NL API methods to web dashboard ApiService**
  - `getNLRiskSummary(userId)`
  - `getNLTodaysWorkout(userId, date)`
  - `getNLAlertExplanation(userId, alertId)`
  - `getNLProgressSummary(userId, range)`

- [ ] **Implement intelligent chatbot intent routing in both platforms**
  - Move from hardcoded responses to backend calls
  - Map user questions to appropriate NL endpoints
  - Handle multiple intents in single message

### Priority 3: MEDIUM (Polish & optimization)

- [ ] **Implement real database queries in NL endpoints**
  - Replace dummy data with actual user vitals
  - Add caching for frequently accessed data
  - Optimize query performance

- [ ] **Deprecate legacy `/risk-summary/natural-language` endpoint**
  - Redirect to new `/nl/risk-summary`
  - Add deprecation warning header
  - Plan removal date

- [ ] **Add comprehensive test coverage**
  - Unit tests for NL endpoint builders
  - Integration tests for API methods
  - E2E tests for chatbot flows

- [ ] **Add error recovery & failover**
  - Graceful degradation when backend unavailable
  - Offline mode for previously cached summaries
  - User-friendly error messages

### Priority 4: NICE-TO-HAVE (Enhancement)

- [ ] **Add voice input/output to mobile AI Coach**
  - Speech-to-text for user messages
  - Text-to-speech for AI responses

- [ ] **Implement chat history persistence**
  - Store/retrieve past conversations
  - Resume conversations across sessions

- [ ] **Add AI Coach customization**
  - Personality/tone preferences
  - Language selection
  - Detail level (simple vs detailed responses)

---

## FILE LOCATION REFERENCE

### Backend
- **NL Endpoints:** `app/api/nl_endpoints.py`
- **NL Builders:** `app/services/nl_builders.py` (generates text)
- **Route Registration:** `app/main.py` (lines 253-257)
- **Legacy Endpoint:** `app/api/advanced_ml.py` (line 499)

### Mobile App
- **Floating Chatbot:** `mobile-app/lib/widgets/floating_chatbot.dart`
- **API Client:** `mobile-app/lib/services/api_client.dart` (line 625)
- **AI Store:** `mobile-app/lib/features/ai/ai_store.dart`
- **Deprecated Chatbot:** `mobile-app/lib/screens/chatbot_screen.dart` (REMOVE)
- **Home Screen Integration:** `mobile-app/lib/screens/home_screen.dart` (line 218)

### Web Dashboard
- **API Service:** `web-dashboard/src/services/api.ts` (lines 1-820)
- **Components:** `web-dashboard/src/components/` (NO AI Coach component)
- **Pages:** `web-dashboard/src/pages/` (PatientDashboardPage, MessagingPage)
- **Types:** `web-dashboard/src/types/index.ts`

---

## IMPLEMENTATION ROADMAP

### Week 1: Mobile Integration
1. Add missing API methods to ApiClient
2. Update chatbot intent routing
3. Test with backend endpoints
4. Delete deprecated chatbot screen
5. Add unit tests

### Week 2: Web Integration
1. Create FloatingAiCoach component
2. Add NL API methods to ApiService
3. Integrate chat UI
4. Test with backend
5. Deploy to dashboard

### Week 3: Backend Enhancement
1. Add real database queries to NL endpoints
2. Remove dummy data dependencies
3. Test with actual user data
4. Add caching layer
5. Performance optimization

### Week 4: Polish & Documentation
1. Add E2E tests for both platforms
2. Write API integration guide
3. Create user documentation
4. Add error handling & failover
5. Production readiness review

---

## CONCLUSION

**Current State:** AI Coach is 40% integrated - UI exists on mobile, backend endpoints are ready, but critical API integration gaps exist on both platforms.

**Blockers for Production:**
1. Mobile/web missing 3 of 4 NL endpoint methods
2. Web dashboard has no AI Coach UI
3. Backend using dummy data (needs DB integration)
4. No test coverage for AI Coach flows

**Estimated Effort to Complete:** 20-30 hours (3-4 developer days)

**Recommendation:** Prioritize Mobile fixes first (4-6 hours), then implement Web dashboard (8-10 hours), then optimize backend (4-6 hours).

