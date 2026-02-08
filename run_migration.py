"""
Quick migration script to add consent columns to users table.
"""
import sqlite3

conn = sqlite3.connect('adaptiv_health.db')
cursor = conn.cursor()

try:
    # Add consent management columns
    print("Adding consent columns to users table...")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_state VARCHAR(30) DEFAULT "SHARING_ON"')
    print("  ✓ share_state")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_requested_at TIMESTAMP')
    print("  ✓ share_requested_at")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_requested_by INTEGER')
    print("  ✓ share_requested_by")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_reviewed_at TIMESTAMP')
    print("  ✓ share_reviewed_at")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_reviewed_by INTEGER')
    print("  ✓ share_reviewed_by")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_decision VARCHAR(20)')
    print("  ✓ share_decision")
    
    cursor.execute('ALTER TABLE users ADD COLUMN share_reason VARCHAR(500)')
    print("  ✓ share_reason")
    
    conn.commit()
    print("\n✅ All consent columns added successfully")
    
    # Set defaults for existing users
    cursor.execute('UPDATE users SET share_state = "SHARING_ON" WHERE share_state IS NULL')
    rows_updated = cursor.rowcount
    conn.commit()
    print(f"✅ Set default share_state for {rows_updated} existing users")
    
    # Verify
    cursor.execute('PRAGMA table_info(users)')
    columns = [row[1] for row in cursor.fetchall()]
    
    consent_columns = ['share_state', 'share_requested_at', 'share_requested_by', 
                      'share_reviewed_at', 'share_reviewed_by', 'share_decision', 'share_reason']
    
    print("\nVerification:")
    for col in consent_columns:
        status = "✓" if col in columns else "✗"
        print(f"  {status} {col}")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print(f"⚠️  Columns already exist: {e}")
    else:
        print(f"❌ Error: {e}")
        raise
finally:
    conn.close()

print("\n✅ Migration complete!")
