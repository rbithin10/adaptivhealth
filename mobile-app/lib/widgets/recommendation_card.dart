/*
RecommendationCard - Fitness recommendation display widget.

Shows personalized workout recommendations with activity type,
duration, target HR zone, confidence score, and action button.

Usage:
```dart
RecommendationCard(
  activityType: ActivityType.walking,
  title: "Morning Walk",
  description: "Light cardio to start your day",
  duration: Duration(minutes: 30),
  targetHRZone: HRZone.light,
  confidence: 0.87,
  onStart: () => startWorkout(),
)
```
*/

import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';

/// Activity types for recommendations
enum ActivityType {
  walking,
  running,
  cycling,
  swimming,
  yoga,
  strength,
  hiit,
  stretching,
  meditation,
  other,
}

/// Heart rate zones
enum HRZone {
  resting,  // <70 BPM
  light,    // 70-100 BPM (50-60% max)
  moderate, // 100-140 BPM (60-70% max)
  hard,     // 140-170 BPM (70-85% max)
  maximum,  // 170+ BPM (85%+ max)
}

class RecommendationCard extends StatelessWidget {
  /// Type of activity
  final ActivityType activityType;
  
  /// Recommendation title
  final String title;
  
  /// Brief description
  final String? description;
  
  /// Recommended duration
  final Duration duration;
  
  /// Target heart rate zone
  final HRZone? targetHRZone;
  
  /// AI confidence score (0.0 - 1.0)
  final double? confidence;
  
  /// Whether this is a priority recommendation
  final bool isPriority;
  
  /// Callback when user taps to start
  final VoidCallback? onStart;
  
  /// Callback when user dismisses
  final VoidCallback? onDismiss;

  const RecommendationCard({
    super.key,
    required this.activityType,
    required this.title,
    this.description,
    required this.duration,
    this.targetHRZone,
    this.confidence,
    this.isPriority = false,
    this.onStart,
    this.onDismiss,
  });

  IconData get _activityIcon {
    switch (activityType) {
      case ActivityType.walking:
        return Icons.directions_walk;
      case ActivityType.running:
        return Icons.directions_run;
      case ActivityType.cycling:
        return Icons.directions_bike;
      case ActivityType.swimming:
        return Icons.pool;
      case ActivityType.yoga:
        return Icons.self_improvement;
      case ActivityType.strength:
        return Icons.fitness_center;
      case ActivityType.hiit:
        return Icons.whatshot;
      case ActivityType.stretching:
        return Icons.accessibility_new;
      case ActivityType.meditation:
        return Icons.spa;
      case ActivityType.other:
        return Icons.sports;
    }
  }

  String? get _exerciseImageAsset {
    switch (activityType) {
      case ActivityType.walking:
        return 'assets/exercises/walking.png';
      case ActivityType.running:
      case ActivityType.hiit:
        return 'assets/exercises/light_jogging.png';
      case ActivityType.cycling:
        return 'assets/exercises/cycling.png';
      case ActivityType.swimming:
        return 'assets/exercises/swimming.png';
      case ActivityType.yoga:
        return 'assets/exercises/yoga.png';
      case ActivityType.strength:
        return 'assets/exercises/resistance_bands.png';
      case ActivityType.stretching:
        return 'assets/exercises/stretching.png';
      case ActivityType.meditation:
      case ActivityType.other:
        return null;
    }
  }

  Color get _activityColor {
    switch (activityType) {
      case ActivityType.walking:
        return AdaptivColors.stable;
      case ActivityType.running:
        return AdaptivColors.primary;
      case ActivityType.cycling:
        return const Color(0xFF00BCD4); // Cyan
      case ActivityType.swimming:
        return const Color(0xFF2196F3); // Blue
      case ActivityType.yoga:
        return const Color(0xFF9C27B0); // Purple
      case ActivityType.strength:
        return const Color(0xFFFF5722); // Deep Orange
      case ActivityType.hiit:
        return AdaptivColors.critical;
      case ActivityType.stretching:
        return const Color(0xFF8BC34A); // Light Green
      case ActivityType.meditation:
        return const Color(0xFF673AB7); // Deep Purple
      case ActivityType.other:
        return AdaptivColors.text500;
    }
  }

  String get _durationText {
    final mins = duration.inMinutes;
    if (mins < 60) {
      return '$mins min';
    } else {
      final hours = mins ~/ 60;
      final remainingMins = mins % 60;
      if (remainingMins == 0) {
        return '${hours}h';
      }
      return '${hours}h ${remainingMins}m';
    }
  }

  String get _hrZoneLabel {
    if (targetHRZone == null) return '';
    switch (targetHRZone!) {
      case HRZone.resting:
        return 'Resting';
      case HRZone.light:
        return 'Light';
      case HRZone.moderate:
        return 'Moderate';
      case HRZone.hard:
        return 'Hard';
      case HRZone.maximum:
        return 'Maximum';
    }
  }

  Color get _hrZoneColor {
    if (targetHRZone == null) return AdaptivColors.text500;
    switch (targetHRZone!) {
      case HRZone.resting:
        return AdaptivColors.hrResting;
      case HRZone.light:
        return AdaptivColors.hrLight;
      case HRZone.moderate:
        return AdaptivColors.hrModerate;
      case HRZone.hard:
        return AdaptivColors.hrHard;
      case HRZone.maximum:
        return AdaptivColors.hrMaximum;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isPriority 
              ? AdaptivColors.primary.withOpacity(0.3)
              : AdaptivColors.border300,
          width: isPriority ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header with activity icon and dismiss
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 8, 0),
            child: Row(
              children: [
                // Activity icon
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: _activityColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: _exerciseImageAsset != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.asset(
                            _exerciseImageAsset!,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => Icon(
                              _activityIcon,
                              size: 24,
                              color: _activityColor,
                            ),
                          ),
                        )
                      : Icon(
                          _activityIcon,
                          size: 24,
                          color: _activityColor,
                        ),
                ),
                const SizedBox(width: 12),
                // Title and description
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (isPriority) ...[
                            Icon(
                              Icons.star,
                              size: 14,
                              color: AdaptivColors.warning,
                            ),
                            const SizedBox(width: 4),
                          ],
                          Expanded(
                            child: Text(
                              title,
                              style: AdaptivTypography.subtitle1.copyWith(
                                color: AdaptivColors.text900,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      if (description != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          description!,
                          style: AdaptivTypography.bodySmall.copyWith(
                            color: AdaptivColors.text500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                // Dismiss button
                if (onDismiss != null)
                  IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    color: AdaptivColors.text400,
                    onPressed: onDismiss,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                      minWidth: 32,
                      minHeight: 32,
                    ),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // Info chips (duration, HR zone, confidence)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                // Duration chip
                _InfoChip(
                  icon: Icons.timer_outlined,
                  label: _durationText,
                  color: AdaptivColors.text600,
                ),
                // HR Zone chip
                if (targetHRZone != null)
                  _InfoChip(
                    icon: Icons.favorite_outline,
                    label: _hrZoneLabel,
                    color: _hrZoneColor,
                    bgColor: _hrZoneColor.withOpacity(0.1),
                  ),
                // AI Confidence chip
                if (confidence != null)
                  _InfoChip(
                    icon: Icons.auto_awesome,
                    label: '${(confidence! * 100).toInt()}% match',
                    color: AdaptivColors.primary,
                    bgColor: AdaptivColors.primaryBg,
                  ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Action button
          if (onStart != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onStart,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _activityColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    elevation: 0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.play_arrow, size: 20),
                      const SizedBox(width: 4),
                      Text(
                        'Start Workout',
                        style: AdaptivTypography.button,
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Small info chip for displaying duration, HR zone, etc.
class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final Color? bgColor;

  const _InfoChip({
    required this.icon,
    required this.label,
    required this.color,
    this.bgColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor ?? AdaptivColors.bg200,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: AdaptivTypography.label.copyWith(
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

/// Compact recommendation card for list views
class CompactRecommendationCard extends StatelessWidget {
  final ActivityType activityType;
  final String title;
  final Duration duration;
  final HRZone? targetHRZone;
  final VoidCallback? onTap;

  const CompactRecommendationCard({
    super.key,
    required this.activityType,
    required this.title,
    required this.duration,
    this.targetHRZone,
    this.onTap,
  });

  IconData get _activityIcon {
    switch (activityType) {
      case ActivityType.walking:
        return Icons.directions_walk;
      case ActivityType.running:
        return Icons.directions_run;
      case ActivityType.cycling:
        return Icons.directions_bike;
      case ActivityType.swimming:
        return Icons.pool;
      case ActivityType.yoga:
        return Icons.self_improvement;
      case ActivityType.strength:
        return Icons.fitness_center;
      case ActivityType.hiit:
        return Icons.whatshot;
      case ActivityType.stretching:
        return Icons.accessibility_new;
      case ActivityType.meditation:
        return Icons.spa;
      case ActivityType.other:
        return Icons.sports;
    }
  }

  String? get _exerciseImageAsset {
    switch (activityType) {
      case ActivityType.walking:
        return 'assets/exercises/walking.png';
      case ActivityType.running:
      case ActivityType.hiit:
        return 'assets/exercises/light_jogging.png';
      case ActivityType.cycling:
        return 'assets/exercises/cycling.png';
      case ActivityType.swimming:
        return 'assets/exercises/swimming.png';
      case ActivityType.yoga:
        return 'assets/exercises/yoga.png';
      case ActivityType.strength:
        return 'assets/exercises/resistance_bands.png';
      case ActivityType.stretching:
        return 'assets/exercises/stretching.png';
      case ActivityType.meditation:
      case ActivityType.other:
        return null;
    }
  }

  Color get _activityColor {
    switch (activityType) {
      case ActivityType.walking:
        return AdaptivColors.stable;
      case ActivityType.running:
        return AdaptivColors.primary;
      case ActivityType.cycling:
        return const Color(0xFF00BCD4);
      case ActivityType.swimming:
      case ActivityType.yoga:
      case ActivityType.strength:
      case ActivityType.hiit:
      case ActivityType.stretching:
      case ActivityType.meditation:
      case ActivityType.other:
        return AdaptivColors.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AdaptivColors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AdaptivColors.border300),
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: _activityColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: _exerciseImageAsset != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.asset(
                        _exerciseImageAsset!,
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) => Icon(
                          _activityIcon,
                          size: 20,
                          color: _activityColor,
                        ),
                      ),
                    )
                  : Icon(
                      _activityIcon,
                      size: 20,
                      color: _activityColor,
                    ),
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
                      color: AdaptivColors.text900,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${duration.inMinutes} min',
                    style: AdaptivTypography.bodySmall.copyWith(
                      color: AdaptivColors.text500,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              size: 20,
              color: AdaptivColors.text400,
            ),
          ],
        ),
      ),
    );
  }
}
