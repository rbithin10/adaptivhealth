# UX Issues – Fix Checklist

> FOR INTERNAL USE ONLY – NOT FOR SUBMISSION
> Last updated: 2026-03-06

---

## Build Status

**✅ All compile errors resolved.**
- `recovery_screen.dart` — missing `Container` closing paren added. Fixed.
- `health_screen.dart` — missing `Container` closing paren added. Fixed.
- `device_pairing_screen.dart` — missing `Container` closing paren added. Fixed.

---

## Remaining Open Tasks

---

## Issue 1 – Dark Mode Text Readability

**Status:** Architecture fix complete. Primary hierarchy styles (`screenTitle`, `sectionTitle`, `cardTitle`, `body`, `heroNumber`, `metricValue`, `metricValueSmall`, `subtitle1`, `subtitle2`) have no hardcoded color and inherit `colorScheme.onSurface`. Muted styles expose `xxxFor(Brightness)` helpers. All screens are covered.

- [ ] **1.14** Audit any `.copyWith(color: const Color(0xFF...))` overrides across screens that re-introduce hardcoded light colors (secondary pass — lower priority).

---

## Issue 2 – Missing Back Button on Workout History Screen

**Status:** ✅ Fully resolved. `automaticallyImplyLeading: false` removed; `foregroundColor` set to `AdaptivColors.getTextColor(brightness)`.

---

## Issue 3 – Background Images

**Status:** All screens have background images applied. All screens in scope confirmed implemented.

- [ ] **3.11** Verify that card/container surfaces in each screen use semi-transparent backgrounds (not solid white/black) so the background image remains subtly visible.

---

## Issue 4 – Hamburger Icon (Drawer Toggle) Too Light to See

**Status:** `theme.dart` light-mode `foregroundColor` is now `AdaptivColors.white`; `home_screen.dart` AppBar gradient is brightness-aware with explicit `iconTheme`.

- [ ] **4.3** Confirm the hamburger icon passes WCAG AA contrast ratio (at least 3:1) against the AppBar background in both light and dark modes.

---

## Notes

- The `home/` subdirectory inside `screens/` may contain sub-widgets for the home tab — check for any hardcoded text colors there too.
- Card `color:` overrides that use `Colors.white` or `const Color(0xFFFFFFFF)` will appear as bright blobs in dark mode — replace with `AdaptivColors.getSurfaceColor(brightness)`.
- After all fixes, do a full dark/light toggle pass on a physical device or emulator to catch any missed occurrences.
---

## Issue 5 – Platform._operatingSystem Crash on Flutter Web (P0)

**Status:** ✅ Fully resolved.

Root cause: `dart:io Platform` is unavailable on Flutter Web. All usages were in build/service methods, causing immediate crash on web launch.

- [x] **5.1** Created `lib/config/platform_guard.dart` — web-safe `isAndroid`, `isIOS`, `isWeb`, `isMobile`, `safeOsVersion` helpers using `kIsWeb` guard.
- [x] **5.2** `ble_service.dart` — removed `dart:io`, replaced `Platform.isAndroid` with `isAndroid`.
- [x] **5.3** `ble_permission_handler.dart` — removed `dart:io`, replaced all 4 `Platform.isAndroid/isIOS` usages + `Platform.operatingSystemVersion` → `safeOsVersion`.
- [x] **5.4** `health_service.dart` — removed `dart:io`, replaced `!Platform.isIOS && !Platform.isAndroid` → `!isMobile` (both occurrences).
- [x] **5.5** `device_pairing_screen.dart` — removed `dart:io`, replaced 3× `Platform.isIOS` usages, added web-only BLE notice with `if (kIsWeb) … else …` guard around HealthKit section.

---

## Issue 6 – RenderFlex Overflow 158px on Device Pairing Screen (P1)

**Status:** ✅ Resolved.

- [x] **6.1** Divider label "Or connect a BLE heart rate monitor directly" was not in a `Flexible` — caused overflow on narrow screens. Wrapped in `Flexible(child: Text(…, overflow: TextOverflow.ellipsis))` and shortened to "Or connect a BLE device directly".

---

## Issue 7 – /rehab/current-program 404 (P1)

**Status:** ✅ Already implemented in existing code — no change required.

- [x] **7.1** `rehab_program_screen.dart` already has `_buildNoProgram()` empty-state widget and 404 handling in `_loadProgram()`. Verified and confirmed complete.

---

## Issue 8 – AppBar / Title Invisible in Wrong Theme Mode (P0)

**Status:** ✅ Fully resolved.

- [x] **8.1** `health_screen.dart` AppBar missing `foregroundColor` — title and back arrow were invisible in light mode. Added `foregroundColor: AdaptivColors.getTextColor(brightness)`. Share icon updated to `getSecondaryTextColor(brightness)`.
- [x] **8.2** `home_screen.dart` "Adaptiv Health" title used hardcoded `AdaptivColors.text900` (near-black), invisible on dark AppBar. Changed to `AdaptivColors.getTextColor(brightness)`.

---

## Issue 9 – Dev Cards and Key Surfaces White in Dark Mode (P1)

**Status:** ✅ Fully resolved.

- [x] **9.1** `health_screen.dart` — `_buildTrendCard()`, `_buildHistoryItem()`, `_buildInsightCard()`: added `Brightness brightness` param; replaced `AdaptivColors.white` / `border300` with `getSurfaceColor` / `getBorderColor`. All call sites updated.
- [x] **9.2** `health_screen.dart` — `_TabBarDelegate`: added `brightness` field; tab bar label/indicator colors now brightness-aware; `shouldRebuild` compares brightness.
- [x] **9.3** `health_screen.dart` — Edge AI card wrapper in `_buildVitalsSection()`: `AdaptivColors.white` / `border300` fixed.
- [x] **9.4** `home_screen.dart` — `BottomNavigationBar backgroundColor: Colors.white` → `AdaptivColors.getSurfaceColor(brightness)`.
- [x] **9.5** `profile_screen.dart` — `_buildEdgeAiSection()`, `_buildMockVitalsSection()`, `_buildDeveloperUtilities()`, `_buildMedicationRemindersSection()`: added `brightness` local var; `AdaptivColors.white` / `border300` replaced with `getSurfaceColor` / `getBorderColor`; caption text uses `getSecondaryTextColor(brightness)`.