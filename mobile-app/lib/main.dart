/*
This file starts the app.

It decides which screen to show:
- Loading screen while we check login
- Home screen if the user is logged in
- Login screen if the user is not logged in
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'theme/theme.dart';
import 'theme/colors.dart';
import 'services/api_client.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(
    const AdaptivHealthApp(
      initialToken: null,
    ),
  );
}

class AdaptivHealthApp extends StatefulWidget {
  final String? initialToken;

  const AdaptivHealthApp({
    super.key,
    this.initialToken,
  });

  @override
  State<AdaptivHealthApp> createState() => _AdaptivHealthAppState();
}

class _AdaptivHealthAppState extends State<AdaptivHealthApp> {
  late ApiClient _apiClient;
  bool? _isLoggedIn;
  bool _showRegister = false;

  @override
  void initState() {
    super.initState();
    // Create one API client for the whole app.
    // This keeps the login token in one place.
    _apiClient = ApiClient();
    
    // Set the first login state.
    // true = logged in, false = not logged in, null = still checking
    _isLoggedIn = widget.initialToken != null;
  }

  void _handleLoginSuccess() {
    // Login worked. Switch to the Home screen.
    setState(() {
      _isLoggedIn = true;
    });
  }

  void _handleLogout() {
    // User logged out. Show the Login screen again.
    setState(() {
      _isLoggedIn = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Adaptiv Health',
      // One shared theme for all screens.
      theme: buildAdaptivHealthTheme(),
      
      // Choose the right screen based on login state.
      home: _isLoggedIn == null
          ? const SplashScreen()
          : _isLoggedIn!
              ? HomeScreen(
                  apiClient: _apiClient,
                )
              : _showRegister
                  ? RegisterScreen(
                      apiClient: _apiClient,
                      onBackToLogin: () {
                        setState(() {
                          _showRegister = false;
                        });
                      },
                    )
                  : LoginScreen(
                      apiClient: _apiClient,
                      onLoginSuccess: _handleLoginSuccess,
                      onNavigateToRegister: () {
                        setState(() {
                          _showRegister = true;
                        });
                      },
                    ),
      debugShowCheckedModeBanner: false,
    );
  }
}

/*
Splash screen shown while the app starts.
It shows a simple animation so the user knows the app is working.
After a short delay, the app decides whether to show Login or Home.
*/
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;

  @override
  void initState() {
    super.initState();
    // Make the heart icon gently pulse.
    _animationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);

    // Wait a moment before switching screens.
    Future.delayed(const Duration(seconds: 2), () {
      // The parent widget will choose the next screen.
    });
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AdaptivColors.white,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animated heart logo
            ScaleTransition(
              scale: Tween(begin: 0.8, end: 1.0).animate(
                CurvedAnimation(
                  parent: _animationController,
                  curve: Curves.easeInOut,
                ),
              ),
              child: Container(
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
            ),
            const SizedBox(height: 24),
            Text(
              'Adaptiv Health',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: AdaptivColors.text900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Loading...',
              style: GoogleFonts.dmSans(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: AdaptivColors.text500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
