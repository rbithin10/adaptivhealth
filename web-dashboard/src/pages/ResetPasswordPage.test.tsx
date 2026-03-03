import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ResetPasswordPage from './ResetPasswordPage';

const mockApi = {
  confirmPasswordReset: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows invalid link when token is missing', () => {
    render(
      <MemoryRouter initialEntries={['/reset-password']}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Invalid reset link')).toBeInTheDocument();
  });

  it('submits valid reset and shows success message', async () => {
    mockApi.confirmPasswordReset.mockResolvedValue({
      message: 'Password reset successful. You can now log in.',
    });

    render(
      <MemoryRouter initialEntries={['/reset-password?token=abc123']}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    userEvent.type(screen.getByLabelText('New Password'), 'Pass1234');
    userEvent.type(screen.getByLabelText('Confirm Password'), 'Pass1234');
    userEvent.click(screen.getByRole('button', { name: 'Reset Password' }));

    await waitFor(() => {
      expect(mockApi.confirmPasswordReset).toHaveBeenCalledWith('abc123', 'Pass1234');
      expect(screen.getByText('Password reset successful. You can now log in.')).toBeInTheDocument();
    });
  });
});
