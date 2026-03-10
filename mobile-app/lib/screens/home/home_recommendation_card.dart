/*
HomeRecommendationCard widget — "Recommended For You" section on the Home tab.
Loads the backend recommendation via a pre-created Future and renders a
CompactRecommendationCard with activity type, duration, and HR zone.
Falls back to a conservative offline suggestion based on the patient's
current risk level.
*/

import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/widgets.dart';

/// Section widget that wraps a FutureBuilder for the daily recommendation.
class HomeRecommendationCard extends StatelessWidget {
  final Future<Map<String, dynamic>> recommendationFuture;
  final String riskLevel;
  final VoidCallback onNavigateToFitness;

  const HomeRecommendationCard({
    super.key,
    required this.recommendationFuture,
    required this.riskLevel,
    required this.onNavigateToFitness,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            'Recommended For You',
            style: AdaptivTypography.subtitle1.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        FutureBuilder<Map<String, dynamic>>(
          future: recommendationFuture,
          builder: (context, snapshot) {
            // Show a placeholder while the recommendation loads from the server
            if (snapshot.connectionState == ConnectionState.waiting) {
              return _loadingPlaceholder();
            }

            final hasError = snapshot.hasError || snapshot.data == null;

            if (hasError) {
              // If we can't reach the server, show a safe offline suggestion based on risk
              final isHighRisk = riskLevel.toLowerCase() == 'high';
              return CompactRecommendationCard(
                activityType: isHighRisk ? ActivityType.meditation : ActivityType.walking,
                title: isHighRisk ? 'Rest & Recovery' : 'Steady Movement',
                duration: Duration(minutes: isHighRisk ? 15 : 30),
                targetHRZone: isHighRisk ? HRZone.resting : HRZone.light,
                onTap: onNavigateToFitness,
              );
            }

            // We got a recommendation from the server — display it
            final rec             = snapshot.data!;
            final activityType    = _mapActivityType(
              rec['suggested_activity'] ?? rec['activity_type'],
            );
            final durationMinutes = _safeToInt(rec['duration_minutes'], 20);

            return CompactRecommendationCard(
              activityType: activityType,
              title: (rec['title'] ?? 'Today\'s Recommendation').toString(),
              duration: Duration(minutes: durationMinutes > 0 ? durationMinutes : 20),
              targetHRZone: _mapIntensityToHRZone(rec['intensity_level']),
              onTap: onNavigateToFitness,
            );
          },
        ),
      ],
    );
  }

  // ─── helpers ── convert server values into the app's enum types

  // Loading state placeholder
  Widget _loadingPlaceholder() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AdaptivColors.border300),
      ),
      child: Text(
        'Loading recommendation...',
        style: AdaptivTypography.body.copyWith(color: AdaptivColors.text600),
      ),
    );
  }

  // Map a text activity name from the server to our app's ActivityType enum
  static ActivityType _mapActivityType(dynamic rawValue) {
    final value = (rawValue ?? '').toString().toLowerCase();
    if (value.contains('walk'))    return ActivityType.walking;
    if (value.contains('run'))     return ActivityType.running;
    if (value.contains('cycl'))    return ActivityType.cycling;
    if (value.contains('swim'))    return ActivityType.swimming;
    if (value.contains('yoga'))    return ActivityType.yoga;
    if (value.contains('strength'))return ActivityType.strength;
    if (value.contains('hiit') || value.contains('interval')) return ActivityType.hiit;
    if (value.contains('stretch')) return ActivityType.stretching;
    if (value.contains('meditat') || value.contains('breath') || value.contains('rest')) {
      return ActivityType.meditation;
    }
    return ActivityType.walking;
  }

  // Map an intensity label from the server to our app's heart rate zone enum
  static HRZone _mapIntensityToHRZone(dynamic rawValue) {
    final value = (rawValue ?? '').toString().toLowerCase();
    switch (value) {
      case 'very_high':
      case 'maximum':
        return HRZone.maximum;
      case 'high':
      case 'hard':
        return HRZone.hard;
      case 'moderate':
        return HRZone.moderate;
      case 'low':
      case 'light':
        return HRZone.light;
      default:
        return HRZone.light;
    }
  }

  // Safely convert any value to an integer (handles strings, doubles, and nulls)
  static int _safeToInt(dynamic value, int fallback) {
    if (value == null) return fallback;
    if (value is int)    return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value) ?? fallback;
    return fallback;
  }
}
