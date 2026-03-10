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

// Flutter's UI toolkit
import 'package:flutter/material.dart';
// Our custom brand colors
import '../theme/colors.dart';
// Our custom text styles
import '../theme/typography.dart';

// The types of exercise the app can recommend
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

// Heart rate zones — how hard the heart is working during exercise
enum HRZone {
  resting,  // Relaxed: below 70 BPM
  light,    // Easy effort: 70-100 BPM (50-60% of max)
  moderate, // Medium effort: 100-140 BPM (60-70% of max)
  hard,     // Tough effort: 140-170 BPM (70-85% of max)
  maximum,  // All-out effort: 170+ BPM (85%+ of max)
}

// A card that shows a personalized workout recommendation
class RecommendationCard extends StatelessWidget {
  // What kind of exercise (walking, running, yoga, etc.)
  final ActivityType activityType;
  
  // The name of the recommendation (e.g. "Morning Walk")
  final String title;
  
  // A short description of the recommendation
  final String? description;
  
  // How long the workout should last
  final Duration duration;
  
  // What heart rate zone to aim for during the workout
  final HRZone? targetHRZone;
  
  // How confident the AI is that this is a good recommendation (0-100%)
  final double? confidence;
  
  // Whether this recommendation is marked as high-priority (shows a star)
  final bool isPriority;
  
  // What happens when the user taps "Start Workout"
  final VoidCallback? onStart;
  
  // What happens when the user taps the X to dismiss
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

  // Each activity type has its own color for the icon and button
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

  // Convert the duration into a readable label like "30 min" or "1h 15m"
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

  // Convert the HR zone into a human-readable label like "Light" or "Hard"
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

  // Each HR zone has a different color (green for easy, red for max)
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
    // The main card container with rounded corners and a subtle shadow
    return Container(
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(16),
        // Priority recommendations get a highlighted border
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
          // Top section: activity icon, title, description, and dismiss X
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 8, 0),
            child: Row(
              children: [
                // Round colored box with the activity icon or exercise image
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: _activityColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  // Show the exercise image if available, fall back to icon
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
                // Recommendation name and description text
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
                // X button to dismiss this recommendation
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

          // Small info badges showing duration, target HR zone, and AI confidence
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                // How long the workout should take
                _InfoChip(
                  icon: Icons.timer_outlined,
                  label: _durationText,
                  color: AdaptivColors.text600,
                ),
                // Target heart rate zone (e.g. "Light", "Moderate")
                if (targetHRZone != null)
                  _InfoChip(
                    icon: Icons.favorite_outline,
                    label: _hrZoneLabel,
                    color: _hrZoneColor,
                    bgColor: _hrZoneColor.withOpacity(0.1),
                  ),
                // How well the AI thinks this workout fits the user
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

          // "Start Workout" button at the bottom of the card
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

// A small colored badge with an icon and label (used for duration, HR zone, etc.)
class _InfoChip extends StatelessWidget {
  // The small icon on the left side of the badge
  final IconData icon;
  // The text label (e.g. "30 min", "Light", "87% match")
  final String label;
  // The color for the icon and text
  final Color color;
  // Optional background color for the badge
  final Color? bgColor;

  const _InfoChip({
    required this.icon,
    required this.label,
    required this.color,
    this.bgColor,
  });

  @override
  Widget build(BuildContext context) {
    // A rounded pill-shaped badge with icon + text
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

// A smaller version of the recommendation card, used in scrollable lists
class CompactRecommendationCard extends StatelessWidget {
  // What kind of exercise
  final ActivityType activityType;
  // The workout name
  final String title;
  // How long the workout should take
  final Duration duration;
  // Target heart rate zone
  final HRZone? targetHRZone;
  // What happens when the user taps this card
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

  // Each activity type gets its own color (compact version groups some together)
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
    // Tappable compact card with icon, title, duration, and arrow
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
            // Activity icon in a colored circle
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
