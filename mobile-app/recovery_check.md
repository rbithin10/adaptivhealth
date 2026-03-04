# Recovery Screen — Implementation Checklist

**FOR INTERNAL USE ONLY – NOT FOR SUBMISSION**

Each item is checked only when the code is written, compiles without errors,
and the logic integrates correctly with the surrounding ecosystem.

---

## Items

- [x] **1. Entry & data flow** — accept optional `sessionId`, parallel `Future.wait` across `getActivityById`/`getActivities`, `getLatestVitals`, `getLatestRecommendation`; empty-state guard when no sessions exist
- [x] **2. Post-workout vitals banner** — card at top showing live HR + SpO2 from `getLatestVitals()`, colour-coded status against resting HR
- [x] **3. Recovery score ring (CustomPainter)** — proper arc sweep proportional to score; three sub-components (HR recovery, HRV, intensity) labelled below the ring
- [x] **4. Session summary grid (real data)** — values sourced from activity API response; "Recovered: Yes" card replaced with HRV from vitals
- [x] **5. Breathing technique selector** — horizontal chip row for all 4 BreathingType variants; each updates controller duration, phase thresholds, title, and description
- [x] **6. Personalised recommendation card** — `getLatestRecommendation()` title + content; graceful fallback if endpoint returns nothing
- [x] **7. Contextual recovery tips** — tips chosen at runtime based on session duration, peak HR, and HRV; cardiac-rehab tip always shown
- [x] **8. Bottom action bar** — "Log Recovery Meal" (navigates to Nutrition tab) + "Message Care Team" (navigates to Messaging tab)

---

## Ecosystem integration points verified

- [x] `FitnessPlansScreen` passes `sessionId` when navigating to `RecoveryScreen`
- [x] `RecoveryScreen` constructor keeps `ApiClient` required param — no breaking change
- [x] Dark-mode colours use `AdaptivColors.getXxx(brightness)` helpers throughout
- [x] Typography uses `AdaptivTypography.*` — no inline `TextStyle` for sizes/weights
- [x] All API calls catch `DioException` / general exceptions and show an error banner rather than crashing
- [x] `AnimationController` disposed correctly in all branches (breathing active or idle)
- [x] `BreathingType` enum fully consumed — no dead variants
- [x] Navigation callbacks for bottom actions are optional (`onNavigateToTab`) so screen works standalone

---

## Pass log

| Pass | Result |
|------|--------|
| 1 | Full rewrite of `recovery_screen.dart` — all 8 items implemented; old duplicate class body removed |
| 2 | Both call sites in `FitnessPlansScreen` and `HomeScreen` verified — `sessionId` correctly optional; no breaking API change |
| 3 | `get_errors` on `recovery_screen.dart` → **0 errors**; `get_errors` on entire `lib/` → **0 errors** |
