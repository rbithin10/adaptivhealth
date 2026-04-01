-- =============================================================================
-- Migration: Add Medication Reminders and Adherence Tracking
-- =============================================================================
-- This migration adds:
-- 1. reminder_time and reminder_enabled columns to patient_medications table
-- 2. medication_adherence table for tracking daily adherence
--
-- Run this migration AFTER add_medical_history_medications.sql
-- =============================================================================

-- Add reminder columns to patient_medications table
ALTER TABLE patient_medications ADD COLUMN IF NOT EXISTS reminder_time VARCHAR(5);
ALTER TABLE patient_medications ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT FALSE;

-- Create medication_adherence table
CREATE TABLE IF NOT EXISTS medication_adherence (
    adherence_id SERIAL PRIMARY KEY,
    medication_id INTEGER NOT NULL REFERENCES patient_medications(medication_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    taken BOOLEAN,
    responded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: one record per medication per day
    CONSTRAINT uq_medication_date UNIQUE (medication_id, scheduled_date)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_adherence_medication ON medication_adherence(medication_id);
CREATE INDEX IF NOT EXISTS idx_adherence_user ON medication_adherence(user_id);
CREATE INDEX IF NOT EXISTS idx_adherence_user_date ON medication_adherence(user_id, scheduled_date);
