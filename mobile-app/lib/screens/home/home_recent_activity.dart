/*
HomeRecentActivity widget — recent workout list on the Home tab.
Accepts a pre-created Future so the parent controls data fetching.
*/

import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Renders the most recent activity sessions from [activitiesFuture].
class HomeRecentActivity extends StatelessWidget {
  final Future<List<dynamic>> activitiesFuture;
  final VoidCallback onViewAll;

  const HomeRecentActivity({
    super.key,
    required this.activitiesFuture,
    required this.onViewAll,
  });

  // ─── activity type helpers ── pick the right icon, colour, and image for each workout type

  // Choose an icon based on what kind of exercise was done
  static IconData _activityIcon(String? type) {
    switch (type?.toLowerCase()) {
      case 'running':       return Icons.directions_run;
      case 'cycling':       return Icons.directions_bike;
      case 'swimming':      return Icons.pool;
      case 'yoga':          return Icons.self_improvement;
      case 'stretching':    return Icons.accessibility_new;
      case 'strength_training': return Icons.fitness_center;
      case 'walking':
      default:              return Icons.directions_walk;
    }
  }

  // Pick a colour for each activity type (different colours help visually distinguish them)
  static Color _activityColor(String? type) {
    switch (type?.toLowerCase()) {
      case 'running':       return AdaptivColors.warning;
      case 'cycling':       return AdaptivColors.primary;
      case 'swimming':      return const Color(0xFF0097A7);
      case 'yoga':
      case 'stretching':    return const Color(0xFF9C27B0);
      case 'strength_training': return AdaptivColors.critical;
      case 'walking':
      default:              return AdaptivColors.stable;
    }
  }

  // Find the matching exercise image asset, if one exists
  static String? _activityImage(String? type) {
    switch (type?.toLowerCase()) {
      case 'walking':       return 'assets/exercises/walking.png';
      case 'running':
      case 'light_jogging': return 'assets/exercises/light_jogging.png';
      case 'cycling':       return 'assets/exercises/cycling.png';
      case 'swimming':      return 'assets/exercises/swimming.png';
      case 'yoga':          return 'assets/exercises/yoga.png';
      case 'stretching':    return 'assets/exercises/stretching.png';
      case 'strength_training': return 'assets/exercises/resistance_bands.png';
      default:              return null;
    }
  }

  // Convert a timestamp into a friendly label like "5m ago", "2h ago", "Yesterday"
  static String _relativeTime(String? isoString) {
    if (isoString == null || isoString.isEmpty) return '';
    try {
      final dt   = DateTime.parse(isoString);
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1)  return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24)   return '${diff.inHours}h ago';
      if (diff.inDays == 1)    return 'Yesterday';
      if (diff.inDays < 7)     return '${diff.inDays}d ago';
      return '${dt.month}/${dt.day}';
    } catch (_) {
      return '';
    }
  }

  // Build a subtitle like "30 min • Peak 142 BPM" from the activity data
  static String _activitySubtitle(Map<String, dynamic> a) {
    final parts = <String>[];
    final dur  = a['duration_minutes'];
    if (dur  != null) parts.add('$dur min');
    final peak = a['peak_heart_rate'];
    if (peak != null) parts.add('Peak $peak BPM');
    if (parts.isEmpty) {
      final status = a['status'];
      return status != null ? status.toString() : 'Session';
    }
    return parts.join(' • ');
  }

  static String _titleCase(String? type) {
    return (type ?? 'Activity')
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
        .join(' ');
  }

  // ─── build ── render the section with a header and list of activity items

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<dynamic>>(
      future: activitiesFuture,
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
                  onTap: onViewAll,
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
              // Show a loading spinner while activities are being fetched
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
              // Show a friendly message if there's nothing to display
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    'No recent activity yet',
                    style: AdaptivTypography.caption.copyWith(
                        color: AdaptivColors.text600),
                  ),
                ),
              )
            else
              // Render one row per activity session
              ...snapshot.data!.map((item) {
                final a    = item as Map<String, dynamic>;
                final type = a['activity_type'] as String?;
                return _ActivityItem(
                  imagePath: _activityImage(type),
                  icon:      _activityIcon(type),
                  title:     _titleCase(type),
                  subtitle:  _activitySubtitle(a),
                  time:      _relativeTime(a['start_time']?.toString() ?? ''),
                  color:     _activityColor(type),
                );
              }),
          ],
        );
      },
    );
  }
}

class _ActivityItem extends StatelessWidget {
  final String? imagePath;
  final IconData icon;
  final String title;
  final String subtitle;
  final String time;
  final Color color;

  const _ActivityItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.time,
    required this.color,
    this.imagePath,
  });

  @override
  Widget build(BuildContext context) {
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
                      imagePath!,
                      width: 20,
                      height: 20,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) =>
                          Icon(icon, color: color, size: 20),
                    ),
                  )
                : Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: AdaptivTypography.body
                        .copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(subtitle,
                    style: AdaptivTypography.caption
                        .copyWith(color: AdaptivColors.text600)),
              ],
            ),
          ),
          Text(time, style: AdaptivTypography.caption),
        ],
      ),
    );
  }
}
