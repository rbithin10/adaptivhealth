/*
Home screen.

This shows the latest heart data, a risk label, and a short tip.
If the server is slow or down, we show safe demo values instead of a blank screen.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../widgets/widgets.dart';
import 'fitness_plans_screen.dart';
import 'recovery_screen.dart';
import 'health_screen.dart';
import 'profile_screen.dart';
import 'nutrition_screen.dart';
import 'doctor_messaging_screen.dart';
// Note: ChatbotScreen removed - AI Coach is now a floating widget (FloatingChatbot)

class HomeScreen extends StatefulWidget {
  final ApiClient apiClient;

  const HomeScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<Map<String, dynamic>> _vitalsFuture;
  late Future<Map<String, dynamic>> _riskFuture;
  late Future<Map<String, dynamic>> _userFuture;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _userFuture = widget.apiClient.getCurrentUser().catchError(
      (e) => {
        'name': 'Patient',
        'age': 35,
      },
    );

    _vitalsFuture = widget.apiClient.getLatestVitals();

    _riskFuture = widget.apiClient.getLatestRiskAssessment().catchError(
      (e) => {
        'risk_level': 'low',
        'risk_score': 0.23,
      },
    );
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
    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.white,
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
                // TODO: Navigate to notifications
              },
            ),
          ),
        ],
      ),
      body: _getSelectedScreen(),
      // Floating AI Health Coach - always accessible
      floatingActionButton: const FloatingChatbot(),
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
        return const NutritionScreen();
      case 3:
        return const DoctorMessagingScreen();
      case 4:
        return ProfileScreen(apiClient: widget.apiClient);
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
      future: Future.wait([_userFuture, _vitalsFuture, _riskFuture])
          .then((results) => ({
            'user': results[0],
            'vitals': results[1],
            'risk': results[2],
          })),
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
        final heartRate = _safeToInt(vitals['heart_rate'], 72);
        final spo2 = _safeToInt(vitals['spo2'], 98);
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
        final riskScore = risk['risk_score'] ?? 0.23;

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
                  const SizedBox(height: 24),

                // HERO HEART RATE RING - Enhanced design
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
                          riskLevel: riskLevel,
                          maxSafeHR: 150,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Activity phase & zone
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildStatusBadge(
                            _getRiskZoneLabel(heartRate),
                            Icons.directions_run,
                            AdaptivColors.primary,
                          ),
                          _buildStatusBadge(
                            _getRiskStatus(riskLevel),
                            Icons.shield_outlined,
                            AdaptivColors.getRiskColor(riskLevel),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Secondary Vitals Grid
                _buildVitalsGrid(
                  spo2: spo2,
                  systolicBp: systolicBp,
                  diastolicBp: diastolicBp,
                  riskLevel: riskLevel,
                  riskScore: riskScore,
                ),
                const SizedBox(height: 24),

                // Quick Actions
                _buildQuickActions(),
                const SizedBox(height: 24),

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
    required String riskLevel,
    required double riskScore,
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
        const SizedBox(height: 16),
        // Risk badge row
        Row(
          children: [
            RiskBadge(
              level: _getRiskLevel(riskLevel),
              size: RiskBadgeSize.medium,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'CV Score: ${(riskScore * 100).toInt()}',
                style: AdaptivTypography.metricValueSmall.copyWith(
                  color: AdaptivColors.text600,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  RiskLevel _getRiskLevel(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'critical':
        return RiskLevel.critical;
      case 'high':
        return RiskLevel.high;
      case 'elevated':
        return RiskLevel.elevated;
      case 'moderate':
        return RiskLevel.moderate;
      case 'low':
        return RiskLevel.low;
      default:
        return RiskLevel.minimal;
    }
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

  Widget _buildRecentActivity() {
    // Demo recent activity data
    final recentActivities = [
      {
        'icon': Icons.directions_walk,
        'title': 'Morning Walk',
        'subtitle': '30 min • 2.1 km',
        'time': '2h ago',
        'color': AdaptivColors.stable,
      },
      {
        'icon': Icons.monitor_heart,
        'title': 'Heart Rate Check',
        'subtitle': '72 BPM - Normal',
        'time': '4h ago',
        'color': AdaptivColors.primary,
      },
      {
        'icon': Icons.spa,
        'title': 'Breathing Exercise',
        'subtitle': '5 min session',
        'time': 'Yesterday',
        'color': const Color(0xFF9C27B0),
      },
    ];

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
              onTap: _navigateToHealth, // Opens Health screen
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
        ...recentActivities.map((activity) => _buildActivityItem(
          icon: activity['icon'] as IconData,
          title: activity['title'] as String,
          subtitle: activity['subtitle'] as String,
          time: activity['time'] as String,
          color: activity['color'] as Color,
        )),
      ],
    );
  }

  Widget _buildActivityItem({
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
            child: Icon(icon, color: color, size: 20),
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
            Container(
              height: 100,
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
                  'Trend chart - coming soon',
                  style: AdaptivTypography.caption.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('6AM', style: AdaptivTypography.caption),
                Text('12PM', style: AdaptivTypography.caption),
                Text('Now', style: AdaptivTypography.caption.copyWith(
                  fontWeight: FontWeight.w600,
                  color: AdaptivColors.primary,
                )),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationCard(String riskLevel) {
    final isHighRisk = riskLevel.toLowerCase() == 'high';

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
        RecommendationCard(
          activityType: isHighRisk ? ActivityType.meditation : ActivityType.walking,
          title: isHighRisk ? 'Rest & Recovery' : 'Morning Walk',
          description: isHighRisk
              ? 'Your recovery score is low. Take it easy today.'
              : 'Light cardio to maintain your heart health.',
          duration: Duration(minutes: isHighRisk ? 15 : 30),
          targetHRZone: isHighRisk ? HRZone.resting : HRZone.light,
          confidence: 0.87,
          isPriority: true,
          onStart: () {
            // Navigate to workout
          },
          onDismiss: () {
            // Dismiss recommendation
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

}
