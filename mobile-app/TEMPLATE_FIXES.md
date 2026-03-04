# Template Fixes — Live Data Integration Plan

**FOR INTERNAL USE ONLY — NOT FOR SUBMISSION**

This document tracks every UI section that currently renders hardcoded or
static template data instead of real data from the API or the on-device
pipeline. Each item has a root-cause analysis, a concrete implementation
plan, and a task checklist.

---

## Overview of Issues

| # | Location | Problem | Priority |
|---|---|---|---|
| ~~1~~ | ~~`fitness_plans_screen.dart` — `_buildWeeklySummary`~~ | ~~Active days, minutes, calories, and workout-goal progress are fully hardcoded~~ | ~~High~~ ✅ |
| ~~2~~ | ~~`fitness_plans_screen.dart` — `_getGenericPlans`~~ | ~~Fallback plans are static and not personalised to profile~~ | ~~Medium~~ ✅ |
| ~~3~~ | ~~`recipe_library_screen.dart`~~ | ~~Recipe catalog is loaded from a local bundled JSON, no backend~~ | ~~Medium~~ ✅ (Phase A) |
| ~~4~~ | ~~`home_screen.dart` — `_buildVitalsGrid` HRV~~ | ~~HRV value is hardcoded `'45'`; never read from API~~ | ~~High~~ ✅ |
| ~~5~~ | ~~`home_screen.dart` + `health_screen.dart` — VitalCard trends~~ | ~~Mini-sparkline arrays use 5 fake historical points~~ | ~~Medium~~ ✅ |
| ~~6~~ | ~~`health_screen.dart` — `_getDemoTrends`~~ | ~~Demo trend data shown in charts with no label when history is empty~~ | ~~Medium~~ ✅ |
| ~~7~~ | ~~`health_screen.dart` — `_staticInsights`~~ | ~~Offline AI insight fallback is unbranded generic advice; not cached~~ | ~~Medium~~ ✅ |
| ~~8~~ | ~~`home_screen.dart` — "View All" label~~ | ~~Non-interactive decorative label looks like a navigation button~~ | ~~Low~~ ✅ |
| ~~9~~ | ~~`screens/home/` folder~~ | ~~Folder is an empty placeholder; `home_screen.dart` is 2100+ lines~~ | ~~Low~~ ✅ |

---

## Fix 1 — Weekly Activity Summary (Fitness Plans Screen)

### Problem
`_buildWeeklySummary()` displays three stat chips (Active Days, Minutes,
Calories) and a weekly progress bar. All values are compile-time constants:
`'4'`, `'120'`, `'680'`, `0.8`. The backend `GET /activities` endpoint
already returns a list of sessions with `duration_minutes`,
`calories_burned`, `start_time`, and `status` fields. No dedicated
`/activities/summary` endpoint exists in the backend, but the data needed
can be derived entirely from the full list that `_loadPlans()` indirectly
triggers.

### Solution
Compute the weekly summary **client-side** from the activity list that is
already fetched during the Fitness Plans screen load. Because `_loadPlans()`
already calls `apiClient.getLatestRecommendation()`, we add a parallel call
to `apiClient.getActivities(limit: 50)` and derive the stats in a pure Dart
helper. This requires no backend changes.

**Helper logic:**

```dart
class _WeekStats {
  final int activeDays;
  final int totalMinutes;
  final int totalCalories;
  final int sessionsCompleted;
  final int sessionsGoal; // default 5
}

_WeekStats _computeThisWeek(List<Map<String, dynamic>> activities) {
  final now   = DateTime.now();
  final monday = now.subtract(Duration(days: now.weekday - 1));
  final weekStart = DateTime(monday.year, monday.month, monday.day);

  final thisWeekDays = <int>{};
  int totalMin = 0;
  int totalCal = 0;
  int sessions = 0;

  for (final a in activities) {
    final ts = DateTime.tryParse(a['start_time'] ?? '');
    if (ts == null || ts.isBefore(weekStart)) continue;
    thisWeekDays.add(ts.weekday);
    totalMin += (a['duration_minutes'] as num?)?.toInt() ?? 0;
    totalCal += (a['calories_burned']  as num?)?.toInt() ?? 0;
    sessions++;
  }

  return _WeekStats(
    activeDays:         thisWeekDays.length,
    totalMinutes:       totalMin,
    totalCalories:      totalCal,
    sessionsCompleted:  sessions,
    sessionsGoal:       5,
  );
}
```

### Task List

- [x] ~~**F1-a** — Add `_activities` list field to `_FitnessPlansScreenState`~~
- [x] ~~**F1-b** — In `_loadPlans()`, call `apiClient.getActivities(limit: 50)` in the same `try` block and store result in `_activities`~~
- [x] ~~**F1-c** — Add `_WeekStats` data class and `_computeThisWeek()` helper to the file~~
- [x] ~~**F1-d** — In `_buildWeeklySummary()`, replace the three hardcoded `_buildSummaryItem` values and the `0.8` progress value with computed values from `_computeThisWeek(_activities)`~~
- [x] ~~**F1-e** — Show `—` or `0` gracefully when `_activities` is empty (new user)~~
- [x] ~~**F1-f** — Display session goal progress as `'$sessionsCompleted/$sessionsGoal sessions'`~~

---

## Fix 2 — Personalised Fallback Fitness Plans

### Problem
When the backend recommendation API fails, `_getGenericPlans()` returns
three static `FitnessPlan` objects with `confidence: 0.0`. These plans are
identical for every user (Zone 2 Training / Yoga / Strength Basics),
regardless of age, rehab phase, or activity level.

### Solution
Make the fallback **profile-aware**. The user profile (age, activity_level,
rehab_phase) is fully available via `apiClient.getCurrentUser()`, which is
already called elsewhere in the app. Cache the profile in
`_FitnessPlansScreenState` alongside `_loadPlans()`, then pass relevant
fields to a `_buildProfileAwareFallback(profile)` method that chooses
appropriate plans based on:
- `rehab_phase` in (`phase_2_light`, `phase_3_moderate`) → gentle walking or
  chair exercises instead of cycling or HIIT
- `activity_level` in (`sedentary`, `lightly_active`) → shorter durations
- `age >= 60` → lower HR zone targets

No backend changes required. This is pure Dart logic.

### Task List

- [x] ~~**F2-a** — Add `_userProfile` field (`Map<String, dynamic>?`) to `_FitnessPlansScreenState`~~
- [x] ~~**F2-b** — In `_loadPlans()`, load profile via `apiClient.getCurrentUser()` and store to `_userProfile`~~
- [x] ~~**F2-c** — Rename `_getGenericPlans()` to `_buildProfileAwareFallback(Map<String, dynamic>? profile)` and implement conditional plan selection~~
- [x] ~~**F2-d** — For rehab users: substitute walking + chair exercises + stretching plans~~
- [x] ~~**F2-e** — Scale `duration` based on `activity_level` (sedentary → 15–20 min, active → 30–45 min)~~
- [x] ~~**F2-f** — Set `confidence: 0.0` label to show `'Offline — offline plan'` instead of a percentage badge in the UI to be transparent with the user~~

---

## Fix 3 — Recipe Library Live Data

### Problem
`RecipeLibraryScreen._loadRecipes()` reads exclusively from
`assets/data/recipes.json` — a bundled file with a fixed set of recipes. The
backend does not currently expose a recipe catalog endpoint. The meal-logging
button does post to the API, but the catalog itself is never updated.

### Solution — Two-phase approach

**Phase A (immediate):** Keep the local JSON as a seeded fallback. Expand the
asset file to include more varied, medically appropriate recipes across all
four tags. Add version metadata to the JSON so we know when to refresh.

**Phase B (medium-term, requires backend work):** Add
`GET /api/v1/nutrition/recipes?tag={tag}` to the backend (FastAPI route in
`app/api/nutrition.py`). The mobile app will try the backend first and fall
back to the bundled JSON. This mirrors the pattern used by
`_loadPlans() / _getGenericPlans()`.

**Backend endpoint spec (Phase B):**

```
GET /api/v1/nutrition/recipes
Query params: tag (optional), limit (default 20)
Response: [ { name, description, meal_type, calories, protein, carbs, fat, tags, steps } ]
```

### Task List

- [x] ~~**F3-a** — Expand `assets/data/recipes.json` to ≥ 20 entries covering all four tags: Heart Healthy, High Fiber, Omega-3 Rich, Anti-Inflammatory~~
- [x] ~~**F3-b** — Add `"version": 2` and `"last_updated": "2025-07-15"` metadata to the JSON root so stale detection is possible~~
- [x] ~~**F3-c** — Update `_loadRecipes()` parser to handle both the legacy array format and the v2 versioned-object format~~
- [ ] **F3-d** — Add `getRecipes({String? tag})` method to `ApiClient` targeting `GET /api/v1/nutrition/recipes` (returns empty on 404 so Phase B back-compat is safe)
- [ ] **F3-e** *(backend, Phase B)* — Add `GET /api/v1/nutrition/recipes` FastAPI route in `app/api/nutrition.py` with a static list or database-backed catalog
- [ ] **F3-f** *(backend, Phase B)* — Register the route in `app/main.py`

---

## Fix 4 — HRV on the Home Screen Vitals Grid

### Problem
In `home_screen.dart _buildVitalsGrid()`, the HRV `VitalCard` is wired as:

```dart
value: '45',
unit: 'ms',
status: VitalStatus.safe,
```

The value `45` never changes. The `getLatestVitals()` response already
includes an `hrv` field (confirmed in `api_client.dart` line 456 and the
`health_screen.dart` implementation). The fix is a single line change
in `_buildVitalsGrid()` to read `hrv` from the `vitals` map passed in.

### Task List

- [x] ~~**F4-a** — Add `required int hrv` parameter to `_buildVitalsGrid()` signature~~
- [x] ~~**F4-b** — In `_buildHomeTab()`, extract `hrv` from `vitals` map with safe fallback: `final hrv = _safeToInt(vitals['hrv'], 0);`~~
- [x] ~~**F4-c** — Pass `hrv: hrv` into `_buildVitalsGrid()` call~~
- [x] ~~**F4-d** — Replace `value: '45'` with `value: hrv > 0 ? hrv.toString() : '—'`~~
- [x] ~~**F4-e** — Replace `status: VitalStatus.safe` with real logic: `hrv > 40 ? VitalStatus.safe : hrv > 20 ? VitalStatus.caution : VitalStatus.warning`~~
- [ ] **F4-f** — Add the HRV sparkline: extract last-6-readings from `_vitalsHistoryNotifier.value` via a small helper (reused by Fix 5)

---

## Fix 5 — VitalCard Mini-Sparklines from Real History

### Problem
All `VitalCard` widgets on both `home_screen.dart` and `health_screen.dart`
pass 5 hardcoded historical points as the `trend` array. Only the last value
in the array is the real current reading. This means the sparkline always
shows the same generic healthy-looking shape regardless of the patient's
actual history.

```dart
trend: [68.0, 70.0, 72.0, 71.0, 73.0, hr.toDouble()],  // fake history
```

### Solution
Add a `_sparklinesFrom()` pure Dart helper that extracts the most recent N
readings for a named metric from the `vitalsHistory` list that is already
loaded by `_combinedFuture` / `_vitalHistoryFuture`. If fewer than N readings
are available, the helper left-pads with the first known value, ensuring the
sparkline always has the correct number of points.

```dart
List<double> _sparklinesFrom({
  required List<dynamic> history,
  required String field,
  required double current,
  int points = 6,
  double fallback = 0,
}) {
  final values = history
      .reversed
      .take(points - 1)
      .map((v) => (v is Map ? (v[field] as num?)?.toDouble() : null) ?? fallback)
      .toList()
      .reversed
      .toList();
  while (values.length < points - 1) values.insert(0, fallback);
  values.add(current);
  return values;
}
```

### Task List

- [x] ~~**F5-a** — Add `_sparklinesFrom()` helper as a private method in `_HomeScreenState` in `home_screen.dart`~~
- [x] ~~**F5-b** — In `_buildVitalsGrid()`, extract vitals history from `_vitalsHistoryNotifier.value` and pass it to `_sparklinesFrom` for HR, SpO2, and HRV trend arrays~~
- [x] ~~**F5-c** — Add the same `_sparklinesFrom()` helper to `_HealthScreenState` in `health_screen.dart`~~
- [x] ~~**F5-d** — In `health_screen.dart _buildVitalsSection()`, replace four hardcoded trend arrays with `_sparklinesFrom()` calls using the `vitalsHistory` from `_healthData`~~
- [x] ~~**F5-e** — Handle the edge case of an empty history list: all 6 values should equal `current` so the sparkline is flat (not zero-value)~~

---

## Fix 6 — Demo Trend Label in Health Screen Charts

### Problem
When `vitalsHistory` is empty (first login, or API not yet synced),
`_buildSpots()` calls `_getDemoTrends()` which returns a static 7-day
dataset showing ideal healthy flat values. This fabricated data is shown
inside the same chart UI as real data with no visible distinction. A
clinician or user could mistake this for real readings.

### Solution
A `_hasRealHistory` boolean getter already exists in the code and is passed
to `_buildTrendCard()` as `isDemoData`. The chart line is already rendered at
`0.45` opacity when `isDemoData == true`. What is missing is:
1. A clearly visible banner above the chart when demo data is active
2. A meaningful message explaining why and when it will auto-fill

### Task List

- [x] ~~**F6-a** — In `_buildTrendCard()`, when `isDemoData == true`, add a `Container` banner above the chart body reading `'No readings yet — chart will fill automatically as vitals sync'` with a `Icons.info_outline` icon and soft amber styling~~
- [x] ~~**F6-b** — Add a `Text` watermark positioned in the center of the chart area saying `'Sample data'` when `isDemoData == true`~~
- [x] ~~**F6-c** — Rename `_getDemoTrends()` to `_getSampleTrends()` so the intent is clear in the codebase~~
- [x] ~~**F6-d** — Add a comment above `_getSampleTrends()` documenting that this is display-only seed data and must never be uploaded or used for risk computation~~

---

## Fix 7 — AI Insights Caching and Transparent Offline Fallback

### Problem
`health_screen.dart _staticInsights()` returns 4 generic cardiovascular tips
that are identical for every user. When shown, they are visually
indistinguishable from a real AI-generated response. There is no indication
that these are offline fallbacks. Additionally, if the user loaded real AI
insights in a previous session, those personalised results are discarded on
app restart.

### Solution — Two changes

**A — Labelled offline state:**  
When `_aiInsights.isEmpty` after an attempted load, show a single labelled
card: `'AI Coach offline — check your connection and retry'` rather than
silently substituting generic advice. The existing `_staticInsights()` can be
kept as labelled "general tips" in a separate section clearly below an empty
AI card.

**B — SharedPreferences cache:**  
Persist the last successful AI insights response to
`SharedPreferences` under a key like `ai_insights_cache_json`. On screen
open, load from cache immediately (shows stale but real data), then
attempt a live refresh in background. Update the cache on each successful
fetch.

```dart
// Persist
final prefs = await SharedPreferences.getInstance();
await prefs.setString('ai_insights_cache_json', jsonEncode(_aiInsights));

// Restore
final cached = prefs.getString('ai_insights_cache_json');
if (cached != null) {
  _aiInsights = List<Map<String, dynamic>>.from(jsonDecode(cached));
}
```

### Task List

- [x] ~~**F7-a** — Add `shared_preferences` import to `health_screen.dart` (it is already in `pubspec.yaml`)~~
- [x] ~~**F7-b** — Add `_loadCachedInsights()` private async method that reads from SharedPreferences and populates `_aiInsights` if the cache exists~~
- [x] ~~**F7-c** — Call `_loadCachedInsights()` in `initState()` so the screen opens with last-known-good data instantly~~
- [x] ~~**F7-d** — In `_loadAiInsights()`, after a successful parse, call `_saveInsightsCache(_aiInsights)` to persist~~
- [x] ~~**F7-e** — Replace the silent fallback to `_staticInsights()` in `_buildInsightsTab()` with an explicit offline-state card showing `'No AI insights available — tap to retry'`~~
- [x] ~~**F7-f** — Keep `_staticInsights()` but render it under a heading `'General Cardiovascular Tips'` as a clearly labelled supplement, not a replacement~~
- [x] ~~**F7-g** — Add `'Cached — updated {relative time}'` subtitle when showing cached insights so the user knows the data age~~

---

## Fix 8 — "View All" Vitals Label Navigation

### Problem
In `home_screen.dart _buildVitalsGrid()`, the `'View All'` text label in the
vitals section header has no `GestureDetector`. It appears to be a tappable
link but does nothing when tapped.

### Solution
Wrap the existing `Text('View All', ...)` in a `GestureDetector` with
`onTap: _navigateToHealth`. The `_navigateToHealth()` method already exists
and pushes `HealthScreen` onto the navigator stack.

### Task List

- [x] ~~**F8-a** — Wrap `Text('View All', ...)` in a `GestureDetector(onTap: _navigateToHealth)` in `_buildVitalsGrid()`~~

---

## ~~Fix 9 — Home Screen Decomposition into `screens/home/`~~ ✅

### Problem
`home_screen.dart` is 2104 lines long. The `screens/home/` directory exists
as a documented placeholder (it has a `README.md`) but contains no Dart
files. The monolithic file makes navigation, testing, and incremental updates
difficult. The structure also makes it impossible to write meaningful widget
tests for individual home sections.

### Solution
Extract the major sections of `_buildHomeTab()` into dedicated widget files
inside `screens/home/`. Each extracted widget receives only the data it needs
(no direct `ApiClient` unless it needs its own async call).

**Target file structure:**

```
screens/home/
  home_greeting_card.dart       — Good morning card
  home_vitals_grid.dart         — SpO2 / BP / HRV VitalCard row
  home_heart_rate_ring.dart     — Central HR ring widget
  home_quick_actions.dart       — 4-button quick-action row
  home_rehab_card.dart          — Rehab program status card
  home_recent_activity.dart     — Recent activity list
  home_sparkline.dart           — Heart rate sparkline chart
  home_recommendation_card.dart — Compact AI recommendation card
```

`home_screen.dart` becomes an orchestrator: it owns state, futures, and
navigation, and passes data down to these stateless or minimally-stateful
widgets.

### Task List

- [x] ~~**F9-a** — Extract `_buildHeartRateRing()` and its supporting method `_buildStatusBadge()` into `screens/home/home_heart_rate_ring.dart` as a `HomeHeartRateRing` stateless widget~~
- [x] ~~**F9-b** — Extract `_buildVitalsGrid()` into `screens/home/home_vitals_grid.dart` as `HomeVitalsGrid`, with `spo2`, `systolicBp`, `diastolicBp`, `hrv` and `history` as constructor parameters~~
- [x] ~~**F9-c** — Extract `_buildQuickActions()` into `screens/home/home_quick_actions.dart` as `HomeQuickActions`; pass callbacks as `VoidCallback` parameters~~
- [x] ~~**F9-d** — Extract `_buildRehabCard()` into `screens/home/home_rehab_card.dart` as `HomeRehabCard`; pass user map and ApiClient~~
- [x] ~~**F9-e** — Extract `_buildRecentActivity()` into `screens/home/home_recent_activity.dart` as `HomeRecentActivity`; pass the future and helper methods~~
- [x] ~~**F9-f** — Extract `_buildHeartRateSparkline()` into `screens/home/home_sparkline.dart` as `HomeSparkline`~~
- [x] ~~**F9-g** — Extract `_buildRecommendationCard()` into `screens/home/home_recommendation_card.dart` as `HomeRecommendationCard`~~
- [x] ~~**F9-h** — In `home_screen.dart`, import all new widgets and replace inline build calls with the extracted widget classes~~
- [x] ~~**F9-i** — Verify app still builds and runs correctly after decomposition with `flutter analyze lib/` (zero errors)~~

---

## Implementation Order

Execute fixes in this sequence to minimise risk and merge conflicts:

1. **Fix 8** — 1 line change; eliminates a dead UI element immediately
2. **Fix 4** — 4 line changes; high-value, zero backend risk
3. **Fix 6** — Adds labelling only; purely additive, no logic change
4. **Fix 7** — Adds caching; purely additive, no logic change
5. **Fix 1** — Requires adding one API call inside existing `_loadPlans()`
6. **Fix 5** — Adds helper method; replaces hardcoded arrays
7. **Fix 2** — Profile-aware fallback; safe, no backend change
8. **Fix 3 Phase A** — Expand local JSON; no code change required
9. **Fix 3 Phase B** — Backend work; coordinate with backend engineer
10. **Fix 9** — Structural refactor; do last after all data fixes are stable

---

## Definition of Done (per fix)

- All hardcoded values replaced with values sourced from the API, device
  pipeline, or local cache derived from real data
- Graceful handling of empty/null state (new user, offline, API error)
- No console `debugPrint` errors for the affected screen during a normal
  authenticated session
- The screen renders correctly on both a cold launch (no prior data) and a
  warm re-open (cached or streamed data available)
