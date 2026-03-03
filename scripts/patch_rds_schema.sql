-- =============================================
-- RDS Schema Patch — adds columns missing from RDS vs local
-- Run on EC2: psql <RDS_URL> -f scripts/patch_rds_schema.sql
-- Safe to run multiple times (uses IF NOT EXISTS)
-- =============================================

-- users: add any missing columns (local has 39, RDS has 38)
ALTER TABLE users ADD COLUMN IF NOT EXISTS activity_level VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS exercise_limitations TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_goal VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stress_level INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sleep_quality VARCHAR(10);
ALTER TABLE users ADD COLUMN IF NOT EXISTS smoking_status VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS alcohol_frequency VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS sedentary_hours DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phq2_score INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS rehab_phase VARCHAR(30) DEFAULT 'not_in_rehab';
ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_clinician_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL;

-- rehab_programs: RDS has 8 cols, local has 14 — add the missing ones
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS program_name VARCHAR(255);
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS phase VARCHAR(30);
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS total_sessions INTEGER;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS completed_sessions INTEGER DEFAULT 0;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS end_date DATE;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS created_by INTEGER;
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE rehab_programs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Verify final column counts
SELECT table_name, count(*) AS column_count
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;
