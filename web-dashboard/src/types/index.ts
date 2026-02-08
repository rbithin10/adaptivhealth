/*
TypeScript interfaces for AdaptivHealth API responses.

These interfaces match the backend Pydantic schemas exactly.
Keep in sync with app/schemas/ in the FastAPI backend.
*/

// ============================================================================
// Authentication
// ============================================================================

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

// ============================================================================
// User
// ============================================================================

export interface User {
  user_id: number;
  email: string;
  full_name?: string;
  age?: number;
  gender?: string;
  phone?: string;
  weight_kg?: number;
  height_cm?: number;
  baseline_hr?: number;
  max_safe_hr?: number;
  is_active: boolean;
  is_verified: boolean;
  user_role: 'patient' | 'clinician' | 'admin';
  created_at: string;
  updated_at?: string;
}

export interface UserProfileResponse extends User {
  medical_history_encrypted?: string;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Vital Signs
// ============================================================================

export interface VitalSignResponse {
  id: number;
  user_id: number;
  heart_rate: number;
  spo2?: number;
  blood_pressure?: {
    systolic: number;
    diastolic: number;
  };
  hrv?: number;
  source_device?: string;
  is_valid: boolean;
  confidence_score?: number;
  activity_phase?: string;
  timestamp: string;
  created_at: string;
}

export interface VitalSignsSummary {
  date: string;
  avg_heart_rate?: number;
  min_heart_rate?: number;
  max_heart_rate?: number;
  avg_spo2?: number;
  min_spo2?: number;
  avg_hrv?: number;
  total_readings: number;
  valid_readings: number;
  alerts_triggered: number;
}

export interface VitalSignsHistoryResponse {
  vitals: VitalSignResponse[];
  summary?: VitalSignsSummary;
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Risk Assessment
// ============================================================================

export interface RiskAssessmentResponse {
  assessment_id: number;
  user_id: number;
  risk_level: 'low' | 'moderate' | 'high' | 'critical';
  risk_score: number;
  model_name?: string;
  model_version?: string;
  confidence?: number;
  inference_time_ms?: number;
  alert_triggered: boolean;
  activity_session_id?: number;
  assessment_date?: string;
  created_at?: string;
}

export interface RiskAssessmentComputeResponse {
  assessment_id: number;
  user_id: number;
  risk_score: number;
  risk_level: 'low' | 'moderate' | 'high' | 'critical';
  confidence?: number;
  inference_time_ms?: number;
  /** Risk factors that drove the assessment */
  drivers: string[];
  /** Aggregated vitals and features used */
  based_on: Record<string, any>;
}

export interface RiskAssessmentListResponse {
  assessments: RiskAssessmentResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Exercise Recommendation
// ============================================================================

export interface RecommendationResponse {
  recommendation_id: number;
  user_id: number;
  title: string;
  suggested_activity: string;
  intensity_level: 'low' | 'moderate' | 'high' | 'very_high';
  duration_minutes: number;
  target_heart_rate_min?: number;
  target_heart_rate_max?: number;
  description?: string;
  warnings?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  is_completed: boolean;
  generated_by: string;
  model_name?: string;
  confidence_score?: number;
  based_on_risk_assessment_id?: number;
  valid_from?: string;
  valid_until?: string;
  created_at?: string;
  updated_at?: string;
  user_feedback?: string;
  completed_at?: string;
}

export interface RecommendationListResponse {
  recommendations: RecommendationResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Alert
// ============================================================================

export interface AlertResponse {
  alert_id: number;
  user_id: number;
  alert_type:
    | 'high_heart_rate'
    | 'low_heart_rate'
    | 'low_spo2'
    | 'high_blood_pressure'
    | 'irregular_rhythm'
    | 'abnormal_activity'
    | 'other';
  severity: 'info' | 'warning' | 'critical' | 'emergency';
  title?: string;
  message?: string;
  action_required?: string;
  acknowledged: boolean;
  risk_score?: number;
  activity_session_id?: number;
  trigger_value?: string;
  threshold_value?: string;
  resolved_at?: string;
  resolved_by?: number;
  resolution_notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AlertListResponse {
  alerts: AlertResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface AlertStatsResponse {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  unacknowledged_count: number;
}

// ============================================================================
// Activity Session
// ============================================================================

export interface ActivitySessionResponse {
  session_id: number;
  user_id: number;
  activity_type:
    | 'walking'
    | 'running'
    | 'cycling'
    | 'swimming'
    | 'strength_training'
    | 'yoga'
    | 'stretching'
    | 'other';
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  avg_heart_rate?: number;
  peak_heart_rate?: number;
  min_heart_rate?: number;
  avg_spo2?: number;
  calories_burned?: number;
  recovery_time_minutes?: number;
  baseline_heart_rate?: number;
  risk_score?: number;
  recovery_score?: number;
  status?: 'active' | 'completed' | 'paused' | 'cancelled';
  alerts_triggered?: number;
  feeling_before?: string;
  feeling_after?: string;
  user_notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ActivityListResponse {
  activities: ActivitySessionResponse[];
  total: number;
  page: number;
  per_page: number;
}

// ============================================================================
// Health Checks
// ============================================================================

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  environment: 'development' | 'staging' | 'production';
  timestamp: number;
}

export interface DatabaseHealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  database: 'connected' | 'disconnected';
  timestamp: number;
}

// ============================================================================
// Error Response
// ============================================================================

export interface ErrorResponse {
  error: {
    code: number;
    message: string;
    type: string;
    details?: string;
  };
}
