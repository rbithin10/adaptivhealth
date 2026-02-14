/*
Recovery screen.

This page helps the user cool down after a workout.
It shows a recovery score and a simple breathing guide.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

class RecoveryScreen extends StatefulWidget {
  final ApiClient apiClient;

  const RecoveryScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<RecoveryScreen> createState() => _RecoveryScreenState();
}

class _RecoveryScreenState extends State<RecoveryScreen>
    with SingleTickerProviderStateMixin {
  late Future<Map<String, dynamic>> _sessionFuture;
  late AnimationController _breathingController;

  @override
  void initState() {
    super.initState();
    _sessionFuture = _loadSessionData();

    // Breathing animation (slow in, hold, slow out).
    _breathingController = AnimationController(
      duration: const Duration(seconds: 9),
      vsync: this,
    );
  }

  Future<Map<String, dynamic>> _loadSessionData() {
    // Demo data for now. Replace with real API data later.
    return Future.delayed(
      const Duration(milliseconds: 500),
      () => {
        'recovery_score': 78,
        'session_duration': 28,
        'avg_heart_rate': 120,
        'peak_heart_rate': 165,
        'recovery_time': 12,
        'calories_burned': 245,
      },
    );
  }

  @override
  void dispose() {
    // Clean up the animation controller.
    _breathingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: AdaptivColors.white,
        title: Text(
          'Recovery',
          style: GoogleFonts.dmSans(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: AdaptivColors.text900,
          ),
        ),
      ),
      body: Container(
        decoration: BoxDecoration(
          image: DecorationImage(
            image: const AssetImage('assets/images/recovery_bg.png'),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(
              Colors.white.withOpacity(0.85),
              BlendMode.lighten,
            ),
          ),
        ),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _sessionFuture,
          builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (!snapshot.hasData) {
            return Center(child: Text('Error: ${snapshot.error}'));
          }

          final data = snapshot.data!;
          final recoveryScore = data['recovery_score'] as int;
          final sessionDuration = data['session_duration'] as int;
          final avgHR = data['avg_heart_rate'] as int;
          final peakHR = data['peak_heart_rate'] as int;
          final recoveryTime = data['recovery_time'] as int;
          final caloriesBurned = data['calories_burned'] as int;

          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Recovery Score Ring
                  Center(
                    child: _buildRecoveryScoreRing(recoveryScore),
                  ),
                  const SizedBox(height: 32),

                  // Session Summary
                  Text(
                    'Session Summary',
                    style: AdaptivTypography.sectionTitle,
                  ),
                  const SizedBox(height: 12),

                  GridView.count(
                    crossAxisCount: 2,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    children: [
                      _buildSummaryCard(
                        icon: Icons.timer,
                        label: 'Duration',
                        value: '$sessionDuration min',
                      ),
                      _buildSummaryCard(
                        icon: Icons.favorite,
                        label: 'Avg Heart Rate',
                        value: '$avgHR BPM',
                      ),
                      _buildSummaryCard(
                        icon: Icons.trending_up,
                        label: 'Peak Heart Rate',
                        value: '$peakHR BPM',
                      ),
                      _buildSummaryCard(
                        icon: Icons.local_fire_department,
                        label: 'Calories Burned',
                        value: '$caloriesBurned kcal',
                      ),
                      _buildSummaryCard(
                        icon: Icons.trending_down,
                        label: 'Recovery Time',
                        value: '$recoveryTime min',
                      ),
                      _buildSummaryCard(
                        icon: Icons.check_circle,
                        label: 'Recovered',
                        value: 'Yes',
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  // Breathing Exercise
                  Text(
                    'Breathing Exercise',
                    style: AdaptivTypography.sectionTitle,
                  ),
                  const SizedBox(height: 12),

                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Text(
                            ' 4-7-8 Breathing Technique',
                            style: AdaptivTypography.cardTitle,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Deep breathing activates your parasympathetic nervous system, promoting relaxation and faster recovery.',
                            style: AdaptivTypography.caption,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 32),

                          // Animated breathing circle
                          _buildBreathingCircle(),
                          const SizedBox(height: 32),

                          // Start button
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: () {
                                if (_breathingController.isAnimating) {
                                  _breathingController.stop();
                                } else {
                                  _breathingController.repeat();
                                }
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AdaptivColors.primary,
                              ),
                              child: Text(
                                _breathingController.isAnimating
                                    ? 'Stop Exercise'
                                    : 'Start Exercise',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Daily Tips
                  Text(
                    'Recovery Tips',
                    style: AdaptivTypography.sectionTitle,
                  ),
                  const SizedBox(height: 12),

                  _buildTipCard(
                    icon: Icons.water_drop,
                    title: 'Hydration',
                    description:
                        'Drink water to replenish electrolytes lost during exercise.',
                  ),
                  const SizedBox(height: 12),

                  _buildTipCard(
                    icon: Icons.restaurant,
                    title: 'Nutrition',
                    description:
                        'Eat protein and carbs within 30-60 minutes after exercise.',
                  ),
                  const SizedBox(height: 12),

                  _buildTipCard(
                    icon: Icons.nights_stay,
                    title: 'Sleep',
                    description: 'Get 7-9 hours of sleep for optimal recovery.',
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          );
        },
      ),
      ),
    );
  }

  Widget _buildRecoveryScoreRing(int score) {
    return Column(
      children: [
        Text(
          'Recovery Score',
          style: AdaptivTypography.cardTitle,
        ),
        const SizedBox(height: 20),
        Stack(
          alignment: Alignment.center,
          children: [
            // Background circle
            Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: AdaptivColors.neutral300,
                  width: 8,
                ),
              ),
            ),
            // Progress circle (simplified - using container)
            Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: score > 75
                      ? AdaptivColors.stable
                      : score > 50
                      ? AdaptivColors.warning
                      : AdaptivColors.critical,
                  width: 8,
                ),
              ),
            ),
            // Score text
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '$score/100',
                  style: AdaptivTypography.heroNumber,
                ),
                Text(
                  score > 75
                      ? 'Excellent'
                      : score > 50
                      ? 'Good'
                      : 'Needs work',
                  style: AdaptivTypography.caption,
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSummaryCard({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(
              icon,
              color: AdaptivColors.primary,
              size: 20,
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: AdaptivTypography.overline,
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: AdaptivTypography.cardTitle,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBreathingCircle() {
    return ScaleTransition(
      scale: Tween(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(
          parent: _breathingController,
          curve: Curves.easeInOut,
        ),
      ),
      child: Container(
        width: 120,
        height: 120,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AdaptivColors.primaryUltralight,
          border: Border.all(
            color: AdaptivColors.primary,
            width: 2,
          ),
        ),
        child: const Center(
          child: Icon(
            Icons.air,
            color: AdaptivColors.primary,
            size: 40,
          ),
        ),
      ),
    );
  }

  Widget _buildTipCard({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              icon,
              color: AdaptivColors.primary,
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: AdaptivTypography.cardTitle,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: AdaptivTypography.caption,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
