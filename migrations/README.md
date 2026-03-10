# migrations/ — Database Migration Scripts

SQL scripts that modify the database schema over time. Each file adds new tables or columns without losing existing data. They are applied in order by `scripts/apply_migrations.py`.

## How to Apply

```bash
python scripts/apply_migrations.py
```

The script tracks which migrations have already run using the `migration_tracker` table, so it's safe to run multiple times — it will only apply new ones.

## Migration Files (in order)

| File | What It Changes |
|------|----------------|
| `000_create_migration_tracker.sql` | Creates the tracking table that records which migrations have been applied |
| `add_clinician_assignment.sql` | Adds clinician-to-patient assignment columns for care management |
| `add_lifestyle_fields.sql` | Adds lifestyle data columns — smoking, alcohol, exercise level |
| `add_lifestyle_screening_fields.sql` | Adds screening questionnaire fields for lifestyle assessment |
| `add_medical_history_medications.sql` | Adds tables for medical history and current medications |
| `add_medication_reminders.sql` | Adds medication reminder and adherence tracking tables |
| `add_messages.sql` | Creates the messages table for patient–clinician chat |
| `add_message_encryption.sql` | Adds encryption columns to protect message content |
| `add_message_read_at.sql` | Adds read-receipt timestamps to messages |
| `add_nutrition_entries.sql` | Creates the nutrition log table for daily food intake |
| `add_rbac_consent.sql` | Adds role-based access control and patient consent tables |
| `add_rehab_phase.sql` | Adds phase tracking columns to the rehab programme |
| `add_rehab_tables.sql` | Creates full rehab tables — programmes, exercises, progress logs |
| `add_token_blocklist.sql` | Creates a table to store revoked JWT tokens |
