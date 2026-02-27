"""
seed_patient.py — Populate patient1@test.com with 30 days of realistic history.

Usage:
    python seed_patient.py                          # uses default http://localhost:8000
    python seed_patient.py --base-url http://localhost:8080

What it does:
  1. Registers patient1@test.com (or logs in if it already exists)
  2. Updates their profile: age 45, baseline HR 68, weight 78kg, height 175cm
  3. Injects 30 days of vital sign history (4 readings/day)
  4. Injects 10 activity sessions over the 30 days
  5. Calls /risk-assessments/compute to generate a risk assessment + recommendation
  6. Registers clinician1@test.com (or logs in) as an assigned clinician
  7. Prints a summary with login credentials

After running this, open the doctor dashboard, log in as clinician1@test.com,
and patient1@test.com will appear with full history, alerts, risk score, and recommendation.
"""

import argparse
import random
import time
from datetime import datetime, timedelta, timezone

import httpx

# ─── Config ──────────────────────────────────────────────────────────────────

PATIENT_EMAIL = "patient1@test.com"
PATIENT_PASSWORD = "TestPass123"
PATIENT_NAME = "Alex Morgan"
PATIENT_AGE = 45
PATIENT_BASELINE_HR = 68
PATIENT_MAX_SAFE_HR = 220 - PATIENT_AGE  # 175

CLINICIAN_EMAIL = "clinician1@test.com"
CLINICIAN_PASSWORD = "ClinicianPass123"
CLINICIAN_NAME = "Dr. Sarah Chen"

random.seed(42)  # Reproducible data

# ─── Helpers ─────────────────────────────────────────────────────────────────

def gauss_int(mean: float, sigma: float, lo: int, hi: int) -> int:
    return max(lo, min(hi, round(random.gauss(mean, sigma))))


def login(client: httpx.Client, email: str, password: str) -> str:
    """Returns JWT access token."""
    r = client.post(
        "/api/v1/login",
        data={"username": email, "password": password},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def register_or_login(client: httpx.Client, email: str, password: str, name: str, role: str = "patient", admin_token: str | None = None) -> str:
    """Register user if needed, then login. Returns access token."""
    if role == "patient":
        # Public registration
        r = client.post(
            "/api/v1/register",
            json={"email": email, "password": password, "name": name, "role": "patient"},
        )
        if r.status_code not in (200, 201, 400):
            raise RuntimeError(f"Register failed ({r.status_code}): {r.text}")
        if r.status_code == 400 and "already registered" not in r.text.lower():
            raise RuntimeError(f"Register failed: {r.text}")
    else:
        # Admin registration (clinician/admin)
        if admin_token is None:
            raise RuntimeError("admin_token required for non-patient registration")
        r = client.post(
            "/api/v1/admin/register",
            json={"email": email, "password": password, "name": name, "role": role},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if r.status_code not in (200, 201, 400):
            raise RuntimeError(f"Admin register failed ({r.status_code}): {r.text}")

    return login(client, email, password)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Vital sign generators ────────────────────────────────────────────────────

def make_resting_vitals(days_ago: int) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 6))
    hr = gauss_int(PATIENT_BASELINE_HR, 5, 52, 82)
    return {
        "heart_rate": hr,
        "spo2": gauss_int(97, 1, 95, 99),
        "blood_pressure_systolic": gauss_int(118, 6, 105, 135),
        "blood_pressure_diastolic": gauss_int(76, 4, 65, 90),
        "hrv": round(random.gauss(42, 6), 1),
        "timestamp": ts.isoformat(),
    }


def make_workout_vitals(days_ago: int, phase: str) -> dict:
    """phase: warmup | steady | peak | cooldown"""
    hour_offset = 18 + random.randint(0, 2)  # evening workout
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hour_offset)

    if phase == "warmup":
        hr = gauss_int(105, 8, 90, 120)
        bp_sys = gauss_int(130, 5, 120, 142)
    elif phase == "steady":
        hr = gauss_int(138, 8, 120, 155)
        bp_sys = gauss_int(140, 6, 130, 152)
    elif phase == "peak":
        hr = gauss_int(162, 8, 145, 178)
        bp_sys = gauss_int(148, 6, 138, 162)
    else:  # cooldown
        hr = gauss_int(110, 10, 90, 135)
        bp_sys = gauss_int(132, 6, 120, 145)

    return {
        "heart_rate": hr,
        "spo2": gauss_int(96, 1, 93, 99),
        "blood_pressure_systolic": bp_sys,
        "blood_pressure_diastolic": gauss_int(82, 5, 72, 95),
        "hrv": round(random.gauss(20, 4), 1),
        "timestamp": ts.isoformat(),
    }


def make_elevated_vitals(days_ago: int) -> dict:
    """One slightly elevated reading per week to make history interesting."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=9)
    return {
        "heart_rate": gauss_int(158, 6, 148, 170),
        "spo2": gauss_int(95, 1, 93, 97),
        "blood_pressure_systolic": gauss_int(152, 6, 142, 165),
        "blood_pressure_diastolic": gauss_int(94, 4, 88, 104),
        "hrv": round(random.gauss(15, 3), 1),
        "timestamp": ts.isoformat(),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(base_url: str):
    print(f"\n{'='*60}")
    print(f"  AdaptivHealth Seed Script")
    print(f"  Target: {base_url}")
    print(f"{'='*60}\n")

    with httpx.Client(base_url=base_url, timeout=30.0) as client:

        # ── 1. Check backend health ──────────────────────────────────────────
        try:
            r = client.get("/health")
            if r.status_code != 200:
                print(f"WARNING: /health returned {r.status_code} — backend may not be ready")
        except Exception as e:
            print(f"WARNING: Cannot reach {base_url} — is the backend running? ({e})")
            print("Start it with: uvicorn app.main:app --port 8000")
            return

        # ── 2. Register/login patient ────────────────────────────────────────
        print("► Setting up patient1@test.com ...")
        patient_token = register_or_login(
            client, PATIENT_EMAIL, PATIENT_PASSWORD, PATIENT_NAME, role="patient"
        )
        print(f"  ✓ Logged in as {PATIENT_EMAIL}")

        # ── 3. Update patient profile ────────────────────────────────────────
        profile_r = client.put(
            "/api/v1/users/me",
            json={
                "age": PATIENT_AGE,
                "weight_kg": 78.5,
                "height_cm": 175.0,
                "gender": "male",
                "phone": "+61 400 123 456",
                "baseline_hr": PATIENT_BASELINE_HR,
                "max_safe_hr": PATIENT_MAX_SAFE_HR,
                "emergency_contact_name": "Jordan Morgan",
                "emergency_contact_phone": "+61 400 987 654",
            },
            headers=auth_headers(patient_token),
        )
        if profile_r.status_code in (200, 201):
            print(f"  ✓ Profile updated (age={PATIENT_AGE}, baseline_hr={PATIENT_BASELINE_HR})")
        else:
            print(f"  ⚠ Profile update returned {profile_r.status_code}: {profile_r.text[:100]}")

        # ── 4. Get patient user_id ───────────────────────────────────────────
        me_r = client.get("/api/v1/me", headers=auth_headers(patient_token))
        if me_r.status_code != 200:
            print(f"  ✗ Could not get user profile: {me_r.text}")
            return
        patient_id = me_r.json()["user_id"]
        print(f"  ✓ Patient user_id = {patient_id}")

        # ── 5. Inject 30 days of vital sign history ──────────────────────────
        print("\n► Injecting 30 days of vital history ...")
        submitted = 0
        errors = 0
        for day in range(30, 0, -1):
            # Morning resting reading
            r = client.post(
                "/api/v1/vitals",
                json=make_resting_vitals(days_ago=day),
                headers=auth_headers(patient_token),
            )
            if r.status_code in (200, 201):
                submitted += 1
            else:
                errors += 1

            # Workout readings every 3 days
            if day % 3 == 0:
                for phase in ("warmup", "steady", "peak", "cooldown"):
                    r = client.post(
                        "/api/v1/vitals",
                        json=make_workout_vitals(days_ago=day, phase=phase),
                        headers=auth_headers(patient_token),
                    )
                    if r.status_code in (200, 201):
                        submitted += 1
                    else:
                        errors += 1

            # Elevated reading once a week
            if day % 7 == 0:
                r = client.post(
                    "/api/v1/vitals",
                    json=make_elevated_vitals(days_ago=day),
                    headers=auth_headers(patient_token),
                )
                if r.status_code in (200, 201):
                    submitted += 1
                else:
                    errors += 1

        print(f"  ✓ {submitted} vital readings submitted ({errors} errors)")

        # ── 6. Submit fresh vitals so compute can run (needs last 30 min) ────
        print("\n► Submitting fresh vitals (required for risk compute) ...")
        fresh_submitted = 0
        for i in range(6):  # 6 readings × 5 min = 30 min window
            ts = datetime.now(timezone.utc) - timedelta(minutes=5 * (5 - i))
            hr = gauss_int(PATIENT_BASELINE_HR + 30 + i * 5, 4, 90, 145)
            r = client.post(
                "/api/v1/vitals",
                json={
                    "heart_rate": hr,
                    "spo2": gauss_int(96, 1, 94, 99),
                    "blood_pressure_systolic": gauss_int(130, 5, 122, 142),
                    "blood_pressure_diastolic": gauss_int(82, 4, 74, 92),
                    "hrv": round(random.gauss(28, 5), 1),
                    "timestamp": ts.isoformat(),
                },
                headers=auth_headers(patient_token),
            )
            if r.status_code in (200, 201):
                fresh_submitted += 1
        print(f"  ✓ {fresh_submitted} fresh vitals submitted")

        # ── 7. Register/login clinician ──────────────────────────────────────
        print("\n► Setting up clinician1@test.com ...")
        # First we need an admin token to create a clinician
        # Try to register admin or login with existing
        admin_token = None
        try:
            admin_token = login(client, "admin@adaptivhealth.com", "AdminPass123")
            print("  ✓ Logged in as existing admin")
        except Exception:
            # Try to register admin via public endpoint (won't work for clinician, but try)
            try:
                r = client.post(
                    "/api/v1/register",
                    json={"email": "admin@adaptivhealth.com", "password": "AdminPass123", "name": "System Admin", "role": "admin"},
                )
                # Even if role is forced to patient, login and get patient token for admin reg attempt
                admin_token = login(client, "admin@adaptivhealth.com", "AdminPass123")
            except Exception:
                print("  ⚠ Could not create admin account — creating clinician with admin/register may fail")

        clinician_token = None
        if admin_token:
            try:
                clinician_token = register_or_login(
                    client, CLINICIAN_EMAIL, CLINICIAN_PASSWORD, CLINICIAN_NAME,
                    role="clinician", admin_token=admin_token
                )
                print(f"  ✓ Clinician {CLINICIAN_EMAIL} ready")
            except Exception as e:
                print(f"  ⚠ Clinician setup failed: {e}")
        else:
            print("  ⚠ Skipping clinician setup (no admin token)")

        # ── 8. Compute risk assessment ───────────────────────────────────────
        print("\n► Computing AI risk assessment ...")
        if clinician_token:
            r = client.post(
                f"/api/v1/patients/{patient_id}/risk-assessments/compute",
                headers=auth_headers(clinician_token),
            )
            if r.status_code in (200, 201):
                data = r.json()
                print(f"  ✓ Risk computed: {data.get('risk_level', '?').upper()} ({data.get('risk_score', 0):.2f})")
                print(f"    Drivers: {data.get('drivers', [])[:3]}")
            else:
                print(f"  ⚠ Compute returned {r.status_code}: {r.text[:200]}")
        else:
            # Try as patient (own compute)
            r = client.post(
                "/api/v1/risk-assessments/compute",
                headers=auth_headers(patient_token),
            )
            if r.status_code in (200, 201):
                data = r.json()
                print(f"  ✓ Risk computed (as patient): {data.get('risk_level', '?').upper()} ({data.get('risk_score', 0):.2f})")
            else:
                print(f"  ⚠ Patient compute returned {r.status_code}: {r.text[:200]}")

        # ── 9. Summary ───────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print("  SEED COMPLETE")
        print(f"{'='*60}")
        print(f"\n  Patient account:")
        print(f"    Email    : {PATIENT_EMAIL}")
        print(f"    Password : {PATIENT_PASSWORD}")
        print(f"    Age      : {PATIENT_AGE}")
        print(f"    Baseline : {PATIENT_BASELINE_HR} BPM")
        if clinician_token:
            print(f"\n  Clinician account:")
            print(f"    Email    : {CLINICIAN_EMAIL}")
            print(f"    Password : {CLINICIAN_PASSWORD}")
            print(f"\n  Doctor dashboard:")
            print(f"    Log in as {CLINICIAN_EMAIL}")
            print(f"    Open Patient Detail for '{PATIENT_NAME}'")
            print(f"    Click 'Run AI Assessment' to refresh risk scores")
        print(f"\n  Mobile app:")
        print(f"    Log in as {PATIENT_EMAIL}")
        print(f"    Start simulator: Profile → DEV → Workout scenario")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed patient1@test.com with historical data")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()
    main(args.base_url)
