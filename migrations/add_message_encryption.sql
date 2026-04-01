/*
Migration: Add message encryption support.

Adds encrypted_content column to messages table for end-to-end encrypted messaging.
Uses AES-256-GCM encryption with PHI_ENCRYPTION_KEY from environment.

Messages can be stored in encrypted form for security at rest.
Backend decrypts before sending to UI (HTTPS provides transit encryption).
*/

-- Add encrypted_content column (nullable for backward compatibility)
ALTER TABLE messages ADD COLUMN encrypted_content TEXT;

-- Create index for efficient lookup of encrypted messages
CREATE INDEX IF NOT EXISTS idx_messages_encrypted ON messages(sender_id, receiver_id, encrypted_content IS NOT NULL);
