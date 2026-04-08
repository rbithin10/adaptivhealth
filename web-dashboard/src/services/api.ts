/*
API client for the web dashboard.

Talks to the backend server to get user data, vital signs, risk scores,
and alerts. Automatically adds the login token to every request so the
server knows who is asking.

Matches backend API at /api/v1 with correct endpoint prefixes and schemas.
*/

// Import the HTTP library (axios) used to talk to the backend server
import axios, { AxiosInstance, AxiosError } from 'axios';
// Import all the data shapes we expect back from the server
import {
  TokenResponse,
  User,
  UserProfileResponse,
  UserListResponse,
  VitalSignResponse,
  VitalSignsHistoryResponse,
  RiskAssessmentResponse,
  RiskAssessmentComputeResponse,
  RecommendationResponse,
  AlertResponse,
  AlertListResponse,
  AlertStatsResponse,
  ActivitySessionResponse,
  ActivityListResponse,
  HealthCheckResponse,
  DatabaseHealthCheckResponse,
  AnomalyDetectionResponse,
  TrendForecastResponse,
  BaselineOptimizationResponse,
  BaselineApplyResponse,
  RankedRecommendationResponse,
  RecommendationOutcomeResponse,
  NaturalLanguageAlertResponse,
  NaturalLanguageRiskSummaryResponse,
  RetrainingStatusResponse,
  RetrainingReadinessResponse,
  ExplainPredictionResponse,
  MessageResponse,
  InboxSummaryResponse,
  VitalSignsSummaryResponse,
  ConsentStatusResponse,
  PendingConsentRequestsResponse,
  ReviewConsentResponse,
  AdminResetPasswordResponse,
  DeactivateUserResponse,
  AssignClinicianResponse,
  MedicalCondition,
  Medication,
  MedicalProfile,
  MedicalConditionCreate,
  MedicationCreate,
  DocumentUploadResponse,
  MedicalExtractionStatusResponse,
  ClinicalNote,
} from '../types';

// The server address — uses an environment variable if set, otherwise the live production URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://back-adaptivhealthuowd.xyz';

// The backend sometimes returns user data with different field names
// This function makes them consistent so the rest of the app doesn't have to guess
const normalizeUser = (
  data: Partial<User> & { id?: number; name?: string; role?: string }
): User => ({
  ...data,
  user_id: data.user_id ?? data.id,         // Use "user_id" or fall back to "id"
  full_name: data.full_name ?? data.name,    // Use "full_name" or fall back to "name"
  user_role: data.user_role ?? data.role,    // Use "user_role" or fall back to "role"
  assigned_clinician_id: data.assigned_clinician_id,
} as User);

// This class handles ALL communication between the web dashboard and the backend server
class ApiService {
  private client: AxiosInstance; // The HTTP client that actually sends/receives data

  constructor() {
    const axiosBase = `${API_BASE_URL}/api/v1`;
    console.info('[DIAG][REACT_API_TARGET]', {
      envApiUrl: process.env.REACT_APP_API_URL ?? null,
      apiBaseUrlResolved: API_BASE_URL,
      axiosBaseUrl: axiosBase,
      refreshUrl: `${API_BASE_URL}/api/v1/session/extend`,
    });

    // Set up the HTTP client with the server address and default settings
    this.client = axios.create({
      baseURL: axiosBase,  // All requests go to /api/v1 on the server
      headers: {
        'Content-Type': 'application/json', // Tell the server we're sending JSON data
      },
    });

    // Before every request, automatically attach the user's login token
    // so the server knows who is making the request
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token'); // Get the saved login token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`; // Add it to the request header
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // After every response, check if the user's session expired (401 error)
    // If so, try to refresh the token automatically so the user stays logged in
    this.client.interceptors.response.use(
      (response) => response, // If the response is fine, just pass it through
      async (error: AxiosError) => {
        const originalRequest = (error.config ?? {}) as AxiosError['config'] & { _retry?: boolean };
        if (error.response?.status === 401 && !originalRequest._retry) {
          console.log('[DEBUG] 401 detected, attempting refresh');
          originalRequest._retry = true; // Mark this request so we don't retry forever
          const refreshResult = await this.refreshSession();
          if (refreshResult) {
            const newToken = localStorage.getItem('token');
            if (newToken) {
              originalRequest.headers = originalRequest.headers ?? {};
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }
            return this.client(originalRequest);
          }
          // Refresh failed — clear login data and send the user to login
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Refresh the current session using the saved refresh token.
  // Returns true if a new access token was stored.
  private async refreshSession(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      return false;
    }

    try {
      const resp = await axios.post(`${API_BASE_URL}/api/v1/session/extend`, { refresh_token: refreshToken });
      const newToken = resp.data.access_token;
      localStorage.setItem('token', newToken);
      if (resp.data.refresh_token) {
        localStorage.setItem('refresh_token', resp.data.refresh_token);
      }
      return Boolean(newToken);
    } catch {
      return false;
    }
  }

  // =========================================================================
  // Health Checks — Quick checks to see if the server is running
  // =========================================================================

  // Check if the main server is alive and responding
  async getHealth(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');
    return response.data;
  }

  // Check if the database connection is working
  async getDatabaseHealth(): Promise<DatabaseHealthCheckResponse> {
    const response = await this.client.get<DatabaseHealthCheckResponse>('/health/db');
    return response.data;
  }

  // =========================================================================
  // Authentication — Login, logout, register, and password reset
  // =========================================================================

  // Log in with email and password — returns a token the app stores to stay logged in
  async login(email: string, password: string): Promise<TokenResponse> {
    // The login endpoint expects form data (not JSON), like a traditional web form
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await axios.post<TokenResponse>(`${API_BASE_URL}/api/v1/session/start`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  // Send a password reset email to the user
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const response = await this.client.post('/reset-password', { email });
    return response.data;
  }

  // Complete the password reset using the token from the email link
  async confirmPasswordReset(token: string, newPassword: string): Promise<{ message: string }> {
    const response = await this.client.post('/reset-password/confirm', {
      token,
      new_password: newPassword,
    });
    return response.data;
  }

  // Log out — tells the server to expire the token and clears local saved data
  async logout(): Promise<void> {
    try {
      // Tell the server to revoke the token so it can't be reused
      await axios.post(`${API_BASE_URL}/api/v1/session/end`);
    } catch {
      // Even if the server request fails, we still clear local data
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  }

  // Create a new user account with the provided details
  async register(userData: {
    email: string;
    password: string;
    full_name: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<User> {
    const response = await this.client.post<User>('/users/enroll', {
      email: userData.email,
      password: userData.password,
      name: userData.full_name,
      age: userData.age,
      gender: userData.gender,
      phone: userData.phone,
    });
    return normalizeUser(response.data);
  }

  // =========================================================================
  // User Management — View and update user profiles
  // =========================================================================

  // Get the profile of the currently logged-in user
  async getCurrentUser(): Promise<UserProfileResponse> {
    const response = await this.client.get<UserProfileResponse>('/users/me');
    return normalizeUser(response.data) as UserProfileResponse;
  }

  // Update the logged-in user's own profile details
  async updateCurrentUserProfile(data: {
    full_name?: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<UserProfileResponse> {
    const response = await this.client.put<UserProfileResponse>('/users/me', {
      name: data.full_name,
      age: data.age,
      gender: data.gender,
      phone: data.phone,
    });
    return normalizeUser(response.data) as UserProfileResponse;
  }

  // Get a list of all users — can filter by role (patient/clinician/admin) and search by name
  async getAllUsers(
    page: number = 1,
    perPage: number = 50,
    role?: 'patient' | 'clinician' | 'admin',
    search?: string
  ): Promise<UserListResponse> {
    const response = await this.client.get<UserListResponse>('/users', {
      params: {
        page,
        per_page: perPage,
        ...(role ? { role } : {}),       // Only include role filter if specified
        ...(search ? { search } : {}),   // Only include search term if specified
      },
    });
    return {
      ...response.data,
      users: response.data.users.map(normalizeUser), // Normalize every user in the list
    };
  }

  // Get a specific user's profile by their ID number
  async getUserById(userId: number): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return normalizeUser(response.data);
  }

  // =========================================================================
  // Vital Signs — Heart rate, oxygen levels, blood pressure readings
  // =========================================================================

  // Get the most recent vital signs for the logged-in user
  async getLatestVitalSigns(): Promise<VitalSignResponse> {
    const response = await this.client.get<VitalSignResponse>('/vitals/latest');
    return response.data;
  }

  // Get the most recent vital signs for a specific patient (by their ID)
  async getLatestVitalSignsForUser(userId: number): Promise<VitalSignResponse> {
    const response = await this.client.get<VitalSignResponse>(`/vitals/user/${userId}/latest`);
    return response.data;
  }

  // Get a paginated list of past vital sign readings for the logged-in user
  async getVitalSignsHistory(
    page: number = 1,
    perPage: number = 50
  ): Promise<VitalSignsHistoryResponse> {
    const response = await this.client.get<VitalSignsHistoryResponse>(
      '/vitals/history',
      {
        params: { page, per_page: perPage },
      }
    );
    return response.data;
  }

  // Get past vital sign readings for a specific patient over a number of days
  async getVitalSignsHistoryForUser(
    userId: number,
    days: number = 7,
    page: number = 1,
    perPage: number = 50
  ): Promise<VitalSignsHistoryResponse> {
    const response = await this.client.get<VitalSignsHistoryResponse>(
      `/vitals/user/${userId}/history`,
      {
        params: { days, page, per_page: perPage },
      }
    );
    return response.data;
  }

  // Get a statistical summary (averages, min, max) of recent vitals
  async getVitalSignsSummary(days: number = 7): Promise<VitalSignsSummaryResponse> {
    const response = await this.client.get<VitalSignsSummaryResponse>('/vitals/summary', {
      params: { days },
    });
    return response.data;
  }

  // Get a statistical summary of vitals for a specific patient
  async getVitalSignsSummaryForUser(userId: number, days: number = 7): Promise<VitalSignsSummaryResponse> {
    const response = await this.client.get<VitalSignsSummaryResponse>(`/vitals/user/${userId}/summary`, {
      params: { days },
    });
    return response.data;
  }

  // Submit new vital sign readings (e.g. from a wearable device or manual entry)
  async submitVitalSigns(vitals: {
    heart_rate: number;
    spo2?: number;
    blood_pressure_systolic?: number;
    blood_pressure_diastolic?: number;
    hrv?: number;
    source_device?: string;
    device_id?: string;
    timestamp?: string;
  }): Promise<VitalSignResponse> {
    const response = await this.client.post<VitalSignResponse>('/vitals', vitals);
    return response.data;
  }

  // =========================================================================
  // Risk Assessments — How likely is a cardiac event for this patient?
  // =========================================================================

  // Get the most recent risk assessment for the logged-in user
  async getLatestRiskAssessment(): Promise<RiskAssessmentResponse> {
    const response = await this.client.get<RiskAssessmentResponse>(
      '/risk-assessments/latest'
    );
    return response.data;
  }

  // Get the most recent risk assessment for a specific patient
  async getLatestRiskAssessmentForUser(userId: number): Promise<RiskAssessmentResponse> {
    const response = await this.client.get<RiskAssessmentResponse>(
      `/patients/${userId}/risk-assessments/latest`
    );
    return response.data;
  }

  // Ask the server to calculate a fresh risk assessment for the logged-in user
  async computeRiskAssessment(): Promise<RiskAssessmentComputeResponse> {
    const response = await this.client.post<RiskAssessmentComputeResponse>(
      '/risk-assessments/compute'
    );
    return response.data;
  }

  // Ask the server to calculate a fresh risk assessment for a specific patient
  async computeRiskAssessmentForUser(userId: number): Promise<RiskAssessmentComputeResponse> {
    const response = await this.client.post<RiskAssessmentComputeResponse>(
      `/patients/${userId}/risk-assessments/compute`
    );
    return response.data;
  }

  // Run a custom risk prediction using manually provided health measurements
  async predictRisk(data: {
    age: number;
    baseline_hr: number;
    max_safe_hr: number;
    avg_heart_rate: number;
    peak_heart_rate: number;
    min_heart_rate: number;
    avg_spo2: number;
    duration_minutes: number;
    recovery_time_minutes: number;
    activity_type?: string;
  }): Promise<RiskAssessmentResponse> {
    const response = await this.client.post<RiskAssessmentResponse>(
      '/predict/risk',
      data
    );
    return response.data;
  }

  // =========================================================================
  // Recommendations — Personalised health advice for patients
  // =========================================================================

  // Get the most recent recommendation for the logged-in user
  async getLatestRecommendation(): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>(
      '/recommendations/latest'
    );
    return response.data;
  }

  // Get the most recent recommendation for a specific patient
  async getLatestRecommendationForUser(userId: number): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>(
      `/patients/${userId}/recommendations/latest`
    );
    return response.data;
  }

  // =========================================================================
  // Alerts — Health warnings and notifications for patients
  // =========================================================================

  // Get a paginated list of alerts for the logged-in user
  async getAlerts(
    page: number = 1,
    perPage: number = 50
  ): Promise<AlertListResponse> {
    const response = await this.client.get<AlertListResponse>('/alerts', {
      params: { page, per_page: perPage },
    });
    return response.data;
  }

  // Get alerts for a specific patient by their ID
  async getAlertsForUser(
    userId: number,
    page: number = 1,
    perPage: number = 50
  ): Promise<AlertListResponse> {
    const response = await this.client.get<AlertListResponse>(`/alerts/user/${userId}`, {
      params: { page, per_page: perPage },
    });
    return response.data;
  }

  // Get alert statistics (counts by severity, type, etc.)
  async getAlertStats(): Promise<AlertStatsResponse> {
    const response = await this.client.get<AlertStatsResponse>('/alerts/stats', {
      params: { days: 1, _ts: Date.now() },
    });
    return response.data;
  }

  // Mark an alert as "seen" by the clinician
  async acknowledgeAlert(alertId: number): Promise<AlertResponse> {
    const response = await this.client.patch<AlertResponse>(
      `/alerts/${alertId}/acknowledge`
    );
    return response.data;
  }

  // Mark an alert as resolved with optional notes about what was done
  async resolveAlert(
    alertId: number,
    data: {
      resolution_notes?: string;
      acknowledged?: boolean;
    }
  ): Promise<AlertResponse> {
    const response = await this.client.patch<AlertResponse>(
      `/alerts/${alertId}/resolve`,
      data
    );
    return response.data;
  }

  // =========================================================================
  // Activities — Exercise sessions tracked by the patient
  // =========================================================================

  // Get a list of recent activity sessions for the logged-in user
  async getActivities(limit: number = 50, offset: number = 0): Promise<ActivityListResponse> {
    const response = await this.client.get('/activities', {
      params: { limit, offset },
    });
    const data = response.data;
    // The server might return a plain array or a structured object — handle both
    if (Array.isArray(data)) {
      return {
        activities: data,
        total: data.length,
        page: 1,
        per_page: data.length,
      };
    }
    return data as ActivityListResponse;
  }

  // Get activity sessions for a specific patient
  async getActivitiesForUser(
    userId: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<ActivityListResponse> {
    const response = await this.client.get(`/activities/user/${userId}`, {
      params: { limit, offset },
    });
    const data = response.data;
    if (Array.isArray(data)) {
      return {
        activities: data,
        total: data.length,
        page: 1,
        per_page: data.length,
      };
    }
    return data as ActivityListResponse;
  }

  // Get details of a single activity session by its ID
  async getActivityById(sessionId: number): Promise<ActivitySessionResponse> {
    const response = await this.client.get<ActivitySessionResponse>(
      `/activities/${sessionId}`
    );
    return response.data;
  }

  // Start a new activity session (e.g. "walking", "cycling")
  async startActivity(data: {
    activity_type: string;
  }): Promise<ActivitySessionResponse> {
    const response = await this.client.post<ActivitySessionResponse>(
      '/activities/start',
      data
    );
    return response.data;
  }

  // End an in-progress activity session
  async endActivity(sessionId: number): Promise<ActivitySessionResponse> {
    const response = await this.client.post<ActivitySessionResponse>(
      `/activities/end/${sessionId}`
    );
    return response.data;
  }

  // =========================================================================
  // Advanced ML — Smart analytics powered by machine learning
  // =========================================================================

  // Look for unusual patterns in a patient's recent vitals (anomaly detection)
  async getAnomalyDetection(
    userId: number,
    hours: number = 24,
    zThreshold: number = 2.0
  ): Promise<AnomalyDetectionResponse> {
    const response = await this.client.get<AnomalyDetectionResponse>(
      '/anomaly-detection',
      { params: { user_id: userId, hours, z_threshold: zThreshold } }
    );
    return response.data;
  }

  // Predict where a patient's vitals are heading over the next few weeks
  async getTrendForecast(
    userId: number,
    days: number = 14,
    forecastDays: number = 14
  ): Promise<TrendForecastResponse> {
    const response = await this.client.get<TrendForecastResponse>(
      '/trend-forecast',
      { params: { user_id: userId, days, forecast_days: forecastDays } }
    );
    return response.data;
  }

  // Get a personalised recommendation that's been A/B tested for effectiveness
  async getRankedRecommendation(
    userId: number,
    riskLevel: string = 'low',
    variant?: string
  ): Promise<RankedRecommendationResponse> {
    const params: Record<string, string | number> = { user_id: userId, risk_level: riskLevel };
    if (variant) params.variant = variant;
    const response = await this.client.get<RankedRecommendationResponse>(
      '/recommendation-ranking',
      { params }
    );
    return response.data;
  }

  // Record whether a patient followed through on a recommendation (for improving future ones)
  async recordRecommendationOutcome(
    userId: number,
    experimentId: string,
    variant: string,
    outcome: 'completed' | 'skipped' | 'partial',
    outcomeValue?: number
  ): Promise<RecommendationOutcomeResponse> {
    const response = await this.client.post<RecommendationOutcomeResponse>(
      '/recommendation-ranking/outcome',
      {
        experiment_id: experimentId,
        variant,
        outcome,
        outcome_value: outcomeValue ?? null,
      },
      { params: { user_id: userId } }
    );
    return response.data;
  }

  // Create a plain-English alert message that patients can easily understand
  async generateNaturalLanguageAlert(
    userId: number,
    alertType: string,
    severity: string,
    triggerValue?: string,
    thresholdValue?: string,
    riskScore?: number,
    riskLevel?: string
  ): Promise<NaturalLanguageAlertResponse> {
    const response = await this.client.post<NaturalLanguageAlertResponse>(
      '/alerts/natural-language',
      {
        alert_type: alertType,
        severity,
        trigger_value: triggerValue ?? null,
        threshold_value: thresholdValue ?? null,
        risk_score: riskScore ?? null,
        risk_level: riskLevel ?? null,
      },
      { params: { user_id: userId } }
    );
    return response.data;
  }

  // Get an easy-to-read summary of a patient's risk level in plain English
  async getNaturalLanguageRiskSummary(
    userId: number,
    audience: 'clinician' | 'patient' = 'clinician'
  ): Promise<NaturalLanguageRiskSummaryResponse> {
    const response = await this.client.get<NaturalLanguageRiskSummaryResponse>(
      '/risk-summary/natural-language',
      { params: { user_id: userId, audience } }
    );
    return response.data;
  }

  // ── Clinical Notes ────────────────────────────────────────────────────────

  async getClinicalNotes(userId: number): Promise<ClinicalNote[]> {
    const response = await this.client.get(`/clinical-notes/${userId}`);
    return response.data;
  }

  async createClinicalNote(userId: number, content: string): Promise<ClinicalNote> {
    const response = await this.client.post('/clinical-notes', { user_id: userId, content });
    return response.data;
  }

  async updateClinicalNote(noteId: number, content: string): Promise<ClinicalNote> {
    const response = await this.client.patch(`/clinical-notes/${noteId}`, { content });
    return response.data;
  }

  async deleteClinicalNote(noteId: number): Promise<void> {
    await this.client.delete(`/clinical-notes/${noteId}`);
  }

  // ── Model Retraining ──────────────────────────────────────────────────────

  // Check whether the AI model is currently being retrained (clinician-only)
  async getRetrainingStatus(): Promise<RetrainingStatusResponse> {
    const response = await this.client.get<RetrainingStatusResponse>(
      '/model/retraining-status'
    );
    return response.data;
  }

  // Check if there's enough new data to retrain the AI model (clinician-only)
  async getRetrainingReadiness(): Promise<RetrainingReadinessResponse> {
    const response = await this.client.get<RetrainingReadinessResponse>(
      '/model/retraining-readiness'
    );
    return response.data;
  }

  // Run a risk prediction and explain WHY the AI made that decision
  async explainPrediction(
    params: {
      age: number;
      baseline_hr: number;
      max_safe_hr: number;
      avg_heart_rate: number;
      peak_heart_rate: number;
      min_heart_rate: number;
      avg_spo2: number;
      duration_minutes: number;
      recovery_time_minutes: number;
      activity_type: string;
    }
  ): Promise<ExplainPredictionResponse> {
    const response = await this.client.post<ExplainPredictionResponse>(
      '/predict/explain',
      params
    );
    return response.data;
  }

  // Calculate the best resting heart rate baseline from recent data
  async getBaselineOptimization(
    userId: number,
    days: number = 7
  ): Promise<BaselineOptimizationResponse> {
    const response = await this.client.get<BaselineOptimizationResponse>(
      '/baseline-optimization',
      { params: { user_id: userId, days } }
    );
    return response.data;
  }

  // Save the calculated baseline to the patient's profile
  async applyBaselineOptimization(
    userId: number
  ): Promise<BaselineApplyResponse> {
    const response = await this.client.post<BaselineApplyResponse>(
      '/baseline-optimization/apply',
      null,
      { params: { user_id: userId } }
    );
    return response.data;
  }

  // =========================================================================
  // Consent / Data Sharing — Patient permission to share their health data
  // =========================================================================

  // Check the current data sharing status for the logged-in patient
  async getConsentStatus(): Promise<ConsentStatusResponse> {
    const response = await this.client.get<ConsentStatusResponse>('/consent/status');
    return response.data;
  }

  // Get a list of patients who have requested changes to their data sharing settings
  async getPendingConsentRequests(): Promise<PendingConsentRequestsResponse> {
    const response = await this.client.get<PendingConsentRequestsResponse>('/consent/pending');
    return response.data;
  }

  // Approve or reject a patient's consent change request (clinician action)
  async reviewConsentRequest(
    patientId: number,
    decision: 'approve' | 'reject',
    reason?: string
  ): Promise<ReviewConsentResponse> {
    const response = await this.client.post<ReviewConsentResponse>(`/consent/${patientId}/review`, {
      decision,
      reason,
    });
    return response.data;
  }

  // =========================================================================
  // Admin - User Management — Admin-only actions for managing user accounts
  // =========================================================================

  // Reset a user's password (admin-only, doesn't need the old password)
  async adminResetUserPassword(userId: number, newPassword: string): Promise<AdminResetPasswordResponse> {
    const response = await this.client.post<AdminResetPasswordResponse>(`/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return response.data;
  }

  // Create a new user account as an admin (can set any role)
  async createUser(userData: {
    email: string;
    password: string;
    name: string;
    role: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<User> {
    const response = await this.client.post<User>('/users/', userData);
    return normalizeUser(response.data);
  }

  // Deactivate (soft-delete) a user account so they can no longer log in
  async deactivateUser(userId: number): Promise<DeactivateUserResponse> {
    const response = await this.client.delete<DeactivateUserResponse>(`/users/${userId}`);
    return response.data;
  }

  // Update a user's profile information
  async updateUser(
    userId: number,
    userData: {
      name?: string;
      age?: number;
      gender?: string;
      phone?: string;
    }
  ): Promise<User> {
    const response = await this.client.put<User>(`/users/${userId}`, userData);
    return normalizeUser(response.data);
  }

  // Link a clinician to a patient so the clinician can view their data
  async assignClinicianToPatient(
    patientId: number,
    clinicianId: number
  ): Promise<AssignClinicianResponse> {
    const response = await this.client.put<AssignClinicianResponse>(
      `/users/${patientId}/assign-clinician?clinician_id=${clinicianId}`
    );
    return response.data;
  }

  // ========================================================================
  // Messaging — Secure messages between patients and clinicians
  // ========================================================================

  // Get the list of recent conversations (inbox)
  async getMessagingInbox(): Promise<InboxSummaryResponse[]> {
    const response = await this.client.get('/messages/inbox');
    return response.data;
  }

  // Get the full message history between the logged-in user and another user
  async getMessageThread(otherUserId: number, limit: number = 50): Promise<MessageResponse[]> {
    const response = await this.client.get(`/messages/thread/${otherUserId}`, {
      params: { limit },
    });
    return response.data;
  }

  // Send a new message to another user
  async sendMessage(receiverId: number, content: string): Promise<MessageResponse> {
    const response = await this.client.post('/messages', {
      receiver_id: receiverId,
      content,
    });
    return response.data;
  }

  // Mark a message as "read" so the sender knows it was seen
  async markMessageAsRead(messageId: number): Promise<MessageResponse> {
    const response = await this.client.post(`/messages/${messageId}/read`);
    return response.data;
  }

  // ========================================================================
  // Medical Profile — Patient conditions, medications, and documents
  // ========================================================================

  // Get a patient's medical history (list of conditions like hypertension, diabetes)
  async getPatientMedicalHistory(userId: number): Promise<MedicalCondition[]> {
    const response = await this.client.get(`/patients/${userId}/medical-history`);
    return response.data;
  }

  // Add a new medical condition to a patient's history
  async addPatientCondition(userId: number, data: MedicalConditionCreate): Promise<MedicalCondition> {
    const response = await this.client.post(`/patients/${userId}/medical-history`, data);
    return response.data;
  }

  // Update an existing medical condition entry
  async updatePatientCondition(userId: number, historyId: number, data: Partial<MedicalConditionCreate>): Promise<MedicalCondition> {
    const response = await this.client.put(`/patients/${userId}/medical-history/${historyId}`, data);
    return response.data;
  }

  // Remove a medical condition from a patient's history
  async deletePatientCondition(userId: number, historyId: number): Promise<void> {
    await this.client.delete(`/patients/${userId}/medical-history/${historyId}`);
  }

  // Get a patient's list of current and past medications
  async getPatientMedications(userId: number): Promise<Medication[]> {
    const response = await this.client.get(`/patients/${userId}/medications`);
    return response.data;
  }

  // Add a new medication to a patient's profile
  async addPatientMedication(userId: number, data: MedicationCreate): Promise<Medication> {
    const response = await this.client.post(`/patients/${userId}/medications`, data);
    return response.data;
  }

  // Update details of an existing medication entry
  async updatePatientMedication(userId: number, medicationId: number, data: Partial<MedicationCreate>): Promise<Medication> {
    const response = await this.client.put(`/patients/${userId}/medications/${medicationId}`, data);
    return response.data;
  }

  // Remove a medication from a patient's profile
  async deletePatientMedication(userId: number, medicationId: number): Promise<void> {
    await this.client.delete(`/patients/${userId}/medications/${medicationId}`);
  }

  // Get the complete medical profile (conditions + medications + documents combined)
  async getPatientMedicalProfile(userId: number): Promise<MedicalProfile> {
    const response = await this.client.get(`/patients/${userId}/medical-profile`);
    return response.data;
  }

  // Upload a medical document (PDF, image) for AI-powered data extraction
  async uploadPatientDocument(userId: number, file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post(`/patients/${userId}/upload-document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  // Confirm the AI-extracted conditions and medications from an uploaded document
  async confirmDocumentExtraction(userId: number, data: {
    document_id: number;
    conditions: MedicalConditionCreate[];
    medications: MedicationCreate[];
  }): Promise<MedicalProfile> {
    const response = await this.client.post(`/patients/${userId}/confirm-extraction`, data);
    return response.data;
  }

  // Check if the AI document extraction feature is available and configured
  async getMedicalExtractionStatus(): Promise<MedicalExtractionStatusResponse> {
    const response = await this.client.get('/medical-extraction/status');
    return response.data;
  }

  // Download a file from the server as raw binary data (used for document viewing)
  async getDocumentBlobByUrl(url: string): Promise<Blob> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });
    return response.data as Blob;
  }
}

// Create one shared instance of the API service for the whole app to use
export const api = new ApiService();
export default api;