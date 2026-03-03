import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from './DashboardPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockApi = {
  getCurrentUser: jest.fn(),
  getAllUsers: jest.fn(),
  getAlertStats: jest.fn(),
  getAlerts: jest.fn(),
  getPendingConsentRequests: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders dashboard for clinician users', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'clinician' });
    mockApi.getAllUsers.mockResolvedValue({ users: [], total: 0, page: 1, per_page: 200 });
    mockApi.getAlertStats.mockResolvedValue({ total: 0, by_severity: {}, by_type: {}, unacknowledged_count: 0 });
    mockApi.getAlerts.mockResolvedValue({ alerts: [], total: 0, page: 1, per_page: 5 });
    mockApi.getPendingConsentRequests.mockResolvedValue({ pending_requests: [] });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Clinical Dashboard')).toBeInTheDocument();
    });
  });

  it('redirects admin users to admin page', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'admin' });

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
