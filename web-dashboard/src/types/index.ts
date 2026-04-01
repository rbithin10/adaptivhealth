/*
types/index.ts — All the data shapes (interfaces) used across the dashboard.

Each interface describes what a piece of data looks like when it comes from the server.
For example, a "User" has an email, name, role, etc. A "VitalSignResponse"
has heart rate, blood oxygen, and blood pressure values.

These must stay in sync with the backend's data models (app/schemas/).
If the backend adds a new field, it should be added here too.
*/

// ============================================================================
// Authentication — Data returned when a user logs in or refreshes their session
// ============================================================================

// What we get back right after a successful login
export interface LoginResponse {
  access_token: string;       // The secret key we send with every request to prove who we are
  token_type: string;         // Always "bearer" — tells the server how to read the token
}

// Extended login response that may include a refresh token for staying logged in longer
export interface TokenResponse {
  access_token: string;       // Short-lived key for making requests
  refresh_token?: string;     // Longer-lived key used to get a new access_token without logging in again
  token_type: string;         // How the server reads the token
  expires_in?: number;        // How many seconds until the access token expires
}

// ============================================================================
// User — Information about a person using the system (patient, clinician, or admin)
// ============================================================================

export interface User {
  user_id: number;            // Unique number that identifies this user in the database
  email: string;              // User's email address (also used for login)
  full_name?: string;         // Display name like "Dr. Smith" or "Jane Doe"
  age?: number;               // Patient's age in years
  gender?: string;            // e.g. "male", "female", "other"
  phone?: string;             // Contact phone number
  weight_kg?: number;         // Patient's weight in kilograms
  height_cm?: number;         // Patient's height in centimetres
  baseline_hr?: number;       // Normal resting heart rate for this patient
  max_safe_hr?: number;       // The highest heart rate considered safe during exercise
  is_active: boolean;         // Whether the account is currently usable (false = deactivated)
  is_verified: boolean;       // Whether the user has verified their email
  user_role: 'patient' | 'clinician' | 'admin';  // What kind of user this is
  risk_level?: 'low' | 'moderate' | 'high' | 'critical';  // Latest overall risk assessment
  risk_score?: number;        // Numeric risk score (0 to 1, where 1 is highest risk)
  assigned_clinician_id?: number;  // Which clinician is responsible for this patient
  created_at: string;         // When the account was created
  updated_at?: string;        // When the account was last modified
  medical_profile_summary?: MedicalProfileSummary;  // Quick overview of medical conditions/meds
}

// Same as User but may include encrypted medical history data
export interface UserProfileResponse extends User {
  medical_history_encrypted?: string;
}

// A paginated list of users returned by the "get all users" endpoint
export interface UserListResponse {
  users: User[];              // The list of user records for this page
  total: number;              // Total number of users across all pages
  page: number;               // Which page we're on  
  per_page: number;           // How many users per page
}

// ============================================================================
// Vital Signs — Heart rate, blood oxygen, blood pressure readings from devices
// ============================================================================

// A single vital signs reading from a patient's wearable or manual input
export interface VitalSignResponse {
  id: number;                 // Unique ID for this reading
  user_id: number;            // Which patient this reading belongs to
  heart_rate: number;         // Beats per minute (normal resting: 60-100)
  spo2?: number;              // Blood oxygen percentage (normal: 95-100%)
  blood_pressure?: {          // Blood pressure reading if available
    systolic: number;         // Top number — pressure when the heart beats
    diastolic: number;        // Bottom number — pressure between beats
  };
  hrv?: number;               // Heart rate variability — how much time varies between beats
  source_device?: string;     // Which device took the reading (e.g. "Apple Watch", "manual")
  is_valid: boolean;          // Whether the reading passed quality checks
  confidence_score?: number;  // How confident the system is in this reading (0 to 1)
  activity_phase?: string;    // What the patient was doing (resting, exercising, recovering)
  timestamp: string;          // When the reading was taken
  created_at: string;         // When it was saved to the database
}

// Summary statistics for a patient's vitals over a period of time
export interface VitalSignsSummary {
  date: string;               // The date this summary covers
  avg_heart_rate?: number;    // Average heart rate for the period
  min_heart_rate?: number;    // Lowest heart rate recorded
  max_heart_rate?: number;    // Highest heart rate recorded
  avg_spo2?: number;          // Average blood oxygen level
  min_spo2?: number;          // Lowest blood oxygen level
  avg_hrv?: number;           // Average heart rate variability
  total_readings: number;     // How many readings were taken
  valid_readings: number;     // How many passed quality checks
  alerts_triggered: number;   // How many alerts were triggered
}

export interface VitalSignsSummaryResponse extends VitalSignsSummary {}

// A page of vital sign readings plus an optional summary
export interface VitalSignsHistoryResponse {
  vitals: VitalSignResponse[];  // List of individual readings
  summary?: VitalSignsSummary;  // Aggregate stats for the period
  total: number;                // Total readings available
  page: number;                 // Current page number
  per_page: number;             // Readings per page
}

// ============================================================================
// Risk Assessment — AI-calculated cardiovascular risk for a patient
// ============================================================================

// The result of an AI risk assessment — how at-risk is this patient?
export interface RiskAssessmentResponse {
  assessment_id: number;       // Unique ID for this assessment
  user_id: number;             // Which patient was assessed
  risk_level: 'low' | 'moderate' | 'high' | 'critical';  // Simple risk category
  risk_score: number;          // Numeric score (0 to 1, higher = more at risk)
  assessment_type?: string;    // How the assessment was generated
  generated_by?: string;       // The system or model that created it
  input_heart_rate?: number;   // Heart rate used in the calculation
  input_spo2?: number;         // Blood oxygen used in the calculation
  input_hrv?: number;          // Heart rate variability used
  input_blood_pressure_sys?: number;   // Systolic blood pressure used
  input_blood_pressure_dia?: number;   // Diastolic blood pressure used
  model_name?: string;         // Name of the AI model that ran the assessment
  model_version?: string;      // Version of the AI model
  confidence?: number;         // How confident the model is (0 to 1)
  inference_time_ms?: number;  // How many milliseconds the prediction took
  primary_concern?: string;    // The biggest risk factor identified
  risk_factors_json?: string;  // JSON string listing all contributing factors
  alert_triggered: boolean;    // Whether this assessment caused an alert
  activity_session_id?: number; // If linked to a specific exercise session
  assessment_date?: string;    // When the assessment was performed
  created_at?: string;         // When it was saved
}

// Response from running a new risk computation — includes the driving factors
export interface RiskAssessmentComputeResponse {
  assessment_id: number;
  user_id: number;
  risk_score: number;
  risk_level: 'low' | 'moderate' | 'high' | 'critical';
  confidence?: number;
  inference_time_ms?: number;
  drivers: string[];           // List of factors that drove the risk score (e.g. "High resting HR")
  based_on: Record<string, unknown>;  // The raw vitals and features that were fed to the model
}

// A paginated list of risk assessments
export interface RiskAssessmentListResponse {
  assessments: RiskAssessmentResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Exercise Recommendation — AI-generated exercise suggestions for patients
// ============================================================================

// A personalised exercise recommendation generated by the AI based on risk level
export interface RecommendationResponse {
  recommendation_id: number;   // Unique ID for this recommendation
  user_id: number;             // Which patient this is for
  title: string;               // Short title like "Light Walking Session"
  suggested_activity: string;  // Type of exercise: walking, cycling, yoga, etc.
  intensity_level: 'low' | 'moderate' | 'high' | 'very_high';  // How hard the exercise should be
  duration_minutes: number;    // How long the session should last
  target_heart_rate_min?: number;  // Minimum safe heart rate during exercise
  target_heart_rate_max?: number;  // Maximum safe heart rate during exercise
  description?: string;        // Detailed instructions for the patient
  warnings?: string;           // Safety warnings (e.g. "Stop if you feel dizzy")
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';  // Progress status
  is_completed: boolean;       // Whether the patient finished the recommended exercise
  generated_by: string;        // The system that created this (e.g. "ml_model_v2")
  model_name?: string;         // AI model name used
  confidence_score?: number;   // Model confidence in this recommendation
  based_on_risk_assessment_id?: number;  // Which risk assessment prompted this recommendation
  valid_from?: string;         // When the recommendation becomes active
  valid_until?: string;        // When it expires
  created_at?: string;
  updated_at?: string;
  user_feedback?: string;      // Optional feedback from the patient
  completed_at?: string;       // When the patient completed the exercise
}

// A paginated list of recommendations
export interface RecommendationListResponse {
  recommendations: RecommendationResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Alert — Automated warnings when vitals go outside safe ranges
// ============================================================================

// A clinical alert triggered when something needs attention (e.g. heart rate too high)
export interface AlertResponse {
  alert_id: number;            // Unique ID for this alert
  user_id: number;             // Which patient triggered the alert
  alert_type:                  // What kind of issue was detected
    | 'high_heart_rate'        // Heart rate above the safe threshold
    | 'low_heart_rate'         // Heart rate below normal
    | 'low_spo2'              // Blood oxygen dropped too low
    | 'high_blood_pressure'    // Blood pressure reading too high
    | 'irregular_rhythm'       // Irregular heartbeat pattern detected
    | 'abnormal_activity'      // Unusual activity during exercise
    | 'other';
  severity: 'info' | 'warning' | 'critical' | 'emergency';  // How urgent the alert is
  title?: string;              // Short alert title
  message?: string;            // Detailed alert message
  action_required?: string;    // What the clinician should do
  acknowledged: boolean;       // Whether a clinician has seen and acknowledged this alert
  risk_score?: number;         // Risk score at the time of the alert
  activity_session_id?: number; // If this alert happened during an exercise session
  trigger_value?: string;      // The actual value that triggered the alert (e.g. "142 BPM")
  threshold_value?: string;    // The threshold that was exceeded (e.g. "120 BPM")
  resolved_at?: string;        // When the alert was resolved
  resolved_by?: number;        // Which clinician resolved it
  resolution_notes?: string;   // Notes about how it was resolved
  created_at?: string;
  updated_at?: string;
}

// Summary statistics about alerts across all patients
export interface AlertListResponse {
  alerts: AlertResponse[];     // List of alerts on this page
  total: number;               // Total alerts across all pages
  page: number;
  per_page: number;
}

// Aggregated alert statistics for the dashboard overview cards
export interface AlertStatsResponse {
  total: number;                           // Total number of alerts
  by_severity: Record<string, number>;     // Count of alerts grouped by severity (e.g. critical: 3)
  by_type: Record<string, number>;         // Count of alerts grouped by type (e.g. high_heart_rate: 5)
  unacknowledged_count: number;            // How many alerts still haven't been seen by a clinician
}

// ============================================================================
// Activity Session — Records of patient exercise or movement sessions
// ============================================================================

// One exercise session — tracks what the patient did and their vitals during it
export interface ActivitySessionResponse {
  session_id: number;          // Unique ID for this session
  user_id: number;             // Which patient exercised
  activity_type:               // What kind of exercise
    | 'walking'
    | 'running'
    | 'cycling'
    | 'swimming'
    | 'strength_training'
    | 'yoga'
    | 'stretching'
    | 'other';
  start_time: string;          // When the session started
  end_time?: string;           // When it ended (empty if still in progress)
  duration_minutes?: number;   // How long the session lasted
  avg_heart_rate?: number;     // Average heart rate during the session
  peak_heart_rate?: number;    // Highest heart rate reached
  min_heart_rate?: number;     // Lowest heart rate during the session
  avg_spo2?: number;           // Average blood oxygen during the session
  calories_burned?: number;    // Estimated calories burned
  recovery_time_minutes?: number;  // How long it took heart rate to return to normal
  baseline_heart_rate?: number;    // The patient's resting HR before the session
  risk_score?: number;         // Risk score calculated for this session
  recovery_score?: number;     // How well the patient recovered
  status?: 'active' | 'completed' | 'paused' | 'cancelled';
  alerts_triggered?: number;   // How many alerts were triggered during the session
  feeling_before?: string;     // Patient's self-reported feeling before exercise
  feeling_after?: string;      // Patient's self-reported feeling after exercise
  user_notes?: string;         // Any notes the patient added
  created_at?: string;
  updated_at?: string;
}

// A paginated list of activity sessions
export interface ActivityListResponse {
  activities: ActivitySessionResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Health Checks — Used to verify the backend server and database are running
// ============================================================================

// Response from the basic health check endpoint
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';     // Whether the server is working
  version: string;                      // Backend version number
  environment: 'development' | 'staging' | 'production';  // Which environment we're talking to
  timestamp: number;                    // Server time as a Unix timestamp
}

// Response from the database health check endpoint
export interface DatabaseHealthCheckResponse {
  status: 'healthy' | 'unhealthy';     // Whether the database is accessible
  database: 'connected' | 'disconnected';  // Connection status
  timestamp: number;
}

// ============================================================================
// Advanced ML — Anomaly Detection (spots unusual readings in a patient's vitals)
// ============================================================================

// A single anomalous (unusual) reading that the AI flagged
export interface AnomalyItem {
  index: number;               // Position in the list of readings
  metric: 'heart_rate' | 'spo2' | 'hr_variability';  // Which vital sign was unusual
  value: number;               // The actual value that was flagged
  z_score: number | null;      // How far from normal this value is (higher = more unusual)
  direction: 'high' | 'low' | 'spike' | 'drop';  // Whether the value was too high or too low
  timestamp: string | null;    // When the unusual reading occurred
}

// Full response from the anomaly detection endpoint
export interface AnomalyDetectionResponse {
  anomalies: AnomalyItem[];   // List of all unusual readings found
  total_readings: number;      // How many total readings were analysed
  anomaly_count: number;       // How many were flagged as unusual
  status: 'normal' | 'anomalies_detected' | 'insufficient_data';  // Overall result
  message?: string;            // Human-readable explanation of the result
  stats: {                     // Statistical summary used for comparison
    hr_mean: number | null;    // Average heart rate
    hr_std: number | null;     // How much heart rate varies (standard deviation)
    spo2_mean: number | null;  // Average SpO2
    spo2_std: number | null;   // How much SpO2 varies
  };
  z_threshold: number;         // The cutoff used to decide what's "unusual"
  user_id: number;
  window_hours: number;        // How many hours of data were checked
}

// ============================================================================
// Advanced ML — Model Retraining Pipeline (for clinicians to monitor AI model health)
// ============================================================================

// Current status of the AI model — is it up to date?
export interface RetrainingStatusResponse {
  model_dir: string;           // Where the model files live on the server
  model_exists: boolean;       // Whether a trained model file exists
  scaler_exists: boolean;      // Whether the data scaler file exists (needed for predictions)
  features_exists: boolean;    // Whether the feature list file exists
  model_size_bytes?: number;   // How big the model file is
  model_modified?: string;     // When the model was last updated
  metadata: {                  // Information about the current model version
    model_name: string;
    version: string;
    accuracy: string;          // How accurate the model is (e.g. "0.93")
    note?: string;
    records_used?: number;     // How many patient records were used to train it
    retrained_at?: string;     // When it was last retrained
  } | null;
}

// Whether the model is ready to be retrained with new data
export interface RetrainingReadinessResponse {
  ready: boolean;              // True if retraining can proceed
  new_records: number;         // How many new records are available since last training
  min_records_required: number; // Minimum records needed to trigger retraining
  last_retrain_date: string | null;  // When the model was last retrained
  min_days_between_retrains: number; // Minimum days that must pass between retraining runs
  reasons: string[];           // Human-readable reasons why retraining is/isn't ready
}

// ============================================================================
// Advanced ML — Prediction Explainability (explains WHY the AI gave a certain risk score)
// ============================================================================

// One factor that contributed to the risk prediction
export interface ExplainFeatureItem {
  feature: string;             // Name of the factor (e.g. "avg_heart_rate")
  value: number;               // The actual value for this patient
  contribution: number;        // How much this factor pushed the risk score (positive or negative)
  direction: 'increasing' | 'decreasing' | 'neutral';  // Whether it raised or lowered the risk
  explanation: string;         // Plain English explanation
  global_importance: number;   // How important this factor is across ALL patients (0 to 1)
}

// Full explanation response — tells you why the AI gave a specific risk score
export interface ExplainPredictionResponse {
  risk_score: number;          // The predicted risk score
  risk_level: string;          // "low", "moderate", "high", or "critical"
  feature_importance: {        // Breakdown of what influenced the prediction
    top_features: ExplainFeatureItem[];  // The most influential factors, ranked
    global_importances: Record<string, number>;  // Every feature's general importance
    feature_count: number;     // Total features analysed
    method: string;            // The analysis method used (e.g. "permutation_importance")
  };
  plain_explanation: string;   // A simple English paragraph explaining the result
}

// ============================================================================
// Advanced ML — Natural Language Alerts & Risk Summary (AI-written patient-friendly text)
// ============================================================================

// A patient-friendly alert message written by AI instead of raw numbers
export interface NaturalLanguageAlertResponse {
  friendly_message: string;    // The alert in plain, easy-to-understand language
  action_steps: string[];      // List of things the patient should do
  urgency_level: 'act_now' | 'urgent' | 'attention_needed' | 'for_your_info';
  risk_context: string | null; // Additional context about the patient's overall risk
  original_alert_type: string; // The technical alert type this was generated from
  original_severity: string;   // The technical severity level
  user_id: number;
}

// A plain English summary of a patient's risk status
export interface NaturalLanguageRiskSummaryResponse {
  user_id: number;
  risk_score: number;
  risk_level: string;
  plain_summary: string;       // Easy-to-read summary of the patient's risk situation
  assessment_date: string | null;
}

// ============================================================================
// Clinical Notes — Clinician-authored notes per patient
// ============================================================================

export interface ClinicalNote {
  note_id: number;
  user_id: number;
  clinician_id: number;
  clinician_name?: string;
  content: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Advanced ML — Recommendation Ranking (A/B Testing different exercise plans)
// ============================================================================

// One variant of an exercise recommendation used in A/B testing
export interface RankedRecommendationVariant {
  title: string;               // Name of the exercise plan
  suggested_activity: string;  // Type of activity
  intensity_level: 'low' | 'moderate' | 'high';
  duration_minutes: number;    // How long the session should be
  description: string;         // Detailed instructions
  target_heart_rate_min?: number;  // Safe minimum HR during exercise
  target_heart_rate_max?: number;  // Safe maximum HR during exercise
  created_at?: string;         // When recommendation was generated
}

// The A/B test result — which variant was shown to this patient
export interface RankedRecommendationResponse {
  variant: 'A' | 'B';         // Which version was selected (A or B)
  risk_level: 'low' | 'moderate' | 'high' | 'critical';
  recommendation: RankedRecommendationVariant;  // The actual recommendation details
  experiment_id: string;       // ID to track this experiment for outcome analysis
  user_id: number;
}

// Records whether the patient completed, skipped, or partially did the recommendation
export interface RecommendationOutcomeResponse {
  user_id: number;
  experiment_id: string;
  variant: string;
  outcome: 'completed' | 'skipped' | 'partial';
  outcome_value: number | null;  // Optional numeric measure of how well they did
  status: string;
}

// ============================================================================
// Advanced ML — Baseline Optimization (automatically adjusting a patient's normal heart rate)
// ============================================================================

// Result of computing an optimised baseline heart rate from recent resting data
export interface BaselineOptimizationResponse {
  status: 'ok' | 'insufficient_data' | 'insufficient_valid_data';
  message?: string;
  current_baseline: number | null;  // The patient's current baseline HR in their profile
  new_baseline: number | null;      // The suggested new baseline HR based on recent data
  adjustment: number;               // How much the baseline would change
  adjusted: boolean;                // Whether an adjustment is recommended
  confidence: number;               // How confident the system is in the new baseline
  readings_used: number;            // How many resting readings contributed to the calculation
  readings_total: number;           // Total readings in the time window
  stats: {                          // Statistical details of the resting readings
    mean_hr: number;                // Average resting heart rate
    std_hr: number;                 // Standard deviation of resting HR
    min_hr: number;                 // Lowest resting HR recorded
    max_hr: number;                 // Highest resting HR recorded
  };
  user_id: number;
  data_window_days: number;         // How many days of data were analysed
}

// Response after actually applying the optimised baseline to the patient
export interface BaselineApplyResponse extends BaselineOptimizationResponse {
  applied: boolean;                 // Whether the new baseline was actually saved
}

// ============================================================================
// Advanced ML — Trend Forecast (predicts where a patient's vitals are heading)
// ============================================================================

// Trend analysis for a single metric (e.g. heart rate going up 0.5 BPM per day)
export interface TrendMetric {
  slope_per_day: number;       // How much the metric changes each day (positive = rising)
  direction: 'increasing' | 'stable' | 'decreasing';  // Overall direction
  current_fitted: number;      // The model's estimate of the current value
  forecasted_value: number;    // Where the model predicts the value will be
  forecast_day: number;        // How many days ahead the forecast is looking
  r_squared: number;           // How well the trend line fits the data (0 to 1)
  data_points: number;         // How many readings were used in the analysis
}

// Projection of how the patient's overall risk is expected to change
export interface RiskProjection {
  risk_direction: 'increasing' | 'stable' | 'decreasing';  // Which way risk is trending
  risk_score_delta: number;    // Expected change in risk score
  factors: string[];           // Which factors are driving the trend
}

// Full trend forecast response including vital trends and risk projection
export interface TrendForecastResponse {
  status: 'ok' | 'insufficient_data';
  message?: string;
  total_readings: number;      // How many readings were analysed
  forecast_days: number;       // How many days ahead we're forecasting
  trends: {                    // Trend analysis per metric
    heart_rate?: TrendMetric;  // Heart rate trend (if enough data)
    spo2?: TrendMetric;        // Blood oxygen trend (if enough data)
  };
  risk_projection?: RiskProjection;  // Overall risk direction prediction
  user_id: number;
  analysis_days: number;       // How many days of historical data were used
}

// ============================================================================
// Messaging — Secure messages between clinicians and patients
// ============================================================================

// A single message in a conversation
export interface MessageResponse {
  message_id: number;          // Unique ID for this message
  sender_id: number;           // Who sent it
  receiver_id: number;         // Who it's addressed to
  content: string;             // The actual message text
  sent_at: string;             // When it was sent
  is_read: boolean;            // Whether the recipient has read it
}

// An inbox entry showing the latest message with a patient and unread count
export interface InboxSummaryResponse {
  patient_id: number;          // Which patient this conversation is with
  patient_name: string;        // The patient's display name
  last_message_content: string; // Preview of the most recent message
  last_message_sender_id: number;  // Who sent the most recent message
  last_message_sent_at: string;    // When the most recent message was sent
  unread_count: number;        // How many messages the clinician hasn't read yet
}

// ============================================================================
// Medical History & Medications — A patient's recorded conditions and drugs
// ============================================================================

// A single medical condition on a patient's record (e.g. "Prior heart attack")
export interface MedicalCondition {
  history_id: number;          // Unique ID for this record
  user_id: number;             // Which patient
  condition_type: string;      // Category like "prior_mi" (prior heart attack) or "heart_failure"
  condition_detail?: string;   // More specific details about the condition
  diagnosis_date?: string;     // When the condition was diagnosed
  status: 'active' | 'resolved' | 'managed';  // Current status of the condition
  notes?: string;              // Clinician notes about this condition
  created_at?: string;
  updated_at?: string;
}

// A single medication a patient is taking
export interface Medication {
  medication_id: number;       // Unique ID for this medication record
  user_id: number;             // Which patient
  drug_class: string;          // Category like "beta_blocker" or "anticoagulant"
  drug_name: string;           // Specific drug name like "Metoprolol"
  dose?: string;               // Dosage like "50mg"
  frequency: string;           // How often: "daily", "twice_daily", etc.
  is_hr_blunting: boolean;     // Whether this drug slows heart rate (affects exercise targets)
  is_anticoagulant: boolean;   // Whether this is a blood thinner (affects risk calculations)
  status: 'active' | 'discontinued' | 'on_hold';
  start_date?: string;         // When the patient started taking this
  end_date?: string;           // When they stopped (if discontinued)
  prescribed_by?: string;      // Which clinician prescribed it
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

// Complete medical profile combining conditions, medications, and key flags
export interface MedicalProfile {
  user_id: number;
  conditions: MedicalCondition[];    // All recorded medical conditions
  medications: Medication[];          // All recorded medications
  has_prior_mi: boolean;              // Has the patient had a heart attack before?
  has_heart_failure: boolean;         // Does the patient have heart failure?
  heart_failure_class?: string;       // NYHA class (I-IV) if heart failure is present
  is_on_beta_blocker: boolean;        // Taking a beta-blocker? (lowers heart rate targets)
  is_on_anticoagulant: boolean;       // Taking blood thinners?
  is_on_antiplatelet: boolean;        // Taking antiplatelet drugs like aspirin?
  active_condition_count: number;     // Total number of active conditions
  active_medication_count: number;    // Total number of active medications
  uploaded_documents?: UploadedDocumentSummary[];  // Medical documents uploaded for this patient
  latest_document_url?: string;       // Link to the most recent uploaded document
  has_document_storage_warning?: boolean;  // True if some document files are missing
  missing_document_count?: number;    // How many documents have lost their files
}

// A quick-glance summary of the medical profile, used in patient list tables
export interface MedicalProfileSummary {
  user_id: number;
  has_prior_mi: boolean;
  has_heart_failure: boolean;
  is_on_beta_blocker: boolean;
  is_on_anticoagulant: boolean;
  has_uploaded_document?: boolean;
  has_accessible_document?: boolean;
  active_condition_count: number;
  active_medication_count: number;
}

// Information about an uploaded medical document (PDF, image, etc.)
export interface UploadedDocumentSummary {
  document_id: number;
  filename: string;            // Original file name
  file_type: string;           // MIME type like "application/pdf"
  status: string;              // Processing status
  created_at?: string;
  view_url: string;            // URL to view/download the document
  file_available?: boolean;    // Whether the actual file still exists on the server
}

// Response after uploading a medical document — includes AI-extracted conditions and medications
export interface DocumentUploadResponse {
  document_id: number;
  filename: string;
  status: string;
  extracted_conditions: MedicalConditionCreate[];   // Conditions the AI found in the document
  extracted_medications: MedicationCreate[];         // Medications the AI found in the document
  extraction_message: string;  // Summary of what the AI extracted
}

// Data needed to add a new medical condition to a patient's profile
export interface MedicalConditionCreate {
  condition_type: string;
  condition_detail?: string;
  diagnosis_date?: string;
  status?: string;
  notes?: string;
}

// Data needed to add a new medication to a patient's profile
export interface MedicationCreate {
  drug_class: string;          // Category of drug (e.g. "beta_blocker")
  drug_name: string;           // Specific drug name (e.g. "Metoprolol")
  dose?: string;               // Dosage (e.g. "50mg")
  frequency?: string;          // How often taken (e.g. "daily")
  status?: string;             // "active", "discontinued", or "on_hold"
  start_date?: string;
  end_date?: string;
  prescribed_by?: string;
  notes?: string;
}

// ============================================================================
// Error Response — Standard error format returned by the backend
// ============================================================================

export interface ErrorResponse {
  error: {
    code: number;              // HTTP status code (e.g. 404, 500)
    message: string;           // Human-readable error message
    type: string;              // Error category (e.g. "validation_error")
    details?: string;          // Extra detail about what went wrong
  };
}

// Status of the AI medical document extraction feature (is it available?)
export interface MedicalExtractionStatusResponse {
  feature: string;             // Feature name
  provider: string;            // AI provider (e.g. "google")
  model: string;               // Model used (e.g. "gemini-pro")
  gemini_key_configured: boolean;  // Whether the API key is set
  gemini_sdk_available: boolean;   // Whether the SDK is installed
  ready: boolean;              // Overall: can we use this feature right now?
}

// ============================================================================
// Consent / Sharing — Patient data sharing permissions
// ============================================================================

// Current consent/sharing status for a patient
export interface ConsentStatusResponse {
  share_state: string;         // Current sharing state (e.g. "opted_in", "opted_out")
  consent_request_pending?: boolean;  // Whether there's a pending request to change
  requested_share_state?: string;     // What sharing state was requested
  consent_updated_at?: string;        // When consent was last changed
}

// A patient who has requested a change to their data sharing preferences
export interface PendingConsentRequest {
  user_id: number;
  email?: string;
  full_name?: string;
  reason?: string;             // Why they want to change their sharing preference
  requested_at?: string;
}

// List of patients with pending consent changes for clinicians to review
export interface PendingConsentRequestsResponse {
  pending_requests: PendingConsentRequest[];
  total?: number;
}

// Result of a clinician approving or rejecting a consent request
export interface ReviewConsentResponse {
  status: string;
  message?: string;
  user_id?: number;
  decision?: 'approve' | 'reject';
}

// ============================================================================
// Admin — Responses for admin-only user management operations
// ============================================================================

// Result of an admin resetting a user's password
export interface AdminResetPasswordResponse {
  message: string;             // Success/failure message
  user_id?: number;
}

// Result of an admin deactivating a user account
export interface DeactivateUserResponse {
  message: string;
}

// Result of assigning a clinician to a patient
export interface AssignClinicianResponse {
  message: string;
  patient_id?: number;         // Which patient was assigned
  clinician_id?: number;       // Which clinician was assigned to them
}
