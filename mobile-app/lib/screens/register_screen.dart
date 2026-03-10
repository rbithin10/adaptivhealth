/*
Register screen.

New users enter their details here to create an account.
After successful registration, they return to the Login screen.
*/

import 'package:flutter/material.dart'; // Core Flutter UI toolkit
import 'package:google_fonts/google_fonts.dart'; // Custom font support
import '../theme/colors.dart'; // App colour palette
import '../theme/typography.dart'; // Shared text styles
import '../services/api_client.dart'; // Talks to our backend server
import '../utils/validators.dart'; // Shared input validation helpers

class RegisterScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback onBackToLogin;

  const RegisterScreen({
    super.key,
    required this.apiClient,
    required this.onBackToLogin,
  });

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>(); // Validates all fields before submitting
  final _nameController = TextEditingController(); // User's full name
  final _emailController = TextEditingController(); // User's email address
  final _passwordController = TextEditingController(); // User's chosen password
  final _confirmPasswordController = TextEditingController(); // Must match password
  final _ageController = TextEditingController(); // Optional age
  final _phoneController = TextEditingController(); // Optional phone number

  bool _isLoading = false; // True while the request is being sent
  bool _showPassword = false; // Toggle password visibility
  bool _showConfirmPassword = false; // Toggle confirm password visibility
  String? _errorMessage; // Shown when registration fails
  String? _successMessage; // Shown briefly before redirecting to login
  String _selectedGender = ''; // User's chosen gender option

  static const List<String> _genderOptions = [
    'male',
    'female',
    'other',
    'prefer not to say',
  ];

  // Clean up text controllers when this screen is removed
  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _ageController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  // Validate the form, send the new account data to the server, then redirect to login
  void _handleRegister() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      await widget.apiClient.register(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        name: _nameController.text.trim(),
        age: _ageController.text.isNotEmpty
            ? int.parse(_ageController.text)
            : null,
        gender: _selectedGender.isNotEmpty ? _selectedGender : null,
        phone: _phoneController.text.trim().isNotEmpty
            ? _phoneController.text.trim()
            : null,
      );

      setState(() {
        _successMessage = 'Account created! Redirecting to login...';
      });

      await Future.delayed(const Duration(seconds: 2));
      widget.onBackToLogin();
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

  // Build the registration form with all fields and submit button
  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        decoration: BoxDecoration(
          image: DecorationImage(
            image: const AssetImage('assets/images/login_bg.png'),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(
              brightness == Brightness.dark
                  ? Colors.black.withOpacity(0.6)
                  : Colors.white.withOpacity(0.85),
              brightness == Brightness.dark
                  ? BlendMode.darken
                  : BlendMode.lighten,
            ),
          ),
        ),
        child: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 24),

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
                const SizedBox(height: 24),

                // Title
                Text(
                  'Create Account',
                  style: GoogleFonts.dmSans(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AdaptivColors.text900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Join Adaptiv Health',
                  style: AdaptivTypography.body,
                ),
                const SizedBox(height: 32),

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
                if (_errorMessage != null) const SizedBox(height: 16),

                // Success message
                if (_successMessage != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AdaptivColors.stableBg,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AdaptivColors.stableBorder,
                      ),
                    ),
                    child: Text(
                      _successMessage!,
                      style: AdaptivTypography.caption.copyWith(
                        color: AdaptivColors.stableText,
                      ),
                    ),
                  ),
                if (_successMessage != null) const SizedBox(height: 16),

                // Form
                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      // Full name
                      TextFormField(
                        controller: _nameController,
                        decoration: InputDecoration(
                          labelText: 'Full Name',
                          prefixIcon: const Icon(Icons.person_outlined),
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
                        validator: Validators.name,
                      ),
                      const SizedBox(height: 16),

                      // Email
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
                        validator: Validators.email,
                      ),
                      const SizedBox(height: 16),

                      // Password
                      TextFormField(
                        controller: _passwordController,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock_outlined),
                          helperText: 'Min 8 chars, at least one letter and one digit',
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
                        validator: Validators.password,
                      ),
                      const SizedBox(height: 16),

                      // Confirm password
                      TextFormField(
                        controller: _confirmPasswordController,
                        decoration: InputDecoration(
                          labelText: 'Confirm Password',
                          prefixIcon: const Icon(Icons.lock_outlined),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _showConfirmPassword
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            onPressed: () {
                              setState(() {
                                _showConfirmPassword = !_showConfirmPassword;
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
                        obscureText: !_showConfirmPassword,
                        validator: (value) =>
                            Validators.confirmPassword(value, _passwordController.text),
                      ),
                      const SizedBox(height: 16),

                      // Age
                      TextFormField(
                        controller: _ageController,
                        decoration: InputDecoration(
                          labelText: 'Age (optional)',
                          prefixIcon: const Icon(Icons.cake_outlined),
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
                        keyboardType: TextInputType.number,
                        validator: Validators.age,
                      ),
                      const SizedBox(height: 16),

                      // Gender dropdown
                      DropdownButtonFormField<String>(
                        initialValue: _selectedGender.isEmpty ? null : _selectedGender,
                        decoration: InputDecoration(
                          labelText: 'Gender (optional)',
                          prefixIcon: const Icon(Icons.people_outlined),
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
                        items: _genderOptions
                            .map((g) => DropdownMenuItem(
                                  value: g,
                                  child: Text(
                                    g[0].toUpperCase() + g.substring(1),
                                  ),
                                ))
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            _selectedGender = value ?? '';
                          });
                        },
                      ),
                      const SizedBox(height: 16),

                      // Phone
                      TextFormField(
                        controller: _phoneController,
                        decoration: InputDecoration(
                          labelText: 'Phone (optional)',
                          prefixIcon: const Icon(Icons.phone_outlined),
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
                        keyboardType: TextInputType.phone,
                        validator: Validators.phone,
                      ),
                      const SizedBox(height: 24),

                      // Register button
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _handleRegister,
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
                                  'Create Account',
                                  style: AdaptivTypography.button,
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Back to login link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'Already have an account? ',
                      style: AdaptivTypography.body,
                    ),
                    TextButton(
                      onPressed: widget.onBackToLogin,
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                      ),
                      child: Text(
                        'Sign in',
                        style: AdaptivTypography.body.copyWith(
                          color: AdaptivColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
        ),
      ),
    );
  }
}
