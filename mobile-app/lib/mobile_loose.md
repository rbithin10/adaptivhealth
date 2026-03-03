# mobile_loose

Status legend: [x] done, [~] in progress, [ ] remaining, [!] blocked

## Done so far
- [x] Completed a full loose-ends scan of `mobile-app/lib`.
- [x] Identified and prioritized 7 concrete loose-end items.

## In progress now
- [x] Checklist completed.

## Checklist
1. [x] Fix provider scope so all pushed routes inherit `AuthProvider`, `ChatProvider`, `EdgeAiStore`, `VitalsProvider`, and `ChatStore`.
2. [x] Remove dead splash no-op logic in `main.dart`.
3. [x] Normalize Android notification icon config (`@mipmap/ic_launcher`) in notification service.
4. [x] Remove dead developer utility file `lib/dev_utils/reset_onboarding.dart`.
5. [x] Resolve unused `assets/exercises/` by wiring exercise-specific images in workout UI.
6. [x] Add smoke widget tests for key tabs/screens (nutrition, workout, messaging).
7. [x] Clean empty folders under `lib` (`config/`, `screens/home/`) by adding explicit placeholder docs.

## Progress log
- Checklist file created.
- Confirmed core runtime fixes already present in codebase (`main.dart`, `notification_service.dart`).
- Wired workout activity imagery to `assets/exercises/*.png` and simplified activity image resolver.
- Confirmed `lib/dev_utils/` no longer contains stale reset utility file.
- Added smoke tests in `test/screens/core_tabs_smoke_test.dart` for workout, nutrition, and messaging.
- Added placeholder docs to `lib/config/` and `lib/screens/home/` so those folders are intentional and self-documented.
