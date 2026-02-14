/*
History screen.

Shows a list of past workout and recovery sessions with stats like duration,
average heart rate, and date/time. Users can view details of each session.
*/

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

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
  List<Map<String, dynamic>> _activities = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadActivities();
  }

  Future<void> _loadActivities() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await widget.apiClient.getActivities(limit: 50, offset: 0);
      
      setState(() {
        _activities = response.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _formatDateTime(String? isoString) {
    if (isoString == null) return 'Unknown';
    try {
      final date = DateTime.parse(isoString);
      return DateFormat('MMM dd, yyyy h:mm a').format(date);
    } catch (e) {
      return 'Unknown';
    }
  }

  String _formatDuration(int? minutes) {
    if (minutes == null || minutes == 0) return 'N/A';
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return '${hours}h ${mins}m';
  }

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
      default:
        return Icons.fitness_center;
    }
  }

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
      default:
        return AdaptivColors.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      appBar: AppBar(
        title: Text('Activity History', style: AdaptivTypography.screenTitle),
        backgroundColor: Colors.white,
        elevation: 0,
        automaticallyImplyLeading: false,
      ),
      body: Container(
        decoration: BoxDecoration(
          image: DecorationImage(
            image: const AssetImage('assets/images/history_bg.png'),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(
              Colors.white.withOpacity(0.85),
              BlendMode.lighten,
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
                          onPressed: _loadActivities,
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
                      onRefresh: _loadActivities,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _activities.length,
                        itemBuilder: (context, index) {
                          final activity = _activities[index];
                          final activityType = activity['activity_type'] as String?;
                          final startTime = activity['start_time'] as String?;
                          final duration = activity['duration_minutes'] as int?;
                          final avgHr = activity['avg_heart_rate'] as int?;
                          final peakHr = activity['peak_heart_rate'] as int?;

                          return Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            elevation: 2,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: InkWell(
                              onTap: () {
                                // TODO: Navigate to session detail page
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Session detail coming soon'),
                                    duration: Duration(seconds: 1),
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
                                      child: Icon(
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
                                            activityType ?? 'Activity',
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
                                              Icon(Icons.timer, size: 16, color: AdaptivColors.text500),
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
                    ),
      ),
    );
  }
}
