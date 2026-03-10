/*
Reset password confirmation page.

Handles password reset links with token query parameter.
Users are not authenticated on this page.
*/

import React, { useMemo, useState } from 'react';
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
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';

const ResetPasswordPage: React.FC = () => {
  // Grab the reset token from the URL (e.g. /reset-password?token=abc123)
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get('token') || '', [searchParams]);

  // Form fields and UI state
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Check if the password meets minimum security rules
  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return 'Password must be at least 8 characters long.';
    }
    if (!/[a-zA-Z]/.test(password)) {
      return 'Password must contain at least one letter.';
    }
    if (!/\d/.test(password)) {
      return 'Password must contain at least one digit.';
    }
    return null;
  };

  // When the user clicks "Reset Password", validate and send to the server
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!token) {
      setError('Invalid reset link');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    const validationError = validatePassword(newPassword);
    if (validationError) {
      setError(validationError);
      return;
    }

    // Send the new password along with the reset token to the backend
    setLoading(true);
    try {
      const response = await api.confirmPasswordReset(token, newPassword);
      setSuccess(response.message || 'Password reset successful. You can now log in.');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.error?.message ||
        'Token expired or invalid token.'
      );
    } finally {
      setLoading(false);
    }
  };

  // If there's no token in the URL, the link is broken or incomplete
  const invalidLink = !token;

  // -- Render the reset password form --
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
            <FavoriteOutlined sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
            <Typography variant="h4" gutterBottom fontWeight={700}>
              Adaptiv Health
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Set a new password
            </Typography>
          </Box>

          {/* Show a warning if the reset link is missing a token */}
          {invalidLink && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Invalid reset link
            </Alert>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {success}
            </Alert>
          )}

          {/* Only show the form if the reset hasn't succeeded yet */}
          {!success && !invalidLink && (
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="New Password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                margin="normal"
                required
                autoFocus
                helperText="Minimum 8 characters with at least one letter and one digit"
              />
              <TextField
                fullWidth
                label="Confirm Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                margin="normal"
                required
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ mt: 2, mb: 2, py: 1.5 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Reset Password'}
              </Button>
            </form>
          )}

          <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
            <Link to="/login" style={{ color: '#1976d2', textDecoration: 'none' }}>
              Back to Login
            </Link>
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default ResetPasswordPage;
