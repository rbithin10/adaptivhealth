import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PatientsPage from './PatientsPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockApi = {
  getCurrentUser: jest.fn(),
  getAllUsers: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('PatientsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders patients page without crashing', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'clinician' });
    mockApi.getAllUsers.mockResolvedValue({ users: [], total: 0, page: 1, per_page: 200 });

    render(
      <MemoryRouter>
        <PatientsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Patient Management')).toBeInTheDocument();
    });
  });

  it('shows only patient rows from mixed-role data', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'clinician' });
    mockApi.getAllUsers.mockResolvedValue({
      users: [
        {
          user_id: 10,
          email: 'patient@example.com',
          full_name: 'Patient One',
          user_role: 'patient',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        },
        {
          user_id: 11,
          email: 'admin@example.com',
          full_name: 'Admin One',
          user_role: 'admin',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        },
      ],
      total: 2,
      page: 1,
      per_page: 200,
    });

    render(
      <MemoryRouter>
        <PatientsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Patient One')).toBeInTheDocument();
      expect(screen.queryByText('Admin One')).not.toBeInTheDocument();
    });
  });

  it('redirects non-clinician users to dashboard', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'admin' });
    mockApi.getAllUsers.mockResolvedValue({ users: [], total: 0, page: 1, per_page: 200 });

    render(
      <MemoryRouter>
        <PatientsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });
});
