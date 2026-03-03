-- =============================================================================
-- Migration: Add rehab_phase column to users table
-- =============================================================================
-- Values: 'phase_2', 'phase_3', 'not_in_rehab' (default)
-- Set during onboarding or via PUT /me profile update.
-- =============================================================================

ALTER TABLE users ADD COLUMN rehab_phase VARCHAR(30) DEFAULT 'not_in_rehab';
