/*
API client for the web dashboard.

Talks to the backend server to get user data, vital signs, risk scores,
and alerts. Automatically adds the login token to every request so the
server knows who is asking.
*/

import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  user_id: string;
  email: string;
  name: string;
  age?: number;
  gender?: string;
  phone?: string;
  weight_kg?: number;
  height_cm?: number;
  risk_level?: string;
  baseline_hr?: number;
  max_safe_hr?: number;
  created_at: string;
}

export interface VitalSigns {
  vital_id?: string;
  user_id: string;
  heart_rate: number;
  spo2?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  temperature?: number;
  timestamp: string;
}

export interface RiskAssessment {
  assessment_id: string;
  user_id: string;
  risk_level: 'low' | 'medium' | 'high';
  risk_score: number;
  confidence: number;
  timestamp: string;
}

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

  // Authentication
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
    name: string;
    age?: number;
    gender?: string;
    phone?: string;
  }): Promise<User> {
    const response = await this.client.post<User>('/register', userData);
    return response.data;
  }

  // Users
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  async getAllUsers(): Promise<User[]> {
    const response = await this.client.get<User[]>('/users');
    return response.data;
  }

  async getUserById(userId: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  // Vital Signs
  async getVitalSigns(userId?: string): Promise<VitalSigns[]> {
    const url = userId ? `/vital-signs?user_id=${userId}` : '/vital-signs';
    const response = await this.client.get<VitalSigns[]>(url);
    return response.data;
  }

  async submitVitalSigns(vitals: Omit<VitalSigns, 'vital_id'>): Promise<VitalSigns> {
    const response = await this.client.post<VitalSigns>('/vital-signs', vitals);
    return response.data;
  }

  // Risk Assessments
  async getRiskAssessments(userId?: string): Promise<RiskAssessment[]> {
    const url = userId ? `/predict/my-risk?user_id=${userId}` : '/predict/my-risk';
    const response = await this.client.get<RiskAssessment[]>(url);
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
    activity_type: string;
  }): Promise<RiskAssessment> {
    const response = await this.client.post<RiskAssessment>('/predict/risk', data);
    return response.data;
  }

  // Alerts
  async getAlerts(): Promise<any[]> {
    const response = await this.client.get('/alerts');
    return response.data;
  }

  async markAlertAsRead(alertId: string): Promise<void> {
    await this.client.patch(`/alerts/${alertId}`, { is_read: true });
  }

  // Activities
  async getActivities(userId?: string): Promise<any[]> {
    const url = userId ? `/activities?user_id=${userId}` : '/activities';
    const response = await this.client.get(url);
    return response.data;
  }
}

export const api = new ApiService();
export default api;
