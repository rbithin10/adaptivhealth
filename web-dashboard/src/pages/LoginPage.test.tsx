/* LoginPage.test.tsx — Tests for the login form, validation, and post-login navigation */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

// Spy on navigation so we can verify redirects after login
const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Fake the API layer — we don't want real HTTP calls in unit tests
const mockApi = {
  login: jest.fn(),
  requestPasswordReset: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

// Login form rendering, validation, and role-based redirect tests
describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  // Basic smoke test — make sure the form shows up with all fields
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

  // Clicking login with empty fields should show an error, not call the API
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

  // After a successful login, admin users should land on the admin page
  it('navigates admin users to admin page after login', async () => {
    mockApi.login.mockResolvedValue({ id: 1, email: 'admin@example.com', role: 'admin' });

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
