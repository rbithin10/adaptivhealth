-- Add read_at timestamp to messages table
-- Run this migration to add read receipt support

ALTER TABLE messages ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE NULL;

-- Create index for performance on read status queries
CREATE INDEX IF NOT EXISTS idx_messages_read_at ON messages(read_at);
