/*
API client for the web dashboard.

Talks to the backend server to get user data, vital signs, risk scores,
and alerts. Automatically adds the login token to every request so the
server knows who is asking.

Matches backend API at /api/v1 with correct endpoint prefixes and schemas.
*/

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  LoginResponse,
  User,
  UserProfileResponse,
  UserListResponse,
  VitalSignResponse,
  VitalSignsHistoryResponse,
  RiskAssessmentResponse,
  RiskAssessmentComputeResponse,
  RiskAssessmentListResponse,
  RecommendationResponse,
  RecommendationListResponse,
  AlertResponse,
  AlertListResponse,
  AlertStatsResponse,
  ActivitySessionResponse,
  ActivityListResponse,
  HealthCheckResponse,
  DatabaseHealthCheckResponse,
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const normalizeUser = (data: any): User => ({
  ...data,
  user_id: data.user_id ?? data.id,
  full_name: data.full_name ?? data.name,
  user_role: data.user_role ?? data.role,
});

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            try {
              const resp = await this.client.post('/refresh', { refresh_token: refreshToken });
              const newToken = resp.data.access_token;
              localStorage.setItem('token', newToken);
              if (resp.data.refresh_token) {
                localStorage.setItem('refresh_token', resp.data.refresh_token);
              }
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            } catch {
              // Refresh failed — fall through to logout
            }
          }
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // =========================================================================
  // Health Checks
  // =========================================================================

  async getHealth(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');
    return response.data;
  }

  async getDatabaseHealth(): Promise<DatabaseHealthCheckResponse> {
    const response = await this.client.get<DatabaseHealthCheckResponse>('/health/db');
    return response.data;
  }

  // =========================================================================
  // Authentication
  // =========================================================================

  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.client.post<LoginResponse>('/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const response = await this.client.post('/reset-password', { email });
    return response.data;
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<{ message: string }> {
    const response = await this.client.post('/reset-password/confirm', {
      token,
      new_password: newPassword,
    });
    return response.data;
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  async register(userData: {
    email: string;
    password: string;
    full_name: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<User> {
    const response = await this.client.post<User>('/register', {
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
  // User Management
  // =========================================================================

  async getCurrentUser(): Promise<UserProfileResponse> {
    const response = await this.client.get<UserProfileResponse>('/users/me');
    return normalizeUser(response.data) as UserProfileResponse;
  }

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

  async getAllUsers(
    page: number = 1,
    perPage: number = 50
  ): Promise<UserListResponse> {
    const response = await this.client.get<UserListResponse>('/users', {
      params: { page, per_page: perPage },
    });
    return {
      ...response.data,
      users: response.data.users.map(normalizeUser),
    };
  }

  async getUserById(userId: number): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return normalizeUser(response.data);
  }

  // =========================================================================
  // Vital Signs
  // =========================================================================

  async getLatestVitalSigns(): Promise<VitalSignResponse> {
    const response = await this.client.get<VitalSignResponse>('/vitals/latest');
    return response.data;
  }

  async getLatestVitalSignsForUser(userId: number): Promise<VitalSignResponse> {
    const response = await this.client.get<VitalSignResponse>(`/vitals/user/${userId}/latest`);
    return response.data;
  }

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

  async getVitalSignsSummary(days: number = 7): Promise<any> {
    const response = await this.client.get('/vitals/summary', {
      params: { days },
    });
    return response.data;
  }

  async getVitalSignsSummaryForUser(userId: number, days: number = 7): Promise<any> {
    const response = await this.client.get(`/vitals/user/${userId}/summary`, {
      params: { days },
    });
    return response.data;
  }

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
  // Risk Assessments
  // =========================================================================

  async getLatestRiskAssessment(): Promise<RiskAssessmentResponse> {
    const response = await this.client.get<RiskAssessmentResponse>(
      '/risk-assessments/latest'
    );
    return response.data;
  }

  async getLatestRiskAssessmentForUser(userId: number): Promise<RiskAssessmentResponse> {
    const response = await this.client.get<RiskAssessmentResponse>(
      `/patients/${userId}/risk-assessments/latest`
    );
    return response.data;
  }

  async computeRiskAssessment(): Promise<RiskAssessmentComputeResponse> {
    const response = await this.client.post<RiskAssessmentComputeResponse>(
      '/risk-assessments/compute'
    );
    return response.data;
  }

  async computeRiskAssessmentForUser(userId: number): Promise<RiskAssessmentComputeResponse> {
    const response = await this.client.post<RiskAssessmentComputeResponse>(
      `/patients/${userId}/risk-assessments/compute`
    );
    return response.data;
  }

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
  // Recommendations
  // =========================================================================

  async getLatestRecommendation(): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>(
      '/recommendations/latest'
    );
    return response.data;
  }

  async getLatestRecommendationForUser(userId: number): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>(
      `/patients/${userId}/recommendations/latest`
    );
    return response.data;
  }

  async getRecommendations(
    page: number = 1,
    perPage: number = 50
  ): Promise<RecommendationListResponse> {
    const response = await this.client.get<RecommendationListResponse>(
      '/recommendations',
      {
        params: { page, per_page: perPage },
      }
    );
    return response.data;
  }

  async getRecommendationById(recommendationId: number): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>(
      `/recommendations/${recommendationId}`
    );
    return response.data;
  }

  async updateRecommendation(
    recommendationId: number,
    data: {
      status?: string;
      is_completed?: boolean;
      user_feedback?: string;
    }
  ): Promise<RecommendationResponse> {
    const response = await this.client.patch<RecommendationResponse>(
      `/recommendations/${recommendationId}`,
      data
    );
    return response.data;
  }

  // =========================================================================
  // Alerts
  // =========================================================================

  async getAlerts(
    page: number = 1,
    perPage: number = 50
  ): Promise<AlertListResponse> {
    const response = await this.client.get<AlertListResponse>('/alerts', {
      params: { page, per_page: perPage },
    });
    return response.data;
  }

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

  async getAlertStats(): Promise<AlertStatsResponse> {
    const response = await this.client.get<AlertStatsResponse>('/alerts/stats');
    return response.data;
  }

  async acknowledgeAlert(alertId: number): Promise<AlertResponse> {
    const response = await this.client.patch<AlertResponse>(
      `/alerts/${alertId}/acknowledge`
    );
    return response.data;
  }

  async resolveAlert(
    alertId: number,
    data: {
      resolution_notes?: string;
    }
  ): Promise<AlertResponse> {
    const response = await this.client.patch<AlertResponse>(
      `/alerts/${alertId}/resolve`,
      data
    );
    return response.data;
  }

  // =========================================================================
  // Activities
  // =========================================================================

  async getActivities(limit: number = 50, offset: number = 0): Promise<ActivityListResponse> {
    const response = await this.client.get('/activities', {
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

  async getActivityById(sessionId: number): Promise<ActivitySessionResponse> {
    const response = await this.client.get<ActivitySessionResponse>(
      `/activities/${sessionId}`
    );
    return response.data;
  }

  async startActivity(data: {
    activity_type: string;
  }): Promise<ActivitySessionResponse> {
    const response = await this.client.post<ActivitySessionResponse>(
      '/activities/start',
      data
    );
    return response.data;
  }

  async endActivity(sessionId: number): Promise<ActivitySessionResponse> {
    const response = await this.client.post<ActivitySessionResponse>(
      `/activities/end/${sessionId}`
    );
    return response.data;
  }

  async updateActivity(
    sessionId: number,
    data: {
      end_time?: string;
      avg_heart_rate?: number;
      peak_heart_rate?: number;
      min_heart_rate?: number;
      duration_minutes?: number;
      feeling_after?: string;
      user_notes?: string;
      status?: string;
    }
  ): Promise<ActivitySessionResponse> {
    const response = await this.client.patch<ActivitySessionResponse>(
      `/activities/${sessionId}`,
      data
    );
    return response.data;
  }

  // =========================================================================
  // Consent / Data Sharing
  // =========================================================================

  async getConsentStatus(): Promise<any> {
    const response = await this.client.get('/consent/status');
    return response.data;
  }

  async getPendingConsentRequests(): Promise<any> {
    const response = await this.client.get('/consent/pending');
    return response.data;
  }

  async reviewConsentRequest(
    patientId: number,
    decision: 'approve' | 'reject',
    reason?: string
  ): Promise<any> {
    const response = await this.client.post(`/consent/${patientId}/review`, {
      decision,
      reason,
    });
    return response.data;
  }

  // =========================================================================
  // Admin - User Management
  // =========================================================================

  async adminResetUserPassword(userId: number, newPassword: string): Promise<any> {
    const response = await this.client.post(`/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return response.data;
  }

  async createUser(userData: {
    email: string;
    password: string;
    name: string;
    role: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<any> {
    const response = await this.client.post('/users/', userData);
    return response.data;
  }

  async deactivateUser(userId: number): Promise<any> {
    const response = await this.client.delete(`/users/${userId}`);
    return response.data;
  }
}

export const api = new ApiService();
export default api;