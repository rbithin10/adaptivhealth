-- Migration version tracking table
-- Run this FIRST before applying other migrations
-- Prevents duplicate or out-of-order migration execution

CREATE TABLE IF NOT EXISTS _applied_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT NOW(),
    checksum VARCHAR(64)
);

-- Seed with all previously applied migrations (manual baseline)
INSERT INTO _applied_migrations (migration_name, applied_at) VALUES
    ('add_clinician_assignment', NOW()),
    ('add_lifestyle_fields', NOW()),
    ('add_medical_history_medications', NOW()),
    ('add_medication_reminders', NOW()),
    ('add_message_encryption', NOW()),
    ('add_message_read_at', NOW()),
    ('add_messages', NOW()),
    ('add_nutrition_entries', NOW()),
    ('add_rbac_consent', NOW()),
    ('add_rehab_phase', NOW()),
    ('add_rehab_tables', NOW())
ON CONFLICT (migration_name) DO NOTHING;
