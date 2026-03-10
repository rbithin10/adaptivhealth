/*
Login page.

A form where users enter their email and password to log in to the
dashboard. After logging in, they see the patient list.
*/

import React, { useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import { FavoriteOutlined } from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

// Pull a readable error message from the server response, or fall back to a default
const getErrorMessage = (error: unknown, fallback: string): string => {
  if (!error || typeof error !== 'object') return fallback;
  const record = error as {
    response?: { data?: { error?: { message?: string }; detail?: string } };
  };
  return record.response?.data?.error?.message || record.response?.data?.detail || fallback;
};

const LoginPage: React.FC = () => {
  const navigate = useNavigate();

  // Login form fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Forgot-password flow fields (shown when user clicks "Forgot password?")
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  // Handle the login form submission
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }

    setLoading(true);

    try {
      // Save tokens so the user stays logged in
      const response = await api.login(email, password);
      localStorage.setItem('token', response.access_token);
      if (response.refresh_token) {
        localStorage.setItem('refresh_token', response.refresh_token);
      }
      
      // Fetch and store user data
      const user = await api.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(user));
      
      // Send admins to the admin page, everyone else to the main dashboard
      const role = user.user_role;
      if (role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Login failed. Please check your credentials.'));
    } finally {
      setLoading(false);
    }
  };

  // Send a password reset link to the user's email
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setResetMessage('');
    setLoading(true);

    try {
      const resp = await api.requestPasswordReset(resetEmail);
      setResetMessage(resp.message || 'If the email exists, a reset link has been sent.');
    } catch (err) {
      setError(getErrorMessage(err, 'Password reset request failed.'));
    } finally {
      setLoading(false);
    }
  };

  // If the user clicked "Forgot password?", show the reset email form instead
  if (showForgotPassword) {
    return (
      <Container maxWidth="sm">
        <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Paper elevation={3} sx={{ p: 4, width: '100%', borderRadius: 3 }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <FavoriteOutlined sx={{ fontSize: 48, color: 'error.main', mb: 1 }} />
              <Typography variant="h5" gutterBottom fontWeight={700}>
                Reset Password
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Enter your email to receive a password reset link
              </Typography>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {resetMessage && (
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  {resetMessage}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Local testing: open /reset-password?token=&lt;jwt_token&gt; from your reset email link.
                </Typography>
              </Alert>
            )}

            <form onSubmit={handleForgotPassword}>
              <TextField
                fullWidth label="Email" type="email" value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                margin="normal" required autoFocus
              />
              <Button type="submit" fullWidth variant="contained" size="large"
                disabled={loading} sx={{ mt: 2, mb: 2, py: 1.5 }}>
                {loading ? <CircularProgress size={24} /> : 'Send Reset Link'}
              </Button>
            </form>

            <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
              <Button variant="text" onClick={() => { setShowForgotPassword(false); setError(''); setResetMessage(''); }}>
                Back to Login
              </Button>
            </Typography>
          </Paper>
        </Box>
      </Container>
    );
  }

  // -- Main login form --
  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
            borderRadius: 3,
          }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <FavoriteOutlined
              sx={{ fontSize: 64, color: 'error.main', mb: 2 }}
            />
            <Typography variant="h4" gutterBottom fontWeight={700}>
              Adaptiv Health
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Healthcare Provider Dashboard
            </Typography>
          </Box>

          {/* Error banner (e.g. wrong password) */}
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleLogin}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoFocus
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
            />
            <Box sx={{ textAlign: 'right', mt: 1 }}>
              <Button variant="text" size="small" onClick={() => setShowForgotPassword(true)}>
                Forgot password?
              </Button>
            </Box>
            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 2, mb: 2, py: 1.5 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Login'}
            </Button>
          </form>

          <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
            Use your assigned clinician account credentials.
          </Typography>

          <Typography variant="body2" color="text.secondary" textAlign="center" mt={1}>
            Need a new account?{' '}
            <Link to="/register" style={{ color: '#2563EB', fontWeight: 600, textDecoration: 'none' }}>
              Register here
            </Link>
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;
