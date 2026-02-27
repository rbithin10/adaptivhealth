/*
This file starts the app.

It decides which screen to show:
- Loading screen while we check login
- Home screen if the user is logged in
- Login screen if the user is not logged in

DARK MODE SUPPORT:
The app respects system theme (light/dark) by default.
Users can override in Settings (Profile screen).
Theme preference is persisted to shared_preferences.

EDGE AI:
Edge AI (TFLite risk prediction + threshold alerts + GPS emergency)
initializes in the background at startup. It does NOT block the UI.
If the ML model fails to load, the app falls back to cloud API calls.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'theme/theme.dart';
import 'theme/colors.dart';
import 'services/api_client.dart';
import 'services/edge_ai_store.dart';
import 'services/chat_store.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  runApp(const AdaptivHealthApp(initialToken: null));
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
  bool _showOnboarding = false;

  // Edge AI store — initialized after ApiClient is ready
  EdgeAiStore? _edgeAiStore;

  // Chat store — session-scoped conversation history for the AI coach
  final ChatStore _chatStore = ChatStore();

  @override
  void initState() {
    super.initState();
    // Create one API client for the whole app.
    _apiClient = ApiClient();
    
    // Set the first login state.
    _isLoggedIn = widget.initialToken != null;
  }

  void _handleLoginSuccess() async {
    // Login worked. Initialize edge AI with the authenticated Dio client.
    _initializeEdgeAi();

    // Get the current user's email to check their onboarding status
    String? userEmail;
    try {
      final userProfile = await _apiClient.getCurrentUser();
      userEmail = userProfile['email'] as String?;
      print('DEBUG: Logged in user email: $userEmail');
    } catch (e) {
      print('ERROR: Could not fetch user profile: $e');
      // If we can't get the email, default to showing onboarding
      userEmail = null;
    }

    // Check whether this user has completed onboarding
    final completed = userEmail != null 
        ? await hasCompletedOnboarding(userEmail)
        : false;  // Show onboarding if we couldn't get user email
    
    // Debug: Print onboarding status
    print('DEBUG: Onboarding completed: $completed');
    print('DEBUG: Will show onboarding: ${!completed}');

    setState(() {
      _isLoggedIn = true;
      _showOnboarding = !completed;
    });
    
    // Debug: Print state after setState
    print('DEBUG: State updated - isLoggedIn: $_isLoggedIn, showOnboarding: $_showOnboarding');
  }

  /// Initialize edge AI after login (needs authenticated Dio for cloud sync)
  void _initializeEdgeAi() {
    // Create edge AI store with the API client's Dio instance
    _edgeAiStore = EdgeAiStore(_apiClient.dio);
    // Initialize in background — does NOT block the UI
    _edgeAiStore!.initialize();
  }

  /// Handles logout from any screen. Call this to return to login.
  void handleLogout() async {
    // Dispose edge AI on logout
    _edgeAiStore?.dispose();
    _edgeAiStore = null;

    // Clear chat history so the next user starts fresh
    _chatStore.clear();

    // Note: We don't clear the onboarding flag anymore because it's now user-specific.
    // Each user's onboarding completion is stored separately by email,
    // so different accounts will automatically see/skip onboarding appropriately.

    setState(() {
      _isLoggedIn = false;
      _showOnboarding = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    // Wrap with EdgeAiStore provider when available (after login)
    Widget home;
    if (_isLoggedIn == null) {
      home = const SplashScreen();
    } else if (_isLoggedIn! && _showOnboarding) {
      print('DEBUG BUILD: Showing OnboardingScreen');
      home = OnboardingScreen(
        apiClient: _apiClient,
        onComplete: () {
          print('DEBUG: Onboarding complete callback called');
          setState(() => _showOnboarding = false);
        },
      );
    } else if (_isLoggedIn!) {
      print('DEBUG BUILD: Showing HomeScreen');
      home = HomeScreen(apiClient: _apiClient, onLogout: handleLogout);
    } else if (_showRegister) {
      print('DEBUG BUILD: Showing RegisterScreen');
      home = RegisterScreen(
        apiClient: _apiClient,
        onBackToLogin: () => setState(() => _showRegister = false),
      );
    } else {
      print('DEBUG BUILD: Showing LoginScreen');
      // Login & Register screens always use light theme
      home = LoginScreen(
        apiClient: _apiClient,
        onLoginSuccess: _handleLoginSuccess,
        onNavigateToRegister: () => setState(() => _showRegister = true),
      );
    }

    // Provide EdgeAiStore to the widget tree when initialized
    if (_edgeAiStore != null) {
      home = ChangeNotifierProvider<EdgeAiStore>.value(
        value: _edgeAiStore!,
        child: home,
      );
    }

    // Provide ChatStore to the entire widget tree so the AI coach
    // conversation survives bottom-sheet dismissals.
    home = ChangeNotifierProvider<ChatStore>.value(
      value: _chatStore,
      child: home,
    );

    return MaterialApp(
      title: 'Adaptiv Health',
      theme: buildAdaptivHealthTheme(Brightness.light),
      themeMode: ThemeMode.light,
      home: home,
      debugShowCheckedModeBanner: false,
    );
  }
}

/*
Splash screen shown while the app starts.
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
    _animationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);

    Future.delayed(const Duration(seconds: 2), () {});
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    final bgColor = AdaptivColors.getBackgroundColor(brightness);
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryTextColor = AdaptivColors.getSecondaryTextColor(brightness);

    return Scaffold(
      backgroundColor: bgColor,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Semantics(
              label: 'Adaptiv Health loading indicator',
              enabled: true,
              child: ScaleTransition(
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
                      color: AdaptivColors.getPrimaryColor(brightness),
                      width: 3,
                    ),
                  ),
                  child: Icon(
                    Icons.favorite,
                    color: AdaptivColors.critical,
                    size: 40,
                    semanticLabel: 'Heart icon',
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Adaptiv Health',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Loading...',
              style: GoogleFonts.dmSans(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: secondaryTextColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
