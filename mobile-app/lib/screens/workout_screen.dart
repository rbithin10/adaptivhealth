/*
Workout screen.

The app shows safe heart-rate zones and asks how the user feels.
When the user taps "Start Workout", we create a workout session on the server.
*/

import 'dart:async';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../services/edge_ai_store.dart';
import '../providers/vitals_provider.dart';
import '../models/edge_prediction.dart';
import '../widgets/ai_coach_overlay.dart';

class WorkoutScreen extends StatefulWidget {
  final ApiClient apiClient;
  final String initialExercise;

  const WorkoutScreen({
    super.key,
    required this.apiClient,
    this.initialExercise = 'walking',
  });

  @override
  State<WorkoutScreen> createState() => _WorkoutScreenState();
}

class _WorkoutScreenState extends State<WorkoutScreen> {
  String _selectedWellness = 'good'; // good, okay, tired
  String _currentExercise = 'walking';
  bool _isStartingWorkout = false;

  static const Map<String, String> _exerciseImages = {
    'walking': 'assets/exercises/walking.png',
    'light_jogging': 'assets/exercises/light_jogging.png',
    'cycling': 'assets/exercises/cycling.png',
    'swimming': 'assets/exercises/swimming.png',
    'stretching': 'assets/exercises/stretching.png',
    'yoga': 'assets/exercises/yoga.png',
    'resistance_bands': 'assets/exercises/resistance_bands.png',
    'chair_exercises': 'assets/exercises/chair_exercises.png',
    'arm_raises': 'assets/exercises/arm_raises.png',
    'leg_raises': 'assets/exercises/leg_raises.png',
    'wall_pushups': 'assets/exercises/wall_pushups.png',
    'seated_marches': 'assets/exercises/seated_marches.png',
    'balance_exercises': 'assets/exercises/balance_exercises.png',
    'cooldown_stretches': 'assets/exercises/cooldown_stretches.png',
  };

  // Calculate target zones based on age from profile.
  int _userAge = 35; // fallback: profile unavailable.
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
    _currentExercise = _exerciseImages.containsKey(widget.initialExercise)
        ? widget.initialExercise
        : 'walking';
    _calculateZones();
    _loadUserAge();
  }

  Future<void> _loadUserAge() async {
    try {
      final profile = await widget.apiClient.getCurrentUser();
      final ageFromProfile = profile['age'];

      int resolvedAge = 35; // fallback: profile unavailable.
      if (ageFromProfile is int) {
        resolvedAge = ageFromProfile;
      } else if (ageFromProfile is String) {
        resolvedAge = int.tryParse(ageFromProfile) ?? 35;
      }

      if (!mounted) return;
      setState(() {
        _userAge = resolvedAge;
        _calculateZones();
      });
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Error in _loadUserAge: $e');
      }
    }
  }

  void _calculateZones() {
    // Basic heart-rate zone math using the user's age.
    maxHR = 220 - _userAge;
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

      final sessionIdValue = response['session_id'];
      final sessionId = int.tryParse('$sessionIdValue');
      if (sessionId == null) {
        throw 'Invalid start-session response: missing session_id';
      }

      if (mounted) {
        // Navigate to active workout screen
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ActiveWorkoutScreen(
              apiClient: widget.apiClient,
              sessionId: sessionId,
              wellnessLevel: _selectedWellness,
              activityType: _currentExercise,
            ),
          ),
        );

        if (mounted) {
          setState(() {
            _isStartingWorkout = false;
          });
        }
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
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
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
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Selected Exercise:',
                    style: AdaptivTypography.sectionTitle,
                  ),
                  const SizedBox(width: 12),
                  Image.asset(
                    _exerciseImages[_currentExercise] ?? 'assets/exercises/walking.png',
                    height: 64,
                    width: 64,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) =>
                        const Icon(Icons.directions_walk, size: 64, color: AdaptivColors.primary),
                  ),
                ],
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
// Edge AI processes every heart rate reading for instant risk detection
class ActiveWorkoutScreen extends StatefulWidget {
  final ApiClient apiClient;
  final int sessionId;
  final String wellnessLevel;
  final String activityType;

  const ActiveWorkoutScreen({
    super.key,
    required this.apiClient,
    required this.sessionId,
    required this.wellnessLevel,
    this.activityType = 'walking',
  });

  @override
  State<ActiveWorkoutScreen> createState() => _ActiveWorkoutScreenState();
}

class _ActiveWorkoutScreenState extends State<ActiveWorkoutScreen> {
  static const Map<String, String> _exerciseImages = {
    'walking': 'assets/exercises/walking.png',
    'light_jogging': 'assets/exercises/light_jogging.png',
    'cycling': 'assets/exercises/cycling.png',
    'swimming': 'assets/exercises/swimming.png',
    'stretching': 'assets/exercises/stretching.png',
    'yoga': 'assets/exercises/yoga.png',
    'resistance_bands': 'assets/exercises/resistance_bands.png',
    'chair_exercises': 'assets/exercises/chair_exercises.png',
    'arm_raises': 'assets/exercises/arm_raises.png',
    'leg_raises': 'assets/exercises/leg_raises.png',
    'wall_pushups': 'assets/exercises/wall_pushups.png',
    'seated_marches': 'assets/exercises/seated_marches.png',
    'balance_exercises': 'assets/exercises/balance_exercises.png',
    'cooldown_stretches': 'assets/exercises/cooldown_stretches.png',
  };

  int _currentHR = 80;
  int _peakHR = 0;
  int _minHR = 999;
  int _maxSafeHR = 185;
  bool _isEndingWorkout = false;
  int _elapsedSeconds = 0;
  Timer? _timer;
  Timer? _hrSimTimer;

  // Live BLE/VitalsProvider subscription (used when a real device is paired)
  StreamSubscription<VitalsReading>? _vitalsSubscription;
  bool _usingLiveSource = false;

  // Edge AI state for this workout
  String _edgeRiskLevel = 'low';
  double _edgeRiskScore = 0.0;
  List<ThresholdAlert> _activeAlerts = [];
  bool _showAlertBanner = false;

  @override
  void initState() {
    super.initState();
    _loadUserProfile();
    _startWorkoutTimer();
    _startHeartRateSource();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _hrSimTimer?.cancel();
    _vitalsSubscription?.cancel();
    super.dispose();
  }

  // Load user profile for max safe HR calculation
  void _loadUserProfile() async {
    try {
      final user = await widget.apiClient.getCurrentUser();
      final age = user['age'] as int? ?? 35;
      setState(() {
        _maxSafeHR = 220 - age;
      });
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Error in _loadUserProfile: $e');
      }
    }
  }

  // Workout elapsed timer
  void _startWorkoutTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSeconds++);
    });
  }

  /// Determines whether a live vitals source (BLE or HealthKit) is available
  /// and subscribes to it. Falls back to simulated HR when only mock data is
  /// available (e.g. no paired device).
  void _startHeartRateSource() {
    try {
      final vitals = Provider.of<VitalsProvider>(context, listen: false);
      if (vitals.activeSource != VitalsSource.mock) {
        // A real data source is active — subscribe to live readings.
        _usingLiveSource = true;
        _vitalsSubscription = vitals.vitalsStream.listen(_onLiveReading);
        return;
      }
    } catch (_) {
      // VitalsProvider may not be in the widget tree (e.g. tests).
    }

    // No live source available — use simulated HR for demo/testing.
    _startHeartRateSimulation();
  }

  /// Handle an incoming live vitals reading from BLE or HealthKit.
  void _onLiveReading(VitalsReading reading) {
    if (!mounted) return;
    final newHR = reading.heartRate.round();

    setState(() {
      _currentHR = newHR;
      if (newHR > _peakHR) _peakHR = newHR;
      if (newHR < _minHR) _minHR = newHR;
    });

    _processWithEdgeAi(newHR);
  }

  /// Fallback: simulate heart rate when no real data source is connected.
  void _startHeartRateSimulation() {
    _hrSimTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!mounted) return;
      final base = 80 + (_elapsedSeconds ~/ 10).clamp(0, 60);
      final jitter = (DateTime.now().millisecond % 15) - 7;
      final newHR = (base + jitter).clamp(55, 200);

      setState(() {
        _currentHR = newHR;
        if (newHR > _peakHR) _peakHR = newHR;
        if (newHR < _minHR) _minHR = newHR;
      });

      _processWithEdgeAi(newHR);
    });
  }

  // Run edge AI on each heart rate reading
  void _processWithEdgeAi(int heartRate) {
    try {
      final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
      edgeStore.processVitals(
        heartRate: heartRate,
        age: (220 - _maxSafeHR) > 0 ? 220 - _maxSafeHR : null, // reverse calc
        baselineHr: 72,
        maxSafeHr: _maxSafeHR,
        durationMinutes: _elapsedSeconds ~/ 60,
        recoveryTimeMinutes: 0, // still exercising
        activityType: widget.activityType,
      );

      // Read back the results
      if (mounted) {
        setState(() {
          _activeAlerts = edgeStore.activeAlerts;
          _showAlertBanner = _activeAlerts.isNotEmpty;
          if (edgeStore.latestPrediction != null) {
            _edgeRiskLevel = edgeStore.latestPrediction!.riskLevel;
            _edgeRiskScore = edgeStore.latestPrediction!.riskScore;
          }
        });
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Error in _processWithEdgeAi: $e');
      }
    }
  }

  String _formatTimer(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  void _endWorkout() async {
    _timer?.cancel();
    _hrSimTimer?.cancel();
    _vitalsSubscription?.cancel();
    setState(() => _isEndingWorkout = true);

    try {
      await widget.apiClient.endSession(
        sessionId: widget.sessionId,
        avgHeartRate: _currentHR,
        maxHeartRate: _peakHR,
      );

      // Trigger a cloud sync after workout ends
      try {
        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
        edgeStore.syncNow();
      } catch (e) {
        if (kDebugMode) {
          debugPrint('Error in _endWorkout.syncNow: $e');
        }
      }

      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Workout saved successfully!')),
        );
      }
    } catch (e) {
      setState(() => _isEndingWorkout = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error ending workout: $e')),
        );
      }
    }
  }

  // Get color based on edge AI risk level
  Color _getHRColor() {
    if (_edgeRiskLevel == 'high' || _activeAlerts.any((a) => a.severity == 'critical')) {
      return AdaptivColors.critical;
    } else if (_edgeRiskLevel == 'moderate' || _activeAlerts.any((a) => a.severity == 'warning')) {
      return AdaptivColors.warning;
    }
    return AdaptivColors.stable;
  }

  String _exerciseImageFor(String activityType) {
    return _exerciseImages[activityType] ?? 'assets/exercises/walking.png';
  }

  @override
  Widget build(BuildContext context) {
    final fillPercentage = _maxSafeHR > 0 ? (_currentHR / _maxSafeHR).clamp(0.0, 1.0) : 0.5;
    final hrColor = _getHRColor();

    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: const Color(0xFF1A1A2E),
        body: SafeArea(
          child: Column(
            children: [
            // Header: Timer + Risk badge
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Back button
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: Colors.white),
                    onPressed: () => Navigator.pop(context),
                  ),
                  // Timer
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.timer, color: Colors.white70, size: 16),
                        const SizedBox(width: 6),
                        Text(
                          _formatTimer(_elapsedSeconds),
                          style: GoogleFonts.dmSans(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Edge AI risk badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: hrColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: hrColor.withOpacity(0.5)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: hrColor,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _edgeRiskLevel.toUpperCase(),
                          style: GoogleFonts.dmSans(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: hrColor,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.asset(
                  _exerciseImageFor(widget.activityType),
                  height: 44,
                  width: 44,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => const Icon(
                    Icons.fitness_center,
                    color: Colors.white70,
                    size: 36,
                  ),
                ),
              ),
            ),

            // Critical alert banner (edge AI threshold alerts)
            if (_showAlertBanner && _activeAlerts.isNotEmpty)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.symmetric(horizontal: 24),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _activeAlerts.first.severity == 'critical'
                      ? AdaptivColors.critical.withOpacity(0.9)
                      : AdaptivColors.warning.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(
                      _activeAlerts.first.severity == 'critical'
                          ? Icons.error_rounded
                          : Icons.warning_amber_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _activeAlerts.first.title,
                            style: GoogleFonts.dmSans(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                          if (_activeAlerts.first.actions.isNotEmpty)
                            Text(
                              _activeAlerts.first.actions.first,
                              style: GoogleFonts.dmSans(
                                fontSize: 11,
                                color: Colors.white70,
                              ),
                            ),
                        ],
                      ),
                    ),
                    // Dismiss
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white70, size: 18),
                      onPressed: () => setState(() => _showAlertBanner = false),
                      constraints: const BoxConstraints(),
                      padding: EdgeInsets.zero,
                    ),
                  ],
                ),
              ),

            // Giant BPM Display with edge AI risk color
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Pulsing heart icon
                    Icon(Icons.favorite, color: hrColor, size: 36),
                    const SizedBox(height: 8),
                    Text(
                      _currentHR.toString(),
                      style: GoogleFonts.dmSans(
                        fontSize: 110,
                        fontWeight: FontWeight.w700,
                        color: hrColor,
                        height: 1.0,
                      ),
                    ),
                    Text(
                      'BPM',
                      style: GoogleFonts.dmSans(
                        fontSize: 22,
                        fontWeight: FontWeight.w400,
                        color: Colors.white60,
                      ),
                    ),
                    const SizedBox(height: 16),
                    // Risk score from edge AI
                    if (_edgeRiskScore > 0)
                      Text(
                        'Risk: ${(_edgeRiskScore * 100).toStringAsFixed(0)}%',
                        style: GoogleFonts.dmSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: hrColor.withOpacity(0.8),
                        ),
                      ),
                  ],
                ),
              ),
            ),

            // Stats row: Peak HR, Min HR, Zone
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildWorkoutStat('Peak', '$_peakHR', 'BPM'),
                  _buildWorkoutStat('Min', '${_minHR < 999 ? _minHR : 0}', 'BPM'),
                  _buildWorkoutStat('Max Safe', '$_maxSafeHR', 'BPM'),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Zone progress bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Heart Rate Zone',
                        style: GoogleFonts.dmSans(
                          fontSize: 13,
                          color: Colors.white60,
                        ),
                      ),
                      Text(
                        '${(fillPercentage * 100).toInt()}% of max',
                        style: GoogleFonts.dmSans(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: hrColor,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: fillPercentage,
                      minHeight: 12,
                      backgroundColor: Colors.white.withOpacity(0.1),
                      valueColor: AlwaysStoppedAnimation<Color>(hrColor),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // End Workout Button
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isEndingWorkout ? null : _endWorkout,
                  icon: _isEndingWorkout
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.stop_rounded),
                  label: Text(_isEndingWorkout ? 'Saving...' : 'End Workout'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: AdaptivColors.critical,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                ),
              ),
            ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWorkoutStat(String label, String value, String unit) {
    return Column(
      children: [
        Text(
          label,
          style: GoogleFonts.dmSans(
            fontSize: 12,
            color: Colors.white38,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: GoogleFonts.dmSans(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
        Text(
          unit,
          style: GoogleFonts.dmSans(
            fontSize: 11,
            color: Colors.white38,
          ),
        ),
      ],
    );
  }
}
