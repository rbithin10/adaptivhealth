"""
Test RDS PostgreSQL connectivity and run all migrations.
DEV ONLY - run manually: python scripts/migrate_to_rds.py
"""
import sys  # System utilities like exit
import os  # File path and environment variable tools

# Add project root to path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

RDS_URL = "postgresql://postgres:password@adaptivhealth-db.c34gaqco4qk4.ap-south-1.rds.amazonaws.com:5432/postgres"  # AWS cloud database address

def test_connection():
    try:
        import psycopg  # Modern PostgreSQL driver
        conn = psycopg.connect(RDS_URL, connect_timeout=10)  # Try to reach the cloud database within 10 seconds
        cur = conn.cursor()  # Create a cursor for running queries
        cur.execute("SELECT version()")  # Ask PostgreSQL what version it's running
        version = cur.fetchone()[0]  # Get the version string
        print(f"✓ RDS connected: {version[:60]}")  # Show first 60 chars of the version
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")  # Count how many tables exist
        table_count = cur.fetchone()[0]  # Get the count
        print(f"✓ Tables in RDS: {table_count}")  # Show table count
        conn.close()  # Done checking — close connection
        return True  # Connection successful
    except Exception as e:
        print(f"✗ RDS connection failed: {e}")  # Could not reach the cloud database
        return False

def run_migrations():
    """Run SQLAlchemy create_all to create all tables on RDS."""
    print("\nRunning migrations on RDS...")
    # Point the app at the cloud database instead of local
    os.environ["DATABASE_URL"] = RDS_URL

    from app.database import engine, Base  # Load the database engine and base model class
    # Import every model so SQLAlchemy registers them and creates their tables
    from app.models import user, vital_signs, alert          # noqa: F401
    from app.models import activity, recommendation          # noqa: F401
    try:
        from app.models import message, nutrition_entry      # noqa: F401  # Optional models — skip if not yet created
    except ImportError:
        pass
    try:
        from app.models import medication_reminder           # noqa: F401  # Medication reminders might not exist yet
    except ImportError:
        pass
    try:
        from app.models import rehab                         # noqa: F401  # Rehab module might not exist yet
    except ImportError:
        pass
    try:
        from app.models import document                      # noqa: F401  # Document uploads might not exist yet
    except ImportError:
        pass

    Base.metadata.create_all(bind=engine)  # Create any missing tables in the cloud database
    print("✓ All tables created / verified on RDS.")

if __name__ == "__main__":
    print("=" * 60)
    print("RDS Migration Script")
    print("=" * 60)
    if not test_connection():
        sys.exit(1)
    run_migrations()
    print("\nDone. RDS is ready.")
