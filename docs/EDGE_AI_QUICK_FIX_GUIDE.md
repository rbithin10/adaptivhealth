# Edge AI Coach - Quick Fix Implementation Guide

**Status:** Ready to implement  
**Priority:** Critical - Needed for full integration  
**Time Estimate:** 4-6 hours

---

## QUICK FIXES - IMPLEMENTATION STEPS

### FIX 1: Add Missing API Methods to Mobile App (Priority: CRITICAL)

**File:** `mobile-app/lib/services/api_client.dart`

**Current State:** Only has `getRiskSummaryNL()` calling legacy endpoint

**Action:** Replace with new unified methods calling `/api/v1/nl/*` endpoints

```dart
// REPLACE lines 625-637 with:

// ============ Natural Language AI Coach ============

/// Get patient-friendly risk summary for AI chatbot
/// (Replaces old getRiskSummaryNL - now uses new standardized endpoint)
Future<String> getNLRiskSummary() async {
  try {
    final response = await _dio.get('/nl/risk-summary');
    if (response.data is Map && response.data['nl_summary'] != null) {
      return response.data['nl_summary'] as String;
    }
    return 'Your health status is stable. Keep up your current routine.';
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Get today's personalized workout recommendation
Future<String> getNLTodaysWorkout() async {
  try {
    final response = await _dio.get('/nl/todays-workout');
    if (response.data is Map && response.data['nl_summary'] != null) {
      return response.data['nl_summary'] as String;
    }
    return 'Check the Fitness tab for today\'s recommended activity.';
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Get explanation for a specific health alert
/// Optional: pass alertId to get specific alert, otherwise gets latest
Future<String> getNLAlertExplanation({String? alertId}) async {
  try {
    final params = <String, dynamic>{};
    if (alertId != null) params['alert_id'] = alertId;
    
    final response = await _dio.get(
      '/nl/alert-explanation',
      queryParameters: params,
    );
    if (response.data is Map && response.data['nl_summary'] != null) {
      return response.data['nl_summary'] as String;
    }
    return 'No recent alerts to explain.';
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Get motivational progress summary comparing periods
/// range: '7d' (weekly) or '30d' (monthly)
Future<String> getNLProgressSummary({String range = '7d'}) async {
  try {
    final response = await _dio.get(
      '/nl/progress-summary',
      queryParameters: {'range': range},
    );
    if (response.data is Map && response.data['nl_summary'] != null) {
      return response.data['nl_summary'] as String;
    }
    return 'Great work! You\'re making positive progress.';
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

// Keep old method for backwards compatibility (deprecated)
@Deprecated('Use getNLRiskSummary() instead')
Future<String> getRiskSummaryNL() async {
  return getNLRiskSummary();
}
```

**Why:**
- Unifies all NL endpoints with consistent prefix `/nl/*`
- Uses new standardized response format with `nl_summary` field
- Provides fallback messages if backend unavailable
- Deprecates old method but maintains backwards compatibility

---

### FIX 2: Update Floating Chatbot to Use New Methods (Priority: CRITICAL)

**File:** `mobile-app/lib/widgets/floating_chatbot.dart`

**Current Problem:** 
- Lines 109-145: Most responses are hardcoded
- Only one API call implemented
- Uses old `getRiskSummaryNL()` method

**Action:** Replace `_getAIResponse()` method

```dart
// REPLACE lines 108-155 with:

Future<String> _getAIResponse(String userMessage) async {
  final lowerMessage = userMessage.toLowerCase();
  
  // === HEALTH STATUS QUERIES ===
  if (lowerMessage.contains('heart') || 
      lowerMessage.contains('health') || 
      lowerMessage.contains('risk') ||
      lowerMessage.contains('safe') ||
      lowerMessage.contains('status') ||
      lowerMessage.contains('how am i') ||
      lowerMessage.contains('doing')) {
    try {
      return await widget.apiClient.getNLRiskSummary();
    } catch (e) {
      return "I can access your health data, but I'm having trouble connecting right now. Your latest vitals are available on the home screen.";
    }
  }
  
  // === WORKOUT/EXERCISE QUERIES ===
  else if (lowerMessage.contains('workout') || 
           lowerMessage.contains('exercise') ||
           lowerMessage.contains('activity') ||
           lowerMessage.contains('moving') ||
           lowerMessage.contains('today\'s plan')) {
    try {
      return await widget.apiClient.getNLTodaysWorkout();
    } catch (e) {
      return "Check the Fitness tab for your personalized workout plan based on your current health status.";
    }
  }
  
  // === ALERT/WARNING QUERIES ===
  else if (lowerMessage.contains('alert') || 
           lowerMessage.contains('warning') ||
           lowerMessage.contains('problem') ||
           lowerMessage.contains('wrong')) {
    try {
      return await widget.apiClient.getNLAlertExplanation();
    } catch (e) {
      return "You can view all your health alerts by tapping the bell icon on the home screen. I'll help explain any specific alert you're concerned about.";
    }
  }
  
  // === PROGRESS/IMPROVEMENT QUERIES ===
  else if (lowerMessage.contains('progress') || 
           lowerMessage.contains('improve') ||
           lowerMessage.contains('better') ||
           lowerMessage.contains('trend') ||
           lowerMessage.contains('how am i doing')) {
    try {
      // Check if user asked about longer period
      final range = lowerMessage.contains('month') ? '30d' : '7d';
      return await widget.apiClient.getNLProgressSummary(range: range);
    } catch (e) {
      return "You're making positive progress! Keep up your current routine for the best results.";
    }
  }
  
  // === SLEEP QUERIES ===
  else if (lowerMessage.contains('sleep')) {
    return "Good sleep is essential for heart recovery. Aim for 7-8 hours and try to maintain a consistent sleep schedule. It helps stabilize your heart rate.";
  }
  
  // === NUTRITION QUERIES ===
  else if (lowerMessage.contains('nutrition') || 
           lowerMessage.contains('food') || 
           lowerMessage.contains('eat') ||
           lowerMessage.contains('diet')) {
    return "Visit the Nutrition tab for meal recommendations tailored to your cardiovascular health. Focus on low-sodium foods and heart-healthy nutrients.";
  }
  
  // === MESSAGING QUERIES ===
  else if (lowerMessage.contains('doctor') || 
           lowerMessage.contains('clinician') ||
           lowerMessage.contains('message') ||
           lowerMessage.contains('contact care')) {
    return "You can reach your care team through the Messaging tab. They typically respond within a few hours during business hours.";
  }
  
  // === HELP/GENERAL QUERIES ===
  else if (lowerMessage.contains('help') || 
           lowerMessage.contains('what can you do') ||
           lowerMessage.contains('features')) {
    return "I'm your AI health coach. I can help you understand:\n"
        "• Your current heart health status\n"
        "• Today's recommended activity\n"
        "• Explanations for any health alerts\n"
        "• Your progress and improvements\n\n"
        "Just ask about your health, workouts, nutrition, or progress!";
  }
  
  // === DEFAULT FALLBACK ===
  else {
    return "I can help you understand your heart health status, workout plans, nutrition guidance, and alerts. What would you like to know?";
  }
}
```

**Why:**
- Removes hardcoded responses where possible
- Calls real backend endpoints for personalized data
- Provides fallback messages for network errors
- Maps user intents to appropriate NL endpoints

---

### FIX 3: Delete Deprecated Chatbot Screen (Priority: MEDIUM)

**File:** `mobile-app/lib/screens/chatbot_screen.dart`

**Action:** DELETE THIS FILE ENTIRELY

This screen was replaced by the floating chatbot widget. Having both causes:
- Code duplication
- Navigation confusion
- Maintenance burden
- Unused dependencies

**Verification:** Check no other files import it:
```bash
grep -r "chatbot_screen" mobile-app/lib/
grep -r "ChatbotScreen" mobile-app/lib/
```

If no results, safe to delete.

---

### FIX 4: Update Mobile AI Store (Priority: MEDIUM)

**File:** `mobile-app/lib/features/ai/ai_store.dart`

**Current Issue:** Doesn't load AI coach data

**Action:** Add methods to load NL summaries

```dart
// ADD to AiStore class:

// Cache for AI coach responses
String? cachedRiskSummary;
String? cachedWorkoutSummary;
String? cachedProgressSummary;
DateTime? lastNLUpdate;

/// Load all AI coach summaries for home screen
Future<void> loadAICoachSummaries() async {
  loading = true;
  error = null;
  notifyListeners();

  try {
    // Load in parallel for faster UI updates
    final riskFuture = api.getNLRiskSummary().catchError((_) => '');
    final workoutFuture = api.getNLTodaysWorkout().catchError((_) => '');
    final progressFuture = api.getNLProgressSummary().catchError((_) => '');
    
    final results = await Future.wait([riskFuture, workoutFuture, progressFuture]);
    
    cachedRiskSummary = results[0];
    cachedWorkoutSummary = results[1];
    cachedProgressSummary = results[2];
    lastNLUpdate = DateTime.now();
  } catch (e) {
    error = _prettyError(e);
  } finally {
    loading = false;
    notifyListeners();
  }
}

/// Get risk summary with caching (5 min TTL)
Future<String> getRiskSummaryWithCache() async {
  if (_isCacheValid()) {
    return cachedRiskSummary ?? '';
  }
  await loadAICoachSummaries();
  return cachedRiskSummary ?? '';
}

bool _isCacheValid() {
  if (cachedRiskSummary == null || lastNLUpdate == null) return false;
  final elapsed = DateTime.now().difference(lastNLUpdate!);
  return elapsed.inMinutes < 5;
}
```

---

### FIX 5: Add Web Dashboard AI Coach Component (Priority: HIGH)

**File:** Create `web-dashboard/src/components/FloatingAiCoach.tsx`

```typescript
/*
Floating AI Coach for web dashboard.

Always-accessible AI assistant providing health summaries,
workout recommendations, alert explanations, and progress updates.
*/

import React, { useState, useRef, useEffect } from 'react';
import { Minimize2, X, Send, Loader } from 'lucide-react';
import { api } from '../services/api';
import { colors } from '../theme/colors';
import './FloatingAiCoach.css';

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

const FloatingAiCoach: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      text: "Hi! 👋 I'm your AI Health Coach. How can I help you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: inputValue,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((p) => [...p, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await getAiResponse(inputValue);
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: response,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((p) => [...p, botMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I'm having trouble connecting. Please try again in a moment.",
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((p) => [...p, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const getAiResponse = async (userMessage: string): Promise<string> => {
    const lower = userMessage.toLowerCase();

    // Health status queries
    if (lower.includes('health') || lower.includes('status') || lower.includes('risk')) {
      const response = await api.getNaturalLanguageRiskSummary(0); // TODO: get actual user_id
      return response.plain_summary || 'Your health status is stable.';
    }

    // Workout queries
    if (lower.includes('workout') || lower.includes('exercise') || lower.includes('activity')) {
      return "Check the Fitness tab for personalized workout recommendations based on your current health status.";
    }

    // Alert queries
    if (lower.includes('alert') || lower.includes('warning')) {
      return "You can view all your health alerts in the Alerts section. I can explain any specific alert you're concerned about.";
    }

    // Progress queries
    if (lower.includes('progress') || lower.includes('improve')) {
      return "You're making great progress! Keep maintaining your current routine for best results.";
    }

    // Nutrition queries
    if (lower.includes('nutrition') || lower.includes('food')) {
      return "Visit the Nutrition tab for personalized meal recommendations tailored to your cardiovascular health.";
    }

    // Default
    return "I can help you understand your health status, workout plans, alerts, and progress. What would you like to know?";
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: colors.primary.default,
          border: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          cursor: 'pointer',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
        }}
        title="AI Health Coach"
      >
        🤖
      </button>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        width: isMinimized ? '300px' : '400px',
        height: isMinimized ? '56px' : '600px',
        backgroundColor: 'white',
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        transition: 'all 0.3s ease',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: colors.primary.default,
          color: 'white',
          borderRadius: '12px 12px 0 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>🤖</span>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 600 }}>AI Health Coach</div>
            <div style={{ fontSize: '11px', opacity: 0.8 }}>Online</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <Minimize2 size={16} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.isUser ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '12px 16px',
                    backgroundColor: msg.isUser ? colors.primary.default : '#f0f0f0',
                    color: msg.isUser ? 'white' : '#333',
                    borderRadius: '12px',
                    fontSize: '14px',
                    lineHeight: '1.4',
                  }}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {isLoading && (
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '12px', color: '#999' }}>Thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={{ padding: '12px', borderTop: '1px solid #eee' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask about your health..."
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontFamily: 'inherit',
                }}
              />
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !inputValue.trim()}
                style={{
                  padding: '10px',
                  backgroundColor: colors.primary.default,
                  border: 'none',
                  borderRadius: '6px',
                  color: 'white',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: isLoading || !inputValue.trim() ? 0.5 : 1,
                }}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default FloatingAiCoach;
```

**CSS:** Create `web-dashboard/src/components/FloatingAiCoach.css`

```css
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
```

**Integration:** Add to `web-dashboard/src/App.tsx`:

```typescript
import FloatingAiCoach from './components/FloatingAiCoach';

export const App = () => {
  return (
    <>
      {/* ... existing content ... */}
      <FloatingAiCoach />
    </>
  );
};
```

---

### FIX 6: Add Missing API Methods to Web Dashboard (Priority: HIGH)

**File:** `web-dashboard/src/services/api.ts`

**Add these methods:**

```typescript
// =========================================================================
// Natural Language AI Coach Endpoints
// =========================================================================

async getNLRiskSummary(): Promise<string> {
  try {
    const response = await this.client.get('/nl/risk-summary');
    return response.data.nl_summary || 'Your health status is stable.';
  } catch (error) {
    console.error('Failed to get NL risk summary:', error);
    throw error;
  }
}

async getNLTodaysWorkout(date?: string): Promise<string> {
  try {
    const params: any = {};
    if (date) params.date = date;
    const response = await this.client.get('/nl/todays-workout', { params });
    return response.data.nl_summary || 'Check Fitness tab for workout recommendations.';
  } catch (error) {
    console.error('Failed to get today\'s workout:', error);
    throw error;
  }
}

async getNLAlertExplanation(alertId?: string): Promise<string> {
  try {
    const params: any = {};
    if (alertId) params.alert_id = alertId;
    const response = await this.client.get('/nl/alert-explanation', { params });
    return response.data.nl_summary || 'No alerts to explain.';
  } catch (error) {
    console.error('Failed to get alert explanation:', error);
    throw error;
  }
}

async getNLProgressSummary(range: '7d' | '30d' = '7d'): Promise<string> {
  try {
    const response = await this.client.get('/nl/progress-summary', {
      params: { range },
    });
    return response.data.nl_summary || 'Great progress!';
  } catch (error) {
    console.error('Failed to get progress summary:', error);
    throw error;
  }
}
```

**Location:** Add after line 588 (after existing Advanced ML methods)

---

## TESTING CHECKLIST

After implementing fixes, verify:

```typescript
// Test 1: All NL endpoints respond
GET /api/v1/nl/risk-summary         → 200 with nl_summary
GET /api/v1/nl/todays-workout       → 200 with nl_summary
GET /api/v1/nl/alert-explanation    → 200 with nl_summary
GET /api/v1/nl/progress-summary     → 200 with nl_summary

// Test 2: Mobile chatbot calls correct endpoints
- "How am I?" → calls getNLRiskSummary()
- "Workout?" → calls getNLTodaysWorkout()
- "Alert?" → calls getNLAlertExplanation()
- "Progress?" → calls getNLProgressSummary()

// Test 3: Web dashboard AI Coach works
- Button appears in fixed position (bottom-right)
- Opens/closes modal
- Sends messages
- Displays responses
- Handles errors gracefully

// Test 4: Error handling
- Backend down → shows fallback message
- No network → graceful failure
- Invalid responses → safe parsing
```

---

## DEPLOYMENT CHECKLIST

- [ ] Mobile: Add 4 new API methods
- [ ] Mobile: Update `_getAIResponse()` to use backend calls
- [ ] Mobile: Delete deprecated `chatbot_screen.dart`
- [ ] Mobile: Test all chatbot intents
- [ ] Web: Create `FloatingAiCoach.tsx` component
- [ ] Web: Create `FloatingAiCoach.css`
- [ ] Web: Add 4 new API methods to `api.ts`
- [ ] Web: Integrate component in `App.tsx`
- [ ] Backend: Run integration tests (ensure dummy data is acceptable for now)
- [ ] Test: Both platforms work with backend endpoints
- [ ] Documentation: Update AI Coach user guide

---

## SUCCESS CRITERIA

✅ Mobile: Floating chatbot calls all 4 NL endpoints  
✅ Web: Floating AI Coach exists and functional  
✅ Both: Intelligent intent routing based on user message  
✅ Both: Graceful error handling & fallbacks  
✅ Tests: All integration tests passing  

