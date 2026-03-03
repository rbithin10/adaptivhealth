/*
Web dashboard main app.

Sets up the pages (login, dashboard, patients list, patient details).
Protects pages so only logged-in users can see them.
*/

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import PatientDashboardPage from './pages/PatientDashboardPage';
import PatientsPage from './pages/PatientsPage';
import PatientDetailPage from './pages/PatientDetailPage';
import AdminPage from './pages/AdminPage';
import MessagingPage from './pages/MessagingPage';
import './App.css';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

interface RoleProtectedRouteProps extends ProtectedRouteProps {
  allowedRoles: Array<'patient' | 'clinician' | 'admin'>;
}

const getStoredUserRole = (): 'patient' | 'clinician' | 'admin' | null => {
  const raw = localStorage.getItem('user');
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { user_role?: string; role?: string };
    const role = (parsed.user_role || parsed.role || '').toLowerCase();
    if (role === 'patient' || role === 'clinician' || role === 'admin') {
      return role;
    }
    return null;
  } catch {
    return null;
  }
};

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const RoleProtectedRoute: React.FC<RoleProtectedRouteProps> = ({ children, allowedRoles }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const role = getStoredUserRole();
  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

// Wrapper to show appropriate dashboard based on user role
interface DashboardWrapperProps {}

const DashboardWrapper: React.FC<DashboardWrapperProps> = () => {
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  
  // Patient role: show patient dashboard
  if (user?.user_role === 'patient') {
    return <PatientDashboardPage />;
  }
  
  // Clinician/Admin: show clinician dashboard
  return <DashboardPage />;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <RoleProtectedRoute allowedRoles={['admin']}>
              <AdminPage />
            </RoleProtectedRoute>
          }
        />
        <Route
          path="/patients"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <PatientsPage />
            </RoleProtectedRoute>
          }
        />
        <Route
          path="/patients/:patientId"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <PatientDetailPage />
            </RoleProtectedRoute>
          }
        />
        <Route
          path="/messages"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <MessagingPage />
            </RoleProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
