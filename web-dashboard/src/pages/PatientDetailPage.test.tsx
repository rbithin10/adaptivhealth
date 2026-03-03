import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PatientDetailPage from './PatientDetailPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({ patientId: '1' }),
}));

const mockApi: Record<string, jest.Mock> = {
  getMedicalExtractionStatus: jest.fn(),
};

jest.mock('../services/api', () => ({
  api: mockApi,
  default: mockApi,
}));

describe('PatientDetailPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows fallback error when patient load fails', async () => {
    mockApi.getMedicalExtractionStatus.mockResolvedValue({
      enabled: false,
      provider: 'gemini',
      api_key_configured: false,
      model_name: 'gemini-2.0-flash',
      per_user_rate_limit_per_minute: 10,
      max_file_size_mb: 10,
      supported_file_types: ['pdf'],
    });

    render(
      <MemoryRouter>
        <PatientDetailPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load patient data:/i)).toBeInTheDocument();
    });
  });
});
