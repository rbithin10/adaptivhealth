/*
Health Screen - Central hub for health metrics and data.

Displays comprehensive health information including:
- Vital signs overview (HR, BP, SpO2, HRV)
- Health trends and charts
- Risk assessments
- Activity history
*/

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/widgets.dart';
import '../widgets/edge_ai_status_card.dart';
import '../widgets/ai_coach_overlay.dart';
import '../services/api_client.dart';
import '../services/edge_ai_store.dart';

class HealthScreen extends StatefulWidget {
  final ApiClient apiClient;

  const HealthScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<HealthScreen> createState() => _HealthScreenState();
}

class _HealthScreenState extends State<HealthScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  Map<String, dynamic> _healthData = {};

  // Profile fields used by edge ML predictions
  int? _userAge;
  int? _baselineHr;
  int? _maxSafeHr;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadHealthData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadHealthData() async {
    setState(() => _isLoading = true);

    // Load user profile + latest vitals in parallel
    final results = await Future.wait([
      widget.apiClient.getCurrentUser().catchError((_) => <String, dynamic>{}),
      widget.apiClient.getLatestVitals().catchError(
        (_) => <String, dynamic>{
          'heart_rate': 72,
          'spo2': 98,
          'systolic_bp': 120,
          'diastolic_bp': 80,
          'hrv': 45,
        },
      ),
    ]);

    final profile = results[0] as Map<String, dynamic>;
    final vitals  = results[1] as Map<String, dynamic>;

    // Extract profile fields needed for edge ML risk prediction
    final age = (profile['age'] as num?)?.toInt();
    final baselineHr = (profile['baseline_hr'] as num?)?.toInt();
    if (age != null && age > 0) {
      _userAge     = age;
      _baselineHr  = baselineHr ?? 72;
      _maxSafeHr   = 220 - age;
    }

    _healthData = {
      'vitals': vitals.isNotEmpty ? vitals : {
        'heart_rate': 72,
        'spo2': 98,
        'systolic_bp': 120,
        'diastolic_bp': 80,
        'hrv': 45,
      },
      'trends': _getDemoTrends(),
      'history': _getDemoHistory(),
    };

    setState(() => _isLoading = false);
  }

  List<Map<String, dynamic>> _getDemoTrends() {
    return [
      {'date': 'Mon', 'hr': 72, 'spo2': 98, 'bp': 118},
      {'date': 'Tue', 'hr': 75, 'spo2': 97, 'bp': 120},
      {'date': 'Wed', 'hr': 70, 'spo2': 98, 'bp': 119},
      {'date': 'Thu', 'hr': 73, 'spo2': 98, 'bp': 121},
      {'date': 'Fri', 'hr': 71, 'spo2': 99, 'bp': 118},
      {'date': 'Sat', 'hr': 68, 'spo2': 98, 'bp': 116},
      {'date': 'Sun', 'hr': 72, 'spo2': 98, 'bp': 120},
    ];
  }

  List<Map<String, dynamic>> _getDemoHistory() {
    return [
      {
        'type': 'measurement',
        'title': 'Blood Pressure',
        'value': '120/80 mmHg',
        'time': '2 hours ago',
        'status': 'normal',
      },
      {
        'type': 'workout',
        'title': 'Morning Walk',
        'value': '30 min • 2.1 km',
        'time': '5 hours ago',
        'status': 'completed',
      },
      {
        'type': 'measurement',
        'title': 'Heart Rate',
        'value': '72 BPM',
        'time': '6 hours ago',
        'status': 'normal',
      },
      {
        'type': 'alert',
        'title': 'High HR Detected',
        'value': '145 BPM during rest',
        'time': 'Yesterday',
        'status': 'warning',
      },
    ];
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).pop(),
          ),
          title: Text('Health Insights', style: AdaptivTypography.screenTitle),
          actions: [
            IconButton(
              icon: const Icon(Icons.share_outlined),
              color: AdaptivColors.text600,
              onPressed: () {
                // Export health report
              },
            ),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _loadHealthData,
                child: CustomScrollView(
                  slivers: [
                    // Header
                    SliverToBoxAdapter(
                      child: _buildHeader(),
                    ),
                    // Vital cards grid
                    SliverToBoxAdapter(
                      child: _buildVitalsSection(),
                    ),
                    // Tab bar
                    SliverPersistentHeader(
                      pinned: true,
                      delegate: _TabBarDelegate(
                        tabController: _tabController,
                      ),
                    ),
                    // Tab content
                    SliverFillRemaining(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          _buildTrendsTab(),
                          _buildHistoryTab(),
                          _buildInsightsTab(),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Health score summary
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AdaptivColors.stable,
                  AdaptivColors.stable.withOpacity(0.8),
                ],
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Health Score',
                      style: AdaptivTypography.label.copyWith(
                        color: Colors.white.withOpacity(0.9),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '85',
                      style: AdaptivTypography.metricValue.copyWith(
                        color: Colors.white,
                        fontSize: 36,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.trending_up, color: Colors.white, size: 16),
                      const SizedBox(width: 4),
                      Text(
                        '+3 this week',
                        style: AdaptivTypography.label.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVitalsSection() {
    final vitals = _healthData['vitals'] as Map<String, dynamic>? ?? {};
    final hr = vitals['heart_rate'] ?? 72;
    final spo2 = vitals['spo2'] ?? 98;
    final systolic = vitals['systolic_bp'] ?? 120;
    final diastolic = vitals['diastolic_bp'] ?? 80;
    final hrv = vitals['hrv'] ?? 45;

    // Feed vitals to edge AI when they load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      try {
        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
        if (edgeStore.isReady && hr > 0) {
          edgeStore.processVitals(
            heartRate: hr,
            spo2: spo2 > 0 ? spo2 : null,
            bpSystolic: systolic > 0 ? systolic : null,
            age: _userAge,
            baselineHr: _baselineHr,
            maxSafeHr: _maxSafeHr,
          );
        }
      } catch (e) {
        if (kDebugMode) {
          debugPrint('Error in _buildVitalsSection.feedEdgeAi: $e');
        }
      }
    });

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Edge AI status card — shows on-device risk + alerts
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AdaptivColors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.border300),
            ),
            child: const EdgeAiStatusCard(),
          ),
          // Risk badge from edge AI prediction
          Builder(builder: (context) {
            RiskLevel riskLevel = RiskLevel.low;
            try {
              final edgeStore = Provider.of<EdgeAiStore>(context);
              final prediction = edgeStore.latestPrediction;
              if (prediction != null) {
                final level = prediction.riskLevel.toLowerCase();
                riskLevel = RiskLevel.values.firstWhere(
                  (e) => e.name == level,
                  orElse: () => RiskLevel.low,
                );
              }
            } catch (_) {}
            return Row(
              children: [
                Expanded(child: RiskBadge(level: riskLevel, label: 'CV Risk')),
                const SizedBox(width: 12),
                Expanded(
                  child: TargetZoneIndicator(
                    currentBPM: hr as int,
                    maxHR: _maxSafeHr ?? 190,
                    showLabels: false,
                    showCurrentValue: true,
                  ),
                ),
              ],
            );
          }),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(
                'Current Vitals',
                style: AdaptivTypography.subtitle1.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              Text(
                'Just now',
                style: AdaptivTypography.label.copyWith(
                  color: AdaptivColors.stable,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                SizedBox(
                  width: 160,
                  child: VitalCard(
                    icon: Icons.favorite,
                    label: 'Heart Rate',
                    value: hr.toString(),
                    unit: 'BPM',
                    status: _getHRStatus(hr),
                    trend: [68.0, 70.0, 72.0, 71.0, 73.0, hr.toDouble()],
                    onTap: () => _showVitalDetail('Heart Rate'),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 160,
                  child: VitalCard(
                    icon: Icons.air,
                    label: 'SpO2',
                    value: spo2.toString(),
                    unit: '%',
                    status: spo2 < 95 ? VitalStatus.warning : VitalStatus.safe,
                    trend: [97.0, 98.0, 98.0, 97.0, 98.0, spo2.toDouble()],
                    onTap: () => _showVitalDetail('SpO2'),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 160,
                  child: VitalCard(
                    icon: Icons.water_drop,
                    label: 'Blood Pressure',
                    value: '$systolic/$diastolic',
                    unit: 'mmHg',
                    status: _getBPStatus(systolic),
                    onTap: () => _showVitalDetail('Blood Pressure'),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 160,
                  child: VitalCard(
                    icon: Icons.timeline,
                    label: 'HRV',
                    value: hrv.toString(),
                    unit: 'ms',
                    status: hrv > 40 ? VitalStatus.safe : VitalStatus.caution,
                    trend: [42.0, 44.0, 45.0, 43.0, 46.0, hrv.toDouble()],
                    onTap: () => _showVitalDetail('HRV'),
                  ),
                ),
                const SizedBox(width: 12),
              ],
            ),
          ),
        ],
      ),
    );
  }

  VitalStatus _getHRStatus(int hr) {
    if (hr < 50 || hr > 120) return VitalStatus.warning;
    if (hr > 100) return VitalStatus.caution;
    return VitalStatus.safe;
  }

  VitalStatus _getBPStatus(int systolic) {
    if (systolic > 140) return VitalStatus.critical;
    if (systolic > 130) return VitalStatus.warning;
    return VitalStatus.safe;
  }

  void _showVitalDetail(String vital) {
    // Navigate to detailed vital view
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$vital details coming soon')),
    );
  }

  Widget _buildTrendsTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildTrendCard(
          'Heart Rate',
          '72 BPM avg',
          Icons.favorite,
          AdaptivColors.critical,
          'Stable this week',
        ),
        const SizedBox(height: 12),
        _buildTrendCard(
          'Blood Pressure',
          '118/78 avg',
          Icons.water_drop,
          AdaptivColors.primary,
          'Improved from last week',
        ),
        const SizedBox(height: 12),
        _buildTrendCard(
          'SpO2',
          '98% avg',
          Icons.air,
          AdaptivColors.stable,
          'Consistently normal',
        ),
        const SizedBox(height: 12),
        _buildTrendCard(
          'HRV',
          '45ms avg',
          Icons.timeline,
          const Color(0xFF9C27B0),
          'Good recovery capacity',
        ),
      ],
    );
  }

  Widget _buildTrendCard(
    String title,
    String value,
    IconData icon,
    Color color,
    String insight,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.border300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: AdaptivTypography.body),
                  Text(value, style: AdaptivTypography.metricValueSmall),
                ],
              ),
              const Spacer(),
              const Icon(Icons.chevron_right, color: AdaptivColors.text400),
            ],
          ),
          const SizedBox(height: 12),
          // Mini chart placeholder
          Container(
            height: 60,
            decoration: BoxDecoration(
              color: color.withOpacity(0.05),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                'Trend chart',
                style: AdaptivTypography.caption.copyWith(color: color),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.lightbulb_outline, size: 14, color: AdaptivColors.text500),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  insight,
                  style: AdaptivTypography.caption,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryTab() {
    final history = _healthData['history'] as List<Map<String, dynamic>>? ?? [];
    
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: history.length,
      itemBuilder: (context, index) {
        final item = history[index];
        return _buildHistoryItem(item);
      },
    );
  }

  Widget _buildHistoryItem(Map<String, dynamic> item) {
    final type = item['type'] as String;
    final title = item['title'] as String;
    final value = item['value'] as String;
    final time = item['time'] as String;
    final status = item['status'] as String;

    IconData icon;
    Color color;
    
    switch (type) {
      case 'measurement':
        icon = Icons.monitor_heart;
        color = AdaptivColors.primary;
        break;
      case 'workout':
        icon = Icons.directions_run;
        color = AdaptivColors.stable;
        break;
      case 'alert':
        icon = Icons.warning_amber;
        color = AdaptivColors.warning;
        break;
      default:
        icon = Icons.info;
        color = AdaptivColors.text500;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.white,
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
            child: Icon(icon, color: color, size: 20),
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
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: AdaptivTypography.bodySmall.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                time,
                style: AdaptivTypography.caption,
              ),
              const SizedBox(height: 4),
              _buildStatusBadge(status),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    String label;
    
    switch (status) {
      case 'normal':
        color = AdaptivColors.stable;
        label = 'Normal';
        break;
      case 'completed':
        color = AdaptivColors.primary;
        label = 'Done';
        break;
      case 'warning':
        color = AdaptivColors.warning;
        label = 'Alert';
        break;
      default:
        color = AdaptivColors.text500;
        label = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: AdaptivTypography.overline.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildInsightsTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildInsightCard(
          'Heart Health',
          'Your resting heart rate has been stable this week. Keep up the good work!',
          Icons.favorite,
          AdaptivColors.stable,
        ),
        const SizedBox(height: 12),
        _buildInsightCard(
          'Recovery',
          'Your HRV indicates good recovery. You\'re ready for moderate intensity exercise.',
          Icons.battery_charging_full,
          AdaptivColors.primary,
        ),
        const SizedBox(height: 12),
        _buildInsightCard(
          'Sleep Impact',
          'Better sleep quality correlates with lower resting HR. Consider 7-8hrs tonight.',
          Icons.bedtime,
          const Color(0xFF673AB7),
        ),
        const SizedBox(height: 12),
        _buildInsightCard(
          'Activity Goal',
          'You\'re 80% towards your weekly activity goal. 2 more sessions to go!',
          Icons.emoji_events,
          AdaptivColors.warning,
        ),
      ],
    );
  }

  Widget _buildInsightCard(
    String title,
    String description,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AdaptivTypography.body.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: AdaptivTypography.bodySmall.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  final TabController tabController;

  _TabBarDelegate({required this.tabController});

  @override
  Widget build(context, shrinkOffset, overlapsContent) {
    return Container(
      color: AdaptivColors.white,
      child: TabBar(
        controller: tabController,
        labelColor: AdaptivColors.primary,
        unselectedLabelColor: AdaptivColors.text500,
        indicatorColor: AdaptivColors.primary,
        labelStyle: AdaptivTypography.label.copyWith(fontWeight: FontWeight.w600),
        tabs: const [
          Tab(text: 'Trends'),
          Tab(text: 'History'),
          Tab(text: 'Insights'),
        ],
      ),
    );
  }

  @override
  double get maxExtent => 48;

  @override
  double get minExtent => 48;

  @override
  bool shouldRebuild(covariant _TabBarDelegate oldDelegate) => false;
}
