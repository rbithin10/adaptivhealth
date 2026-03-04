"""
Inspect local PostgreSQL DB: list tables + row counts.
DEV ONLY - NOT FOR PRODUCTION
"""
import sys

try:
    import psycopg
except ImportError:
    print("psycopg not installed. Trying psycopg2...")
    try:
        import psycopg2 as psycopg
    except ImportError:
        print("Neither psycopg nor psycopg2 found. Install with: pip install psycopg2-binary")
        sys.exit(1)

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/adaptiv_health"

try:
    conn = psycopg.connect(LOCAL_URL)
    cur = conn.cursor()

    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [row[0] for row in cur.fetchall()]
    print(f"\nFound {len(tables)} tables in local DB:")
    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"  {t:<40} {count:>6} rows")

    conn.close()
    print("\nLocal DB OK.")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
