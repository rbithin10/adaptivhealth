# Admin & Patients Manual QA Checklist

Use this checklist to validate Admin CRUD, clinician assignment, and clinician-scoped patient list behavior in the web dashboard.

## Preconditions

- Backend running on configured API base URL.
- Web dashboard running and logged in users available:
  - Admin account
  - Clinician account
  - At least one patient account
- Browser DevTools Network tab open (optional but recommended).

---

## 1) Admin: Create User

1. Login as **Admin** and open `/admin`.
2. Click **Create New User**.
3. Enter valid values:
   - Email: unique email
   - Full Name
   - Temporary Password (>= 8 chars)
   - Role: `patient` or `clinician`
4. Submit.

### Expected
- Success message appears: user created.
- New user appears in table without manual refresh.
- Network call:
  - `POST /api/v1/users/` returns `200`.

---

## 2) Admin: Update User

1. On `/admin`, locate a non-admin user row.
2. Click **Edit**.
3. Change one or more fields (name, age, gender, phone).
4. Click **Update**.

### Expected
- Success message appears: user updated.
- Updated values appear in the table after modal closes.
- Network call:
  - `PUT /api/v1/users/{user_id}` returns `200`.

---

## 3) Admin: Delete (Deactivate) User

1. On `/admin`, locate a non-admin active user.
2. Click **Deactivate**.
3. Confirm in the browser confirmation prompt.

### Expected
- Row refreshes with inactive state.
- User cannot be deactivated if it is the current admin account.
- Network call:
  - `DELETE /api/v1/users/{user_id}` returns `200`.

---

## 4) Admin: Assign Clinician to Patient

1. On `/admin`, find a row where role is **patient**.
2. In **Assign Clinician** column, click **Assign**.
3. Select a clinician from dropdown.
4. Click the checkmark button.

### Expected
- Success message appears.
- Assigned clinician name appears in the same row immediately.
- Assignment persists after page reload.
- Network call:
  - `PUT /api/v1/users/{patient_id}/assign-clinician?clinician_id={id}` returns `200`.

### Negative Checks
- Non-patient rows should show `—` in assignment column.
- If no clinician selected, submit button stays disabled.

---

## 5) Clinician-Filtered Patients Page

1. Login as **Clinician** and open `/patients`.
2. Observe listed rows.

### Expected
- Only users with patient role are shown.
- List should reflect backend clinician data isolation (assigned patients only for clinician role).
- No admin/clinician accounts shown in table rows.
- Network call should include patient role filter:
  - `GET /api/v1/users?page=1&per_page=200&role=patient`

### Search/Filter Checks
- Search by patient name and ID works.
- Risk filter buttons (`all`, `low`, `moderate`, `high`) update row list correctly.

---

## 6) Quick Regression Checks

- Admin role guard:
  - Non-admin user opening `/admin` is redirected away.
- Patients page view button:
  - Clicking **View** opens `/patients/{patient_id}` for listed patient.

---

## Pass Criteria

- All steps above match expected behavior with no console errors.
- API responses are successful for positive scenarios.
- UI updates occur without requiring manual hard refresh.
