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

class FitnessPlansScreen extends StatefulWidget {
  final ApiClient apiClient;

  const FitnessPlansScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<FitnessPlansScreen> createState() => _FitnessPlansScreenState();
}

class _FitnessPlansScreenState extends State<FitnessPlansScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  List<FitnessPlan> _plans = [];
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
    
    // Load AI-recommended plans from API
    try {
      // For now, use demo data
      await Future.delayed(const Duration(milliseconds: 500));
      _plans = _getDemoPlans();
    } catch (e) {
      _plans = _getDemoPlans();
    }
    
    setState(() => _isLoading = false);
  }

  List<FitnessPlan> _getDemoPlans() {
    return [
      FitnessPlan(
        id: '1',
        title: 'Heart Health Walk',
        description: 'Gentle cardio to improve cardiovascular endurance',
        activityType: ActivityType.walking,
        duration: const Duration(minutes: 30),
        targetHRZone: HRZone.light,
        confidence: 0.92,
        isPriority: true,
        benefits: ['Improves circulation', 'Lowers blood pressure', 'Reduces stress'],
        caloriesBurn: 150,
      ),
      FitnessPlan(
        id: '2',
        title: 'Zone 2 Training',
        description: 'Build aerobic base with steady-state cardio',
        activityType: ActivityType.cycling,
        duration: const Duration(minutes: 45),
        targetHRZone: HRZone.moderate,
        confidence: 0.85,
        isPriority: false,
        benefits: ['Fat burning', 'Endurance building', 'Heart efficiency'],
        caloriesBurn: 320,
      ),
      FitnessPlan(
        id: '3',
        title: 'Gentle Yoga Flow',
        description: 'Recovery-focused stretching and breathing',
        activityType: ActivityType.yoga,
        duration: const Duration(minutes: 20),
        targetHRZone: HRZone.resting,
        confidence: 0.88,
        isPriority: false,
        benefits: ['Flexibility', 'Stress relief', 'Better sleep'],
        caloriesBurn: 80,
      ),
      FitnessPlan(
        id: '4',
        title: 'Interval Training',
        description: 'Short bursts of intensity for heart strength',
        activityType: ActivityType.hiit,
        duration: const Duration(minutes: 25),
        targetHRZone: HRZone.hard,
        confidence: 0.75,
        isPriority: false,
        benefits: ['VO2 max improvement', 'Metabolism boost', 'Time efficient'],
        caloriesBurn: 280,
      ),
      FitnessPlan(
        id: '5',
        title: 'Strength Basics',
        description: 'Light resistance training for muscle tone',
        activityType: ActivityType.strength,
        duration: const Duration(minutes: 35),
        targetHRZone: HRZone.moderate,
        confidence: 0.82,
        isPriority: false,
        benefits: ['Muscle strength', 'Bone density', 'Metabolism'],
        caloriesBurn: 200,
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
    return Scaffold(
      backgroundColor: AdaptivColors.bg100,
      appBar: AppBar(
        backgroundColor: AdaptivColors.white,
        elevation: 0,
        title: Text(
          'Fitness Plans',
          style: AdaptivTypography.screenTitle,
        ),
        actions: [
          // Recovery button - navigate to recovery screen
          TextButton.icon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => RecoveryScreen(apiClient: widget.apiClient),
                ),
              );
            },
            icon: const Icon(Icons.spa, size: 18),
            label: const Text('Recovery'),
            style: TextButton.styleFrom(
              foregroundColor: AdaptivColors.primary,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.tune, color: AdaptivColors.text600),
            onPressed: () {
              // Show filter options
            },
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(88),
          child: Column(
            children: [
              Padding(
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
              _buildFilterChips(),
            ],
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadPlans,
              child: CustomScrollView(
                slivers: [
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
              _buildSummaryItem('Active Days', '4', Icons.directions_run),
              _buildSummaryItem('Minutes', '120', Icons.timer),
              _buildSummaryItem('Calories', '680', Icons.local_fire_department),
            ],
          ),
          const SizedBox(height: 16),
          // Weekly progress bar
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
                    '4/5 workouts',
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
                  value: 0.8,
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
    // Navigate to workout session with this plan
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Starting ${plan.title}...'),
        backgroundColor: AdaptivColors.primary,
      ),
    );
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
