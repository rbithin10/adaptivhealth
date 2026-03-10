/*
App.tsx — Main application file.

This sets up every page in the dashboard (login, register, patient list, etc.)
and protects pages so only logged-in users with the right role can access them.
For example, only admins can see the admin panel, only clinicians see patient lists.
*/

import React from 'react';
// Router handles page navigation — clicking links changes what's shown without reloading the page
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
// Import all the page components the user can navigate to
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

// Defines the shape of the "children" prop for protected routes
interface ProtectedRouteProps {
  children: React.ReactNode;
}

// Same as above, but also specifies which user roles are allowed to see this page
interface RoleProtectedRouteProps extends ProtectedRouteProps {
  allowedRoles: Array<'patient' | 'clinician' | 'admin'>;
}

// Read the logged-in user's role from the browser's local storage
// Returns 'patient', 'clinician', 'admin', or null if nobody is logged in
const getStoredUserRole = (): 'patient' | 'clinician' | 'admin' | null => {
  const raw = localStorage.getItem('user');
  if (!raw) return null;
  try {
    // Parse the stored JSON and look for the role field
    const parsed = JSON.parse(raw) as { user_role?: string; role?: string };
    const role = (parsed.user_role || parsed.role || '').toLowerCase();
    // Only accept known roles — anything else is treated as "not logged in"
    if (role === 'patient' || role === 'clinician' || role === 'admin') {
      return role;
    }
    return null;
  } catch {
    return null;
  }
};

// A wrapper that checks if the user is logged in before showing a page
// If not logged in, it sends them to the login page instead
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

// Same as ProtectedRoute, but also checks the user's role
// If logged in but wrong role (e.g. patient trying to access admin), redirect to dashboard
const RoleProtectedRoute: React.FC<RoleProtectedRouteProps> = ({ children, allowedRoles }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const role = getStoredUserRole();
  // If the user's role isn't in the allowed list, send them to the dashboard
  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

// Decides which dashboard to show based on the user's role
interface DashboardWrapperProps {}

const DashboardWrapper: React.FC<DashboardWrapperProps> = () => {
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  
  // Patients see their personal health dashboard
  if (user?.user_role === 'patient') {
    return <PatientDashboardPage />;
  }
  
  // Clinicians and admins see the clinician overview dashboard
  return <DashboardPage />;
};

// The main App component that defines all the routes (URLs) and which page to show for each
function App() {
  return (
    <Router>
      <Routes>
        {/* Public pages — anyone can see these without logging in */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Dashboard — requires login, shows different views for patients vs clinicians */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardWrapper />
            </ProtectedRoute>
          }
        />

        {/* Admin panel — only users with the "admin" role can access this */}
        <Route
          path="/admin"
          element={
            <RoleProtectedRoute allowedRoles={['admin']}>
              <AdminPage />
            </RoleProtectedRoute>
          }
        />

        {/* Patient list — only clinicians can see the full patient roster */}
        <Route
          path="/patients"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <PatientsPage />
            </RoleProtectedRoute>
          }
        />

        {/* Individual patient detail — clinicians click a patient to see their full details */}
        <Route
          path="/patients/:patientId"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <PatientDetailPage />
            </RoleProtectedRoute>
          }
        />

        {/* Messaging — clinicians can send and receive messages with patients */}
        <Route
          path="/messages"
          element={
            <RoleProtectedRoute allowedRoles={['clinician']}>
              <MessagingPage />
            </RoleProtectedRoute>
          }
        />

        {/* If someone visits the root URL "/", redirect them to their dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
