/* App.test.tsx — Tests top-level routing and role-based access control */
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

// Replace every page with a simple stub so we only test routing logic, not page content
jest.mock('./pages/LoginPage', () => () => <div>Login Page</div>);
jest.mock('./pages/ResetPasswordPage', () => () => <div>Reset Password Page</div>);
jest.mock('./pages/DashboardPage', () => () => <div>Dashboard Page</div>);
jest.mock('./pages/PatientDashboardPage', () => () => <div>Patient Dashboard Page</div>);
jest.mock('./pages/PatientsPage', () => () => <div>Patients Page</div>);
jest.mock('./pages/PatientDetailPage', () => () => <div>Patient Detail Page</div>);
jest.mock('./pages/AdminPage', () => () => <div>Admin Page</div>);
jest.mock('./pages/MessagingPage', () => () => <div>Messaging Page</div>);

// Routing + role-based access guard tests
describe('App routing and RBAC', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // Visiting /register should bounce the user back to login
  it('redirects /register to /login', () => {
    window.history.pushState({}, '', '/register');

    render(<App />);

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  // A logged-in clinician should be able to reach the patients list
  it('allows clinician access to /patients', () => {
    localStorage.setItem('token', 'fake-token');
    localStorage.setItem('user', JSON.stringify({ user_role: 'clinician' }));
    window.history.pushState({}, '', '/patients');

    render(<App />);

    expect(screen.getByText('Patients Page')).toBeInTheDocument();
  });

  // An admin trying to access /patients should get redirected to the dashboard instead
  it('blocks non-clinician access to /patients and redirects to dashboard', () => {
    localStorage.setItem('token', 'fake-token');
    localStorage.setItem('user', JSON.stringify({ user_role: 'admin' }));
    window.history.pushState({}, '', '/patients');

    render(<App />);

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });
});
