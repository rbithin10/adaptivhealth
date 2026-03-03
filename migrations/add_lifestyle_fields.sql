-- Migration: Add lifestyle and wellness fields to users table
-- These columns collect fitness, goals, and wellbeing data during onboarding.

ALTER TABLE users ADD COLUMN IF NOT EXISTS activity_level VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS exercise_limitations TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_goal VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stress_level INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sleep_quality VARCHAR(10);
