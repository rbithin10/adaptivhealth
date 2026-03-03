import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('./pages/LoginPage', () => () => <div>Login Page</div>);
jest.mock('./pages/ResetPasswordPage', () => () => <div>Reset Password Page</div>);
jest.mock('./pages/DashboardPage', () => () => <div>Dashboard Page</div>);
jest.mock('./pages/PatientDashboardPage', () => () => <div>Patient Dashboard Page</div>);
jest.mock('./pages/PatientsPage', () => () => <div>Patients Page</div>);
jest.mock('./pages/PatientDetailPage', () => () => <div>Patient Detail Page</div>);
jest.mock('./pages/AdminPage', () => () => <div>Admin Page</div>);
jest.mock('./pages/MessagingPage', () => () => <div>Messaging Page</div>);

describe('App routing and RBAC', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirects /register to /login', () => {
    window.history.pushState({}, '', '/register');

    render(<App />);

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('allows clinician access to /patients', () => {
    localStorage.setItem('token', 'fake-token');
    localStorage.setItem('user', JSON.stringify({ user_role: 'clinician' }));
    window.history.pushState({}, '', '/patients');

    render(<App />);

    expect(screen.getByText('Patients Page')).toBeInTheDocument();
  });

  it('blocks non-clinician access to /patients and redirects to dashboard', () => {
    localStorage.setItem('token', 'fake-token');
    localStorage.setItem('user', JSON.stringify({ user_role: 'admin' }));
    window.history.pushState({}, '', '/patients');

    render(<App />);

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });
});
