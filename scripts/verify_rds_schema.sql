-- =============================================
-- Schema verification query — run on RDS
-- All counts should match the local values
-- =============================================

SELECT
  table_name,
  count(*) AS column_count
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;

-- Expected (from local):
--   activity_sessions                        22 columns
--   alerts                                   21 columns
--   auth_credentials                         9 columns
--   exercise_recommendations                 20 columns
--   medication_adherence                     7 columns
--   messages                                 8 columns
--   nutrition_entries                        9 columns
--   patient_medical_history                  11 columns
--   patient_medications                      19 columns
--   rehab_programs                           8 columns
--   rehab_session_logs                       12 columns
--   risk_assessments                         21 columns
--   uploaded_documents                       10 columns
--   users                                    38 columns
--   vital_signs                              17 columns

-- Detailed column check — look for any missing columns:
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;