"""
Migration runner: Apply all pending database migrations.

Runs SQL migration files from the migrations/ folder against the database
configured in app.config / app.database (SQLite or PostgreSQL).
Safe to run multiple times - migrations include IF NOT EXISTS checks where applicable.

Usage:
    python apply_migrations.py
"""

import sys
from pathlib import Path

from sqlalchemy import text

from app.database import engine


def run_migrations() -> bool:
    """
    Run all SQL migrations from the migrations/ folder using SQLAlchemy.

    Returns:
        True if all migrations applied (or already applied), False on error.
    """
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    if not migrations_dir.exists():
        print(f"❌ Migrations folder not found: {migrations_dir}")
        return False

    # Collect *.sql files in alphabetical order
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("✅ No migration files found — nothing to do.")
        return True

    print(f"Found {len(migration_files)} migration(s):")
    for mf in migration_files:
        print(f"  • {mf.name}")
    print()

    applied_count = 0

    for migration_file in migration_files:
        migration_name = migration_file.name
        print(f"Applying {migration_name}...")

        try:
            sql_content = migration_file.read_text(encoding="utf-8")
            # Split by semicolons to handle multiple statements
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]

            with engine.begin() as conn:
                for statement in statements:
                    conn.execute(text(statement))

            print(f"  ✓ {migration_name} applied successfully")
            applied_count += 1

        except Exception as exc:
            err_msg = str(exc).lower()
            # Column/table already exists — treat as idempotent success
            if "already exists" in err_msg or "duplicate column" in err_msg:
                print(f"  ℹ  {migration_name} already applied: {exc}")
                applied_count += 1
            else:
                print(f"  ❌ Error in {migration_name}: {exc}")
                return False

    print()
    print(f"✅ Successfully applied {applied_count}/{len(migration_files)} migration(s)")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("ADAPTIV HEALTH - DATABASE MIGRATION RUNNER")
    print(f"  Engine: {engine.url}")
    print("=" * 70)
    print()

    success = run_migrations()

    if not success:
        print()
        print("⚠️  Migration failed. Please check the errors above.")
        sys.exit(1)
    else:
        print()
        print("✅ All migrations completed successfully!")
        print("   Your database schema is now up to date.")
