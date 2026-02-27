/*
Migration: Add clinician assignment support for patient-clinician pairing.

This adds the assigned_clinician_id column to allow admins to assign
specific clinicians to patients for messaging and care coordination.

BEFORE running this migration:
  1. Backup your database: cp adaptiv_health.db adaptiv_health.db.backup
  2. Ensure the backend is not running

TO APPLY THIS MIGRATION:
  1. Run from project root: python apply_migrations.py
  OR
  2. Manual SQLite: sqlite3 adaptiv_health.db < migrations/add_clinician_assignment.sql
*/

-- Add clinician assignment column (nullable - clinicians can be unassigned initially)
ALTER TABLE users ADD COLUMN assigned_clinician_id INTEGER;

-- Create index for fast clinician-to-patient lookups (used in dashboard filtering)
CREATE INDEX IF NOT EXISTS idx_assigned_clinician ON users(assigned_clinician_id);
