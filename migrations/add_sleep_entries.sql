-- Create sleep entries table for manual sleep logging

CREATE TABLE IF NOT EXISTS sleep_entries (
    sleep_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    bedtime TIMESTAMP WITH TIME ZONE,
    wake_time TIMESTAMP WITH TIME ZONE,
    duration_hours FLOAT,
    quality_rating INTEGER,
    sleep_score INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sleep_user_date
    ON sleep_entries (user_id, date);
