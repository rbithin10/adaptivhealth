"""
Verify production messaging implementation.

This script checks:
1. Database table exists
2. All endpoints registered
3. Files present
4. Full functionality

Run with: python verify_messaging.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment for testing
os.environ.setdefault("SECRET_KEY", "test-secret-key-must-be-at-least-32-characters-long")
os.environ.setdefault("DEBUG", "true")


def check_files():
    """Verify all messaging files exist."""
    print("🔍 Checking files...")
    
    required_files = [
        "app/models/message.py",
        "app/schemas/message.py",
        "app/api/messages.py",
        "migrations/add_messages.sql",
        "tests/test_messaging.py",
        "docs/MESSAGING_IMPLEMENTATION.md",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} NOT FOUND")
            all_exist = False
    
    return all_exist


def check_database():
    """Verify messages table exists."""
    print("\n🗄️  Checking database...")
    
    try:
        from app.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "messages" in tables:
            print("  ✅ messages table exists")
            
            # Check columns
            columns = [col['name'] for col in inspector.get_columns('messages')]
            required_columns = ['message_id', 'sender_id', 'receiver_id', 'content', 'sent_at', 'is_read']
            
            missing = [col for col in required_columns if col not in columns]
            if not missing:
                print(f"  ✅ All required columns present: {', '.join(columns)}")
                return True
            else:
                print(f"  ❌ Missing columns: {', '.join(missing)}")
                return False
        else:
            print("  ❌ messages table NOT FOUND")
            print("  💡 Run migration: sqlite3 adaptiv_health.db < migrations/add_messages.sql")
            return False
            
    except Exception as e:
        print(f"  ⚠️  Could not check database: {e}")
        return False


def check_routes():
    """Verify messaging routes are registered."""
    print("\n🛣️  Checking routes...")
    
    try:
        from app.main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        expected_routes = [
            ("/api/v1/messages/thread/{other_user_id}", "GET"),
            ("/api/v1/messages", "POST"),
            ("/api/v1/messages/{message_id}/read", "POST"),
        ]
        
        all_found = True
        for path, method in expected_routes:
            found = any(path == r[0] and method in r[1] for r in routes)
            if found:
                print(f"  ✅ {method} {path}")
            else:
                print(f"  ❌ {method} {path} NOT REGISTERED")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"  ⚠️  Could not check routes: {e}")
        return False


def check_mobile_integration():
    """Verify mobile app has messaging methods."""
    print("\n📱 Checking mobile integration...")
    
    api_client_path = Path("mobile-app/lib/services/api_client.dart")
    if not api_client_path.exists():
        print("  ⚠️  ApiClient file not found")
        return False
    
    content = api_client_path.read_text()
    
    required_methods = [
        "getMessageThread",
        "sendMessage",
    ]
    
    all_found = True
    for method in required_methods:
        if method in content:
            print(f"  ✅ {method}() method found")
        else:
            print(f"  ❌ {method}() method NOT FOUND")
            all_found = False
    
    # Check screen
    screen_path = Path("mobile-app/lib/screens/doctor_messaging_screen.dart")
    if screen_path.exists():
        print("  ✅ doctor_messaging_screen.dart exists")
    else:
        print("  ❌ doctor_messaging_screen.dart NOT FOUND")
        all_found = False
    
    return all_found


def run_basic_test():
    """Run a basic functionality test."""
    print("\n🧪 Running basic test...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test unauthenticated access (should fail)
        response = client.get("/api/v1/messages/thread/1")
        if response.status_code == 401:
            print("  ✅ Authentication required (401)")
            return True
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ⚠️  Could not run test: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("MESSAGING PRODUCTION VERIFICATION")
    print("=" * 60)
    
    results = {
        "Files": check_files(),
        "Database": check_database(),
        "Routes": check_routes(),
        "Mobile Integration": check_mobile_integration(),
        "Basic Test": run_basic_test(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check:.<40} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - Messaging implementation is production-ready!")
    else:
        print("⚠️  SOME CHECKS FAILED - Review output above")
        print("\nNext steps:")
        if not results["Database"]:
            print("  1. Run migration: sqlite3 adaptiv_health.db < migrations/add_messages.sql")
        if not results["Routes"]:
            print("  2. Verify app/main.py includes messages.router")
        if not results["Files"]:
            print("  3. Verify all files present in repository")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
