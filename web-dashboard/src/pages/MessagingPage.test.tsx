import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MessagingPage from './MessagingPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockApi = {
  getCurrentUser: jest.fn(),
  getMessagingInbox: jest.fn(),
  getMessageThread: jest.fn(),
  markMessageAsRead: jest.fn(),
  sendMessage: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('MessagingPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('redirects non-clinician users to dashboard', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'admin' });

    render(
      <MemoryRouter>
        <MessagingPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('loads inbox for clinicians', async () => {
    mockApi.getCurrentUser.mockResolvedValue({ user_role: 'clinician', user_id: 99 });
    mockApi.getMessagingInbox.mockResolvedValue([]);

    const { getByText } = render(
      <MemoryRouter>
        <MessagingPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(getByText('Messages')).toBeInTheDocument();
      expect(mockApi.getMessagingInbox).toHaveBeenCalled();
    });
  });
});
