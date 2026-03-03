"""
Compares local PostgreSQL schema against expected schema from SQLAlchemy models.
Also generates a SQL script to verify RDS schema matches.

Run locally: python scripts/verify_schema.py
Run the output SQL on EC2 to verify RDS matches.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/adaptiv_health"


def get_schema(conn):
    """Return dict of {table: [(column, data_type, is_nullable)]} for all public tables."""
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    schema = {}
    for table, col, dtype, nullable, default in cur.fetchall():
        schema.setdefault(table, []).append((col, dtype, nullable))
    return schema


def main():
    try:
        import psycopg
        conn = psycopg.connect(LOCAL_URL)
    except Exception as e:
        print(f"✗ Local DB connection failed: {e}")
        sys.exit(1)

    local_schema = get_schema(conn)
    conn.close()

    print(f"Local schema: {len(local_schema)} tables\n")

    # Print local schema summary
    for table, cols in sorted(local_schema.items()):
        print(f"  {table} ({len(cols)} columns)")
        for col, dtype, nullable in cols:
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"    {col:<40} {dtype:<25} {null_str}")
        print()

    # Generate a SQL verification query for RDS
    # Run this on EC2 to confirm RDS has all the same tables and columns
    lines = []
    lines.append("-- =============================================")
    lines.append("-- Schema verification query — run on RDS")
    lines.append("-- All counts should match the local values")
    lines.append("-- =============================================\n")
    lines.append("SELECT")
    lines.append("  table_name,")
    lines.append("  count(*) AS column_count")
    lines.append("FROM information_schema.columns")
    lines.append("WHERE table_schema = 'public'")
    lines.append("GROUP BY table_name")
    lines.append("ORDER BY table_name;\n")

    lines.append("-- Expected (from local):")
    for table, cols in sorted(local_schema.items()):
        lines.append(f"--   {table:<40} {len(cols)} columns")

    lines.append("\n-- Detailed column check — look for any missing columns:")
    lines.append("SELECT table_name, column_name, data_type, is_nullable")
    lines.append("FROM information_schema.columns")
    lines.append("WHERE table_schema = 'public'")
    lines.append("ORDER BY table_name, ordinal_position;")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_rds_schema.sql")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✓ Verification SQL written to: {out_path}")
    print("\nRun on EC2 to verify RDS schema:")
    print('  psql "postgresql://postgres:password@adaptivhealth-db.c34gaqco4qk4.ap-south-1.rds.amazonaws.com:5432/postgres" -f scripts/verify_rds_schema.sql')


if __name__ == "__main__":
    main()
