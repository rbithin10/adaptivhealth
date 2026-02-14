/*
Workout screen.

The app shows safe heart-rate zones and asks how the user feels.
When the user taps "Start Workout", we create a workout session on the server.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

class WorkoutScreen extends StatefulWidget {
  final ApiClient apiClient;

  const WorkoutScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<WorkoutScreen> createState() => _WorkoutScreenState();
}

class _WorkoutScreenState extends State<WorkoutScreen> {
  String _selectedWellness = 'good'; // good, okay, tired
  bool _isStartingWorkout = false;

  // Calculate target zones based on age (assume 35-year-old by default)
  final int age = 35;
  late int maxHR;
  late int warmupMin;
  late int warmupMax;
  late int cardioMin;
  late int cardioMax;
  late int recoveryMin;
  late int recoveryMax;

  @override
  void initState() {
    super.initState();
    _calculateZones();
  }

  void _calculateZones() {
    // Basic heart-rate zone math using the user's age.
    maxHR = 220 - age;
    warmupMin = (maxHR * 0.5).toInt();
    warmupMax = (maxHR * 0.65).toInt();
    cardioMin = (maxHR * 0.65).toInt();
    cardioMax = (maxHR * 0.85).toInt();
    recoveryMin = (maxHR * 0.3).toInt();
    recoveryMax = (maxHR * 0.5).toInt();
  }

  void _startWorkout() async {
    // Tell the server we are starting a workout.
    setState(() {
      _isStartingWorkout = true;
    });

    try {
      // Call API to start session
      final response = await widget.apiClient.startSession(
        sessionType: 'workout',
        targetDuration: 30, // Default 30 minute workout
      );

      if (mounted) {
        // Navigate to active workout screen
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ActiveWorkoutScreen(
              apiClient: widget.apiClient,
              sessionId: response['session_id'],
              wellnessLevel: _selectedWellness,
            ),
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isStartingWorkout = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error starting workout: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        elevation: 0,
        backgroundColor: AdaptivColors.white,
        title: Text(
          'Workout',
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
            image: const AssetImage('assets/images/workout_bg.png'),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(
              Colors.white.withOpacity(0.9),
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
              // Wellness Check Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'How are you feeling?',
                        style: AdaptivTypography.sectionTitle,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'We\'ll adjust your workout intensity based on your wellness level',
                        style: AdaptivTypography.caption,
                      ),
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _buildWellnessOption(
                            emoji: '😄',
                            label: 'Good',
                            value: 'good',
                          ),
                          _buildWellnessOption(
                            emoji: '😐',
                            label: 'Okay',
                            value: 'okay',
                          ),
                          _buildWellnessOption(
                            emoji: '😴',
                            label: 'Tired',
                            value: 'tired',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Exercise Phases
              Text(
                'Your Workout Plan',
                style: AdaptivTypography.sectionTitle,
              ),
              const SizedBox(height: 12),

              _buildPhaseCard(
                phase: 'Warm-up',
                icon: Icons.local_fire_department,
                duration: '5-10 min',
                hrMin: warmupMin,
                hrMax: warmupMax,
                description: 'Prepare your body for exercise',
              ),
              const SizedBox(height: 12),

              _buildPhaseCard(
                phase: 'Cardio',
                icon: Icons.trending_up,
                duration: '20-30 min',
                hrMin: cardioMin,
                hrMax: cardioMax,
                description: 'Main exercise at comfortable intensity',
              ),
              const SizedBox(height: 12),

              _buildPhaseCard(
                phase: 'Cool-down',
                icon: Icons.trending_down,
                duration: '5-10 min',
                hrMin: recoveryMin,
                hrMax: recoveryMax,
                description: 'Let your heart rate return to normal',
              ),
              const SizedBox(height: 24),

              // Max HR Info
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AdaptivColors.primaryUltralight,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AdaptivColors.primaryLight,
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.info,
                      color: AdaptivColors.primary,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Your Max Heart Rate',
                            style: AdaptivTypography.cardTitle,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '$maxHR BPM (age-based estimate)',
                            style: AdaptivTypography.caption,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Start Workout Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isStartingWorkout ? null : _startWorkout,
                  icon: const Icon(Icons.play_arrow),
                  label: _isStartingWorkout
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
                      : const Text('Start Workout'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: AdaptivColors.stable,
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
        ),
      ),
    );
  }

  Widget _buildWellnessOption({
    required String emoji,
    required String label,
    required String value,
  }) {
    final isSelected = _selectedWellness == value;

    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedWellness = value;
        });
      },
      child: Column(
        children: [
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isSelected
                  ? AdaptivColors.primaryLight
                  : AdaptivColors.background50,
              border: isSelected
                  ? Border.all(
                      color: AdaptivColors.primary,
                      width: 3,
                    )
                  : null,
            ),
            child: Center(
              child: Text(emoji, style: const TextStyle(fontSize: 24)),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: AdaptivTypography.caption.copyWith(
              color: isSelected
                  ? AdaptivColors.primary
                  : AdaptivColors.text600,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPhaseCard({
    required String phase,
    required IconData icon,
    required String duration,
    required int hrMin,
    required int hrMax,
    required String description,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: AdaptivColors.primary),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      phase,
                      style: AdaptivTypography.cardTitle,
                    ),
                    Text(
                      duration,
                      style: AdaptivTypography.caption,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              description,
              style: AdaptivTypography.body,
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AdaptivColors.background50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Target HR Zone',
                        style: AdaptivTypography.overline,
                      ),
                      Text(
                        '$hrMin - $hrMax BPM',
                        style: AdaptivTypography.body.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AdaptivColors.primary,
                        ),
                      ),
                    ],
                  ),
                  const Icon(
                    Icons.favorite,
                    color: AdaptivColors.critical,
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

// Active Workout Screen - Real-time HR monitoring during exercise
class ActiveWorkoutScreen extends StatefulWidget {
  final ApiClient apiClient;
  final String sessionId;
  final String wellnessLevel;

  const ActiveWorkoutScreen({
    super.key,
    required this.apiClient,
    required this.sessionId,
    required this.wellnessLevel,
  });

  @override
  State<ActiveWorkoutScreen> createState() => _ActiveWorkoutScreenState();
}

class _ActiveWorkoutScreenState extends State<ActiveWorkoutScreen> {
  late Stream<Map<String, dynamic>> _vitalStream;
  int _currentHR = 0;
  int _maxHR = 0;
  bool _isEndingWorkout = false;

  @override
  void initState() {
    super.initState();
    // Simulate live heart rate data
    _simulateLiveHR();
  }

  void _simulateLiveHR() {
    // In production, this would be a WebSocket stream
    _currentHR = 80;
    _maxHR = 150;
  }

  void _endWorkout() async {
    setState(() {
      _isEndingWorkout = true;
    });

    try {
      await widget.apiClient.endSession(
        sessionId: int.parse(widget.sessionId),
        avgHeartRate: _currentHR,
        maxHeartRate: _maxHR,
      );

      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Workout saved successfully!')),
        );
      }
    } catch (e) {
      setState(() {
        _isEndingWorkout = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error ending workout: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final fillPercentage = (_currentHR / _maxHR).clamp(0.0, 1.0);

    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                // Timer
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Active Workout',
                        style: GoogleFonts.dmSans(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: AdaptivColors.white,
                        ),
                      ),
                      Text(
                        '12:34',
                        style: GoogleFonts.dmSans(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: AdaptivColors.white,
                        ),
                      ),
                    ],
                  ),
                ),

                // Giant BPM Display
                const SizedBox(height: 40),
                Center(
                  child: Column(
                    children: [
                      Text(
                        _currentHR.toString(),
                        style: GoogleFonts.dmSans(
                          fontSize: 120,
                          fontWeight: FontWeight.w700,
                          color: AdaptivColors.critical,
                        ),
                      ),
                      Text(
                        'BPM',
                        style: GoogleFonts.dmSans(
                          fontSize: 24,
                          fontWeight: FontWeight.w400,
                          color: AdaptivColors.white,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 40),

                // Zone Bar
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 40),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Workout Zone',
                        style: GoogleFonts.dmSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w400,
                          color: AdaptivColors.white,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: LinearProgressIndicator(
                          value: fillPercentage,
                          minHeight: 40,
                          backgroundColor: AdaptivColors.neutral400,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            fillPercentage > 0.85
                                ? AdaptivColors.warning
                                : fillPercentage > 0.65
                                ? AdaptivColors.primary
                                : AdaptivColors.stable,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                const Spacer(),

                // End Workout Button
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isEndingWorkout ? null : _endWorkout,
                      icon: const Icon(Icons.stop),
                      label: _isEndingWorkout
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Text('End Workout'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        backgroundColor: AdaptivColors.critical,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
