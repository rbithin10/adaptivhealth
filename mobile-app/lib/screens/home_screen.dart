/*
Home screen.

This shows the latest heart data, a risk label, and a short tip.
If the server is slow or down, we show safe demo values instead of a blank screen.
*/

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../services/chat_store.dart';
import '../services/edge_ai_store.dart';
import '../services/mock_vitals_service.dart';
import '../widgets/ai_coach_position_store.dart';
import '../widgets/widgets.dart';
import 'fitness_plans_screen.dart';
import 'recovery_screen.dart';
import 'health_screen.dart';
import 'profile_screen.dart';
import 'nutrition_screen.dart';
import 'doctor_messaging_screen.dart';
import 'notifications_screen.dart';
import 'rehab_program_screen.dart';
import 'history_screen.dart';
import 'device_pairing_screen.dart';
import '../widgets/sos_button.dart';
// Note: ChatbotScreen removed - AI Coach is now a floating widget (FloatingChatbot)

class HomeScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback? onLogout;

  const HomeScreen({
    super.key,
    required this.apiClient,
    this.onLogout,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<Map<String, dynamic>> _vitalsFuture;
  late Future<Map<String, dynamic>> _riskFuture;
  late Future<Map<String, dynamic>> _userFuture;
  late Future<Map<String, dynamic>> _recommendationFuture;
  late Future<List<dynamic>> _activitiesFuture;
  late Future<List<dynamic>> _vitalHistoryFuture;

  // Stable combined future — set once in _loadData(), never recreated.
  // Prevents FutureBuilder from resetting to ConnectionState.waiting every
  // time the mock-vitals stream calls setState.
  late Future<Map<String, dynamic>> _combinedFuture;

  int _selectedIndex = 0;

  // Draggable AI Coach button position (bottom-right default).
  double _fabX = -1;
  double _fabY = -1;

  MockVitalsService? _mockVitalsService;
  StreamSubscription<VitalReading>? _mockVitalsRefreshSub;

  // ValueNotifiers for live vitals — updates without triggering full rebuilds.
  final ValueNotifier<VitalReading?> _liveVitalsNotifier = ValueNotifier(null);
  final ValueNotifier<List<VitalReading>> _vitalsHistoryNotifier =
      ValueNotifier([]);

  @override
  void initState() {
    super.initState();
    _loadData();

    // Initialize simulator service after first frame so Provider context is ready.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeMockVitalsServiceIfPossible();
    });
  }

  @override
  void dispose() {
    _mockVitalsRefreshSub?.cancel();
    _mockVitalsService?.dispose();
    _liveVitalsNotifier.dispose();
    _vitalsHistoryNotifier.dispose();
    super.dispose();
  }

  void _initializeMockVitalsServiceIfPossible() {
    if (_mockVitalsService != null || !mounted) return;

    try {
      final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
      _mockVitalsService = MockVitalsService(
        apiClient: widget.apiClient,
        edgeAiStore: edgeStore,
      );

      _mockVitalsRefreshSub = _mockVitalsService!.stream.listen((reading) {
        if (!mounted) return;
        // Update ValueNotifiers directly — no setState, so no full-screen rebuild.
        _liveVitalsNotifier.value = reading;
        final updated = [..._vitalsHistoryNotifier.value, reading];
        if (updated.length > 50) updated.removeAt(0);
        _vitalsHistoryNotifier.value = updated;
      });
    } catch (_) {
      // EdgeAiStore may not be available yet; profile will still show guidance.
    }
  }

  /// Feed loaded vitals into edge AI for on-device risk prediction.
  /// Called after vitals + user data load successfully.
  void _feedEdgeAi(Map<String, dynamic> user, Map<String, dynamic> vitals) {
    // Safely get EdgeAiStore from provider tree (may not exist yet)
    try {
      final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
      if (!edgeStore.isReady && !edgeStore.isInitializing) return;

      // Extract vitals
      final heartRate = _safeToInt(vitals['heart_rate'], 0);
      if (heartRate <= 0) return; // No valid HR, skip

      final spo2 = _safeToInt(vitals['spo2'], 0);
      final bpSystolic = _safeBloodPressure(vitals['blood_pressure'], 'systolic', 0);
      final bpDiastolic = _safeBloodPressure(vitals['blood_pressure'], 'diastolic', 0);

      // Extract user profile for ML prediction
      final age = _safeToInt(user['age'], 0);
      // Calculate max safe HR: 220 - age (standard formula)
      final maxSafeHr = age > 0 ? 220 - age : 185;
      // Use resting HR as baseline (or default 72)
      final baselineHr = _safeToInt(user['resting_hr'] ?? user['baseline_hr'], 72);

      // Run edge AI: threshold alerts + ML risk prediction + GPS if critical
      edgeStore.processVitals(
        heartRate: heartRate,
        spo2: spo2 > 0 ? spo2 : null,
        bpSystolic: bpSystolic > 0 ? bpSystolic : null,
        bpDiastolic: bpDiastolic > 0 ? bpDiastolic : null,
        age: age > 0 ? age : null,
        baselineHr: baselineHr,
        maxSafeHr: maxSafeHr,
      );
    } catch (_) {
      // EdgeAiStore not in widget tree yet — skip silently
    }
  }

  void _loadData() {
    _userFuture = widget.apiClient.getCurrentUser().catchError(
      (e) => {
        'name': 'Patient',
        'age': 35,
      },
    );

    _vitalsFuture = widget.apiClient.getLatestVitals().catchError(
      (e) => {
        'heart_rate': 0,
        'spo2': 0,
        'systolic_bp': 0,
        'diastolic_bp': 0,
        'timestamp': DateTime.now().toIso8601String(),
        'error': true,
      },
    );

    _riskFuture = widget.apiClient.getLatestRiskAssessment().catchError(
      (e) => {
        'risk_level': 'low',
        'risk_score': 0.23,
      },
    );

    _recommendationFuture = widget.apiClient.getLatestRecommendation();

    _activitiesFuture = widget.apiClient.getActivities(limit: 5).catchError(
      (e) => <dynamic>[],
    );

    _vitalHistoryFuture = widget.apiClient.getVitalHistory(days: 1).catchError(
      (e) => <dynamic>[],
    );

    // Combine the three API calls into one stable future. Setting this once
    // here means the FutureBuilder in _buildHomeTab() never resets to
    // ConnectionState.waiting when mock-vitals trigger a redraw.
    _combinedFuture = Future.wait([_userFuture, _vitalsFuture, _riskFuture])
        .then((results) => <String, dynamic>{
              'user': results[0],
              'vitals': results[1],
              'risk': results[2],
            });
  }

  String _getRiskZoneLabel(int heartRate) {
    // Simple labels so non-medical users can understand quickly.
    if (heartRate < 60) return 'Resting';
    if (heartRate < 100) return 'Active';
    return 'Recovery';
  }

  String _getRiskStatus(String riskLevel) {
    // Turn technical risk levels into plain words.
    switch (riskLevel.toLowerCase()) {
      case 'high':
        return 'Elevated Risk';
      case 'moderate':
        return 'Caution Zone';
      case 'low':
      default:
        return 'Safe Zone';
    }
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    return Scaffold(
      backgroundColor: AdaptivColors.getBackgroundColor(brightness),
      drawer: Drawer(
        child: SafeArea(
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              DrawerHeader(
                decoration: const BoxDecoration(
                  color: AdaptivColors.primaryUltralight,
                ),
                child: Align(
                  alignment: Alignment.bottomLeft,
                  child: Text(
                    'Quick Navigation',
                    style: AdaptivTypography.sectionTitle,
                  ),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.notifications_none),
                title: const Text('Notifications'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) =>
                          NotificationsScreen(apiClient: widget.apiClient),
                    ),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.health_and_safety_outlined),
                title: const Text('Health Insights'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => HealthScreen(apiClient: widget.apiClient),
                    ),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.history),
                title: const Text('Activity History'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => HistoryScreen(apiClient: widget.apiClient),
                    ),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.spa_outlined),
                title: const Text('Rehabilitation'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => RehabProgramScreen(apiClient: widget.apiClient),
                    ),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.bluetooth),
                title: const Text('Device Pairing'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => DevicePairingScreen(
                        apiClient: widget.apiClient,
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: AdaptivColors.getSurfaceColor(brightness),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white,
                AdaptivColors.primaryUltralight,
              ],
            ),
          ),
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AdaptivColors.critical.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.favorite,
                color: AdaptivColors.critical,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Text(
              'Adaptiv Health',
              style: GoogleFonts.dmSans(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AdaptivColors.text900,
              ),
            ),
          ],
        ),
        actions: [
          SOSButton(apiClient: widget.apiClient),
          Container(
            margin: const EdgeInsets.only(right: 8),
            decoration: BoxDecoration(
              color: AdaptivColors.primaryUltralight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: IconButton(
              icon: const Icon(Icons.notifications_none),
              color: AdaptivColors.primary,
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) =>
                        NotificationsScreen(apiClient: widget.apiClient),
                  ),
                );
              },
            ),
          ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          // Keep chatbot inside visible body bounds at all times.
          const double fabSize = 56.0;
          const double horizontalMargin = 16.0;
          const double topMargin = 8.0;
          const double bottomMargin = 16.0;

          final double minFabX = 0.0;
          final double maxFabX = (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
          final double minFabY = topMargin;
          final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
              .clamp(minFabY, double.infinity);

          // Sync with global coach position (shared across all screens).
          final sharedPosition = AiCoachPositionStore.position;
          if (sharedPosition != null) {
            _fabX = sharedPosition.dx;
            _fabY = sharedPosition.dy;
          }

          // Initialise FAB position to bottom-right on first layout.
          if (_fabX < 0 || _fabY < 0) {
            _fabX = (constraints.maxWidth - fabSize - horizontalMargin)
                .clamp(minFabX, maxFabX);
            _fabY = (constraints.maxHeight - fabSize - bottomMargin)
                .clamp(minFabY, maxFabY);
          } else {
            // Re-clamp on rebuild (rotation/layout changes) to prevent
            // chatbot from being rendered outside the body stack.
            _fabX = _fabX.clamp(minFabX, maxFabX);
            _fabY = _fabY.clamp(minFabY, maxFabY);
          }

          AiCoachPositionStore.setPosition(Offset(_fabX, _fabY));
          return Stack(
            children: [
              // Main tab content fills the available space.
              Positioned.fill(child: _getSelectedScreen()),

              if (_selectedIndex != 4)
                // Draggable floating AI Health Coach.
                Positioned(
                  left: _fabX,
                  top: _fabY,
                  child: FloatingChatbot(
                    apiClient: widget.apiClient,
                    posX: _fabX,
                    posY: _fabY,
                    onPositionChanged: (offset) {
                      setState(() {
                        _fabX = offset.dx.clamp(minFabX, maxFabX);
                        _fabY = offset.dy.clamp(minFabY, maxFabY);
                        AiCoachPositionStore.setPosition(Offset(_fabX, _fabY));
                      });
                    },
                  ),
                ),
            ],
          );
        },
      ),
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            activeIcon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.fitness_center_outlined),
            activeIcon: Icon(Icons.fitness_center),
            label: 'Fitness',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.restaurant_outlined),
            activeIcon: Icon(Icons.restaurant),
            label: 'Nutrition',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.message_outlined),
            activeIcon: Icon(Icons.message),
            label: 'Messages',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            activeIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
        currentIndex: _selectedIndex,
        selectedItemColor: AdaptivColors.primary,
        unselectedItemColor: AdaptivColors.text500,
        onTap: (index) {
          setState(() {
            _selectedIndex = index;
          });
          final chatStore = Provider.of<ChatStore>(context, listen: false);
          chatStore.currentScreen = [
            'home',
            'health',
            'fitness',
            'wellness',
            'recovery',
            'nutrition',
            'messaging',
            'rehab',
          ][_selectedIndex];
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: Colors.white,
        elevation: 8,
      ),
    );
  }

  // Returns the screen widget for each bottom nav tab
  // New 5-tab structure: Home, Fitness, Nutrition, Messages, Profile
  // AI Chatbot is now a floating button (always accessible)
  // Recovery is accessible from Fitness screen
  // Health metrics are shown on Home dashboard
  Widget _getSelectedScreen() {
    switch (_selectedIndex) {
      case 0:
        return _buildHomeTab();
      case 1:
        return FitnessPlansScreen(apiClient: widget.apiClient);
      case 2:
        return NutritionScreen(apiClient: widget.apiClient);
      case 3:
        return DoctorMessagingScreen(apiClient: widget.apiClient);
      case 4:
        return ProfileScreen(
          apiClient: widget.apiClient,
          mockVitalsService: _mockVitalsService,
          onLogout: widget.onLogout,
        );
      default:
        return _buildHomeTab();
    }
  }

  // Navigate to Recovery screen (accessible from Fitness or quick actions)
  void _navigateToRecovery() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => RecoveryScreen(apiClient: widget.apiClient),
      ),
    );
  }

  // Navigate to Health screen (accessible from Home or quick actions)
  void _navigateToHealth() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => HealthScreen(apiClient: widget.apiClient),
      ),
    );
  }

  Widget _buildHomeTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _combinedFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const SizedBox.expand(
            child: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        if (snapshot.hasError) {
          return SizedBox.expand(
            child: Center(
              child: Text('Error loading data: ${snapshot.error}'),
            ),
          );
        }

        final data = snapshot.data;
        if (data == null) {
          return const SizedBox.expand(
            child: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        final user = data['user'] as Map<String, dynamic>;
        final vitals = data['vitals'] as Map<String, dynamic>;
        final risk = data['risk'] as Map<String, dynamic>;

        final userName = user['name'] ?? 'Patient';
        final firstName = userName.split(' ').first;
        // Base values from API; overridden live by ValueListenableBuilder below
        final apiHeartRate = _safeToInt(vitals['heart_rate'], 72);
        final apiSpo2     = _safeToInt(vitals['spo2'], 98);
        final systolicBp = _safeBloodPressure(
          vitals['blood_pressure'],
          'systolic',
          120,
        );
        final diastolicBp = _safeBloodPressure(
          vitals['blood_pressure'],
          'diastolic',
          80,
        );
        final riskLevel = risk['risk_level'] ?? 'low';

        // Feed vitals into edge AI for on-device risk prediction
        // This runs threshold checks + ML prediction + GPS emergency if critical
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _feedEdgeAi(user, vitals);
        });

        return Container(
          // Image backdrop for patient dashboard
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/home_bg.png'),
              fit: BoxFit.cover,
              colorFilter: ColorFilter.mode(
                Colors.white.withOpacity(0.85),
                BlendMode.lighten,
              ),
            ),
          ),
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Greeting card with glass effect
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: AdaptivColors.primary.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(
                                Icons.waving_hand,
                                color: Colors.amber,
                                size: 24,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Good morning, $firstName',
                                    style: AdaptivTypography.screenTitle,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    riskLevel.toLowerCase() == 'high'
                                        ? 'Stay calm — your heart is working hard'
                                        : 'Your heart is looking good today',
                                    style: AdaptivTypography.caption.copyWith(
                                      color: AdaptivColors.text600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                // HERO HEART RATE RING + EDGE AI RISK (merged).
                // ValueListenableBuilder updates live vitals; edge AI risk
                // is read from EdgeAiStore via Provider inside the builder.
                ValueListenableBuilder<VitalReading?>(
                  valueListenable: _liveVitalsNotifier,
                  builder: (context, liveReading, _) {
                    final heartRate = liveReading?.heartRate ?? apiHeartRate;
                    final spo2      = liveReading?.spo2      ?? apiSpo2;

                    // Read edge AI prediction (may be null if model not loaded yet)
                    EdgeAiStore? edgeStore;
                    try {
                      edgeStore = Provider.of<EdgeAiStore>(context);
                    } catch (e) {
                      if (kDebugMode) {
                        debugPrint('Error in _buildHomeTab.edgeStoreLookup: $e');
                      }
                    }
                    final prediction = edgeStore?.latestPrediction;
                    final edgeRiskLevel = prediction?.riskLevel ?? riskLevel;
                    final edgeRiskColor = AdaptivColors.getRiskColor(edgeRiskLevel);

                    return Column(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.9),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.08),
                                blurRadius: 15,
                                offset: const Offset(0, 5),
                              ),
                            ],
                          ),
                          child: Column(
                            children: [
                              Center(
                                child: _buildHeartRateRing(
                                  heartRate: heartRate,
                                  riskLevel: edgeRiskLevel,
                                  maxSafeHR: 150,
                                ),
                              ),
                              const SizedBox(height: 16),
                              // Edge AI risk badges (replaces old zone/status badges)
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  _buildStatusBadge(
                                    prediction != null
                                        ? 'Risk: ${edgeRiskLevel.toUpperCase()}'
                                        : _getRiskZoneLabel(heartRate),
                                    prediction != null
                                        ? (edgeRiskLevel == 'high'
                                            ? Icons.warning_rounded
                                            : edgeRiskLevel == 'moderate'
                                                ? Icons.info_rounded
                                                : Icons.check_circle_rounded)
                                        : Icons.directions_run,
                                    prediction != null ? edgeRiskColor : AdaptivColors.primary,
                                  ),
                                  _buildStatusBadge(
                                    prediction != null
                                        ? 'Score: ${(prediction.riskScore * 100).toInt()}%'
                                        : _getRiskStatus(riskLevel),
                                    prediction != null
                                        ? Icons.analytics_outlined
                                        : Icons.shield_outlined,
                                    prediction != null ? edgeRiskColor : AdaptivColors.getRiskColor(riskLevel),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              // Compact Edge AI status line
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: edgeStore?.modelLoaded == true
                                          ? AdaptivColors.stable
                                          : Colors.orange,
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    edgeStore?.modelLoaded == true
                                        ? 'On-Device AI • v${edgeStore!.modelVersion}'
                                            '${prediction != null ? ' • ${prediction.inferenceTimeMs}ms' : ''}'
                                        : edgeStore?.isInitializing == true
                                            ? 'Edge AI Loading...'
                                            : 'Waiting for Edge AI',
                                    style: GoogleFonts.dmSans(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w500,
                                      color: AdaptivColors.text500,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),

                        // Threshold alerts from edge AI (if any)
                        if (edgeStore != null && edgeStore.activeAlerts.isNotEmpty)
                          ...edgeStore.activeAlerts.map((alert) {
                            final alertColor = alert.severity == 'critical'
                                ? AdaptivColors.critical : Colors.orange;
                            return Container(
                              margin: const EdgeInsets.only(top: 10),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: alertColor.withOpacity(0.08),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: alertColor.withOpacity(0.3)),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    alert.severity == 'critical'
                                        ? Icons.error_rounded
                                        : Icons.warning_amber_rounded,
                                    color: alertColor, size: 18,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      alert.message,
                                      style: GoogleFonts.dmSans(
                                        fontSize: 12,
                                        color: alertColor,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }),

                        const SizedBox(height: 24),
                        // Secondary Vitals Grid
                        _buildVitalsGrid(
                          spo2: spo2,
                          systolicBp: systolicBp,
                          diastolicBp: diastolicBp,
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 24),

                // Quick Actions
                _buildQuickActions(),
                const SizedBox(height: 24),

                // Rehab Program Card (if user is in rehab)
                _buildRehabCard(user),

                // Recent Activity
                _buildRecentActivity(),
                const SizedBox(height: 24),

                // Heart Rate Sparkline
                _buildHeartRateSparkline(),
                const SizedBox(height: 24),

                // AI Recommendation Card
                _buildRecommendationCard(riskLevel),
                const SizedBox(height: 24),

                // Refresh button with enhanced design
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      setState(() {
                        _loadData();
                      });
                      // Also trigger edge AI cloud sync
                      try {
                        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
                        edgeStore.syncNow();
                      } catch (e) {
                        if (kDebugMode) {
                          debugPrint('Error in _buildHomeTab.syncNow: $e');
                        }
                      }
                    },
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh Data'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      backgroundColor: AdaptivColors.primary,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 0,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
        );
      },
    );
  }

  // Helper method for status badges
  Widget _buildStatusBadge(String label, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: AdaptivTypography.caption.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeartRateRing({
    required int heartRate,
    required String riskLevel,
    required int maxSafeHR,
  }) {
    // Calculate fill percentage for potential future progress ring visualization
    final _ = (heartRate / maxSafeHR).clamp(0.0, 1.0);
    final ringColor = AdaptivColors.getRiskColor(riskLevel);

    return Column(
      children: [
        // Heart rate ring visualization with enhanced design
        Stack(
          alignment: Alignment.center,
          children: [
            // Outer glow effect
            Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: ringColor.withOpacity(0.3),
                    blurRadius: 30,
                    spreadRadius: 5,
                  ),
                ],
              ),
            ),
            // Main ring
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: ringColor,
                  width: 12,
                ),
                gradient: RadialGradient(
                  colors: [
                    Colors.white,
                    ringColor.withOpacity(0.05),
                  ],
                ),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Animated heart icon
                    Icon(
                      Icons.favorite,
                      color: ringColor,
                      size: 32,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      heartRate.toString(),
                      style: AdaptivTypography.heroNumber.copyWith(
                        color: ringColor,
                        fontSize: 48,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'BPM',
                      style: AdaptivTypography.heroUnit.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: AdaptivColors.stable.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AdaptivColors.stable,
                              boxShadow: [
                                BoxShadow(
                                  color: AdaptivColors.stable.withOpacity(0.5),
                                  blurRadius: 4,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Live',
                            style: AdaptivTypography.caption.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildVitalsGrid({
    required int spo2,
    required int systolicBp,
    required int diastolicBp,
  }) {
    // Sample trend data for visualization
    final hrTrend = [68.0, 72.0, 75.0, 71.0, 73.0, 72.0];
    final spo2Trend = [97.0, 98.0, 98.0, 97.0, 98.0, spo2.toDouble()];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              Text(
                'Vitals',
                style: AdaptivTypography.subtitle1.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              Text(
                'View All',
                style: AdaptivTypography.label.copyWith(
                  color: AdaptivColors.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        // Compact horizontal scroll of VitalCards
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.air,
                  label: 'SpO2',
                  value: spo2.toString(),
                  unit: '%',
                  status: spo2 < 90
                      ? VitalStatus.critical
                      : spo2 < 95
                          ? VitalStatus.warning
                          : VitalStatus.safe,
                  trend: spo2Trend,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.water_drop,
                  label: 'BP',
                  value: '$systolicBp/$diastolicBp',
                  unit: 'mmHg',
                  status: systolicBp > 140
                      ? VitalStatus.critical
                      : systolicBp > 130
                          ? VitalStatus.warning
                          : VitalStatus.safe,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.timeline,
                  label: 'HRV',
                  value: '45',
                  unit: 'ms',
                  status: VitalStatus.safe,
                  trend: hrTrend,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
            ],
          ),
        ),
      ],
    );
  }



  Widget _buildQuickActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick Actions',
          style: AdaptivTypography.subtitle1.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildQuickActionButton(
                icon: Icons.directions_run,
                label: 'Start Workout',
                color: AdaptivColors.primary,
                onTap: () {
                  setState(() => _selectedIndex = 1); // Go to Fitness
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildQuickActionButton(
                icon: Icons.self_improvement,
                label: 'Recovery',
                color: const Color(0xFF9C27B0),
                onTap: _navigateToRecovery, // Opens Recovery screen
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildQuickActionButton(
                icon: Icons.monitor_heart,
                label: 'Health',
                color: AdaptivColors.critical,
                onTap: _navigateToHealth, // Opens Health screen
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildQuickActionButton(
                icon: Icons.smart_toy_outlined,
                label: 'AI Coach',
                color: AdaptivColors.stable,
                onTap: () {
                  // Hint user to use the floating chatbot button
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Tap the AI Coach button in the corner →'),
                      duration: Duration(seconds: 2),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildQuickActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 104),
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              label,
              style: AdaptivTypography.caption.copyWith(
                color: color,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  /// Map activity_type string to an icon + color for the list.
  IconData _activityIcon(String? type) {
    switch (type?.toLowerCase()) {
      case 'running':
        return Icons.directions_run;
      case 'cycling':
        return Icons.directions_bike;
      case 'swimming':
        return Icons.pool;
      case 'yoga':
        return Icons.self_improvement;
      case 'stretching':
        return Icons.accessibility_new;
      case 'strength_training':
        return Icons.fitness_center;
      case 'walking':
      default:
        return Icons.directions_walk;
    }
  }

  Color _activityColor(String? type) {
    switch (type?.toLowerCase()) {
      case 'running':
        return AdaptivColors.warning;
      case 'cycling':
        return AdaptivColors.primary;
      case 'swimming':
        return const Color(0xFF0097A7);
      case 'yoga':
      case 'stretching':
        return const Color(0xFF9C27B0);
      case 'strength_training':
        return AdaptivColors.critical;
      case 'walking':
      default:
        return AdaptivColors.stable;
    }
  }

  String? _activityImage(String? type) {
    switch (type?.toLowerCase()) {
      case 'walking':
        return 'assets/exercises/walking.png';
      case 'running':
      case 'light_jogging':
        return 'assets/exercises/light_jogging.png';
      case 'cycling':
        return 'assets/exercises/cycling.png';
      case 'swimming':
        return 'assets/exercises/swimming.png';
      case 'yoga':
        return 'assets/exercises/yoga.png';
      case 'stretching':
        return 'assets/exercises/stretching.png';
      case 'strength_training':
        return 'assets/exercises/resistance_bands.png';
      default:
        return null;
    }
  }

  /// Format a datetime string into a relative label like "2h ago" or "Yesterday".
  String _relativeTime(String? isoString) {
    if (isoString == null || isoString.isEmpty) return '';
    try {
      final dt = DateTime.parse(isoString);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays == 1) return 'Yesterday';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.month}/${dt.day}';
    } catch (_) {
      return '';
    }
  }

  /// Build a subtitle string from duration + peak heart rate.
  String _activitySubtitle(Map<String, dynamic> a) {
    final parts = <String>[];
    final dur = a['duration_minutes'];
    if (dur != null) parts.add('$dur min');
    final peak = a['peak_heart_rate'];
    if (peak != null) parts.add('Peak $peak BPM');
    if (parts.isEmpty) {
      final status = a['status'];
      return status != null ? status.toString() : 'Session';
    }
    return parts.join(' • ');
  }

  // ------------------------------------------------------------------
  // Rehab Program card — only visible when user.rehab_phase != 'not_in_rehab'
  // ------------------------------------------------------------------
  Widget _buildRehabCard(Map<String, dynamic> user) {
    final rehabPhase = user['rehab_phase'] as String? ?? 'not_in_rehab';
    if (rehabPhase == 'not_in_rehab') return const SizedBox.shrink();

    return FutureBuilder<Map<String, dynamic>>(
      future: widget.apiClient.getRehabProgram().catchError((e) => <String, dynamic>{}),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(
            padding: EdgeInsets.only(bottom: 24),
            child: SizedBox(height: 80, child: Center(child: CircularProgressIndicator(strokeWidth: 2))),
          );
        }

        final data = snapshot.data;
        if (data == null || data.isEmpty) return const SizedBox.shrink();

        final progress = data['progress_summary'] as Map<String, dynamic>?;
        final programType = data['program_type'] as String? ?? '';
        final status = data['status'] as String? ?? 'active';

        final currentWeek = progress?['current_week'] as int? ?? 1;
        final sessionsThisWeek = progress?['sessions_completed_this_week'] as int? ?? 0;
        final sessionsRequired = progress?['sessions_required_this_week'] as int? ?? 3;

        final isPhase2 = programType == 'phase_2_light';
        final label = isPhase2 ? 'Phase II Rehab' : 'Phase III';
        final isCompleted = status == 'completed';

        return Padding(
          padding: const EdgeInsets.only(bottom: 24),
          child: GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RehabProgramScreen(apiClient: widget.apiClient),
                ),
              ).then((_) => _loadData());
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isCompleted
                      ? [AdaptivColors.stable, AdaptivColors.stable.withOpacity(0.8)]
                      : [AdaptivColors.primary, AdaptivColors.primaryDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      isCompleted ? Icons.emoji_events : Icons.fitness_center,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'My Rehab Program',
                          style: GoogleFonts.dmSans(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          isCompleted
                              ? '$label — completed'
                              : '$label • Week $currentWeek • $sessionsThisWeek of $sessionsRequired today',
                          style: GoogleFonts.dmSans(fontSize: 13, color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.white70),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildRecentActivity() {
    return FutureBuilder<List<dynamic>>(
      future: _activitiesFuture,
      builder: (context, snapshot) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Recent Activity',
                  style: AdaptivTypography.subtitle1.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(),
                GestureDetector(
                  onTap: _navigateToHealth,
                  child: Text(
                    'See All',
                    style: AdaptivTypography.label.copyWith(
                      color: AdaptivColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (snapshot.connectionState == ConnectionState.waiting)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              )
            else if (snapshot.hasError ||
                !snapshot.hasData ||
                snapshot.data!.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    'No recent activity yet',
                    style: AdaptivTypography.caption.copyWith(
                      color: AdaptivColors.text600,
                    ),
                  ),
                ),
              )
            else
              ...snapshot.data!.map((item) {
                final a = item as Map<String, dynamic>;
                final type = a['activity_type'] as String?;
                return _buildActivityItem(
                  imagePath: _activityImage(type),
                  icon: _activityIcon(type),
                  title: (type ?? 'Activity')
                      .replaceAll('_', ' ')
                      .split(' ')
                      .map((w) => w.isNotEmpty
                          ? '${w[0].toUpperCase()}${w.substring(1)}'
                          : '')
                      .join(' '),
                  subtitle: _activitySubtitle(a),
                  time: _relativeTime(
                      a['start_time']?.toString() ?? ''),
                  color: _activityColor(type),
                );
              }),
          ],
        );
      },
    );
  }

  Widget _buildActivityItem({
    String? imagePath,
    required IconData icon,
    required String title,
    required String subtitle,
    required String time,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.border300),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: imagePath != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.asset(
                      imagePath,
                      width: 20,
                      height: 20,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) => Icon(icon, color: color, size: 20),
                    ),
                  )
                : Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AdaptivTypography.body.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: AdaptivTypography.caption.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
              ],
            ),
          ),
          Text(
            time,
            style: AdaptivTypography.caption,
          ),
        ],
      ),
    );
  }

  Widget _buildHeartRateSparkline() {
    return FutureBuilder<List<dynamic>>(
      future: _vitalHistoryFuture,
      builder: (context, snapshot) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.9),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AdaptivColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.show_chart,
                        color: AdaptivColors.primary,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'Heart Rate Today',
                      style: AdaptivTypography.cardTitle.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // ValueListenableBuilder re-renders the chart when new mock
                // readings arrive, without rebuilding the whole page.
                ValueListenableBuilder<List<VitalReading>>(
                  valueListenable: _vitalsHistoryNotifier,
                  builder: (context, _, __) => SizedBox(
                    height: 100,
                    child: _buildSparklineContent(snapshot),
                  ),
                ),
                const SizedBox(height: 12),
                _buildSparklineTimeLabels(snapshot),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSparklineContent(AsyncSnapshot<List<dynamic>> snapshot) {
    if (snapshot.connectionState == ConnectionState.waiting) {
      return Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AdaptivColors.primary.withOpacity(0.1),
              AdaptivColors.primary.withOpacity(0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }

    if (snapshot.hasError || !snapshot.hasData) {
      if (_vitalsHistoryNotifier.value.isNotEmpty) {
        final dataPoints = <FlSpot>[];
        for (int i = 0; i < _vitalsHistoryNotifier.value.length; i++) {
          dataPoints.add(FlSpot(i.toDouble(), _vitalsHistoryNotifier.value[i].heartRate.toDouble()));
        }
        return _buildSparklineChart(dataPoints);
      }
      return Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AdaptivColors.primary.withOpacity(0.1),
              AdaptivColors.primary.withOpacity(0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'No heart rate data yet',
            style: AdaptivTypography.caption.copyWith(
              color: AdaptivColors.text600,
            ),
          ),
        ),
      );
    }

    final vitals = snapshot.data!;
    if (vitals.isEmpty) {
      if (_vitalsHistoryNotifier.value.isNotEmpty) {
        final dataPoints = <FlSpot>[];
        for (int i = 0; i < _vitalsHistoryNotifier.value.length; i++) {
          dataPoints.add(FlSpot(i.toDouble(), _vitalsHistoryNotifier.value[i].heartRate.toDouble()));
        }
        return _buildSparklineChart(dataPoints);
      }
      return Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AdaptivColors.primary.withOpacity(0.1),
              AdaptivColors.primary.withOpacity(0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'No heart rate data yet',
            style: AdaptivTypography.caption.copyWith(
              color: AdaptivColors.text600,
            ),
          ),
        ),
      );
    }

    // Extract heart rate data points (timestamp, heart_rate)
    final dataPoints = <FlSpot>[];
    for (int i = 0; i < vitals.length && i < 50; i++) {
      final vital = vitals[i] as Map<String, dynamic>;
      final hr = vital['heart_rate'] as int?;
      if (hr != null && hr > 0) {
        dataPoints.add(FlSpot(i.toDouble(), hr.toDouble()));
      }
    }

    if (dataPoints.isEmpty) {
      if (_vitalsHistoryNotifier.value.isNotEmpty) {
        final fallbackPoints = <FlSpot>[];
        for (int i = 0; i < _vitalsHistoryNotifier.value.length; i++) {
          fallbackPoints.add(FlSpot(i.toDouble(), _vitalsHistoryNotifier.value[i].heartRate.toDouble()));
        }
        return _buildSparklineChart(fallbackPoints);
      }
      return Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AdaptivColors.primary.withOpacity(0.1),
              AdaptivColors.primary.withOpacity(0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'No heart rate data yet',
            style: AdaptivTypography.caption.copyWith(
              color: AdaptivColors.text600,
            ),
          ),
        ),
      );
    }

    // Reverse to show oldest to newest (left to right)
    final reversedPoints = dataPoints.reversed.toList();

    return _buildSparklineChart(reversedPoints);
  }

  Widget _buildSparklineChart(List<FlSpot> points) {
    final hrValues = points.map((p) => p.y).toList();
    final minHR = hrValues.reduce((a, b) => a < b ? a : b);
    final maxHR = hrValues.reduce((a, b) => a > b ? a : b);
    final padding = (maxHR - minHR) * 0.2;

    return Padding(
      padding: const EdgeInsets.only(right: 8, top: 8, bottom: 4),
      child: LineChart(
        LineChartData(
          minY: (minHR - padding).clamp(40, 200),
          maxY: (maxHR + padding).clamp(60, 220),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: 20,
            getDrawingHorizontalLine: (value) {
              return FlLine(
                color: AdaptivColors.border300.withOpacity(0.3),
                strokeWidth: 1,
              );
            },
          ),
          titlesData: FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  return LineTooltipItem(
                    '${spot.y.toInt()} BPM',
                    const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  );
                }).toList();
              },
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: points,
              isCurved: true,
              curveSmoothness: 0.3,
              color: AdaptivColors.primary,
              barWidth: 2,
              isStrokeCapRound: true,
              dotData: FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AdaptivColors.primary.withOpacity(0.3),
                    AdaptivColors.primary.withOpacity(0.05),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSparklineTimeLabels(AsyncSnapshot<List<dynamic>> snapshot) {
    if (!snapshot.hasData || snapshot.data!.isEmpty) {
      if (_vitalsHistoryNotifier.value.isNotEmpty) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Sim start', style: AdaptivTypography.caption),
            Text('Live', style: AdaptivTypography.caption),
            Text(
              'Now',
              style: AdaptivTypography.caption.copyWith(
                fontWeight: FontWeight.w600,
                color: AdaptivColors.primary,
              ),
            ),
          ],
        );
      }
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('24h ago', style: AdaptivTypography.caption),
          Text('12h ago', style: AdaptivTypography.caption),
          Text(
            'Now',
            style: AdaptivTypography.caption.copyWith(
              fontWeight: FontWeight.w600,
              color: AdaptivColors.primary,
            ),
          ),
        ],
      );
    }

    final vitals = snapshot.data!;
    if (vitals.isEmpty) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('24h ago', style: AdaptivTypography.caption),
          Text('12h ago', style: AdaptivTypography.caption),
          Text(
            'Now',
            style: AdaptivTypography.caption.copyWith(
              fontWeight: FontWeight.w600,
              color: AdaptivColors.primary,
            ),
          ),
        ],
      );
    }

    // Get oldest timestamp
    String oldestLabel = '24h ago';
    if (vitals.isNotEmpty) {
      try {
        final oldest = vitals.last as Map<String, dynamic>;
        final timestamp = oldest['timestamp'] as String?;
        if (timestamp != null) {
          final dt = DateTime.parse(timestamp);
          final diff = DateTime.now().difference(dt);
          if (diff.inHours < 1) {
            oldestLabel = '${diff.inMinutes}m ago';
          } else if (diff.inHours < 24) {
            oldestLabel = '${diff.inHours}h ago';
          } else {
            oldestLabel = '${diff.inDays}d ago';
          }
        }
      } catch (e) {
        if (kDebugMode) {
          debugPrint('Error in _buildTimelineLabels: $e');
        }
      }
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(oldestLabel, style: AdaptivTypography.caption),
        Text('', style: AdaptivTypography.caption), // Middle spacer
        Text(
          'Now',
          style: AdaptivTypography.caption.copyWith(
            fontWeight: FontWeight.w600,
            color: AdaptivColors.primary,
          ),
        ),
      ],
    );
  }

  Widget _buildRecommendationCard(String riskLevel) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            'Recommended For You',
            style: AdaptivTypography.subtitle1.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        FutureBuilder<Map<String, dynamic>>(
          future: _recommendationFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AdaptivColors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AdaptivColors.border300),
                ),
                child: Text(
                  'Loading recommendation...',
                  style: AdaptivTypography.body.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
              );
            }

            final hasError = snapshot.hasError || snapshot.data == null;
            final recommendation = snapshot.data ?? <String, dynamic>{};

            if (hasError) {
              final isHighRisk = riskLevel.toLowerCase() == 'high';
              final isSimulatorRunning = _mockVitalsService?.isRunning ?? false;
              return CompactRecommendationCard(
                activityType: isHighRisk ? ActivityType.meditation : ActivityType.walking,
                title: isHighRisk ? 'Rest & Recovery' : 'Steady Movement',
                duration: Duration(minutes: isHighRisk ? 15 : 30),
                targetHRZone: isHighRisk ? HRZone.resting : HRZone.light,
                onTap: () {
                  if (isSimulatorRunning) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Simulator mode is active. Opening Fitness tab.'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                  setState(() => _selectedIndex = 1);
                },
              );
            }

            final activityType = _mapActivityType(
              recommendation['suggested_activity'] ?? recommendation['activity_type'],
            );
            final durationMinutes = _safeToInt(recommendation['duration_minutes'], 20);
            final confidence = _safeToDouble(recommendation['confidence_score'], 0.85);

            return CompactRecommendationCard(
              activityType: activityType,
              title: (recommendation['title'] ?? 'Today\'s Recommendation').toString(),
              duration: Duration(minutes: durationMinutes > 0 ? durationMinutes : 20),
              targetHRZone: _mapIntensityToHRZone(recommendation['intensity_level']),
              onTap: () {
                setState(() => _selectedIndex = 1);
              },
            );
          },
        ),
      ],
    );
  }
  //parsing helpers so Home screen can safely read numbers from the backend response without crashing.
  int _safeToInt(dynamic value, int fallback) {
    if (value == null) return fallback;
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) {
      final parsed = int.tryParse(value);
      return parsed ?? fallback;
    }
    return fallback;
  }

  int _safeBloodPressure(dynamic bpObject, String key, int fallback) {
    if (bpObject == null) return fallback;
    if (bpObject is Map<String, dynamic>) {
      return _safeToInt(bpObject[key], fallback);
    }
    return fallback;
  }

  double _safeToDouble(dynamic value, double fallback) {
    if (value == null) return fallback;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value);
      return parsed ?? fallback;
    }
    return fallback;
  }

  ActivityType _mapActivityType(dynamic rawValue) {
    final value = (rawValue ?? '').toString().toLowerCase();
    if (value.contains('walk')) return ActivityType.walking;
    if (value.contains('run')) return ActivityType.running;
    if (value.contains('cycl')) return ActivityType.cycling;
    if (value.contains('swim')) return ActivityType.swimming;
    if (value.contains('yoga')) return ActivityType.yoga;
    if (value.contains('strength')) return ActivityType.strength;
    if (value.contains('hiit') || value.contains('interval')) return ActivityType.hiit;
    if (value.contains('stretch')) return ActivityType.stretching;
    if (value.contains('meditat') || value.contains('breath') || value.contains('rest')) {
      return ActivityType.meditation;
    }
    return ActivityType.walking;
  }

  HRZone _mapIntensityToHRZone(dynamic rawValue) {
    final value = (rawValue ?? '').toString().toLowerCase();
    switch (value) {
      case 'very_high':
      case 'maximum':
        return HRZone.maximum;
      case 'high':
      case 'hard':
        return HRZone.hard;
      case 'moderate':
        return HRZone.moderate;
      case 'low':
      case 'light':
        return HRZone.light;
      default:
        return HRZone.light;
    }
  }

}
