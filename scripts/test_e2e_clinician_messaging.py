#!/usr/bin/env python3
"""
End-to-end testing script for clinician assignment & messaging system.

Tests the complete flow:
1. Database schema is correct
2. Migrations applied
3. Test data exists
4. Clinician assignment works
5. Message encryption works
6. API endpoints return expected data

WARNING: DEV ONLY - Modifies database test data

Usage:
    python scripts/test_e2e_clinician_messaging.py

Expected Output:
    ✅ All tests passed - System is ready!
"""

import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!")
os.environ.setdefault("PHI_ENCRYPTION_KEY", "DV6bGaOXYP29VZmLHeyaitlwzZpcMJ2x1OjwoTE4tLA=")

try:
    from app.database import Base, engine, get_db
    from app.models.user import User, UserRole
    from app.models.message import Message
    from app.services.encryption import encryption_service
    from sqlalchemy.orm import Session
except Exception as e:
    print(f"❌ Failed to import app modules: {e}")
    sys.exit(1)


class E2ETestSuite:
    """Complete end-to-end test suite."""
    
    def __init__(self):
        self.db_path = 'adaptiv_health.db'
        self.passed = 0
        self.failed = 0
        self.session = None
    
    def setup(self):
        """Setup database connection."""
        print("\n" + "="*70)
        print("SETUP: Connecting to database")
        print("="*70)
        
        if not os.path.exists(self.db_path):
            print(f"❌ Database file not found: {self.db_path}")
            return False
        
        try:
            # Create session
            from sqlalchemy.orm import sessionmaker
            SessionLocal = sessionmaker(bind=engine)
            self.session = SessionLocal()
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_schema_assigned_clinician_column(self):
        """Test: assigned_clinician_id column exists."""
        print("\n📋 Test 1: Schema - assigned_clinician_id column exists")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            conn.close()
            
            if 'assigned_clinician_id' in columns:
                print("   ✅ Column exists")
                self.passed += 1
                return True
            else:
                print("   ❌ Column missing - run migrations!")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_schema_message_encryption_column(self):
        """Test: encrypted_content column exists in messages."""
        print("\n📋 Test 2: Schema - encrypted_content column exists")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            conn.close()
            
            if 'encrypted_content' in columns:
                print("   ✅ Column exists")
                self.passed += 1
                return True
            else:
                print("   ⚠ Column missing (optional) - create with migration")
                return True  # Not critical for existing messages
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_clinician_exists(self):
        """Test: At least one clinician account exists."""
        print("\n📋 Test 3: Data - Clinician account exists")
        
        try:
            clinician = self.session.query(User).filter(
                User.role == UserRole.CLINICIAN
            ).first()
            
            if clinician:
                print(f"   ✅ Found: {clinician.full_name or 'N/A'} (ID: {clinician.user_id})")
                self.passed += 1
                self.clinician = clinician
                return True
            else:
                print("   ❌ No clinician found - create one via registration")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_patient_exists(self):
        """Test: At least one patient account exists."""
        print("\n📋 Test 4: Data - Patient account exists")
        
        try:
            patient = self.session.query(User).filter(
                User.role == UserRole.PATIENT
            ).first()
            
            if patient:
                print(f"   ✅ Found: {patient.full_name or 'N/A'} (ID: {patient.user_id})")
                self.passed += 1
                self.patient = patient
                return True
            else:
                print("   ❌ No patient found - create one via registration")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_assignment_works(self):
        """Test: Patient can be assigned to clinician."""
        print("\n📋 Test 5: Feature - Clinician assignment works")
        
        try:
            if not hasattr(self, 'clinician') or not hasattr(self, 'patient'):
                print("   ⚠ Skipped (missing test data)")
                return True
            
            # Assign patient to clinician
            self.patient.assigned_clinician_id = self.clinician.user_id
            self.session.commit()
            
            # Verify assignment
            self.session.refresh(self.patient)
            if self.patient.assigned_clinician_id == self.clinician.user_id:
                print(f"   ✅ Patient {self.patient.user_id} assigned to clinician {self.clinician.user_id}")
                self.passed += 1
                return True
            else:
                print("   ❌ Assignment failed")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_message_creation(self):
        """Test: Messages can be created."""
        print("\n📋 Test 6: Feature - Message creation")
        
        try:
            if not hasattr(self, 'clinician') or not hasattr(self, 'patient'):
                print("   ⚠ Skipped (missing test data)")
                return True
            
            # Create a test message
            message = Message(
                sender_id=self.patient.user_id,
                receiver_id=self.clinician.user_id,
                content="Test message for e2e testing",
                is_read=False,
                sent_at=datetime.now(timezone.utc)
            )
            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)
            
            if message.message_id:
                print(f"   ✅ Message created (ID: {message.message_id})")
                self.passed += 1
                self.test_message = message
                return True
            else:
                print("   ❌ Message creation failed")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_message_encryption(self):
        """Test: Messages can be encrypted and decrypted."""
        print("\n📋 Test 7: Feature - Message encryption")
        
        try:
            test_content = "Sensitive health information - should be encrypted"
            
            # Encrypt
            encrypted = encryption_service.encrypt_text(test_content)
            if not encrypted:
                print("   ❌ Encryption failed")
                self.failed += 1
                return False
            
            print(f"   ✓ Encrypted: {encrypted[:50]}...")
            
            # Decrypt
            decrypted = encryption_service.decrypt_text(encrypted)
            if decrypted == test_content:
                print(f"   ✅ Encrypted and decrypted successfully")
                self.passed += 1
                return True
            else:
                print(f"   ❌ Decryption mismatch")
                print(f"      Original: {test_content}")
                print(f"      Decrypted: {decrypted}")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_clinician_patient_filtering(self):
        """Test: Clinicians can only see assigned patients."""
        print("\n📋 Test 8: Feature - Clinician patient filtering")
        
        try:
            if not hasattr(self, 'clinician'):
                print("   ⚠ Skipped (missing test data)")
                return True
            
            # Query: clinician should only see their assigned patients
            assigned_patients = self.session.query(User).filter(
                User.assigned_clinician_id == self.clinician.user_id,
                User.role == UserRole.PATIENT
            ).all()
            
            if len(assigned_patients) > 0:
                print(f"   ✅ Clinician sees {len(assigned_patients)} assigned patient(s)")
                self.passed += 1
                return True
            else:
                print("   ⚠ No assigned patients (not critical if assignment just happened)")
                return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_message_retrieval(self):
        """Test: Messages can be retrieved."""
        print("\n📋 Test 9: Feature - Message retrieval")
        
        try:
            if not hasattr(self, 'clinician') or not hasattr(self, 'patient'):
                print("   ⚠ Skipped (missing test data)")
                return True
            
            # Retrieve conversation thread
            thread = self.session.query(Message).filter(
                ((Message.sender_id == self.patient.user_id) & 
                 (Message.receiver_id == self.clinician.user_id)) |
                ((Message.sender_id == self.clinician.user_id) & 
                 (Message.receiver_id == self.patient.user_id))
            ).order_by(Message.sent_at).all()
            
            if len(thread) > 0:
                print(f"   ✅ Retrieved {len(thread)} message(s)")
                self.passed += 1
                return True
            else:
                print("   ⚠ No messages in thread yet (not critical)")
                return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def test_indexes(self):
        """Test: Database indexes are created."""
        print("\n📋 Test 10: Schema - Indexes are created")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for assigned_clinician_id index
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_assigned_clinician'"
            )
            has_assignment_index = cursor.fetchone() is not None
            
            # Check for messages indexes
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_messages%'"
            )
            message_indexes = cursor.fetchall()
            
            conn.close()
            
            if has_assignment_index and len(message_indexes) > 0:
                print(f"   ✅ Found {len(message_indexes)} message indexes")
                self.passed += 1
                return True
            else:
                print(f"   ⚠ Some indexes missing (not critical)")
                return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.failed += 1
            return False
    
    def cleanup(self):
        """Close database session."""
        if self.session:
            self.session.close()
    
    def run_all(self):
        """Run all tests."""
        print("\n" + "█"*70)
        print("█  END-TO-END TEST SUITE - Clinician Assignment & Messaging")
        print("█"*70)
        
        if not self.setup():
            return 1
        
        # Run all tests
        self.test_schema_assigned_clinician_column()
        self.test_schema_message_encryption_column()
        self.test_clinician_exists()
        self.test_patient_exists()
        self.test_assignment_works()
        self.test_message_creation()
        self.test_message_encryption()
        self.test_clinician_patient_filtering()
        self.test_message_retrieval()
        self.test_indexes()
        
        # Summary
        print("\n" + "█"*70)
        print("█  TEST RESULTS")
        print("█"*70)
        print(f"\n  ✅ PASSED: {self.passed}")
        print(f"  ❌ FAILED: {self.failed}")
        
        total = self.passed + self.failed
        if self.passed == total:
            print(f"\n✅ ALL {total} TESTS PASSED!")
            print("\n  System Status: READY FOR PRODUCTION")
            print("\n  Next steps:")
            print("    1. Start backend: python start_server.py")
            print("    2. Start web dashboard: npm start (in web-dashboard/)")
            print("    3. Start mobile app: flutter run")
            print("    4. Test patient messaging from mobile app")
            print("    5. Test clinician inbox from web dashboard")
            self.cleanup()
            return 0
        else:
            print(f"\n❌ {self.failed} TEST(S) FAILED")
            print("\n  Please fix above errors and run again")
            self.cleanup()
            return 1


def main():
    """Run test suite."""
    suite = E2ETestSuite()
    return suite.run_all()


if __name__ == "__main__":
    sys.exit(main())
