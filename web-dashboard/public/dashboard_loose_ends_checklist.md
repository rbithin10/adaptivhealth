# Dashboard Loose Ends Completion Checklist

Last updated: March 2, 2026

## Implementation Checklist

- [x] Add role-based route protection for dashboard routes (`/admin`, `/patients`, `/patients/:patientId`, `/messages`).
- [x] Remove public dashboard registration route exposure and redirect `/register` to login.
- [x] Enforce clinician-only access in patient list page load flow.
- [x] Enforce clinician-only access in messaging page load flow.
- [x] Wire alert resolve action in patient detail alert history UI.
- [x] Remove dead/unused API wrappers from web dashboard `api.ts`.
- [x] Add/adjust tests for updated access control behavior.

## Notes

- This checklist tracks only dashboard-side loose ends identified in the audit pass.
- Backend contract changes were not required for these fixes.