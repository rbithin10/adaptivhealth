-- =============================================================================
-- Migration: Add rehab program tables
-- =============================================================================
-- Two tables for structured cardiac rehabilitation:
--   1. rehab_programs       — one active program per user
--   2. rehab_session_logs   — individual completed sessions
-- =============================================================================

CREATE TABLE IF NOT EXISTS rehab_programs (
    program_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,
    program_type    VARCHAR(50)  NOT NULL,
    current_week    INTEGER NOT NULL DEFAULT 1,
    current_session_in_week INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rehab_user_status ON rehab_programs (user_id, status);


CREATE TABLE IF NOT EXISTS rehab_session_logs (
    log_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id              INTEGER NOT NULL,
    user_id                 INTEGER NOT NULL,
    week_number             INTEGER NOT NULL,
    session_number          INTEGER NOT NULL,
    activity_type           VARCHAR(50) NOT NULL,
    target_duration_minutes INTEGER NOT NULL,
    actual_duration_minutes INTEGER NOT NULL,
    avg_heart_rate          INTEGER,
    peak_heart_rate         INTEGER,
    vitals_in_safe_range    BOOLEAN NOT NULL DEFAULT 1,
    completed_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (program_id) REFERENCES rehab_programs (program_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rehab_log_program_week ON rehab_session_logs (program_id, week_number);
CREATE INDEX IF NOT EXISTS idx_rehab_log_user ON rehab_session_logs (user_id);
