# Edge AI Coach - Integration Issues Summary

**Date:** February 23, 2026  
**Status:** Partially Integrated - 6 Key Issues Found

---

## CRITICAL ISSUES (Must Fix)

### ❌ Issue #1: Mobile Missing 3 of 4 NL API Methods
**Location:** `mobile-app/lib/services/api_client.dart:625`  
**Problem:**
- Only calls `getRiskSummaryNL()` (legacy endpoint)
- Missing: workout, alert-explanation, progress-summary endpoints
- Floating chatbot uses hardcoded responses instead of backend

**Impact:** AI Coach cannot provide workout recommendations, explain alerts, or show progress

**Fix Time:** 30 minutes
```dart
// Add these 3 methods:
getNLTodaysWorkout()
getNLAlertExplanation(alertId)
getNLProgressSummary(range)
```

---

### ❌ Issue #2: Web Dashboard Has NO AI Coach
**Location:** `web-dashboard/src/` - missing entirely  
**Problem:**
- No floating AI coach button anywhere
- No chat interface
- No AI integration at all (mobile has it, web doesn't)
- API methods exist in `api.ts` but no UI uses them

**Impact:** Clinicians/admins on web dashboard can't use AI Coach feature

**Fix Time:** 2-3 hours
```typescript
// Create new component:
FloatingAiCoach.tsx (floating button + modal)
// Add 4 new API methods matching mobile
```

---

### ❌ Issue #3: Floating Chatbot Uses Hardcoded Responses
**Location:** `mobile-app/lib/widgets/floating_chatbot.dart:109-145`  
**Problem:**
```dart
// Current (wrong):
if (lowerMessage.contains('workout')) {
  return "Check the Fitness tab...";  // ← Just text, not from backend
}

// Should be:
if (lowerMessage.contains('workout')) {
  return await widget.apiClient.getNLTodaysWorkout();  // ← Real data
}
```

**Impact:** Users don't get personalized AI responses, just generic tips

**Fix Time:** 45 minutes
- Replace 5-6 hardcoded responses with backend calls

---

## HIGH PRIORITY ISSUES

### ⚠️ Issue #4: Web Dashboard Missing NL API Methods
**Location:** `web-dashboard/src/services/api.ts`  
**Problem:**
- Has `getNaturalLanguageRiskSummary()` but it's not used
- Missing `getNLTodaysWorkout()`
- Missing `getNLAlertExplanation()`
- Missing `getNLProgressSummary()`

**Impact:** Even if you created the web UI, API calls would fail

**Fix Time:** 20 minutes
```typescript
// Add 3 methods to match mobile:
async getNLTodaysWorkout(date?: string)
async getNLAlertExplanation(alertId?: string)
async getNLProgressSummary(range?: string)
```

---

### ⚠️ Issue #5: Deprecated Chatbot Screen Still Exists
**Location:** `mobile-app/lib/screens/chatbot_screen.dart`  
**Problem:**
```dart
/// This screen has been retired.
/// Use FloatingChatbot instead
```
- Old screen still in codebase but not used
- Causes confusion about which implementation to use
- Dead code that needs maintenance

**Impact:** Developer confusion, potential bugs from old code path

**Fix Time:** 5 minutes
- Delete the file

---

### ⚠️ Issue #6: Backend Using Dummy Data
**Location:** `app/api/nl_endpoints.py`  
**Problem:**
```python
# TODO: Real DB query
risk_level = "LOW"
risk_score = 0.23  # Always same for every user!
avg_heart_rate = 72
```

**Impact:**
- AI responses identical for all users (no personalization)
- Can't show real workout recommendations
- Can't explain specific user alerts

**Fix Time:** 2-3 hours (when you have time)
- Replace dummy data with DB queries

---

## INTEGRATION SUMMARY TABLE

| Component | Status | Issue | Fix Time |
|-----------|--------|-------|----------|
| **Backend NL Endpoints** | ✅ Live | Dummy data | 2-3 hrs (later) |
| **Mobile FloatingChatbot UI** | ✅ Works | Hardcoded responses | 45 min |
| **Mobile API Methods** | ⚠️ Partial (1/4) | Missing 3 methods | 30 min |
| **Web Dashboard UI** | ❌ None | Doesn't exist | 2-3 hrs |
| **Web Dashboard API Methods** | ⚠️ Partial (1/4) | Missing 3 methods | 20 min |
| **Deprecated Code** | ⚠️ Present | chatbot_screen.dart | 5 min |

**Total Fix Time:** ~6 hours (3-4 developer hours)

---

## QUICK ACTION PLAN

### Phase 1 (30 min) - Mobile Critical Fixes
1. Add 3 missing methods to `ApiClient` (getNLTodaysWorkout, getNLAlertExplanation, getNLProgressSummary)
2. Update `_getAIResponse()` to call backend instead of hardcoding
3. Delete deprecated `chatbot_screen.dart`

### Phase 2 (2-3 hrs) - Web Dashboard
1. Create `FloatingAiCoach.tsx` component
2. Add 3 missing methods to web `api.ts`
3. Integrate component in `App.tsx`
4. Test all chat flows

### Phase 3 (2-3 hrs, Can do later) - Backend Enhancement
1. Add DB queries to replace dummy data in NL endpoints
2. Ensure user data isolation
3. Add caching for performance
4. Write integration tests

---

## FILES TO CHANGE (Immediate - 6 hours)

```
CRITICAL:
├── mobile-app/lib/services/api_client.dart          (Add 3 methods)
├── mobile-app/lib/widgets/floating_chatbot.dart     (Replace 5 responses)
├── mobile-app/lib/screens/chatbot_screen.dart       (DELETE)
└── web-dashboard/src/services/api.ts               (Add 3 methods)

NEW FILES:
├── web-dashboard/src/components/FloatingAiCoach.tsx (New component)
├── web-dashboard/src/components/FloatingAiCoach.css (New styles)
└── web-dashboard/src/App.tsx                        (Import & use component)

DOCUMENTATION:
└── docs/EDGE_AI_INTEGRATION_AUDIT.md               (Reference guide)
└── docs/EDGE_AI_QUICK_FIX_GUIDE.md                 (Implementation steps)
```

---

## VERIFICATION STEPS

After implementing fixes, verify:

```bash
# 1. Mobile API methods work
- Mobile app compiles without errors
- FloatingChatbot opens
- All 4 chatbot intents trigger (health, workout, alert, progress)
- Backend calls return data
- Error messages appear if backend down

# 2. Web Dashboard works
- FloatingAiCoach button visible (bottom-right)
- Opens/closes modal
- Chat interface responds
- Backend calls work
- Error handling works

# 3. No duplicate code
grep -r "chatbot_screen" mobile-app/lib/  # Should be 0 results
grep -r "ChatbotScreen" mobile-app/lib/   # Should be 0 results
```

---

## BACKEND READINESS

✅ **NL Endpoints:** All 4 endpoints implemented and registered  
✅ **API Routes:** Registered in main.py at `/api/v1/nl/*`  
⚠️ **Data:** Currently returns dummy data (acceptable for demo, needs DB integration for production)  
✅ **Error Handling:** Basic error handling in place  

**Note:** Backend is 90% ready. The "TODO: Real DB query" comments are the only blockers for production. UI/API integration can proceed with dummy data now.

---

## IMPACT IF NOT FIXED

| Issue | Current Impact | User Impact |
|-------|----------------|-------------|
| Missing mobile methods | App works but limited | Users don't get full AI features |
| Hardcoded responses | No personalization | AI seems generic, not helpful |
| No web dashboard AI | Clinicians can't use feature | Reduced platform value for clinicians |
| Deprecated code | Confusion for developers | Maintenance burden, poor code quality |
| Dummy backend data | Works in demo | Fails in production with real users |

---

## RECOMMENDATION

**Priority:** Medium (Not urgent, but completes announced feature)  
**Risk:** Low (All changes are additive, no rewrites needed)  
**Effort:** 6 hours for full integration  

**Go-Forward Plan:**
1. ✅ Do Phases 1 & 2 this week (web parity + mobile completeness)
2. ⏰ Do Phase 3 next week (backend DB integration after feature freeze)
3. 📋 Add edge cases & testing later

