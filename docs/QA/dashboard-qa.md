# Dashboard QA Checklists

Quick manual QA plans for web dashboard features.

---

## Admin CRUD QA Checklist (Web Dashboard)

Use this checklist to validate admin user management in the web dashboard.

### Preconditions
- Admin account exists and can log in
- At least one non-admin user exists
- Backend running on http://localhost:8080

### Access Control
- [ ] Non-admin users are redirected to `/dashboard`
- [ ] Admin users can access `/admin` and see the user table

### Create User
- [ ] Create patient with valid email + password + name
- [ ] Create clinician with valid email + password + name
- [ ] Duplicate email shows error (400)
- [ ] Weak password shows error (min 8 chars + letter + digit)

### Read / Refresh
- [ ] User list loads with pagination values
- [ ] Table refreshes after create/update/deactivate

### Update User
- [ ] Update name, age, gender, phone
- [ ] Invalid age (<1 or >120) rejected
- [ ] Invalid gender rejected (must match allowed list)

### Reset Password
- [ ] Reset password works and success message shown
- [ ] Invalid password rejected with clear error

### Deactivate User
- [ ] Deactivate user succeeds and status updates
- [ ] Self-deactivation blocked with clear error

### UX / Feedback
- [ ] Loading states visible while submitting
- [ ] Buttons disabled during submit
- [ ] Error messages are visible and readable

### Automation Candidates
- Clinician/user role redirect (non-admin blocked from `/admin`)
- Create user success + table refresh
- Deactivate user blocked for self

---

## Patient Management QA Checklist (Web Dashboard)

Use this checklist to validate clinician-facing patient management (list, filters, details) in the web dashboard.

### Prep
- Clinician account exists and can log in
- At least 3 patients exist with varied ages and risk levels
- Backend running on http://localhost:8080

### Access Control
- [ ] Non-clinician users are blocked from patient list routes
- [ ] Clinician users can access patient list and detail pages

### Core Flows (List, View Details, Filters/Search)
- [ ] Patient list loads with name, age, and summary fields
- [ ] Selecting a patient opens the detail view
- [ ] Detail view loads vitals, risk, alerts, activities, and history sections
- [ ] Filters/search (if present) update the list and handle empty results

### Updates/Actions (If Implemented)
- [ ] Actions (e.g., consent review, alerts acknowledgement) update UI after success
- [ ] Refresh/reload works without stale data

### UX Feedback and Error Handling
- [ ] Loading indicators are shown for list and detail sections
- [ ] Partial failures show clear inline warnings (not blank panels)
- [ ] Errors are readable and do not block unrelated sections

### Automation Candidates
- Patient list loads and selecting a row opens details
- Detail view loads all major panels via API calls
- Filters/search return correct list and empty state

---

## Alerts & Safety Events QA Checklist

Use this checklist to validate alerts list, severity display, and acknowledgement flows.

### Prep
- At least 3 alerts exist with mixed severities (critical, warning, info)
- Backend running on http://localhost:8080

### Access Control
- [ ] Patients can see only their own alerts
- [ ] Clinicians can access patient alerts in dashboard

### Core Flows (List, View Details, Filters/Search)
- [ ] Alerts list loads with severity badges and timestamps
- [ ] Selecting an alert opens detail view (if present)
- [ ] Filters (severity, unread) update list correctly

### Updates/Actions (If Implemented)
- [ ] Acknowledge alert updates status and UI state
- [ ] Resolve alert (if available) updates status and list

### UX Feedback and Error Handling
- [ ] Loading states shown while fetching alerts
- [ ] Empty state shown when no alerts
- [ ] Errors are visible and do not crash the page

### Automation Candidates
- Severity filter returns correct alerts and empty state
- Acknowledge action updates status without full page reload
- Alert detail view renders correct fields for critical alerts
