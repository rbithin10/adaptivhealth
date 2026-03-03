"""
Adaptiv Health — Database Initialization & Seed Script
======================================================
Provisions the local SQLite development database from scratch.

Steps:
    1. Removes stale .db and .db-journal files from the project root.
    2. Creates adaptiv_health.db with the full schema (all 9 tables).
    3. Seeds default accounts (Admin, Clinician, Patient).
    4. Prints a complete database inventory (tables, columns, row counts).

Usage:
    python init_db.py
"""

import os
import sys
import glob
import sqlite3
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Environment (must be set before importing app modules)
# ---------------------------------------------------------------------------
os.environ.setdefault("SECRET_KEY", "3d7f8e9c1a5b6f7e8c9a0b1c2d3e4f5a")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./adaptiv_health.db")

# ---------------------------------------------------------------------------
# 1. Clean up stale database files
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
db_files = glob.glob(os.path.join(ROOT_DIR, "*.db"))
journal_files = glob.glob(os.path.join(ROOT_DIR, "*.db-journal"))

print("=" * 60)
print("  STEP 1 — Removing stale database files")
print("=" * 60)

if not db_files and not journal_files:
    print("  No .db files found — nothing to remove.\n")
else:
    for f in db_files + journal_files:
        try:
            os.remove(f)
            print(f"  ✗ Removed: {os.path.basename(f)}")
        except Exception as e:
            print(f"  ⚠ Could not remove {os.path.basename(f)}: {e}")
    print()

# ---------------------------------------------------------------------------
# 2. Create fresh database with full schema
# ---------------------------------------------------------------------------
print("=" * 60)
print("  STEP 2 — Creating adaptiv_health.db (full schema)")
print("=" * 60)

# Import AFTER cleanup so SQLAlchemy creates a brand-new file
from app.database import engine, Base, SessionLocal
from app.models import (
    User, UserRole, AuthCredential,
    VitalSignRecord,
    ActivitySession, ActivityType, ActivityPhase,
    RiskAssessment, RiskLevel,
    Alert, AlertType, SeverityLevel,
    ExerciseRecommendation, IntensityLevel, RecommendationType,
    NutritionEntry, MealType,
    Message,
)
from app.services.auth_service import pwd_context

Base.metadata.create_all(bind=engine)
print("  ✓ All tables created.\n")

# ---------------------------------------------------------------------------
# 3. Seed default accounts
# ---------------------------------------------------------------------------
print("=" * 60)
print("  STEP 3 — Seeding default accounts")
print("=" * 60)

db = SessionLocal()

try:
    # --- Admin ---
    admin = User(
        email="adaptivhealth@gmail.com",
        full_name="Adaptiv Health Admin",
        role=UserRole.ADMIN,
        age=35,
        gender="Other",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(admin)
    db.flush()

    db.add(AuthCredential(
        user_id=admin.user_id,
        hashed_password=pwd_context.hash("Password123"),
        failed_login_attempts=0,
        created_at=datetime.now(timezone.utc),
    ))
    print(f"  ✓ Admin     — adaptivhealth@gmail.com / Password123  (ID {admin.user_id})")

    # --- Clinician ---
    clinician = User(
        email="clinician@adaptivhealth.com",
        full_name="Dr. Sarah Chen",
        role=UserRole.CLINICIAN,
        age=42,
        gender="Female",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(clinician)
    db.flush()

    db.add(AuthCredential(
        user_id=clinician.user_id,
        hashed_password=pwd_context.hash("Password123"),
        failed_login_attempts=0,
        created_at=datetime.now(timezone.utc),
    ))
    print(f"  ✓ Clinician — clinician@adaptivhealth.com / Password123  (ID {clinician.user_id})")

    # --- Patient ---
    patient = User(
        email="patient@adaptivhealth.com",
        full_name="John Doe",
        role=UserRole.PATIENT,
        age=55,
        gender="Male",
        weight_kg=82.5,
        height_cm=175.0,
        baseline_hr=72,
        max_safe_hr=165,
        risk_level="moderate",
        medical_history="History of hypertension. On ACE inhibitors.",
        is_active=True,
        is_verified=True,
        share_state="SHARING_ON",
        created_at=datetime.now(timezone.utc),
    )
    db.add(patient)
    db.flush()

    db.add(AuthCredential(
        user_id=patient.user_id,
        hashed_password=pwd_context.hash("Password123"),
        failed_login_attempts=0,
        created_at=datetime.now(timezone.utc),
    ))
    print(f"  ✓ Patient   — patient@adaptivhealth.com / Password123  (ID {patient.user_id})")

    db.commit()
    print()

except Exception as e:
    db.rollback()
    print(f"  ✗ Seeding error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

# ---------------------------------------------------------------------------
# 4. Database inventory
# ---------------------------------------------------------------------------
print("=" * 60)
print("  STEP 4 — Database Inventory")
print("=" * 60)

db_files_after = glob.glob(os.path.join(ROOT_DIR, "*.db"))

if not db_files_after:
    print("  No .db files found — something went wrong.\n")
    sys.exit(1)

for db_path in sorted(db_files_after):
    name = os.path.basename(db_path)
    size_kb = os.path.getsize(db_path) / 1024
    print(f"\n  📁 {name}  ({size_kb:.1f} KB)")
    print(f"  {'─' * 54}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("    (no tables)")
        conn.close()
        continue

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info([{table}])")
        columns = cursor.fetchall()

        print(f"\n    📋 {table}  ({count} rows)")
        print(f"    {'Col #':<6} {'Name':<30} {'Type':<15} {'PK'}")
        print(f"    {'─'*6} {'─'*30} {'─'*15} {'─'*3}")
        for col in columns:
            pk_marker = "✓" if col[5] else ""
            print(f"    {col[0]:<6} {col[1]:<30} {col[2]:<15} {pk_marker}")

    conn.close()

print("\n" + "=" * 60)
print("  ✅  Database initialized successfully")
print("=" * 60)
print()
print("  Default Logins:")
print("  ┌──────────────────────────────────────────────────────┐")
print("  │ Role      │ Email                          │ Password    │")
print("  ├──────────────────────────────────────────────────────┤")
print("  │ Admin     │ adaptivhealth@gmail.com        │ Password123 │")
print("  │ Clinician │ clinician@adaptivhealth.com    │ Password123 │")
print("  │ Patient   │ patient@adaptivhealth.com      │ Password123 │")
print("  └──────────────────────────────────────────────────────┘")
print()
print("  Next: python start_server.py")
print()
