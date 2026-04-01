-- =============================================================================
-- Migration: Add Clinical Notes Table
-- =============================================================================
-- Stores clinician-authored notes per patient visit.
-- Notes are displayed in the AI Risk Summary panel and fed into future AI summaries.
-- =============================================================================

CREATE TABLE IF NOT EXISTS clinical_notes (
    note_id      SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    clinician_id INTEGER NOT NULL REFERENCES users(user_id),
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clinical_notes_user
    ON clinical_notes(user_id);

CREATE INDEX IF NOT EXISTS idx_clinical_notes_clinician
    ON clinical_notes(clinician_id);
