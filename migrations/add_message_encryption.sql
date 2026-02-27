/*
Migration: Add message encryption support.

Adds encrypted_content column to messages table for end-to-end encrypted messaging.
Uses AES-256-GCM encryption with PHI_ENCRYPTION_KEY from environment.

Messages can be stored in encrypted form for security at rest.
Backend decrypts before sending to UI (HTTPS provides transit encryption).

BEFORE running this migration:
  1. Backup your database: cp adaptiv_health.db adaptiv_health.db.backup
  2. Ensure the backend is not running

TO APPLY THIS MIGRATION:
  1. Run from project root: python apply_migrations.py
  OR
  2. Manual SQLite: sqlite3 adaptiv_health.db < migrations/add_message_encryption.sql
*/

-- Add encrypted_content column (nullable for backward compatibility)
ALTER TABLE messages ADD COLUMN encrypted_content TEXT;

-- Create index for efficient lookup of encrypted messages
CREATE INDEX IF NOT EXISTS idx_messages_encrypted ON messages(sender_id, receiver_id, encrypted_content IS NOT NULL);
