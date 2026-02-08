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
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.login(email, password);
      localStorage.setItem('token', response.access_token);
      if ((response as any).refresh_token) {
        localStorage.setItem('refresh_token', (response as any).refresh_token);
      }
      
      // Fetch and store user data
      const user = await api.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(user));
      
      // Role-based routing
      const role = (user as any).role || (user as any).user_role;
      if (role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setResetMessage('');
    setLoading(true);

    try {
      const resp = await api.requestPasswordReset(resetEmail);
      setResetMessage(resp.message || 'If the email exists, a reset link has been sent.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Password reset request failed.');
    } finally {
      setLoading(false);
    }
  };

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
            {resetMessage && <Alert severity="success" sx={{ mb: 2 }}>{resetMessage}</Alert>}

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
            Demo credentials: test@example.com / Pass1234
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;
