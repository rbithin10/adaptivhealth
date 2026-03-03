"""
Migration runner: Apply all pending database migrations.

Runs SQL migration files from the migrations/ folder against the database
configured in app.config / app.database (PostgreSQL).
Tracks applied migrations in the _applied_migrations table to prevent
duplicate execution and ensure ordering.

Usage:
    python scripts/apply_migrations.py
"""

import hashlib
import sys
from pathlib import Path

from sqlalchemy import text

from app.database import engine

TRACKER_TABLE = "_applied_migrations"


def _ensure_tracker_table(conn) -> None:
    """Create the migration tracking table if it doesn't exist."""
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {TRACKER_TABLE} (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT NOW(),
            checksum VARCHAR(64)
        )
    """))


def _get_applied(conn) -> set:
    """Return set of already-applied migration names."""
    rows = conn.execute(text(f"SELECT migration_name FROM {TRACKER_TABLE}"))
    return {row[0] for row in rows}


def _file_checksum(path: Path) -> str:
    """SHA-256 checksum of a migration file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_migrations() -> bool:
    """
    Run all pending SQL migrations from the migrations/ folder.

    Skips migrations already recorded in _applied_migrations.
    Records each newly applied migration with its checksum.

    Returns:
        True if all migrations applied (or already applied), False on error.
    """
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not migrations_dir.exists():
        print(f"Migrations folder not found: {migrations_dir}")
        return False

    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found.")
        return True

    with engine.begin() as conn:
        _ensure_tracker_table(conn)
        already_applied = _get_applied(conn)

    pending = [f for f in migration_files if f.stem not in already_applied]

    print(f"Found {len(migration_files)} migration(s), {len(pending)} pending:")
    for mf in migration_files:
        status = "SKIP" if mf.stem in already_applied else "PENDING"
        print(f"  [{status}] {mf.name}")
    print()

    if not pending:
        print("Nothing to apply — database is up to date.")
        return True

    applied_count = 0

    for migration_file in pending:
        migration_name = migration_file.stem
        print(f"Applying {migration_file.name}...")

        try:
            sql_content = migration_file.read_text(encoding="utf-8")
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]
            checksum = _file_checksum(migration_file)

            with engine.begin() as conn:
                for statement in statements:
                    conn.execute(text(statement))

                conn.execute(text(
                    f"INSERT INTO {TRACKER_TABLE} (migration_name, checksum) "
                    f"VALUES (:name, :checksum) ON CONFLICT (migration_name) DO NOTHING"
                ), {"name": migration_name, "checksum": checksum})

            print(f"  Applied {migration_file.name}")
            applied_count += 1

        except Exception as exc:
            err_msg = str(exc).lower()
            if "already exists" in err_msg or "duplicate column" in err_msg:
                print(f"  Already applied: {migration_file.name}")
                with engine.begin() as conn:
                    conn.execute(text(
                        f"INSERT INTO {TRACKER_TABLE} (migration_name, checksum) "
                        f"VALUES (:name, :checksum) ON CONFLICT (migration_name) DO NOTHING"
                    ), {"name": migration_name, "checksum": _file_checksum(migration_file)})
                applied_count += 1
            else:
                print(f"  Error in {migration_file.name}: {exc}")
                return False

    print()
    print(f"Applied {applied_count}/{len(pending)} migration(s)")
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
        print("Migration failed. Please check the errors above.")
        sys.exit(1)
    else:
        print()
        print("All migrations completed. Database schema is up to date.")
