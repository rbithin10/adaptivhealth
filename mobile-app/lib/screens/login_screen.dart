/*
Login screen.

People enter their email and password here.
If login works, we switch to the Home screen.
If login fails, we show a simple error message.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

class LoginScreen extends StatefulWidget {
  // The API client used to talk to the server.
  final ApiClient apiClient;
  
  // Called when login succeeds so the app can show Home.
  final VoidCallback onLoginSuccess;

  // Called when user taps "Sign up" to show the Register screen.
  final VoidCallback? onNavigateToRegister;

  const LoginScreen({
    super.key,
    required this.apiClient,
    required this.onLoginSuccess,
    this.onNavigateToRegister,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // Helps us validate the form before sending.
  final _formKey = GlobalKey<FormState>();
  
  // Controllers let us read what the user typed.
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  
  // Simple UI state flags
  bool _isLoading = false;      // Show loading spinner during request
  bool _showPassword = false;   // Show or hide password
  String? _errorMessage;        // Show error to user
  bool _showForgotPassword = false; // Forgot password view
  final _resetEmailController = TextEditingController();
  String? _resetMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _resetEmailController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await widget.apiClient.login(
        _emailController.text.trim(),
        _passwordController.text,
      );

      if (response['access_token'] != null) {
        // Success - token stored in secure storage by ApiClient
        widget.onLoginSuccess();
      } else {
        setState(() {
          _errorMessage = 'Login failed. Please try again.';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_showForgotPassword) {
      return Scaffold(
        backgroundColor: AdaptivColors.white,
        body: SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 60),
                  Text(
                    'Reset Password',
                    style: GoogleFonts.dmSans(
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      color: AdaptivColors.text900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Enter your email to receive a reset link',
                    style: AdaptivTypography.body,
                  ),
                  const SizedBox(height: 32),
                  if (_errorMessage != null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AdaptivColors.criticalUltralight,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AdaptivColors.criticalLight),
                      ),
                      child: Text(
                        _errorMessage!,
                        style: AdaptivTypography.caption.copyWith(color: AdaptivColors.critical),
                      ),
                    ),
                  if (_resetMessage != null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF81C784)),
                      ),
                      child: Text(
                        _resetMessage!,
                        style: AdaptivTypography.caption.copyWith(color: const Color(0xFF2E7D32)),
                      ),
                    ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _resetEmailController,
                    decoration: InputDecoration(
                      labelText: 'Email',
                      prefixIcon: const Icon(Icons.email_outlined),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    keyboardType: TextInputType.emailAddress,
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : () async {
                        final email = _resetEmailController.text.trim();
                        if (email.isEmpty || !email.contains('@')) {
                          setState(() => _errorMessage = 'Please enter a valid email');
                          return;
                        }
                        setState(() { _isLoading = true; _errorMessage = null; _resetMessage = null; });
                        try {
                          await widget.apiClient.requestPasswordReset(email);
                          setState(() => _resetMessage = 'If the email exists, a reset link has been sent.');
                        } catch (e) {
                          setState(() => _errorMessage = e.toString());
                        } finally {
                          setState(() => _isLoading = false);
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        backgroundColor: AdaptivColors.primary,
                      ),
                      child: _isLoading
                          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(AdaptivColors.white)))
                          : Text('Send Reset Link', style: AdaptivTypography.button),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _showForgotPassword = false;
                        _errorMessage = null;
                        _resetMessage = null;
                      });
                    },
                    child: Text(
                      'Back to Login',
                      style: AdaptivTypography.body.copyWith(color: AdaptivColors.primary),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AdaptivColors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 40),

                // Logo
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AdaptivColors.primaryUltralight,
                    border: Border.all(
                      color: AdaptivColors.primary,
                      width: 3,
                    ),
                  ),
                  child: const Icon(
                    Icons.favorite,
                    color: AdaptivColors.critical,
                    size: 40,
                  ),
                ),
                const SizedBox(height: 32),

                // Title
                Text(
                  'Adaptiv Health',
                  style: GoogleFonts.dmSans(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AdaptivColors.text900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Welcome back',
                  style: AdaptivTypography.body,
                ),
                const SizedBox(height: 40),

                // Error message
                if (_errorMessage != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AdaptivColors.criticalUltralight,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AdaptivColors.criticalLight,
                      ),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: AdaptivTypography.caption.copyWith(
                        color: AdaptivColors.critical,
                      ),
                    ),
                  ),
                if (_errorMessage != null) const SizedBox(height: 20),

                // Form
                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      // Email field
                      TextFormField(
                        controller: _emailController,
                        decoration: InputDecoration(
                          labelText: 'Email',
                          prefixIcon: const Icon(Icons.email_outlined),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(
                              color: AdaptivColors.primary,
                              width: 2,
                            ),
                          ),
                        ),
                        keyboardType: TextInputType.emailAddress,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Email is required';
                          }
                          if (!value.contains('@')) {
                            return 'Please enter a valid email';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Password field
                      TextFormField(
                        controller: _passwordController,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock_outlined),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _showPassword
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            onPressed: () {
                              setState(() {
                                _showPassword = !_showPassword;
                              });
                            },
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(
                              color: AdaptivColors.primary,
                              width: 2,
                            ),
                          ),
                        ),
                        obscureText: !_showPassword,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Password is required';
                          }
                          if (value.length < 6) {
                            return 'Password must be at least 6 characters';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 8),

                      // Forgot password link
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: () {
                            setState(() {
                              _showForgotPassword = true;
                              _errorMessage = null;
                              _resetMessage = null;
                            });
                          },
                          child: Text(
                            'Forgot password?',
                            style: AdaptivTypography.caption.copyWith(
                              color: AdaptivColors.primary,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Login button
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _handleLogin,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            backgroundColor: AdaptivColors.primary,
                            disabledBackgroundColor: AdaptivColors.neutral300,
                          ),
                          child: _isLoading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    valueColor: AlwaysStoppedAnimation<Color>(
                                      AdaptivColors.white,
                                    ),
                                    strokeWidth: 2,
                                  ),
                                )
                              : Text(
                                  'Sign In',
                                  style: AdaptivTypography.button,
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Signup link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      "Don't have an account? ",
                      style: AdaptivTypography.body,
                    ),
                    TextButton(
                      onPressed: () {
                        widget.onNavigateToRegister?.call();
                      },
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                      ),
                      child: Text(
                        'Sign up',
                        style: AdaptivTypography.body.copyWith(
                          color: AdaptivColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 40),

                // Demo credentials
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AdaptivColors.background50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AdaptivColors.neutral300,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Demo Credentials:',
                        style: AdaptivTypography.overline,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'test@example.com',
                        style: AdaptivTypography.caption,
                      ),
                      Text(
                        'password123',
                        style: AdaptivTypography.caption,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
