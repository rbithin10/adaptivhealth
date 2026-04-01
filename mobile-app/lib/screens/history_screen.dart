/*
History screen.

Shows a list of past workout and recovery sessions with stats like duration,
average heart rate, and date/time. Users can view details of each session.
*/

import 'package:flutter/material.dart'; // Core Flutter UI toolkit
import 'package:fl_chart/fl_chart.dart'; // Charts for recovery score trend
import 'package:intl/intl.dart'; // Date/number formatting
import '../theme/colors.dart'; // App colour palette
import '../theme/typography.dart'; // Shared text styles
import '../services/api_client.dart'; // Talks to our backend server
import '../widgets/ai_coach_overlay.dart'; // Floating AI coach button overlay

class HistoryScreen extends StatefulWidget {
  final ApiClient apiClient;

  const HistoryScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _activities = []; // Past workout and recovery sessions
  List<Map<String, dynamic>> _weeklyScores = []; // 7-day recovery scores
  bool _loading = true; // True while activities are being fetched
  String? _error; // Error message if loading fails

  // Fetch activities from the server when the screen opens
  @override
  void initState() {
    super.initState();
    _loadData();
  }

  // Pull activities and weekly recovery scores from the server
  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final results = await Future.wait([
        widget.apiClient.getActivities(limit: 50, offset: 0),
        widget.apiClient.getWeeklyRecoveryScores(),
      ]);

      setState(() {
        _activities = results[0].cast<Map<String, dynamic>>();
        _weeklyScores = results[1].cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  // Convert an ISO date string into a friendly format like "Mar 15, 2025 3:30 PM"
  String _formatDateTime(String? isoString) {
    if (isoString == null) return 'Unknown';
    try {
      final date = DateTime.parse(isoString);
      return DateFormat('MMM dd, yyyy h:mm a').format(date);
    } catch (e) {
      return 'Unknown';
    }
  }

  // Turn a number of minutes into a readable format like "1h 30m"
  String _formatDuration(int? minutes) {
    if (minutes == null || minutes == 0) return 'N/A';
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return '${hours}h ${mins}m';
  }

  String _formatActivityLabel(String? activityType) {
    if (activityType == null || activityType.trim().isEmpty) return 'Activity';
    final cleaned = activityType.replaceAll('_', ' ').trim();
    final words = cleaned.split(RegExp(r'\s+'));
    return words
        .map((word) => word.isEmpty
            ? word
            : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  // Pick an icon based on the type of activity (running, breathing, walking, etc.)
  IconData _getActivityIcon(String? activityType) {
    switch (activityType?.toLowerCase()) {
      case 'workout':
      case 'cardio':
        return Icons.directions_run;
      case 'recovery':
      case 'breathing':
        return Icons.self_improvement;
      case 'walking':
        return Icons.directions_walk;
      case 'cycling':
        return Icons.directions_bike;
      case 'swimming':
        return Icons.pool;
      case 'yoga':
        return Icons.self_improvement;
      case 'strength_training':
      case 'strength':
        return Icons.fitness_center;
      default:
        return Icons.fitness_center;
    }
  }

  // Pick a colour for the activity card based on its type
  Color _getActivityColor(String? activityType) {
    switch (activityType?.toLowerCase()) {
      case 'workout':
      case 'cardio':
        return AdaptivColors.critical;
      case 'recovery':
      case 'breathing':
        return AdaptivColors.stable;
      case 'walking':
        return AdaptivColors.warning;
      case 'cycling':
        return AdaptivColors.chartTeal;
      case 'swimming':
        return AdaptivColors.chartBlue;
      case 'yoga':
        return AdaptivColors.primary;
      case 'strength_training':
      case 'strength':
        return AdaptivColors.critical;
      default:
        return AdaptivColors.primary;
    }
  }

  Color _scoreColor(int score) {
    if (score >= 70) return AdaptivColors.stable;
    if (score >= 40) return AdaptivColors.warning;
    return AdaptivColors.critical;
  }

  Widget _buildWeeklyScoreChart(Brightness brightness) {
    if (_weeklyScores.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AdaptivColors.getSurfaceColor(brightness),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Weekly Recovery Score', style: AdaptivTypography.cardTitle),
            const SizedBox(height: 8),
            Text('No recovery scores yet.', style: AdaptivTypography.caption),
          ],
        ),
      );
    }

    final spots = <FlSpot>[];
    final labels = <String>[];
    final scores = <int>[];

    for (var i = 0; i < _weeklyScores.length; i++) {
      final item = _weeklyScores[i];
      final rawScore = item['score'];
      final score = rawScore is int ? rawScore : int.tryParse('$rawScore') ?? 0;
      final dateStr = item['date']?.toString();
      final parsedDate = dateStr != null ? DateTime.tryParse(dateStr) : null;
      final label = parsedDate != null ? DateFormat('EEE').format(parsedDate) : 'Day';

      scores.add(score);
      labels.add(label);
      spots.add(FlSpot(i.toDouble(), score.toDouble()));
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Weekly Recovery Score', style: AdaptivTypography.cardTitle),
          const SizedBox(height: 12),
          SizedBox(
            height: 180,
            child: LineChart(
              LineChartData(
                minY: 0,
                maxY: 100,
                gridData: FlGridData(show: true, drawVerticalLine: false),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      interval: 20,
                      getTitlesWidget: (value, meta) => Text(
                        value.toInt().toString(),
                        style: AdaptivTypography.caption,
                      ),
                    ),
                  ),
                  rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 1,
                      getTitlesWidget: (value, meta) {
                        final index = value.toInt();
                        if (index < 0 || index >= labels.length) {
                          return const SizedBox.shrink();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(labels[index], style: AdaptivTypography.caption),
                        );
                      },
                    ),
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: AdaptivColors.primary,
                    barWidth: 3,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, percent, bar, index) {
                        final score = scores[index];
                        return FlDotCirclePainter(
                          radius: 4,
                          color: _scoreColor(score),
                          strokeWidth: 2,
                          strokeColor: AdaptivColors.getSurfaceColor(brightness),
                        );
                      },
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: AdaptivColors.primary.withOpacity(0.08),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Return the exercise illustration path for an activity type (or null if none)
  String? _getActivityImage(String? activityType) {
    switch (activityType?.toLowerCase()) {
      case 'walking':
        return 'assets/exercises/walking.png';
      case 'running':
      case 'light_jogging':
      case 'workout':
      case 'cardio':
        return 'assets/exercises/light_jogging.png';
      case 'cycling':
        return 'assets/exercises/cycling.png';
      case 'swimming':
        return 'assets/exercises/swimming.png';
      case 'yoga':
        return 'assets/exercises/yoga.png';
      case 'stretching':
      case 'recovery':
      case 'breathing':
        return 'assets/exercises/stretching.png';
      case 'strength':
      case 'strength_training':
        return 'assets/exercises/resistance_bands.png';
      default:
        return null;
    }
  }

  // Build the activity history list with pull-to-refresh
  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          title: Text('Activity History', style: AdaptivTypography.screenTitle),
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          foregroundColor: AdaptivColors.getTextColor(brightness),
          elevation: 0,
        ),
        body: Container(
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/history_bg.png'),
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
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, size: 64, color: Colors.red),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to load activities',
                            style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _error!,
                            style: AdaptivTypography.caption,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 24),
                          ElevatedButton(
                            onPressed: _loadData,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : _activities.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.history, size: 80, color: AdaptivColors.neutral300),
                              const SizedBox(height: 16),
                              Text(
                                'No Activity Yet',
                                style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Start a workout or recovery session\nto see your history here',
                                style: AdaptivTypography.caption,
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      )
                    : RefreshIndicator(
                      onRefresh: _loadData,
                      child: SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            _buildWeeklyScoreChart(brightness),
                            const SizedBox(height: 16),
                            ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: _activities.length,
                              itemBuilder: (context, index) {
                                final activity = _activities[index];
                                final activityType = activity['activity_type'] as String?;
                                final activityImage = _getActivityImage(activityType);
                                final startTime = activity['start_time'] as String?;
                                final duration = activity['duration_minutes'] as int?;
                                final avgHr = activity['avg_heart_rate'] as int?;
                                final peakHr = activity['peak_heart_rate'] as int?;
                                final activityLabel = _formatActivityLabel(activityType);

                                return Card(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  elevation: 2,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: InkWell(
                                    onTap: () {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Detailed activity view is not available in this build.'),
                                          duration: Duration(seconds: 2),
                                        ),
                                      );
                                    },
                                    borderRadius: BorderRadius.circular(12),
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Row(
                                        children: [
                                          // Icon
                                          Container(
                                            width: 56,
                                            height: 56,
                                            decoration: BoxDecoration(
                                              color: _getActivityColor(activityType).withOpacity(0.1),
                                              borderRadius: BorderRadius.circular(12),
                                            ),
                                            child: activityImage != null
                                                ? ClipRRect(
                                                    borderRadius: BorderRadius.circular(12),
                                                    child: Image.asset(
                                                      activityImage,
                                                      fit: BoxFit.cover,
                                                      errorBuilder: (context, error, stackTrace) => Icon(
                                                        _getActivityIcon(activityType),
                                                        color: _getActivityColor(activityType),
                                                        size: 28,
                                                      ),
                                                    ),
                                                  )
                                                : Icon(
                                                    _getActivityIcon(activityType),
                                                    color: _getActivityColor(activityType),
                                                    size: 28,
                                                  ),
                                          ),
                                          const SizedBox(width: 16),
                                          // Details
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  activityLabel,
                                                  style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.bold),
                                                ),
                                                const SizedBox(height: 4),
                                                Text(
                                                  _formatDateTime(startTime),
                                                  style: AdaptivTypography.caption,
                                                ),
                                                const SizedBox(height: 8),
                                                Row(
                                                  children: [
                                                    const Icon(Icons.timer, size: 16, color: AdaptivColors.text500),
                                                    const SizedBox(width: 4),
                                                    Text(
                                                      _formatDuration(duration),
                                                      style: AdaptivTypography.caption,
                                                    ),
                                                    const SizedBox(width: 16),
                                                    const Icon(Icons.favorite, size: 16, color: Colors.red),
                                                    const SizedBox(width: 4),
                                                    Text(
                                                      avgHr != null ? '$avgHr BPM' : 'N/A',
                                                      style: AdaptivTypography.caption,
                                                    ),
                                                    if (peakHr != null) ...[
                                                      const SizedBox(width: 8),
                                                      Text(
                                                        '(Peak: $peakHr)',
                                                        style: AdaptivTypography.caption.copyWith(
                                                          color: AdaptivColors.text500,
                                                        ),
                                                      ),
                                                    ],
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                          // Arrow
                                          const Icon(
                                            Icons.chevron_right,
                                            color: AdaptivColors.neutral300,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
        ),
      ),
    );
  }
}
