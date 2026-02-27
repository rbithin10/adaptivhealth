#!/usr/bin/env python3
"""
Setup script: Apply migrations, create test data, and verify clinician assignment system.

This script:
1. Applies all pending database migrations
2. Creates test data with proper clinician-patient assignments
3. Verifies the system is configured correctly
4. Provides diagnostic information

WARNING: DEV ONLY - NOT FOR PRODUCTION/DEMO
Create backups before running: cp adaptiv_health.db adaptiv_health.db.backup

Usage:
    python scripts/setup_clinician_assignment.py
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("PHI_ENCRYPTION_KEY", "DV6bGaOXYP29VZmLHeyaitlwzZpcMJ2x1OjwoTE4tLA=")

try:
    from app.services.auth_service import AuthService
except ImportError:
    print("⚠ Warning: Could not import AuthService, will use simple password hash")
    AuthService = None

def apply_migrations():
    """Apply database migrations (adds columns and indexes)."""
    print("\n" + "="*70)
    print("STEP 1: Applying Database Migrations")
    print("="*70)
    
    db_path = 'adaptiv_health.db'
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("   Run the backend first: python start_server.py")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Migration 0: Normalize role values to lowercase (matches UserRole enum)
        print("\n   ✓ Migration: Normalize role enum values to lowercase")
        try:
            cursor.execute("UPDATE users SET role = 'patient' WHERE role = 'PATIENT'")
            patient_updated = cursor.rowcount
            cursor.execute("UPDATE users SET role = 'clinician' WHERE role = 'CLINICIAN'")
            clinician_updated = cursor.rowcount
            cursor.execute("UPDATE users SET role = 'admin' WHERE role = 'ADMIN'")
            admin_updated = cursor.rowcount
            
            if patient_updated > 0 or clinician_updated > 0 or admin_updated > 0:
                print(f"      ✓ Fixed: {patient_updated} patients, {clinician_updated} clinicians, {admin_updated} admins")
            else:
                print("      (no uppercase values found)")
        except Exception as e:
            print(f"      (role update skipped: {e})")
        
        # Migration 1: Add assigned_clinician_id column
        print("\n   ✓ Migration: Add clinician assignment column")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN assigned_clinician_id INTEGER")
            print("      ✓ Column added: assigned_clinician_id")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e):
                print("      (column already exists)")
            else:
                raise
        
        # Migration 2: Add index for clinician assignment
        print("\n   ✓ Migration: Add clinician assignment index")
        try:
            # Check if index exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_assigned_clinician'")
            if cursor.fetchone():
                print("      (index already exists)")
            else:
                cursor.execute("CREATE INDEX idx_assigned_clinician ON users(assigned_clinician_id)")
                print("      ✓ Index created: idx_assigned_clinician")
        except sqlite3.OperationalError as e:
            print(f"      (index creation skipped: {e})")
        
        # Migration 3: Add encrypted_content column to messages
        print("\n   ✓ Migration: Add message encryption column")
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN encrypted_content TEXT")
            print("      ✓ Column added: encrypted_content")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e):
                print("      (column already exists)")
            else:
                raise
        
        # Migration 4: Add index for encrypted messages
        print("\n   ✓ Migration: Add message encryption index")
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_messages_encryption'")
            if cursor.fetchone():
                print("      (index already exists)")
            else:
                cursor.execute("CREATE INDEX idx_messages_encryption ON messages(encrypted_content) WHERE encrypted_content IS NOT NULL")
                print("      ✓ Index created: idx_messages_encryption")
        except sqlite3.OperationalError as e:
            print(f"      (index creation skipped: {e})")
        
        conn.commit()
        conn.close()
        print("\n✅ Migrations applied successfully")
        return True
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schema():
    """Verify the database schema has required columns."""
    print("\n" + "="*70)
    print("STEP 2: Verifying Database Schema")
    print("="*70)
    
    db_path = 'adaptiv_health.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if assigned_clinician_id column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'assigned_clinician_id' in columns:
            print("   ✓ assigned_clinician_id column exists")
        else:
            print("   ❌ assigned_clinician_id column missing")
            conn.close()
            return False
        
        # Check if message index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_assigned_clinician'")
        if cursor.fetchone():
            print("   ✓ idx_assigned_clinician index exists")
        else:
            print("   ⚠ idx_assigned_clinician index missing (creating now)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assigned_clinician ON users(assigned_clinician_id)")
            conn.commit()
        
        conn.close()
        print("\n✅ Schema verification passed")
        return True
    except Exception as e:
        print(f"\n❌ Schema error: {e}")
        return False


def create_test_data():
    """
    Create test data: admin, clinician, and patients with assignments.
    
    Creates:
      - admin@test.com (Admin role)
      - doctor@test.com (Clinician role)
      - patient1@test.com, patient2@test.com, patient3@test.com (Patient role)
    
    All passwords: password123
    Assigns all patients to clinician.
    """
    print("\n" + "="*70)
    print("STEP 3: Setting Up Test Data")
    print("="*70)
    
    db_path = 'adaptiv_health.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Hash password once
        if AuthService:
            password_hash = AuthService.hash_password("password123")
        else:
            # Fallback simple hash (DEV ONLY)
            import hashlib
            password_hash = hashlib.sha256("password123".encode()).hexdigest()
        
        created_count = 0
        
        # Test users to create
        test_users = [
            ("admin@test.com", "Admin User", "admin"),
            ("doctor@test.com", "Dr. Smith", "clinician"),
            ("patient1@test.com", "Alice Johnson", "patient"),
            ("patient2@test.com", "Bob Williams", "patient"),
            ("patient3@test.com", "Carol Davis", "patient"),
        ]
        
        print("\n   Creating test users...")
        for email, full_name, role in test_users:
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"      ✓ {email} already exists (ID: {existing[0]})")
            else:
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, full_name, role, age, is_active, is_verified, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (email, full_name, role, 30, 1, 1, datetime.now(timezone.utc)))
                
                user_id = cursor.lastrowid
                
                # Create auth credentials
                cursor.execute("""
                    INSERT INTO auth_credentials (
                        user_id, hashed_password, failed_login_attempts, 
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, password_hash, 0, datetime.now(timezone.utc), datetime.now(timezone.utc)))
                
                print(f"      ✓ Created: {email} ({role}, ID: {user_id})")
                created_count += 1
        
        conn.commit()
        
        # Get clinician ID
        cursor.execute("SELECT user_id FROM users WHERE email = 'doctor@test.com'")
        clinician_row = cursor.fetchone()
        if not clinician_row:
            print("\n   ❌ Clinician not found after creation")
            conn.close()
            return False
        
        clinician_id = clinician_row[0]
        
        # Assign patients to clinician
        print(f"\n   Assigning patients to clinician (ID: {clinician_id})...")
        cursor.execute("""
            SELECT user_id, email FROM users 
            WHERE role = 'patient' AND (assigned_clinician_id IS NULL OR assigned_clinician_id != ?)
        """, (clinician_id,))
        
        patients = cursor.fetchall()
        assigned_count = 0
        
        for patient_id, patient_email in patients:
            cursor.execute(
                "UPDATE users SET assigned_clinician_id = ? WHERE user_id = ?",
                (clinician_id, patient_id)
            )
            print(f"      ✓ Assigned: {patient_email}")
            assigned_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Test data ready:")
        print(f"   - Created: {created_count} new users")
        print(f"   - Assigned: {assigned_count} patients to clinician")
        print(f"\n   Test credentials:")
        print(f"   - Clinician: doctor@test.com / password123")
        print(f"   - Patient:   patient1@test.com / password123")
        print(f"   - Admin:     admin@test.com / password123")
        
        return True
    except Exception as e:
        print(f"\n❌ Test data error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_assignment():
    """Verify clinician assignment is working."""
    print("\n" + "="*70)
    print("STEP 4: Verifying Clinician Assignments")
    print("="*70)
    
    db_path = 'adaptiv_health.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count clinicians
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'clinician'")
        clinician_count = cursor.fetchone()[0]
        print(f"   Clinicians: {clinician_count}")
        
        # Count patients with assignments
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'patient' AND assigned_clinician_id IS NOT NULL"
        )
        assigned_patients = cursor.fetchone()[0]
        
        # Count total patients
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'")
        total_patients = cursor.fetchone()[0]
        
        print(f"   Patients with clinician: {assigned_patients}/{total_patients}")
        
        # Show assignments
        if assigned_patients > 0:
            cursor.execute("""
                SELECT c.full_name, c.user_id, COUNT(p.user_id) as patient_count
                FROM users c
                LEFT JOIN users p ON p.assigned_clinician_id = c.user_id AND p.role = 'patient'
                WHERE c.role = 'clinician'
                GROUP BY c.user_id
            """)
            
            print("\n   Assignment breakdown:")
            for clinician_name, clinician_id, count in cursor.fetchall():
                print(f"      - {clinician_name} (ID: {clinician_id}): {count} patients")
            
            # Show first few assignments
            cursor.execute("""
                SELECT c.full_name, p.full_name, p.user_id
                FROM users p
                JOIN users c ON p.assigned_clinician_id = c.user_id
                WHERE p.role = 'patient' AND p.assigned_clinician_id IS NOT NULL
                LIMIT 5
            """)
            
            assignments = cursor.fetchall()
            if assignments:
                print("\n   Sample patient assignments:")
                for clinician, patient, patient_id in assignments:
                    print(f"      - {patient} (ID: {patient_id}) → {clinician}")
        
        conn.close()
        print("\n✅ Assignment verification complete")
        return True
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        return False


def main():
    """Run all setup steps."""
    print("\n" + "█"*70)
    print("█  CLINICIAN ASSIGNMENT SYSTEM - SETUP & VERIFICATION")
    print("█"*70)
    
    steps = [
        ("Apply Migrations", apply_migrations),
        ("Verify Schema", verify_schema),
        ("Setup Test Data", create_test_data),
        ("Verify Assignments", verify_assignment),
    ]
    
    results = {}
    for step_name, step_func in steps:
        results[step_name] = step_func()
        if not results[step_name]:
            print(f"\n⚠  Stopped at: {step_name}")
            break
    
    # Final summary
    print("\n" + "█"*70)
    print("█  SETUP SUMMARY")
    print("█"*70)
    
    all_passed = all(results.values())
    
    for step_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {step_name}")
    
    if all_passed:
        print("\n✅ ALL CHECKS PASSED - System is ready!")
        print("\nNext steps:")
        print("  1. Open web dashboard: http://localhost:3000")
        print("  2. Log in with clinician account")
        print("  3. Go to /patients - should see assigned patients")
        print("  4. Try messaging from mobile app (if assigned as clinician)")
        return 0
    else:
        print("\n❌ SETUP INCOMPLETE - Please fix above errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
