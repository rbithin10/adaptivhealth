# UX Issues — AdaptivHealth Mobile App
**Audit date:** March 4, 2026  
**Scope:** Dark mode visibility, Health Insights (light + dark), Dev cards (dark), Recovery screen, Health Insights wiring & purpose analysis.

---

## Legend
- `[ ]` TODO
- `[~]` In progress
- `[x]` Done

---

## 1. Dark Mode — Title / Header Visibility (Multiple Screens)

### Root Cause
`home_screen.dart` (line 370) renders the "Adaptiv Health" app-bar title with a hardcoded `color: AdaptivColors.text900` (`#212121` — near-black). In dark mode the app-bar background is `surface900` (`#1F2937` — near-black). Near-black text on near-black background = invisible.

- [ ] **Fix "Adaptiv Health" title in `home_screen.dart`** — replace `color: AdaptivColors.text900` with `color: AdaptivColors.getTextColor(brightness)` on the title `Text` widget (line ~370).
- [ ] **Audit all other screen `AppBar` titles** — check `notifications_screen.dart`, `nutrition_screen.dart`, `fitness_plans_screen.dart`, `rehab_program_screen.dart`, `history_screen.dart`, `device_pairing_screen.dart` for hardcoded title colors that do not respect brightness.
- [ ] **Ensure `iconTheme` colour is correct for each screen's `AppBar`** — some screens set `backgroundColor` but forget to set `foregroundColor` / `iconTheme`, causing icon default colours that match the background.

---

## 2. Health Insights Screen — Light Mode: Title and Back Arrow Invisible

### Root Cause
`health_screen.dart` (line ~154) sets `AppBar.backgroundColor: AdaptivColors.getSurfaceColor(brightness)`. In light mode `getSurfaceColor` returns `white`. The global `AppBarTheme` in `theme.dart` (light branch) sets `foregroundColor: AdaptivColors.white`. So the `←` icon and the `"Health Insights"` title text are **white-on-white — completely invisible**.

- [ ] **Add explicit `foregroundColor` / `titleTextStyle` / `iconTheme` to the Health Insights `AppBar`** — in light mode use `AdaptivColors.text900`; in dark mode use `AdaptivColors.textDark50`. Simplest fix:
  ```dart
  foregroundColor: AdaptivColors.getTextColor(brightness),
  ```
- [ ] **Verify the share icon (top-right) is also visible in both modes** — currently uses hardcoded `color: AdaptivColors.text600`.

---

## 3. Health Insights Screen — Dark Mode: Trend Chart Cards Unreadable

### Root Cause
`_buildTrendCard()`, `_buildHistoryItem()`, and `_buildInsightCard()` all use hardcoded `color: AdaptivColors.white` for the card container background, and `AdaptivColors.border300` (`#E0E0E0`) for borders. In dark mode the page background is `background900` (`#111827`), so white cards render correctly as light rectangles — visually jarring and inconsistent. Key text issues:

- `bodySmall` style has hardcoded `color: #666666` which becomes low-contrast on white cards in some display environments.
- `caption` style has hardcoded `color: #999999` — appears faded.
- The inner "Trend chart" placeholder container uses `color.withOpacity(0.05)` for its background which may render near-invisibly in dark mode.

**Affected widgets within `health_screen.dart`:**

- [ ] **`_buildTrendCard()`** — replace `color: AdaptivColors.white` with `AdaptivColors.getSurfaceColor(brightness)` and `border: Border.all(color: AdaptivColors.getBorderColor(brightness))`. Requires passing `brightness` parameter.
- [ ] **`_buildHistoryItem()`** — same fix: surface + border from brightness helpers.
- [ ] **`_buildInsightCard()`** — same fix.
- [ ] **`_TabBarDelegate`** — `color: AdaptivColors.white` hardcoded on the persistent tab bar strip; renders as a white band across a dark screen. Replace with `AdaptivColors.getSurfaceColor(brightness)`. Requires passing `brightness` to the delegate.
- [ ] **Edge AI status card wrapper in `_buildVitalsSection()`** — `color: AdaptivColors.white` hardcoded; replace with `getSurfaceColor(brightness)`.
- [ ] **"Trend chart" placeholder inner container** — `color: color.withOpacity(0.05)` works in light mode but the text inside uses `AdaptivTypography.caption.copyWith(color: color)` which may not contrast well on dark cards. Review per metric colour.

---

## 4. Dev Cards — Dark Mode Readability (Profile Screen)

**File:** `profile_screen.dart` — `_buildWearableSimulatorCard()` (~line 1040) and `_buildDeveloperUtilities()` (~line 1153).

### Root Cause
Both dev card containers are hardcoded to `color: AdaptivColors.white` with `AdaptivColors.border300` borders. In dark mode they render as bright white rectangles on a dark background — visually jarring and inconsistent with the surrounding dark UI. Some text colours (caption `#999999`, `text600` = `#666666`) may also reduce contrast when on a white card in an otherwise dark environment.

- [ ] **`_buildWearableSimulatorCard()`** — replace hardcoded `color: AdaptivColors.white` and `borderColor: AdaptivColors.border300` with brightness-aware equivalents (`getSurfaceColor(brightness)` / `getBorderColor(brightness)`). Requires reading `Theme.of(context).brightness` at the top of the method.
- [ ] **`_buildDeveloperUtilities()`** — same fix.
- [ ] **`_buildEdgeInfoRow()`** — label text uses `AdaptivColors.text600` = `#666666`; ensure this is readable on dark surfaces by using `AdaptivColors.getSecondaryTextColor(brightness)`.
- [ ] **Caption text across all profile dev sections** — `AdaptivTypography.caption.copyWith(color: AdaptivColors.text600)` is hardcoded; wrap with `AdaptivColors.getSecondaryTextColor(brightness)`.

---

## 5. Recovery Screen — Existence and Accessibility Audit

### Status: EXISTS — accessible but not directly in the main navigation

| Question | Answer |
|---|---|
| File exists? | ✅ `screens/recovery_screen.dart` — 1332 lines, substantial implementation |
| Accessible from app? | ✅ Yes — via `home_screen._navigateToRecovery()` and `fitness_plans_screen.dart` (line 237) |
| In bottom nav bar? | ❌ No — it is a sub-screen of the Fitness tab (push navigation), not a tab item |
| Is it missing? | ❌ Not missing; by design it is accessed post-workout |
| Is it reachable by a user? | ⚠️ Only if they know to look inside Fitness. No dedicated entry point from the Home tab quick-actions section. |

### Recovery Screen Features Implemented
- Live vitals display
- Scored recovery ring
- Session metrics (API-sourced with fallback)
- Breathing exercise widget (4 techniques: 4-7-8, Box, 4-2-4, 2-4-6)
- Personalised AI recommendation from backend
- Bottom actions: Log Meal, Message Care Team
- AI Coach overlay (floating chatbot)

### Recovery Screen Issues

- [ ] **No entry point from the Home dashboard quick-actions** — the Home tab should have a "Recovery" card or button (e.g. in the quick-actions row) so users find it without drilling into Fitness.
- [ ] **Dark mode audit not confirmed for recovery_screen.dart** — given the pattern of other screens, check for hardcoded `AdaptivColors.white` container backgrounds.

---

## 6. Health Insights Screen — Wiring, Functionality and Purpose Analysis

### 6a. What is wired (real data)

| Feature | Status | Notes |
|---|---|---|
| Latest vitals (HR, SpO₂, BP, HRV) from API | ✅ Wired | `getLatestVitals()` with demo fallback |
| User profile (age, baseline HR, max HR) | ✅ Wired | Used for Edge AI predictions |
| Edge AI risk prediction | ✅ Wired | `edgeStore.processVitals()` called in `_buildVitalsSection()` |
| CV Risk badge | ✅ Wired | Reads `edgeStore.latestPrediction` |
| Target zone indicator | ✅ Wired | Uses real HR + max HR |
| Vital cards (HR, SpO₂, BP, HRV) | ✅ Wired | Real values from API |
| Pull-to-refresh | ✅ Wired | Re-calls `_loadHealthData()` |

### 6b. What is NOT wired (demo/placeholder only)

| Feature | Status | Impact |
|---|---|---|
| Trends tab data | ❌ Hardcoded `_getDemoTrends()` — Mon–Sun static values | No real historical trend shown |
| "Trend chart" placeholder | ❌ Empty `Container` with centred text "Trend chart" | `fl_chart` is in pubspec but unused here; cards are not interactive |
| History tab data | ❌ Hardcoded `_getDemoHistory()` — 4 static entries | Real activity + vitals history exists via `/vitals/history` and `/activities` |
| Insights tab content | ❌ Entirely static strings — no AI, no backend | Should call the AI Coach or an insights endpoint |
| Vital detail tap handler | ❌ Shows SnackBar "coming soon" | No in-screen expansion or detail |
| Share / export button | ❌ Empty `onPressed` | No report generation |
| HRV field from API | ⚠️ Uses `vitals['hrv'] ?? 45` — backend may not return HRV in the standard vitals response | Confirm `/vitals/latest` returns `hrv`; if not, always shows `45` |
| Health Score (85 + "+3 this week") | ❌ Hardcoded | Should be derived from ML risk score or removed |

### 6c. Philosophical / Logical Existence

**Is Health Insights the right screen?**  
Yes — for a cardiovascular monitoring platform, a dedicated health-overview screen separate from the real-time home dashboard is architecturally correct. The Home tab is a live vitals monitor; Health Insights is the longitudinal record and trend analysis layer. The duplicate vitals at the top are acceptable — this screen acts as the complete health hub, and repeating last-known values gives context before the user scrolls into trends.

**Current logical gap:** The screen looks feature-rich (cards with chevrons, tabs with content) but every interactive element is a dead end — no card expands, no chart renders, no data is real. It signals depth that isn't there yet.

**Principle going forward — no new pushed screens:**  
All interactivity stays in-screen. Tapping a trend card expands it in place (accordion) to reveal a chart. No `Navigator.push`. This keeps the screen coherent and avoids navigation debt.

---

### 6c-i. Trends Tab — Expandable Cards Design

Each metric card (Heart Rate, Blood Pressure, SpO₂, HRV) becomes an accordion:

**Collapsed state (current appearance):**  
Icon + metric name + 7-day average + chevron → looks exactly as it does now.

**Expanded state (on tap):**  
Same header, chevron rotates → `AnimatedContainer` reveals a `fl_chart` `LineChart` below the header within the same card. A `7D / 30D` chip toggle switches the time range. The insight caption ("Stable this week") remains at the bottom.

**When no real data exists:**  
The chart renders with a dashed flat line at the average value and a muted caption: `"No history yet — chart will fill as data syncs."` The chart axes and grid are always visible. This means the UI looks correct from day one and improves automatically when data flows in.

**State management:**  
`_expandedMetric` — a `String?` in `_HealthScreenState` (only one card open at a time). Stored as the metric key (`'hr'`, `'bp'`, `'spo2'`, `'hrv'`). No new widgets needed — handled entirely within `_buildTrendCard()`.

---

### 6c-ii. History Tab — Design Plan

The History tab is the weakest part of the screen. The current 4-item flat list is insufficiently useful for a cardiovascular patient. The right design is a **clinical event timeline** — a time-ordered record answering: *"What happened to my health over the last 7–30 days?"*

**Structure:**

```
┌─────────────────────────────────────────────┐
│  [All ▼]  [Vitals]  [Workouts]  [Alerts]    │  ← filter chip row
└─────────────────────────────────────────────┘
  TODAY
  ─────
  🫀  Heart Rate          72 BPM  Normal    2h ago
  🏃  Morning Walk   30 min • 2.1 km Done    5h ago

  YESTERDAY
  ──────────
  ⚠️  High HR Alert      145 BPM          09:15
  🫀  Blood Pressure   120/80 mmHg Normal  07:30

  MON  27 FEB
  ──────────
  …
```

**Filter chips:** All | Vitals | Workouts | Alerts  
- "All" shows everything interleaved chronologically  
- Each filter hides irrelevant entries without a network call (client-side filter on loaded data)

**Date grouping:**  
Group by relative date label: `Today`, `Yesterday`, then `DDD DD MMM` for older days. This mirrors how medical apps (Apple Health, Samsung Health) present records.

**Event types and data sources:**

| Event type | Icon | Data source | Fields shown |
|---|---|---|---|
| Vitals reading | `Icons.monitor_heart` | `/vitals/history` | HR / SpO₂ / BP + status badge |
| Workout / Activity | `Icons.directions_run` | `/activities` | type, duration, distance, peak HR |
| Clinical Alert | `Icons.warning_amber` | Local alert store (already shown in Notifications screen) | threshold breached + value |
| Recovery session | `Icons.self_improvement` | `/activities` (type = recovery) | session score if available |

**Empty state per filter:**  
If a filter returns no events, show a centred icon + muted text (e.g. `"No workouts recorded yet"`). Never show a blank list.

**Data load strategy:**  
Load `/vitals/history?days=30` and `/activities?limit=50` once in `_loadHealthData()` alongside the existing vitals + profile calls. Store in `_healthData['historyVitals']` and `_healthData['historyActivities']`. Merge and sort client-side by timestamp. No extra API calls on tab switch.

**Why this design is correct for the app:**  
A cardiovascular patient and their clinician need to see whether an alert happened during a workout (exertional HR) or at rest (arrhythmia risk). Interleaving workouts and vitals in a single timeline makes this immediately visible without drilling into separate screens.

### 6d. Health Insights — Tasks

#### Trends Tab — Expandable Cards
- [ ] **Add `_expandedMetric` state variable** to `_HealthScreenState` — `String? _expandedMetric` (null = all collapsed; only one card open at a time).
- [ ] **Rewrite `_buildTrendCard()`** — make it stateful-aware: on tap toggle `_expandedMetric`. Use `AnimatedContainer` + `AnimatedRotation` on the chevron to smoothly expand/collapse.
- [ ] **Add `fl_chart` `LineChart` inside each expanded card** — 7-day line using data from `_getDemoTrends()` for now (real wire-up follows). Chart shows axes and gridlines always.
- [ ] **Add `7D / 30D` chip toggle inside each expanded card** — stored as `_trendRange` (`int days = 7`). Triggers a re-fetch of `/vitals/history?days=N` for that metric.
- [ ] **Empty/no-data chart state** — when history list is empty, render the chart with a dashed flat line at the current reading value + caption `"No history yet — chart will fill as data syncs."`
- [ ] **Wire Trends tab to real data** — in `_loadHealthData()` call `apiClient.getVitalsHistory(days: 30)` and cache in `_healthData['vitalsHistory']`. `_buildTrendCard()` filters this list by metric for its chart series.
- [ ] **Fix vital card tap handler** — replace `ScaffoldMessenger` SnackBar with `setState(() => _expandedMetric = metricKey)` + scroll to that card. No new screen needed.

#### History Tab — Clinical Event Timeline
- [ ] **Add `_historyFilter` state** — `String _historyFilter = 'all'` (values: `'all'`, `'vitals'`, `'workouts'`, `'alerts'`).
- [ ] **Add filter chip row** at top of `_buildHistoryTab()` — `All | Vitals | Workouts | Alerts` using `FilterChip` widgets. Selecting a chip sets `_historyFilter` and calls `setState`; filtering is client-side, no re-fetch.
- [ ] **Load history data in `_loadHealthData()`** — add `apiClient.getVitalsHistory(days: 30)` and `apiClient.getActivities(limit: 50)` to the parallel `Future.wait`. Store results in `_healthData`.
- [ ] **Merge and sort events client-side** — combine vitals records and activity records into a unified list sorted descending by timestamp. Each item carries a `type` field (`'vitals'`, `'workout'`, `'alert'`).
- [ ] **Group list by relative date** — build sections: `Today`, `Yesterday`, then `DDD DD MMM` for older dates. Render each group with a small date header above its items.
- [ ] **Replace `_buildHistoryItem()`** — update to handle the richer unified event model (vitals show HR+SpO₂+BP, workouts show duration+peak HR, alerts show threshold + value).
- [ ] **Add empty state per filter** — when a filter returns zero events, show a centred illustration + muted message (`"No workouts recorded yet"` etc.).
- [ ] **Integrate alert events** — source clinical alerts from the local `NotificationService` or a cached alert list (already polled by `AlertPollingService`); include them in the merged timeline under the `'alerts'` category.

#### Insights Tab
- [ ] **Wire Insights tab to AI Coach** — call `apiClient.getAiInsights(context: latestVitalsSummary)` or equivalent; replace the 4 hardcoded strings with AI-generated text. Show a loading shimmer while the call is in flight.
- [ ] **Fallback content** — if the AI call fails, keep the current hardcoded cards as fallback so the tab is never empty.

#### Other
- [ ] **Verify HRV field** — confirm `/vitals/latest` returns `hrv`; if it is absent, remove the HRV vital card from the top header row to avoid always showing `45`.
- [ ] **Health Score** — either derive from the ML risk score (`round((1 - risk_score) * 100)`) or replace the banner with a "Last sync" timestamp so it is never misleading.
- [ ] **Share / Export** — implement the top-right share button to share a plain-text summary of the week's averages via `Share.share()` (share_plus package).

---

## 7. Global Theme — Additional Issues Found During Audit

- [ ] **`AppBarTheme` in light mode sets `foregroundColor: white`** (`theme.dart` line ~36) which is correct for the main HomeScreen blue-tinted AppBar, but breaks any screen that overrides `backgroundColor` to white without also setting its own `foregroundColor`. Consider removing the global `foregroundColor` from `AppBarTheme` and setting it per-screen, OR add a `titleTextStyle` to the global theme that uses a brightness-aware colour.
- [ ] **`bodySmall` and `caption` in `typography.dart`** have hardcoded mid-gray colours (`#666666`, `#999999`). These are only accessible-contrast on white/very-light backgrounds. Any dark card that uses these styles inherits low-contrast text. Add `bodySmallFor(brightness)` and `captionFor(brightness)` helpers (the pattern already exists in the file) and migrate usages in `health_screen.dart` and `profile_screen.dart`.
- [ ] **`BottomNavigationBar` in `home_screen.dart`** — `backgroundColor: Colors.white` is hardcoded (line ~494); in dark mode this renders a white nav bar. Replace with `AdaptivColors.getSurfaceColor(brightness)`.

---

## 8. Device Pairing Screen — Crash: `Unsupported operation: Platform._operatingSystem`

### Error (from error log and manual test)
```
Unsupported operation: Platform._operatingSystem  (thrown 3× on open)
RenderFlex overflowed by 158 pixels on the right.
```

### Root Cause A — `dart:io Platform` used on Flutter Web
`device_pairing_screen.dart` imports `dart:io` and calls `Platform.isIOS` directly **inside `build()`** (lines 399 and 537) and inside `_connectViaHealth()` (line 178). `dart:io`'s `Platform` class is **completely unsupported on Flutter Web** — it throws `Unsupported operation: Platform._operatingSystem` the moment Flutter tries to render any widget that branches on `Platform.isIOS`.

The same import pattern exists in:
- `services/ble/ble_service.dart` — `Platform.isAndroid`
- `services/ble/ble_permission_handler.dart` — `Platform.isIOS`, `Platform.isAndroid`
- `services/health/health_service.dart` — `Platform.isIOS`, `Platform.isAndroid`
- `widgets/floating_chatbot.dart` — `Platform` usage

**Fix pattern:** Replace all `Platform.isIOS / Platform.isAndroid` with a platform-safe helper that guards with `kIsWeb` first:
```dart
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io' show Platform;

bool get isIOS => !kIsWeb && Platform.isIOS;
bool get isAndroid => !kIsWeb && Platform.isAndroid;
```

- [ ] **Create `lib/config/platform_guard.dart`** — a single file exporting `isIOS`, `isAndroid`, `isWeb` helpers that are safe to call on all targets.
- [ ] **Fix `device_pairing_screen.dart`** — remove `import 'dart:io'`, import `platform_guard.dart`, replace every `Platform.isIOS` / `Platform.isAndroid` call (lines 178, 399, 537) with the safe helpers.
- [ ] **Fix `ble_service.dart`** — same: replace `Platform.isAndroid` with `isAndroid` from platform guard.
- [ ] **Fix `ble_permission_handler.dart`** — replace `Platform.isIOS` / `Platform.isAndroid` (4 usages).
- [ ] **Fix `health_service.dart`** — replace `Platform.isIOS || Platform.isAndroid` guard (lines 37, 125) with `!kIsWeb && (Platform.isIOS || Platform.isAndroid)`.
- [ ] **Fix `floating_chatbot.dart`** — audit and replace any `Platform.*` usage.
- [ ] **On web, hide the "Connect via Apple Health / Health Connect" row entirely** (BLE and HealthKit are mobile-only features) — show a "BLE pairing is only available on the mobile app" placeholder instead.

### Root Cause B — RenderFlex overflow (158 px to the right)
In `device_pairing_screen.dart` the divider row (around line ~430 in the `build` method) is:
```dart
Row(children: [
  const Expanded(child: Divider()),
  Padding(..., child: Text('Or connect a BLE heart rate monitor directly')),
  const Expanded(child: Divider()),
])
```
The middle `Text` is **not wrapped in `Flexible` or `Expanded`**, so on narrow screens the fixed-width text overflows the row by 158 px.

- [ ] **Wrap the middle `Text` in `Flexible` with `overflow: TextOverflow.ellipsis`** OR reduce the label to a shorter string (e.g. `'Direct BLE pairing'`).

---

## 9. Rehab Program Screen — 404 on Load (`/rehab/current-program`)

### Error (from paste.txt)
```
GET http://localhost:8080/api/v1/rehab/current-program 404 (Not Found)
→ rehab_program_screen.dart:76  _loadProgram  initState
```

### Root Cause
`rehab_program_screen.dart` calls `apiClient.getRehabProgram()` in `initState`. When the logged-in user has no assigned rehab program the backend returns 404. The screen either shows a broken state or throws an unhandled exception.

- [ ] **Handle 404 gracefully in `rehab_program_screen.dart`** — catch the 404-specific Dio error and show an empty state widget ("No rehabilitation program assigned yet. Your clinician will set one up for you.") instead of crashing.
- [ ] **Confirm `api_client.dart getRehabProgram()` wraps 404 as a catchable exception** (not rethrown as a fatal error).
- [ ] **Add an empty-state illustration/message** so the screen does not look broken to users without a rehab program.

---

## Summary — Priority Order

| Priority | Area | Files |
|---|---|---|
| P0 — App Crash | Device Pairing screen crashes on web: `Platform._operatingSystem` unsupported | `device_pairing_screen.dart`, `ble_service.dart`, `ble_permission_handler.dart`, `health_service.dart`, `floating_chatbot.dart` |
| P0 — Invisible UI | Health Insights AppBar in light mode (back arrow + title invisible) | `health_screen.dart` |
| P0 — Invisible UI | "Adaptiv Health" title invisible in dark mode | `home_screen.dart` |
| P1 — Layout Crash | RenderFlex overflow 158 px — Device Pairing divider row | `device_pairing_screen.dart` |
| P1 — Error Handling | Rehab screen 404 shows broken state instead of empty state | `rehab_program_screen.dart` |
| P1 — Readability | Trend / History / Insights cards white-on-dark in dark mode | `health_screen.dart` |
| P1 — Readability | Dev cards white-on-dark in dark mode | `profile_screen.dart` |
| P1 — Readability | Tab bar strip white-on-dark | `health_screen.dart` |
| P1 — Readability | Bottom nav bar white in dark mode | `home_screen.dart` |
| P2 — Functionality | Trends tab — `_expandedMetric` state + `AnimatedContainer` accordion | `health_screen.dart` |
| P2 — Functionality | Trends tab — `fl_chart` LineChart inside each expanded card (empty-data safe) | `health_screen.dart` |
| P2 — Functionality | Trends tab — wire to real `/vitals/history` + `7D/30D` toggle | `health_screen.dart` |
| P2 — Functionality | History tab — filter chips (All/Vitals/Workouts/Alerts) with client-side filter | `health_screen.dart` |
| P2 — Functionality | History tab — load + merge vitals + activities, group by relative date | `health_screen.dart` |
| P2 — Functionality | History tab — integrate alert events from `AlertPollingService` | `health_screen.dart` |
| P2 — Functionality | Insights tab — wire to AI Coach, keep hardcoded fallback | `health_screen.dart` |
| P2 — Functionality | Recovery screen entry point from Home dashboard quick-actions | `home_screen.dart` |
| P2 — Functionality | Device Pairing — hide BLE/HealthKit rows on web, show mobile-only notice | `device_pairing_screen.dart` |
| P3 — Polish | Health Score hardcoded value | `health_screen.dart` |
| P3 — Polish | Share/Export button | `health_screen.dart` |
| P3 — Polish | Typography brightness helpers for caption/bodySmall | `typography.dart` |
| P3 — Polish | Global `AppBarTheme.foregroundColor` conflict | `theme.dart` |
