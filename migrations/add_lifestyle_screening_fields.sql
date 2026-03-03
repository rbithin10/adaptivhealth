-- Migration: Add lifestyle screening fields to users table
-- Adds smoking/alcohol/sedentary/PHQ-2 onboarding fields.

ALTER TABLE users ADD COLUMN IF NOT EXISTS smoking_status VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS alcohol_frequency VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS sedentary_hours FLOAT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phq2_score INTEGER;
