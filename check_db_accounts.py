"""
Check all database files for user accounts.
"""
import sqlite3
import os

db_files = [
    'adaptiv_health.db',
    'adaptive_health.db',
    'test_messages.db',
    'test_nutrition.db',
    'test_rbac_consent.db',
    'test_register.db'
]

print("=" * 80)
print("DATABASE ACCOUNT AUDIT")
print("=" * 80)

for db_file in db_files:
    if not os.path.exists(db_file):
        print(f"\n❌ {db_file:<30} - NOT FOUND")
        continue
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if 'user' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
        if not cursor.fetchone():
            print(f"\n⚠️  {db_file:<30} - No 'user' table")
            conn.close()
            continue
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM user;")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"\n📭 {db_file:<30} - 0 users")
        else:
            print(f"\n✅ {db_file:<30} - {count} user(s)")
            
            # List all users
            cursor.execute("SELECT user_id, email, full_name, role FROM user;")
            users = cursor.fetchall()
            for user in users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ {db_file:<30} - ERROR: {str(e)}")

print("\n" + "=" * 80)
