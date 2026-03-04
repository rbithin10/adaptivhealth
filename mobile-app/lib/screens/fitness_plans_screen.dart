/*
Fitness Plans Screen

Displays AI-recommended fitness plans tailored to the user's
cardiovascular health profile. Shows personalized workout
recommendations with target HR zones and confidence scores.
*/

import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/widgets.dart';
import '../services/api_client.dart';
import 'recovery_screen.dart';
import 'workout_screen.dart';

class FitnessPlansScreen extends StatefulWidget {
  final ApiClient apiClient;

  const FitnessPlansScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<FitnessPlansScreen> createState() => _FitnessPlansScreenState();
}

/// Immutable summary of the current ISO week's activity data.
class _WeekStats {
  final int activeDays;
  final int totalMinutes;
  final int totalCalories;
  final int sessionsCompleted;

  const _WeekStats({
    required this.activeDays,
    required this.totalMinutes,
    required this.totalCalories,
    required this.sessionsCompleted,
  });

  static const int sessionsGoal = 5;
  double get goalFraction => sessionsCompleted / sessionsGoal;
}

/// Derive week stats from a raw activity list returned by the API.
_WeekStats _computeThisWeek(List<dynamic> activities) {
  final now      = DateTime.now();
  final monday   = now.subtract(Duration(days: now.weekday - 1));
  final weekStart = DateTime(monday.year, monday.month, monday.day);

  final activeDays = <int>{};
  int totalMin = 0;
  int totalCal = 0;
  int sessions = 0;

  for (final dynamic raw in activities) {
    if (raw is! Map) continue;
    final a = Map<String, dynamic>.from(raw);
    final ts = DateTime.tryParse(a['start_time'] as String? ?? '');
    if (ts == null || ts.isBefore(weekStart)) continue;
    activeDays.add(ts.weekday);
    totalMin += (a['duration_minutes'] as num?)?.toInt() ?? 0;
    totalCal += (a['calories_burned']  as num?)?.toInt() ?? 0;
    sessions++;
  }

  return _WeekStats(
    activeDays:        activeDays.length,
    totalMinutes:      totalMin,
    totalCalories:     totalCal,
    sessionsCompleted: sessions,
  );
}

class _FitnessPlansScreenState extends State<FitnessPlansScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  List<FitnessPlan> _plans = [];
  List<dynamic> _activities = [];
  Map<String, dynamic>? _userProfile;
  String _selectedFilter = 'All';

  final List<String> _filters = ['All', 'Cardio', 'Strength', 'Recovery', 'HIIT'];

  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadPlans();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    setState(() => _isLoading = true);

    // Fetch AI recommendation, activity history, and user profile in parallel.
    try {
      final results = await Future.wait([
        widget.apiClient.getLatestRecommendation(),
        widget.apiClient.getActivities(limit: 50),
        widget.apiClient.getCurrentUser(),
      ]);
      _userProfile = results[2] as Map<String, dynamic>?;
      final aiPlan  = _mapRecommendationToPlan(results[0] as Map<String, dynamic>);
      _plans        = [aiPlan, ..._buildProfileAwareFallback(_userProfile)];
      _activities   = results[1] as List<dynamic>;
    } catch (e) {
      // If backend fails, fall back to profile-aware generic plans.
      _plans      = _buildProfileAwareFallback(_userProfile);
      _activities = [];
    }

    setState(() => _isLoading = false);
  }

  /// Map backend recommendation to FitnessPlan model.
  FitnessPlan _mapRecommendationToPlan(Map<String, dynamic> rec) {
    final activityStr = (rec['suggested_activity'] as String?)?.toLowerCase() ?? 'walking';
    final intensityStr = (rec['intensity_level'] as String?)?.toLowerCase() ?? 'moderate';
    final durationMin = rec['duration_minutes'] as int? ?? 30;
    final hrMin = rec['target_heart_rate_min'] as int?;
    final hrMax = rec['target_heart_rate_max'] as int?;
    
    // Map activity string to enum
    ActivityType activityType = ActivityType.walking;
    if (activityStr.contains('run')) {
      activityType = ActivityType.running;
    } else if (activityStr.contains('cycl') || activityStr.contains('bike')) activityType = ActivityType.cycling;
    else if (activityStr.contains('swim')) activityType = ActivityType.swimming;
    else if (activityStr.contains('yoga')) activityType = ActivityType.yoga;
    else if (activityStr.contains('strength') || activityStr.contains('weight')) activityType = ActivityType.strength;
    else if (activityStr.contains('hiit') || activityStr.contains('interval')) activityType = ActivityType.hiit;
    else if (activityStr.contains('stretch')) activityType = ActivityType.stretching;
    
    // Map intensity + HR to zone
    HRZone zone = HRZone.moderate;
    if (hrMax != null) {
      if (hrMax < 100) {
        zone = HRZone.light;
      } else if (hrMax < 140) zone = HRZone.moderate;
      else if (hrMax < 170) zone = HRZone.hard;
      else zone = HRZone.maximum;
    } else {
      // Fallback to intensity mapping
      if (intensityStr == 'low') {
        zone = HRZone.light;
      } else if (intensityStr == 'moderate') zone = HRZone.moderate;
      else if (intensityStr == 'high') zone = HRZone.hard;
      else if (intensityStr == 'very_high') zone = HRZone.maximum;
    }
    
    return FitnessPlan(
      id: 'ai_${rec['recommendation_id'] ?? 0}',
      title: rec['title'] as String? ?? 'AI Recommendation',
      description: rec['description'] as String? ?? 'Personalized workout based on your health data',
      activityType: activityType,
      duration: Duration(minutes: durationMin),
      targetHRZone: zone,
      confidence: (rec['confidence_score'] as num?)?.toDouble() ?? 0.85,
      isPriority: true,  // AI recommendation is always priority
      benefits: ['Personalized for you', 'Risk-adjusted', 'AI-optimized'],
      caloriesBurn: _estimateCalories(activityType, durationMin),
    );
  }
  
  /// Estimate calories for activity type and duration.
  int _estimateCalories(ActivityType type, int minutes) {
    final caloriesPerMin = {
      ActivityType.walking: 4,
      ActivityType.running: 10,
      ActivityType.cycling: 7,
      ActivityType.swimming: 9,
      ActivityType.yoga: 3,
      ActivityType.strength: 5,
      ActivityType.hiit: 11,
      ActivityType.stretching: 2,
      ActivityType.meditation: 1,
      ActivityType.other: 4,
    };
    return (caloriesPerMin[type] ?? 4) * minutes;
  }
  
  /// Return fallback fitness plans tailored to the user's profile.
  /// Falls back to safe generic options when the profile is unavailable.
  List<FitnessPlan> _buildProfileAwareFallback(Map<String, dynamic>? profile) {
    final rehabPhase   = (profile?['rehab_phase'] as String? ?? '').toLowerCase();
    final activityLevel= (profile?['activity_level'] as String? ?? 'moderate').toLowerCase();
    final age          = (profile?['age'] as num?)?.toInt() ?? 40;

    final isRehab    = rehabPhase.contains('phase_1') || rehabPhase.contains('phase_2');
    final isSedentary= activityLevel == 'sedentary' || activityLevel == 'lightly_active';
    final isSenior   = age >= 60;

    // Duration tier based on fitness level.
    final int shortDuration  = isSedentary || isSenior ? 15 : 20;
    final int mediumDuration = isSedentary || isSenior ? 25 : 35;
    final int longDuration   = isSedentary || isSenior ? 35 : 45;

    if (isRehab) {
      // Phase 1/2 rehab: very gentle, low HR-zone activities.
      return [
        FitnessPlan(
          id: 'gen_rehab_1',
          title: 'Gentle Walking',
          description: 'Supervised low-intensity walk suited to your recovery phase',
          activityType: ActivityType.walking,
          duration: Duration(minutes: shortDuration),
          targetHRZone: HRZone.light,
          confidence: 0.0,
          isPriority: false,
          benefits: ['Safe for rehab', 'Builds circulation', 'Low impact'],
          caloriesBurn: _estimateCalories(ActivityType.walking, shortDuration),
        ),
        FitnessPlan(
          id: 'gen_rehab_2',
          title: 'Chair Stretching',
          description: 'Seated range-of-motion exercises for joint mobility',
          activityType: ActivityType.stretching,
          duration: Duration(minutes: shortDuration),
          targetHRZone: HRZone.resting,
          confidence: 0.0,
          isPriority: false,
          benefits: ['Joint mobility', 'Safe seated', 'Reduces stiffness'],
          caloriesBurn: _estimateCalories(ActivityType.stretching, shortDuration),
        ),
        FitnessPlan(
          id: 'gen_rehab_3',
          title: 'Breathing & Relaxation',
          description: 'Diaphragmatic breathing to support cardiac recovery',
          activityType: ActivityType.meditation,
          duration: Duration(minutes: shortDuration),
          targetHRZone: HRZone.resting,
          confidence: 0.0,
          isPriority: false,
          benefits: ['Parasympathetic calm', 'Lowers BP', 'Reduces anxiety'],
          caloriesBurn: _estimateCalories(ActivityType.meditation, shortDuration),
        ),
      ];
    }

    // Standard fallback — scaled by age/activity level.
    return [
      FitnessPlan(
        id: 'gen_1',
        title: 'Zone 2 Training',
        description: isSenior
            ? 'Low-intensity steady-state cardio adapted for your age group'
            : 'Build aerobic base with steady-state cardio',
        activityType: ActivityType.cycling,
        duration: Duration(minutes: longDuration),
        targetHRZone: HRZone.moderate,
        confidence: 0.0,
        isPriority: false,
        benefits: ['Fat burning', 'Endurance building', 'Heart efficiency'],
        caloriesBurn: _estimateCalories(ActivityType.cycling, longDuration),
      ),
      FitnessPlan(
        id: 'gen_2',
        title: 'Gentle Yoga Flow',
        description: 'Recovery-focused stretching and breathing',
        activityType: ActivityType.yoga,
        duration: Duration(minutes: shortDuration),
        targetHRZone: HRZone.resting,
        confidence: 0.0,
        isPriority: false,
        benefits: ['Flexibility', 'Stress relief', 'Better sleep'],
        caloriesBurn: _estimateCalories(ActivityType.yoga, shortDuration),
      ),
      FitnessPlan(
        id: 'gen_3',
        title: 'Strength Basics',
        description: isSedentary
            ? 'Beginner-friendly resistance training with minimal load'
            : 'Light resistance training for muscle tone',
        activityType: ActivityType.strength,
        duration: Duration(minutes: mediumDuration),
        targetHRZone: HRZone.moderate,
        confidence: 0.0,
        isPriority: false,
        benefits: ['Muscle strength', 'Bone density', 'Metabolism'],
        caloriesBurn: _estimateCalories(ActivityType.strength, mediumDuration),
      ),
    ];
  }

  List<FitnessPlan> get _filteredPlans {
    if (_selectedFilter == 'All') return _plans;
    
    return _plans.where((plan) {
      switch (_selectedFilter) {
        case 'Cardio':
          return plan.activityType == ActivityType.walking ||
                 plan.activityType == ActivityType.running ||
                 plan.activityType == ActivityType.cycling;
        case 'Strength':
          return plan.activityType == ActivityType.strength;
        case 'Recovery':
          return plan.activityType == ActivityType.yoga ||
                 plan.activityType == ActivityType.stretching ||
                 plan.activityType == ActivityType.meditation;
        case 'HIIT':
          return plan.activityType == ActivityType.hiit;
        default:
          return true;
      }
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return Container(
      decoration: BoxDecoration(
        image: DecorationImage(
          image: const AssetImage('assets/images/workout_bg.png'),
          fit: BoxFit.cover,
          colorFilter: ColorFilter.mode(
            brightness == Brightness.dark
                ? Colors.black.withOpacity(0.6)
                : Colors.white.withOpacity(0.85),
            brightness == Brightness.dark ? BlendMode.darken : BlendMode.lighten,
          ),
        ),
      ),
      child: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadPlans,
              child: CustomScrollView(
                slivers: [
                  // Inline header (title + Recovery button)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Fitness Plans',
                            style: AdaptivTypography.screenTitle,
                          ),
                          TextButton.icon(
                            onPressed: () {
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (context) =>
                                      RecoveryScreen(apiClient: widget.apiClient),
                                ),
                              );
                            },
                            icon: const Icon(Icons.spa, size: 18),
                            label: const Text('Recovery'),
                            style: TextButton.styleFrom(
                              foregroundColor: AdaptivColors.primary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // Week view
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: WeekView(
                        selectedDate: _selectedDate,
                        onDateSelected: (date) {
                          setState(() {
                            _selectedDate = date;
                          });
                        },
                      ),
                    ),
                  ),
                  // Filter chips
                  SliverToBoxAdapter(
                    child: _buildFilterChips(),
                  ),
                  // AI Recommendation Header
                  SliverToBoxAdapter(
                    child: _buildAIHeader(),
                  ),
                  // Plans list
                  SliverPadding(
                    padding: const EdgeInsets.all(16),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final plan = _filteredPlans[index];
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: _buildPlanCard(plan),
                          );
                        },
                        childCount: _filteredPlans.length,
                      ),
                    ),
                  ),
                  // Weekly summary
                  SliverToBoxAdapter(
                    child: _buildWeeklySummary(),
                  ),
                  const SliverToBoxAdapter(
                    child: SizedBox(height: 100),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildFilterChips() {
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _filters.length,
        itemBuilder: (context, index) {
          final filter = _filters[index];
          final isSelected = filter == _selectedFilter;
          
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(filter),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  _selectedFilter = filter;
                });
              },
              backgroundColor: AdaptivColors.bg200,
              selectedColor: AdaptivColors.primaryBg,
              checkmarkColor: AdaptivColors.primary,
              labelStyle: AdaptivTypography.label.copyWith(
                color: isSelected ? AdaptivColors.primary : AdaptivColors.text600,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: BorderSide(
                  color: isSelected ? AdaptivColors.primary : AdaptivColors.border300,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildAIHeader() {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AdaptivColors.primary,
            AdaptivColors.primary.withOpacity(0.8),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AdaptivColors.primary.withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.auto_awesome,
              color: Colors.white,
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI-Powered Plans',
                  style: AdaptivTypography.subtitle1.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Personalized based on your heart data and fitness goals.',
                  style: AdaptivTypography.bodySmall.copyWith(
                    color: Colors.white.withOpacity(0.9),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlanCard(FitnessPlan plan) {
    return RecommendationCard(
      activityType: plan.activityType,
      title: plan.title,
      description: plan.description,
      duration: plan.duration,
      targetHRZone: plan.targetHRZone,
      confidence: plan.confidence,
      isPriority: plan.isPriority,
      onStart: () => _startWorkout(plan),
      onDismiss: () => _dismissPlan(plan),
    );
  }

  Widget _buildWeeklySummary() {
    final stats = _computeThisWeek(_activities);
    final hasData = stats.sessionsCompleted > 0;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AdaptivColors.border300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.calendar_month,
                size: 20,
                color: AdaptivColors.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'This Week',
                style: AdaptivTypography.subtitle1.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSummaryItem(
                'Active Days',
                hasData ? stats.activeDays.toString() : '—',
                Icons.directions_run,
              ),
              _buildSummaryItem(
                'Minutes',
                hasData ? stats.totalMinutes.toString() : '—',
                Icons.timer,
              ),
              _buildSummaryItem(
                'Calories',
                hasData ? stats.totalCalories.toString() : '—',
                Icons.local_fire_department,
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Weekly goal progress
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Weekly Goal',
                    style: AdaptivTypography.label.copyWith(
                      color: AdaptivColors.text600,
                    ),
                  ),
                  Text(
                    '${stats.sessionsCompleted}/${_WeekStats.sessionsGoal} workouts',
                    style: AdaptivTypography.label.copyWith(
                      color: AdaptivColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: stats.goalFraction.clamp(0.0, 1.0),
                  backgroundColor: AdaptivColors.bg200,
                  valueColor: AlwaysStoppedAnimation(AdaptivColors.stable),
                  minHeight: 8,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 24, color: AdaptivColors.primary),
        const SizedBox(height: 4),
        Text(
          value,
          style: AdaptivTypography.metricValue.copyWith(
            color: AdaptivColors.text900,
          ),
        ),
        Text(
          label,
          style: AdaptivTypography.overline.copyWith(
            color: AdaptivColors.text500,
          ),
        ),
      ],
    );
  }

  void _startWorkout(FitnessPlan plan) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => WorkoutScreen(
          apiClient: widget.apiClient,
          initialExercise: _activityTypeToExerciseKey(plan.activityType),
        ),
      ),
    );
  }

  String _activityTypeToExerciseKey(ActivityType activityType) {
    switch (activityType) {
      case ActivityType.walking:
        return 'walking';
      case ActivityType.running:
      case ActivityType.hiit:
        return 'light_jogging';
      case ActivityType.cycling:
        return 'cycling';
      case ActivityType.swimming:
        return 'swimming';
      case ActivityType.yoga:
        return 'yoga';
      case ActivityType.strength:
        return 'resistance_bands';
      case ActivityType.stretching:
        return 'stretching';
      case ActivityType.meditation:
      case ActivityType.other:
        return 'walking';
    }
  }

  void _dismissPlan(FitnessPlan plan) {
    setState(() {
      _plans.removeWhere((p) => p.id == plan.id);
    });
  }
}

/// Data model for fitness plans
class FitnessPlan {
  final String id;
  final String title;
  final String description;
  final ActivityType activityType;
  final Duration duration;
  final HRZone targetHRZone;
  final double confidence;
  final bool isPriority;
  final List<String> benefits;
  final int caloriesBurn;

  FitnessPlan({
    required this.id,
    required this.title,
    required this.description,
    required this.activityType,
    required this.duration,
    required this.targetHRZone,
    required this.confidence,
    this.isPriority = false,
    this.benefits = const [],
    this.caloriesBurn = 0,
  });
}
