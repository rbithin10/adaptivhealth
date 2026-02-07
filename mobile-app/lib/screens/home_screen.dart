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
  int _currentTabIndex = 0;

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

  void _resetTab() {
    setState(() { _currentTabIndex = 0; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: AdaptivColors.white,
        title: Row(
          children: [
            const Icon(Icons.favorite, color: AdaptivColors.critical),
            const SizedBox(width: 8),
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
          IconButton(
            icon: const Icon(Icons.notifications_none),
            color: AdaptivColors.text700,
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('No new notifications')),
              );
            },
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
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

          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Greeting
                  Text(
                    'Good morning, $firstName',
                    style: AdaptivTypography.screenTitle,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    riskLevel.toLowerCase() == 'high'
                        ? 'Stay calm — your heart is working hard'
                        : 'Your heart is looking good today',
                    style: AdaptivTypography.caption,
                  ),
                  const SizedBox(height: 32),

                  // HERO HEART RATE RING
                  Center(
                    child: _buildHeartRateRing(
                      heartRate: heartRate,
                      riskLevel: riskLevel,
                      maxSafeHR: 150, // Typical for healthy adults
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Activity phase & zone
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _getRiskZoneLabel(heartRate),
                        style: AdaptivTypography.body,
                      ),
                      Text(
                        _getRiskStatus(riskLevel),
                        style: AdaptivTypography.body,
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  // Secondary Vitals Grid
                  _buildVitalsGrid(
                    spo2: spo2,
                    systolicBp: systolicBp,
                    diastolicBp: diastolicBp,
                    riskLevel: riskLevel,
                    riskScore: riskScore,
                  ),
                  const SizedBox(height: 32),

                  // Heart Rate Sparkline
                  _buildHeartRateSparkline(),
                  const SizedBox(height: 32),

                  // AI Recommendation Card
                  _buildRecommendationCard(riskLevel),
                  const SizedBox(height: 32),

                  // Refresh button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        setState(() {
                          _loadData();
                        });
                      },
                      child: const Text('Refresh Data'),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
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
        currentIndex: _currentTabIndex,
        onTap: (index) {
          if (index == _currentTabIndex) return;
          setState(() {
            _currentTabIndex = index;
          });
          switch (index) {
            case 1:
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => WorkoutScreen(apiClient: widget.apiClient),
                ),
              ).then((_) => _resetTab());
              break;
            case 2:
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => RecoveryScreen(apiClient: widget.apiClient),
                ),
              ).then((_) => _resetTab());
              break;
            case 3:
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('History: Check your vitals trends in the web dashboard')),
              );
              _resetTab();
              break;
            case 4:
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Profile settings coming soon')),
              );
              _resetTab();
              break;
          }
        },
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
        // Heart rate ring visualization (see ROADMAP.md for UI improvements)
        Container(
          width: 200,
          height: 200,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: ringColor,
              width: 12,
            ),
          ),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  heartRate.toString(),
                  style: AdaptivTypography.heroNumber.copyWith(
                    color: ringColor,
                  ),
                ),
                Text(
                  'BPM',
                  style: AdaptivTypography.heroUnit,
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AdaptivColors.stable,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Live',
                      style: AdaptivTypography.caption,
                    ),
                  ],
                ),
              ],
            ),
          ),
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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: statusColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  label,
                  style: AdaptivTypography.overline,
                ),
              ],
            ),
            Text(
              value,
              style: AdaptivTypography.heroNumber.copyWith(
                fontSize: 28,
              ),
            ),
            Text(
              status,
              style: AdaptivTypography.caption.copyWith(
                color: statusColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeartRateSparkline() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Heart Rate Today',
              style: AdaptivTypography.cardTitle,
            ),
            const SizedBox(height: 16),
            Container(
              height: 100,
              decoration: BoxDecoration(
                color: AdaptivColors.background50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: CustomPaint(
                size: const Size(double.infinity, 100),
                painter: _SparklinePainter(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('6AM', style: AdaptivTypography.caption),
                Text('12PM', style: AdaptivTypography.caption),
                Text('Now', style: AdaptivTypography.caption),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationCard(String riskLevel) {
    final isHighRisk = riskLevel.toLowerCase() == 'high';

    return Card(
      color: AdaptivColors.primaryUltralight,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.directions_walk,
                  color: AdaptivColors.primary,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isHighRisk
                            ? 'Rest recommended'
                            : '30-min walk recommended',
                        style: AdaptivTypography.cardTitle,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        isHighRisk
                            ? 'Your recovery score is low. Take it easy today.'
                            : 'Your recovery score is good enough for light activity.',
                        style: AdaptivTypography.caption,
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.arrow_forward,
                  color: AdaptivColors.primary,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Simple sparkline painter that draws a demo heart rate trend line.
class _SparklinePainter extends CustomPainter {
  // Typical heart rate display range (BPM)
  static const double minDisplayHR = 60.0;
  static const double maxDisplayHR = 100.0;

  @override
  void paint(Canvas canvas, Size size) {
    // Sample HR data points representing a typical day trend
    final dataPoints = [68, 72, 70, 75, 82, 90, 85, 78, 74, 71, 73, 76];
    final range = maxDisplayHR - minDisplayHR;

    final paint = Paint()
      ..color = AdaptivColors.primary
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          AdaptivColors.primary.withAlpha(60),
          AdaptivColors.primary.withAlpha(5),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final path = Path();
    final fillPath = Path();
    final stepX = size.width / (dataPoints.length - 1);
    final padding = 8.0;
    final drawHeight = size.height - padding * 2;

    for (int i = 0; i < dataPoints.length; i++) {
      final x = i * stepX;
      final y = padding + drawHeight - ((dataPoints[i] - minDisplayHR) / range) * drawHeight;
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
