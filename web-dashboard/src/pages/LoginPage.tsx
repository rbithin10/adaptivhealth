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
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../services/api';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.login(email, password);
      localStorage.setItem('token', response.access_token);
      
      // Fetch and store user data
      const user = await api.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(user));
      
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

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
            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 3, mb: 2, py: 1.5 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Login'}
            </Button>
          </form>

          <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: '#1976d2', textDecoration: 'none' }}>
              Sign up
            </Link>
          </Typography>

          <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
            Demo credentials: test@example.com / Pass1234
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;
