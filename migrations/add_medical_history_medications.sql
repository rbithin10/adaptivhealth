-- =============================================================================
-- Medical History, Medications & Document Upload Tables Migration
-- =============================================================================
-- Creates tables for structured patient medical history, medications,
-- and uploaded clinical documents with LLM extraction support.
--
-- Run with: psql -U postgres -d adaptiv_health -f migrations/add_medical_history_medications.sql
-- Or for SQLite: sqlite3 adaptiv_health.db < migrations/add_medical_history_medications.sql
-- =============================================================================

-- Create patient_medical_history table
CREATE TABLE IF NOT EXISTS patient_medical_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    condition_type VARCHAR(50) NOT NULL,
    condition_detail VARCHAR(255),
    diagnosis_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    notes_encrypted TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,

    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users (user_id),
    FOREIGN KEY (updated_by) REFERENCES users (user_id)
);

-- Indexes for patient_medical_history
CREATE INDEX IF NOT EXISTS idx_pmh_user ON patient_medical_history(user_id);
CREATE INDEX IF NOT EXISTS idx_pmh_condition ON patient_medical_history(condition_type);

-- Create patient_medications table
CREATE TABLE IF NOT EXISTS patient_medications (
    medication_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    drug_class VARCHAR(50) NOT NULL,
    drug_name VARCHAR(100) NOT NULL,
    dose VARCHAR(50),
    frequency VARCHAR(50) DEFAULT 'daily',
    is_hr_blunting BOOLEAN DEFAULT 0,
    is_anticoagulant BOOLEAN DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    prescribed_by VARCHAR(100),
    notes_encrypted TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,

    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users (user_id),
    FOREIGN KEY (updated_by) REFERENCES users (user_id)
);

-- Indexes for patient_medications
CREATE INDEX IF NOT EXISTS idx_pm_user ON patient_medications(user_id);
CREATE INDEX IF NOT EXISTS idx_pm_drug_class ON patient_medications(drug_class);
CREATE INDEX IF NOT EXISTS idx_pm_status ON patient_medications(status);

-- Create uploaded_documents table
CREATE TABLE IF NOT EXISTS uploaded_documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size_kb INTEGER,
    status VARCHAR(20) DEFAULT 'uploaded',
    extracted_json TEXT,
    uploaded_by INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
);

CREATE INDEX IF NOT EXISTS idx_ud_user ON uploaded_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_ud_status ON uploaded_documents(status);
