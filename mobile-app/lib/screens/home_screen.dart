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
import 'workout_screen.dart';
import 'recovery_screen.dart';
import 'history_screen.dart';
import 'profile_screen.dart';

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
    // Load data from the server. If anything fails, show demo values.
    _vitalsFuture = widget.apiClient.getLatestVitals().catchError(
      (e) => {
        'heart_rate': 72,
        'spo2': 98,
        'systolic_bp': 120,
        'diastolic_bp': 80,
        'timestamp': DateTime.now().toIso8601String(),
      },
    );

    _riskFuture = widget.apiClient
        .predictRisk(
          heartRate: 72,
          spo2: 98,
          systolicBp: 120,
          diastolicBp: 80,
        )
        .catchError(
          (e) => {
            'risk_level': 'low',
            'risk_score': 0.23,
          },
        );

    _userFuture = widget.apiClient.getCurrentUser().catchError(
      (e) => {
        'name': 'Patient',
        'age': 35,
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
          decoration: BoxDecoration(
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
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.fitness_center),
            label: 'Workout',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.spa),
            label: 'Recovery',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history),
            label: 'History',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
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

  Widget _getSelectedScreen() {
    switch (_selectedIndex) {
      case 0:
        return _buildHomeTab();
      case 1:
        return WorkoutScreen(apiClient: widget.apiClient);
      case 2:
        return RecoveryScreen(apiClient: widget.apiClient);
      case 3:
        return HistoryScreen(apiClient: widget.apiClient);
      case 4:
        return ProfileScreen(apiClient: widget.apiClient);
      default:
        return _buildHomeTab();
    }
  }

  Widget _buildHomeTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: Future.wait([_userFuture, _vitalsFuture, _riskFuture])
          .then((results) => {
            'user': results[0],
            'vitals': results[1],
            'risk': results[2],
          }),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        if (!snapshot.hasData) {
          return Center(
            child: Text('Error loading data: ${snapshot.error}'),
          );
        }

        final user = snapshot.data!['user'] as Map<String, dynamic>;
        final vitals = snapshot.data!['vitals'] as Map<String, dynamic>;
        final risk = snapshot.data!['risk'] as Map<String, dynamic>;

        final userName = user['name'] ?? 'Patient';
        final firstName = userName.split(' ').first;
        final heartRate = vitals['heart_rate'] ?? 72;
        final spo2 = vitals['spo2'] ?? 98;
        final systolicBp = vitals['systolic_bp'] ?? 120;
        final diastolicBp = vitals['diastolic_bp'] ?? 80;
        final riskLevel = risk['risk_level'] ?? 'low';
        final riskScore = risk['risk_score'] ?? 0.23;

        return Container(
          // Appealing gradient background for patient dashboard
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFFf0f9ff), // Very light blue
                Color(0xFFdbeafe), // Light blue
                Color(0xFFbfdbfe), // Soft blue
              ],
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
                              child: Icon(
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
    final fillPercentage = (heartRate / maxSafeHR).clamp(0.0, 1.0);
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
    return GridView.count(
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: [
        _buildVitalCard(
          icon: Icons.air,
          label: 'SpO2',
          value: '$spo2%',
          status: spo2 < 90
              ? 'Critical'
              : spo2 < 95
              ? 'Low'
              : 'Normal',
          statusColor: spo2 < 90
              ? AdaptivColors.critical
              : spo2 < 95
              ? AdaptivColors.warning
              : AdaptivColors.stable,
        ),
        _buildVitalCard(
          icon: Icons.favorite,
          label: 'Blood Pressure',
          value: '$systolicBp/$diastolicBp',
          status: systolicBp > 140
              ? 'High'
              : systolicBp > 130
              ? 'Elevated'
              : 'Normal',
          statusColor: systolicBp > 140
              ? AdaptivColors.critical
              : systolicBp > 130
              ? AdaptivColors.warning
              : AdaptivColors.stable,
        ),
        _buildVitalCard(
          icon: Icons.show_chart,
          label: 'HRV',
          value: '45ms',
          status: 'Good',
          statusColor: AdaptivColors.stable,
        ),
        _buildVitalCard(
          icon: Icons.shield,
          label: 'Risk Level',
          value: riskLevel.toUpperCase(),
          status: riskScore.toStringAsFixed(2),
          statusColor: AdaptivColors.getRiskColor(riskLevel),
        ),
      ],
    );
  }

  Widget _buildVitalCard({
    required IconData icon,
    required String label,
    required String value,
    required String status,
    required Color statusColor,
  }) {
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
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    icon,
                    color: statusColor,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    label,
                    style: AdaptivTypography.overline.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: AdaptivTypography.heroNumber.copyWith(
                fontSize: 28,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                status,
                style: AdaptivTypography.caption.copyWith(
                  color: statusColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
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
                  child: Icon(
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

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AdaptivColors.primary.withOpacity(0.15),
            AdaptivColors.primary.withOpacity(0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AdaptivColors.primary.withOpacity(0.3),
        ),
        boxShadow: [
          BoxShadow(
            color: AdaptivColors.primary.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Icon(
                isHighRisk ? Icons.bed : Icons.directions_walk,
                color: AdaptivColors.primary,
                size: 28,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isHighRisk
                        ? 'Rest recommended'
                        : '30-min walk recommended',
                    style: AdaptivTypography.cardTitle.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isHighRisk
                        ? 'Your recovery score is low. Take it easy today.'
                        : 'Your recovery score is good enough for light activity.',
                    style: AdaptivTypography.caption.copyWith(
                      color: AdaptivColors.text600,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.arrow_forward_ios,
              color: AdaptivColors.primary,
              size: 16,
            ),
          ],
        ),
      ),
    );
  }
}
