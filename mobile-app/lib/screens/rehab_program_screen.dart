/*
Rehab Program screen.

Shows the patient's active cardiac rehab program: weekly progress,
session tracker, today's session plan, and a button to start the workout.
If no program is active it prompts the user to set their rehab phase in Profile.
*/

import 'package:flutter/material.dart'; // Core Flutter UI toolkit
import 'package:google_fonts/google_fonts.dart'; // Custom font support
import '../theme/colors.dart'; // App colour palette
import '../services/api_client.dart'; // Talks to our backend server
import '../widgets/ai_coach_overlay.dart'; // Floating AI coach button overlay
import 'workout_screen.dart'; // Active workout timer screen

class RehabProgramScreen extends StatefulWidget {
  final ApiClient apiClient;

  const RehabProgramScreen({super.key, required this.apiClient});

  @override
  State<RehabProgramScreen> createState() => _RehabProgramScreenState();
}

class _RehabProgramScreenState extends State<RehabProgramScreen> {
  bool _isLoading = true; // True while the program is being fetched
  String? _errorMessage; // Holds an error message if loading fails
  Map<String, dynamic>? _programData; // The rehab program returned by the server

  // Return the matching exercise illustration for a given activity type
  String _exerciseImageFor(String activityType) {
    switch (activityType) {
      case 'light_jogging':
        return 'assets/exercises/light_jogging.png';
      case 'cycling':
        return 'assets/exercises/cycling.png';
      case 'swimming':
        return 'assets/exercises/swimming.png';
      case 'stretching':
        return 'assets/exercises/stretching.png';
      case 'yoga':
        return 'assets/exercises/yoga.png';
      case 'resistance_bands':
        return 'assets/exercises/resistance_bands.png';
      case 'chair_exercises':
        return 'assets/exercises/chair_exercises.png';
      case 'arm_raises':
        return 'assets/exercises/arm_raises.png';
      case 'leg_raises':
        return 'assets/exercises/leg_raises.png';
      case 'wall_pushups':
        return 'assets/exercises/wall_pushups.png';
      case 'seated_marches':
        return 'assets/exercises/seated_marches.png';
      case 'balance_exercises':
        return 'assets/exercises/balance_exercises.png';
      case 'cooldown_stretches':
        return 'assets/exercises/cooldown_stretches.png';
      case 'walking':
      default:
        return 'assets/exercises/walking.png';
    }
  }

  // Fetch the rehab program when the screen opens
  @override
  void initState() {
    super.initState();
    _loadProgram();
  }

  // Load the patient's active rehab program from the server
  Future<void> _loadProgram() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final data = await widget.apiClient.getRehabProgram();
      if (!mounted) return;
      setState(() {
        _programData = data;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      final msg = e.toString();
      if (msg.contains('404') || msg.contains('No rehab program')) {
        setState(() {
          _programData = null;
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = msg;
          _isLoading = false;
        });
      }
    }
  }

  // ------------------------------------------------------------------
  // Navigate to workout, then record the session on return
  // ------------------------------------------------------------------
  Future<void> _startSession() async {
    if (_programData == null) return;
    final plan = _programData!['current_session_plan'] as Map<String, dynamic>?;
    if (plan == null) return;

    final activityType = plan['activity_type'] as String? ?? 'walking';
    final targetDuration = plan['target_duration_minutes'] as int? ?? 10;

    // Navigate to the existing WorkoutScreen
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => WorkoutScreen(
          apiClient: widget.apiClient,
          initialExercise: activityType,
        ),
      ),
    );

    // After workout completes (user returned), record the rehab session
    if (!mounted) return;

    try {
      final progress = await widget.apiClient.completeRehabSession(
        actualDurationMinutes: targetDuration,
        activityType: activityType,
      );

      // Check if week advanced
      final prevWeek = _programData!['current_week'] as int? ?? 1;
      final newWeek = progress['current_week'] as int? ?? prevWeek;
      if (newWeek > prevWeek && mounted) {
        _showMilestoneDialog(prevWeek);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to record session: $e')),
        );
      }
    }

    // Reload program data
    await _loadProgram();
  }

  // Show a congratulations popup when the user finishes a full week
  void _showMilestoneDialog(int completedWeek) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Week $completedWeek Complete! 🎉',
          style: GoogleFonts.dmSans(fontWeight: FontWeight.w700),
        ),
        content: Text(
          'Great work! You\'ve progressed to the next phase of your rehab program.',
          style: GoogleFonts.dmSans(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Continue'),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // Build
  // ------------------------------------------------------------------
  // Build the rehab program screen: loading, error, empty, or full program view
  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            'My Rehab Program',
            style: GoogleFonts.dmSans(fontWeight: FontWeight.w700),
          ),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.pop(context),
          ),
        ),
        body: Container(
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/health_bg6.png'),
              fit: BoxFit.cover,
              colorFilter: ColorFilter.mode(
                brightness == Brightness.dark
                    ? Colors.black.withOpacity(0.6)
                    : Colors.white.withOpacity(0.85),
                brightness == Brightness.dark
                    ? BlendMode.darken
                    : BlendMode.lighten,
              ),
            ),
          ),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _errorMessage != null
                  ? _buildError()
                  : _programData == null
                      ? _buildNoProgram()
                      : RefreshIndicator(
                          onRefresh: _loadProgram,
                          child: _buildProgramContent(),
                        ),
        ),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text(_errorMessage!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadProgram, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }

  Widget _buildNoProgram() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.fitness_center, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No Rehab Program Active',
              style: GoogleFonts.dmSans(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              'Update your rehab phase in Profile to get started.',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: Colors.grey[600]),
            ),
          ],
        ),
      ),
    );
  }

  // ------------------------------------------------------------------
  // Main program content
  // ------------------------------------------------------------------
  Widget _buildProgramContent() {
    final data = _programData!;
    final programType = data['program_type'] as String? ?? '';
    final progress = data['progress_summary'] as Map<String, dynamic>?;
    final plan = data['current_session_plan'] as Map<String, dynamic>?;
    final status = data['status'] as String? ?? 'active';

    final currentWeek = progress?['current_week'] as int? ?? 1;
    final totalWeeks = progress?['total_weeks'] as int?;
    final sessionsThisWeek = progress?['sessions_completed_this_week'] as int? ?? 0;
    final sessionsRequired = progress?['sessions_required_this_week'] as int? ?? 3;
    final overallCompleted = progress?['overall_sessions_completed'] as int? ?? 0;

    final isPhase2 = programType == 'phase_2_light';
    final programTitle = isPhase2 ? 'Phase II Cardiac Rehab' : 'Phase III Maintenance';
    final isCompleted = status == 'completed';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Program Header
        _buildHeader(programTitle, currentWeek, totalWeeks, overallCompleted, isCompleted),
        const SizedBox(height: 24),

        // Weekly session tracker
        _buildWeekTracker(sessionsThisWeek, sessionsRequired, currentWeek),
        const SizedBox(height: 24),

        // Today's session card
        if (plan != null && !isCompleted) ...[
          _buildSessionCard(plan),
          const SizedBox(height: 24),

          // Start Session button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _startSession,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Session'),
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
        ],

        if (isCompleted) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AdaptivColors.stable.withOpacity(0.1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AdaptivColors.stable.withOpacity(0.3)),
            ),
            child: Column(
              children: [
                const Icon(Icons.emoji_events, size: 48, color: AdaptivColors.stable),
                const SizedBox(height: 12),
                Text(
                  'Program Completed!',
                  style: GoogleFonts.dmSans(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AdaptivColors.stable,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Congratulations! You\'ve completed all $overallCompleted sessions.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.dmSans(fontSize: 14),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  // ------------------------------------------------------------------
  // Header card
  // ------------------------------------------------------------------
  Widget _buildHeader(
    String title,
    int currentWeek,
    int? totalWeeks,
    int overallCompleted,
    bool isCompleted,
  ) {
    final weekLabel = totalWeeks != null
        ? 'Week $currentWeek of $totalWeeks'
        : 'Week $currentWeek';
    final progressValue = totalWeeks != null
        ? (currentWeek - 1) / totalWeeks
        : null;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isCompleted
              ? [AdaptivColors.stable, AdaptivColors.stable.withOpacity(0.7)]
              : [AdaptivColors.primary, AdaptivColors.primaryDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.dmSans(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            weekLabel,
            style: GoogleFonts.dmSans(fontSize: 14, color: Colors.white70),
          ),
          if (progressValue != null) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progressValue,
                backgroundColor: Colors.white24,
                valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                minHeight: 6,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Text(
            '$overallCompleted sessions completed overall',
            style: GoogleFonts.dmSans(fontSize: 12, color: Colors.white60),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // Weekly session circles  ●●○
  // ------------------------------------------------------------------
  Widget _buildWeekTracker(int completed, int required, int week) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Week $week Sessions',
            style: GoogleFonts.dmSans(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          Row(
            children: List.generate(required, (i) {
              final isDone = i < completed;
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isDone
                        ? AdaptivColors.primary
                        : Colors.grey[300],
                  ),
                  child: isDone
                      ? const Icon(Icons.check, size: 18, color: Colors.white)
                      : null,
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          Text(
            '$completed of $required completed',
            style: GoogleFonts.dmSans(fontSize: 13, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // Today's session card
  // ------------------------------------------------------------------
  Widget _buildSessionCard(Map<String, dynamic> plan) {
    final activityType = plan['activity_type'] as String? ?? 'walking';
    final duration = plan['target_duration_minutes'] as int? ?? 10;
    final hrMin = plan['target_hr_min'] as int? ?? 0;
    final hrMax = plan['target_hr_max'] as int? ?? 0;
    final description = plan['description'] as String? ?? '';

    IconData activityIcon;
    switch (activityType) {
      case 'cycling':
        activityIcon = Icons.directions_bike;
        break;
      case 'yoga':
        activityIcon = Icons.self_improvement;
        break;
      case 'stretching':
        activityIcon = Icons.accessibility_new;
        break;
      default:
        activityIcon = Icons.directions_walk;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.primary.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Today's Session",
            style: GoogleFonts.dmSans(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AdaptivColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.asset(
                    _exerciseImageFor(activityType),
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Icon(
                      activityIcon,
                      color: AdaptivColors.primary,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      activityType[0].toUpperCase() + activityType.substring(1),
                      style: GoogleFonts.dmSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      '$duration min  •  $hrMin–$hrMax BPM',
                      style: GoogleFonts.dmSans(fontSize: 13, color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (description.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              description,
              style: GoogleFonts.dmSans(fontSize: 13, color: Colors.grey[700]),
            ),
          ],
        ],
      ),
    );
  }
}
