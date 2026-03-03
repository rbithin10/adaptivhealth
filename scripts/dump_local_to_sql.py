"""
Dumps all data from local PostgreSQL to a SQL file that can be run on RDS.
DEV ONLY - run manually: python scripts/dump_local_to_sql.py

Output: scripts/rds_seed.sql
Upload to EC2 and run:
  psql "postgresql://postgres:password@adaptivhealth-db.c34gaqco4qk4.ap-south-1.rds.amazonaws.com:5432/postgres" -f rds_seed.sql
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/adaptiv_health"

# Table import order respects FK constraints
TABLE_ORDER = [
    "users",
    "auth_credentials",
    "vital_signs",
    "activity_sessions",
    "risk_assessments",
    "alerts",
    "exercise_recommendations",
    "nutrition_entries",
    "messages",
    "patient_medical_history",
    "patient_medications",
    "medication_adherence",
    "uploaded_documents",
    "rehab_programs",
    "rehab_session_logs",
]

# Tables with serial/identity PKs where we want to override the sequence
IDENTITY_TABLES = {
    "users": "user_id",
    "auth_credentials": "credential_id",
    "vital_signs": "vital_id",
    "activity_sessions": "session_id",
    "risk_assessments": "assessment_id",
    "alerts": "alert_id",
    "exercise_recommendations": "recommendation_id",
    "nutrition_entries": "entry_id",
    "messages": "message_id",
    "patient_medical_history": "history_id",
    "patient_medications": "medication_id",
    "medication_adherence": "adherence_id",
    "uploaded_documents": "document_id",
    "rehab_programs": "program_id",
    "rehab_session_logs": "log_id",
}

def quote_value(val):
    """Convert Python value to SQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    # Strings, datetimes, enums, UUIDs — escape single quotes
    s = str(val).replace("'", "''")
    return f"'{s}'"

def dump_table(cur, table, output):
    try:
        cur.execute(f"SELECT * FROM {table}")
    except Exception as e:
        output.append(f"-- SKIPPED {table}: {e}\n")
        return 0

    rows = cur.fetchall()
    if not rows:
        output.append(f"-- {table}: 0 rows, skipping\n")
        return 0

    cols = [desc[0] for desc in cur.description]
    pk_col = IDENTITY_TABLES.get(table)

    output.append(f"\n-- =============================================")
    output.append(f"-- {table}: {len(rows)} rows")
    output.append(f"-- =============================================")

    # Temporarily allow manual PK inserts on identity columns
    if pk_col and pk_col in cols:
        output.append(f"ALTER TABLE {table} DISABLE TRIGGER ALL;")
        output.append(f"ALTER TABLE {table} ALTER COLUMN {pk_col} DROP DEFAULT;")

    col_list = ", ".join(cols)
    for row in rows:
        vals = ", ".join(quote_value(v) for v in row)
        output.append(f"INSERT INTO {table} ({col_list}) VALUES ({vals}) ON CONFLICT DO NOTHING;")

    # Restore sequence to max(pk)+1 so future inserts don't collide
    if pk_col and pk_col in cols:
        seq_name = f"{table}_{pk_col}_seq"
        output.append(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({pk_col}) FROM {table}), 1));")
        # Try to restore default (sequence may have different name on RDS)
        output.append(f"ALTER TABLE {table} ALTER COLUMN {pk_col} SET DEFAULT nextval('{seq_name}');")
        output.append(f"ALTER TABLE {table} ENABLE TRIGGER ALL;")

    return len(rows)

def main():
    try:
        import psycopg
        conn = psycopg.connect(LOCAL_URL)
    except Exception as e:
        print(f"✗ Local DB connection failed: {e}")
        sys.exit(1)

    cur = conn.cursor()
    output = []
    output.append("-- =============================================")
    output.append("-- AdaptivHealth RDS Seed File")
    output.append("-- Generated from local PostgreSQL")
    output.append(f"-- Date: 2026-03-03")
    output.append("-- Run from EC2: psql <RDS_URL> -f rds_seed.sql")
    output.append("-- =============================================\n")

    output.append("SET session_replication_role = 'replica';  -- Disable FK checks during import\n")

    # Truncate in reverse order so FK constraints don't block (replica mode disables them anyway)
    output.append("-- Clear existing RDS data before importing local data")
    for table in reversed(TABLE_ORDER):
        output.append(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
    output.append("")

    total_rows = 0
    for table in TABLE_ORDER:
        count = dump_table(cur, table, output)
        total_rows += count
        print(f"  {table:<40} {count:>6} rows")

    output.append("\nSET session_replication_role = 'origin';  -- Re-enable FK checks")
    output.append("\n-- Import complete.")

    conn.close()

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rds_seed.sql")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

    print(f"\n✓ Dumped {total_rows} total rows → {out_path}")
    print("\nNext steps:")
    print("  1. git add scripts/rds_seed.sql && git push")
    print("  2. On EC2: git pull && psql <RDS_URL> -f scripts/rds_seed.sql")

if __name__ == "__main__":
    main()
