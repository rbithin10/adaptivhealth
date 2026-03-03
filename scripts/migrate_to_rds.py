"""
Test RDS PostgreSQL connectivity and run all migrations.
DEV ONLY - run manually: python scripts/migrate_to_rds.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

RDS_URL = "postgresql://postgres:password@adaptivhealth-db.c34gaqco4qk4.ap-south-1.rds.amazonaws.com:5432/postgres"

def test_connection():
    try:
        import psycopg
        conn = psycopg.connect(RDS_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"✓ RDS connected: {version[:60]}")
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
        table_count = cur.fetchone()[0]
        print(f"✓ Tables in RDS: {table_count}")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ RDS connection failed: {e}")
        return False

def run_migrations():
    """Run SQLAlchemy create_all to create all tables on RDS."""
    print("\nRunning migrations on RDS...")
    # Override DATABASE_URL before importing app
    os.environ["DATABASE_URL"] = RDS_URL

    from app.database import engine, Base
    # Import all models so SQLAlchemy knows about them
    from app.models import user, vital_signs, alert          # noqa: F401
    from app.models import activity, recommendation          # noqa: F401
    try:
        from app.models import message, nutrition_entry      # noqa: F401
    except ImportError:
        pass
    try:
        from app.models import medication_reminder           # noqa: F401
    except ImportError:
        pass
    try:
        from app.models import rehab                         # noqa: F401
    except ImportError:
        pass
    try:
        from app.models import document                      # noqa: F401
    except ImportError:
        pass

    Base.metadata.create_all(bind=engine)
    print("✓ All tables created / verified on RDS.")

if __name__ == "__main__":
    print("=" * 60)
    print("RDS Migration Script")
    print("=" * 60)
    if not test_connection():
        sys.exit(1)
    run_migrations()
    print("\nDone. RDS is ready.")
