/* DashboardPage.test.tsx — Tests that the clinical dashboard renders and role-based redirects work */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from './DashboardPage';
import { api } from '../services/api';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../services/api', () => ({
  api: {
    getCurrentUser: jest.fn(),
    getAllUsers: jest.fn(),
    getAlertStats: jest.fn(),
    getRetrainingStatus: jest.fn(),
    getHealth: jest.fn(),
    getDatabaseHealth: jest.fn(),
    getLatestRiskAssessmentForUser: jest.fn(),
    getVitalSignsHistoryForUser: jest.fn(),
    getMessagingInbox: jest.fn(),
    logout: jest.fn(),
    getPendingConsentRequests: jest.fn(),
  },
  default: {
    getCurrentUser: jest.fn(),
    getAllUsers: jest.fn(),
    getAlertStats: jest.fn(),
    getRetrainingStatus: jest.fn(),
    getHealth: jest.fn(),
    getDatabaseHealth: jest.fn(),
    getLatestRiskAssessmentForUser: jest.fn(),
    getVitalSignsHistoryForUser: jest.fn(),
    getMessagingInbox: jest.fn(),
    logout: jest.fn(),
    getPendingConsentRequests: jest.fn(),
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

// Dashboard page — clinician view and admin redirect
describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Clinicians should see the full clinical dashboard with all data loaded
  it('renders dashboard for clinician users', async () => {
    mockApi.getCurrentUser.mockResolvedValue({
      user_id: 1,
      email: 'doctor@example.com',
      full_name: 'Doctor',
      user_role: 'clinician',
      is_active: true,
      is_verified: true,
      created_at: '2026-01-01T00:00:00Z',
    });
    mockApi.getAllUsers.mockResolvedValue({ users: [], total: 0, page: 1, per_page: 200 });
    mockApi.getAlertStats.mockResolvedValue({ total: 0, by_severity: {}, by_type: {}, unacknowledged_count: 0 });
    mockApi.getRetrainingStatus.mockResolvedValue({
      model_dir: '/ml_models',
      model_exists: true,
      scaler_exists: true,
      features_exists: true,
      metadata: { model_name: 'risk_model', version: '1.0.0', accuracy: '0.93' },
    });
    mockApi.getHealth.mockResolvedValue({
      status: 'healthy',
      version: '1.0.0',
      environment: 'development',
      timestamp: Date.now(),
    });
    mockApi.getDatabaseHealth.mockResolvedValue({
      status: 'healthy',
      database: 'connected',
      timestamp: Date.now(),
    });
    mockApi.getMessagingInbox.mockResolvedValue([]);
    mockApi.logout.mockResolvedValue(undefined);
    mockApi.getPendingConsentRequests.mockResolvedValue({ pending_requests: [] });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Welcome back/i)).toBeInTheDocument();
    });

    expect(screen.getByText('ML Prediction Health Status')).toBeInTheDocument();
  });

  // Admins don't belong here — they should be sent to /admin automatically
  it('redirects admin users to admin page', async () => {
    mockApi.getCurrentUser.mockResolvedValue({
      user_id: 2,
      email: 'admin@example.com',
      full_name: 'Admin',
      user_role: 'admin',
      is_active: true,
      is_verified: true,
      created_at: '2026-01-01T00:00:00Z',
    });
    mockApi.getMessagingInbox.mockResolvedValue([]);
    mockApi.logout.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/admin');
    });
  });
});
