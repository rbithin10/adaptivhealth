-- Add read_at timestamp to messages table
-- Run this migration to add read receipt support

-- SQLite
ALTER TABLE messages ADD COLUMN read_at TIMESTAMP NULL;

-- PostgreSQL (alternative syntax if using PostgreSQL)
-- ALTER TABLE messages ADD COLUMN read_at TIMESTAMP WITH TIME ZONE NULL;

-- Create index for performance on read status queries
CREATE INDEX IF NOT EXISTS idx_messages_read_at ON messages(read_at);
