-- =============================================================================
-- Nutrition Entries Table Migration
-- =============================================================================
-- Creates table for nutrition logging (meals, calories, macros)
-- Production feature for patient health tracking
-- =============================================================================

-- Create nutrition_entries table
CREATE TABLE IF NOT EXISTS nutrition_entries (
    entry_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    meal_type VARCHAR(50) NOT NULL DEFAULT 'other',
    description TEXT,
    calories INTEGER NOT NULL,
    protein_grams INTEGER,
    carbs_grams INTEGER,
    fat_grams INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_nutrition_user_id ON nutrition_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_nutrition_timestamp ON nutrition_entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_nutrition_user_timestamp ON nutrition_entries(user_id, timestamp);

-- Add comments (PostgreSQL only - remove for SQLite)
-- COMMENT ON TABLE nutrition_entries IS 'Nutrition logging for patients: meals, calories, macros';
-- COMMENT ON COLUMN nutrition_entries.meal_type IS 'Type of meal: breakfast, lunch, dinner, snack, other';
-- COMMENT ON COLUMN nutrition_entries.calories IS 'Total calories for this meal/entry';
-- COMMENT ON COLUMN nutrition_entries.protein_grams IS 'Protein in grams (optional)';
-- COMMENT ON COLUMN nutrition_entries.carbs_grams IS 'Carbohydrates in grams (optional)';
-- COMMENT ON COLUMN nutrition_entries.fat_grams IS 'Fat in grams (optional)';
-- COMMENT ON COLUMN nutrition_entries.timestamp IS 'When the entry was created';

-- =============================================================================
-- Sample Data (Optional - for testing)
-- =============================================================================
-- INSERT INTO nutrition_entries (user_id, meal_type, description, calories, protein_grams, carbs_grams, fat_grams)
-- VALUES 
--     (1, 'breakfast', 'Oatmeal with berries and almonds', 350, 12, 45, 14),
--     (1, 'lunch', 'Grilled chicken salad', 420, 35, 25, 18),
--     (1, 'snack', 'Greek yogurt with honey', 180, 15, 20, 5),
--     (1, 'dinner', 'Salmon with vegetables and quinoa', 580, 42, 48, 22);
