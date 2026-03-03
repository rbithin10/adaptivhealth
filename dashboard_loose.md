# Dashboard Loose Ends Checklist

## Done so far
- [x] Completed full loose-ends audit across `web-dashboard/src`.
- [x] Identified 10 concrete issues (bugs, dead code, typing gaps, maintainability).
- [x] Prioritized fixes to execute from low-risk/high-impact to larger refactors.
- [x] Created and initialized this checklist for live tracking.
- [x] Completed implementation + validation pass for all 10 items.
- [x] Verified `web-dashboard/src` has no current TypeScript diagnostics.

## Doing now
- [x] Updating checklist state before each implementation batch.
- [x] Starting implementation pass item-by-item with validation after each batch.

## Notes
- No code fixes are marked complete until the corresponding file edits are applied and validated.
- Last status update: 2026-03-03

## Remaining items
- [x] 1) Resolve `/register` route dead-code mismatch (either wire route or remove page).
- [x] 2) Remove dead `AdvancedMLPanel` status by either deleting it or integrating it.
- [x] 3) Fix patient risk data logic so risk is not read from `User` fallback defaults.
- [x] 4) Reduce `as any` usage by strengthening shared types (`User` and related usage).
- [x] 5) Remove font-family conflict between `App.css` and global/theme styles.
- [x] 6) Remove or use dead exports in `theme/typography.ts` (`fontImport`, `fontFamily`).
- [x] 7) Replace `any[]` consent state in `DashboardPage` with proper interface typing.
- [x] 8) Replace `any` state result types in `PatientDetailPage` with strict interfaces.
- [x] 9) Reduce `PatientDetailPage` maintainability debt by extracting/integrating panelized UI.
- [x] 10) Align background color mismatch (`#F5F7FA` vs `#F9FAFB`).

## Final status
- [x] All listed loose ends are completed.
