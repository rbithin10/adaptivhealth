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
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
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

  async register(userData: {
    email: string;
    password: string;
    full_name: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<User> {
    const response = await this.client.post<User>('/register', userData);
    return response.data;
  }

  // =========================================================================
  // User Management
  // =========================================================================

  async getCurrentUser(): Promise<UserProfileResponse> {
    const response = await this.client.get<UserProfileResponse>('/users/me');
    return response.data;
  }

  async updateCurrentUserProfile(data: {
    full_name?: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<UserProfileResponse> {
    const response = await this.client.put<UserProfileResponse>('/users/me', data);
    return response.data;
  }

  async getAllUsers(
    page: number = 1,
    perPage: number = 50
  ): Promise<UserListResponse> {
    const response = await this.client.get<UserListResponse>('/users', {
      params: { page, per_page: perPage },
    });
    return response.data;
  }

  async getUserById(userId: number): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  // =========================================================================
  // Vital Signs
  // =========================================================================

  async getLatestVitalSigns(): Promise<VitalSignResponse> {
    const response = await this.client.get<VitalSignResponse>('/vitals/latest');
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

  async getVitalSignsSummary(date?: string): Promise<any> {
    const response = await this.client.get('/vitals/summary', {
      params: date ? { date } : undefined,
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

  async computeRiskAssessment(): Promise<RiskAssessmentComputeResponse> {
    const response = await this.client.post<RiskAssessmentComputeResponse>(
      '/risk-assessments/compute'
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

  async getActivities(
    page: number = 1,
    perPage: number = 50
  ): Promise<ActivityListResponse> {
    const response = await this.client.get<ActivityListResponse>('/activities', {
      params: { page, per_page: perPage },
    });
    return response.data;
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
}

export const api = new ApiService();
export default api;