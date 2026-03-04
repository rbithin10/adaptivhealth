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
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'theme/theme.dart';
import 'services/api_client.dart';
import 'services/edge_ai_store.dart';
import 'services/chat_store.dart';
import 'services/notification_service.dart';
import 'services/alert_polling_service.dart';
import 'services/medication_reminder_service.dart';
import 'providers/auth_provider.dart';
import 'providers/chat_provider.dart';
import 'providers/vitals_provider.dart';
import 'providers/theme_provider.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.instance.initialize();

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
  late AuthProvider _authProvider;
  late ChatProvider _chatProvider;
  late bool _isLoggedIn;
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
    _authProvider = AuthProvider(apiClient: _apiClient);
    _chatProvider = ChatProvider(apiClient: _apiClient);
    
    // Set the first login state.
    _isLoggedIn = widget.initialToken != null;

    // If app launches with an existing token, initialize background services.
    if (_isLoggedIn) {
      _initializeEdgeAi();
      AlertPollingService.instance.start(_apiClient);
    }
  }

  void _handleLoginSuccess() async {
    // Login worked. Initialize edge AI with the authenticated Dio client.
    _initializeEdgeAi();
    AlertPollingService.instance.start(_apiClient);

    // Initialize medication reminders (local notifications)
    await MedicationReminderService().init();
    await MedicationReminderService().refreshReminders(_apiClient);

    // Get the current user's email to check their onboarding status
    String? userEmail;
    try {
      final userProfile = await _apiClient.getCurrentUser();
      userEmail = userProfile['email'] as String?;
      if (kDebugMode) debugPrint('DEBUG: Logged in user email: $userEmail');
    } catch (e) {
      if (kDebugMode) debugPrint('ERROR: Could not fetch user profile: $e');
      // If we can't get the email, default to showing onboarding
      userEmail = null;
    }

    // Check whether this user has completed onboarding
    final completed = userEmail != null 
        ? await hasCompletedOnboarding(userEmail)
        : false;  // Show onboarding if we couldn't get user email
    
    // Debug: Print onboarding status
    if (kDebugMode) debugPrint('DEBUG: Onboarding completed: $completed');
    if (kDebugMode) debugPrint('DEBUG: Will show onboarding: ${!completed}');

    setState(() {
      _isLoggedIn = true;
      _showOnboarding = !completed;
    });
    
    // Debug: Print state after setState
    if (kDebugMode) {
      debugPrint(
        'DEBUG: State updated - isLoggedIn: $_isLoggedIn, showOnboarding: $_showOnboarding',
      );
    }
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
    try {
      await _authProvider.logout();
    } catch (_) {
      await _apiClient.logout();
    }

    // Dispose edge AI on logout
    _edgeAiStore?.dispose();
    _edgeAiStore = null;
    AlertPollingService.instance.stop();

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
    Widget content;
    if (_isLoggedIn && _showOnboarding) {
      if (kDebugMode) debugPrint('DEBUG BUILD: Showing OnboardingScreen');
      content = OnboardingScreen(
        apiClient: _apiClient,
        onComplete: () {
          if (kDebugMode) debugPrint('DEBUG: Onboarding complete callback called');
          setState(() => _showOnboarding = false);
        },
      );
    } else if (_isLoggedIn) {
      if (kDebugMode) debugPrint('DEBUG BUILD: Showing HomeScreen');
      content = HomeScreen(apiClient: _apiClient, onLogout: handleLogout);
    } else if (_showRegister) {
      if (kDebugMode) debugPrint('DEBUG BUILD: Showing RegisterScreen');
      content = RegisterScreen(
        apiClient: _apiClient,
        onBackToLogin: () => setState(() => _showRegister = false),
      );
    } else {
      if (kDebugMode) debugPrint('DEBUG BUILD: Showing LoginScreen');
      // Login & Register screens always use light theme
      content = LoginScreen(
        apiClient: _apiClient,
        onLoginSuccess: _handleLoginSuccess,
        onNavigateToRegister: () => setState(() => _showRegister = true),
      );
    }

    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: _authProvider),
        ChangeNotifierProvider<ChatProvider>.value(value: _chatProvider),
        ChangeNotifierProvider<ThemeProvider>(create: (_) => ThemeProvider()),
        if (_edgeAiStore != null)
          ChangeNotifierProvider<EdgeAiStore>.value(value: _edgeAiStore!),
        if (_edgeAiStore != null)
          ChangeNotifierProvider<VitalsProvider>(
            create: (_) => VitalsProvider(
              apiClient: _apiClient,
              edgeAiStore: _edgeAiStore!,
            )..fallbackToMock(),
          ),
        ChangeNotifierProvider<ChatStore>.value(value: _chatStore),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) => MaterialApp(
          title: 'Adaptiv Health',
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: themeProvider.themeMode,
          home: content,
          debugShowCheckedModeBanner: false,
        ),
      ),
    );
  }
}
