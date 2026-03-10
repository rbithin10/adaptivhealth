# pages/ — Full-Page Views

Each file in this folder is a complete page that the user sees. The app router (`App.tsx`) maps URL paths to these pages.

## Files

| File | Purpose |
|------|---------|
| `LoginPage.tsx` | The login form — email and password entry, plus a "Forgot Password" option |
| `RegisterPage.tsx` | The registration form — create a new account with name, email, password, and optional details |
| `ResetPasswordPage.tsx` | The password reset confirmation page — users arrive here from a reset email link |
| `DashboardPage.tsx` | The main clinician dashboard — overview stats, patient monitoring coverage, alert management, and charts |
| `AdminPage.tsx` | Admin-only page — create users, reset passwords, deactivate accounts, and assign clinicians to patients |
| `PatientsPage.tsx` | The patient list — searchable, filterable table of all patients with risk badges and quick actions |
| `PatientDetailPage.tsx` | Detailed view of a single patient — vitals, risk assessment, alerts, ML analysis, and medical profile |
| `PatientDashboardPage.tsx` | A simplified patient-facing dashboard showing their own health stats and history |
| `MessagingPage.tsx` | Secure messaging between patients and clinicians — inbox view with real-time message threads |

## Test Files

Each page has a corresponding `.test.tsx` file that verifies the page renders correctly and handles user interactions.
