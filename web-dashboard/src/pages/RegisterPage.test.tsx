/* RegisterPage.test.tsx — Tests for the account registration form and its validation */
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import RegisterPage from './RegisterPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Fake the register endpoint so no real accounts get created
const mockApi = {
  register: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

// Registration form rendering and client-side validation
describe('RegisterPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // All four fields (name, email, password, confirm) should be visible
  it('renders registration form fields', () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
  });

  // Mismatched passwords should block submission and show an error
  it('shows error when passwords do not match', async () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    userEvent.type(screen.getByLabelText('Full Name'), 'Test User');
    userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    userEvent.type(screen.getByLabelText('Password'), 'Pass1234');
    userEvent.type(screen.getByLabelText('Confirm Password'), 'Pass12345');
    userEvent.click(screen.getByRole('button', { name: 'Create Account' }));

    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(mockApi.register).not.toHaveBeenCalled();
  });
});
