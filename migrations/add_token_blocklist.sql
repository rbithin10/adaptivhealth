-- Migration: Add token blocklist table and fix null user roles
-- Run once against the target database before deploying the updated backend.
--
-- WHAT THIS DOES:
--   1. Creates the token_blocklist table used for server-side JWT revocation.
--   2. Ensures existing users with a NULL role are assigned the PATIENT default.
--   3. Adds a server-level DEFAULT of 'patient' to the role column so new rows
--      can never be inserted with a null role via raw SQL.
--
-- SAFE TO RE-RUN: CREATE TABLE IF NOT EXISTS is idempotent and the UPDATE
--   only touches rows where role IS NULL.
-- ============================================================================

-- 1. Token blocklist --- stores revoked JWT jti values
CREATE TABLE IF NOT EXISTS token_blocklist (
    id         SERIAL PRIMARY KEY,
    jti        VARCHAR(36)  NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ  NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_blocklist_jti
    ON token_blocklist (jti);

CREATE INDEX IF NOT EXISTS idx_token_blocklist_expires
    ON token_blocklist (expires_at);

-- 2. Fix any existing users with no role assigned
UPDATE users
SET    role = 'PATIENT'
WHERE  role IS NULL;

-- 3. Add a server-side DEFAULT so future INSERTs never produce a null role
ALTER TABLE users
    ALTER COLUMN role SET DEFAULT 'PATIENT';
