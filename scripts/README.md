# scripts/ — Utility & Maintenance Scripts

One-off and recurring scripts for database setup, data seeding, migrations, testing helpers, and deployment. Run these from the project root.

## Database Scripts

| File | What It Does |
|------|-------------|
| `init_db.py` | Creates all database tables from scratch |
| `reset_database.py` | Drops and recreates all tables —  destroys all data |
| `apply_migrations.py` | Runs SQL migration files from the `migrations/` folder in order |
| `dump_local_to_sql.py` | Exports your local database to a SQL file for backup or transfer |
| `migrate_to_rds.py` | Migrates local data to an AWS RDS (cloud) database |
| `inspect_local_db.py` | Prints the current table structure of your local database |
| `verify_schema.py` | Checks that the database schema matches what the code expects |
| `patch_rds_schema.sql` | SQL patch to fix RDS schema differences |
| `verify_rds_schema.sql` | SQL queries to verify the RDS schema is correct |
| `rds_seed.sql` | Sample data to populate a fresh RDS database |

## User & Data Scripts

| File | What It Does |
|------|-------------|
| `create_admin.py` | Creates an admin user account in the database |
| `seed_patient.py` | Adds a sample patient with realistic test data |
| `setup_clinician_assignment.py` | Links a clinician to a patient for care management |

## Testing & Validation

| File | What It Does |
|------|-------------|
| `run_coverage.py` | Runs the test suite and generates a code-coverage report |
| `_test_chat.py` | Quick manual test for the AI chat service |
| `test_e2e_clinician_messaging.py` | End-to-end test for clinician–patient messaging flow |
| `validate_gemini_key.py` | Checks that your Google Gemini API key is valid |

## Other Utilities

| File | What It Does |
|------|-------------|
| `generate_placeholders.py` | Creates placeholder exercise images for the mobile app |
| `_tmp_list_users_cols.py` | Temporary script to list all columns in the users table |
| `deploy.sh` | Shell script for deploying the backend to production |
| `quick_install.bat` | Windows batch file to install dependencies and set up the project |
