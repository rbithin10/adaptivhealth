import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockApi = {
  login: jest.fn(),
  getCurrentUser: jest.fn(),
  requestPasswordReset: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form without crashing', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Adaptiv Health')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('shows validation error when email or password is empty', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    userEvent.click(screen.getByRole('button', { name: 'Login' }));

    expect(screen.getByText('Email and password are required.')).toBeInTheDocument();
    expect(mockApi.login).not.toHaveBeenCalled();
  });

  it('navigates admin users to admin page after login', async () => {
    mockApi.login.mockResolvedValue({ access_token: 'token-value', refresh_token: 'refresh' });
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'admin', full_name: 'Admin User' });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    userEvent.type(screen.getByLabelText('Email'), 'admin@example.com');
    userEvent.type(screen.getByLabelText('Password'), 'password123');
    userEvent.click(screen.getByRole('button', { name: 'Login' }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/admin');
    });
  });
});
