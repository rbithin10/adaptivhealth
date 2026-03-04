/*
Health Screen - Central hub for health metrics and longitudinal data.

Displays:
- Vital signs overview with Edge AI risk badge
- Interactive expandable trend charts (7D / 30D) powered by fl_chart
- Clinical event timeline with filter chips (All / Vitals / Workouts / Alerts)
- AI-generated health insights via the NL Coach endpoint with static fallback
*/

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
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

  // Latest ML risk score (0.0–1.0); null = not yet loaded
  double? _riskScore;

  // Timestamp of last successful data fetch
  DateTime? _lastSync;

  // Trends tab — expanded metric key ('hr' | 'bp' | 'spo2' | 'hrv' | null)
  String? _expandedMetric;

  // Trends tab — chart time window in days
  int _trendRange = 7;

  // History tab — active filter
  String _historyFilter = 'all';

  // Insights tab
  bool _isInsightsLoading = false;
  List<Map<String, dynamic>> _aiInsights = [];
  bool _insightsLoaded = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    // Auto-load AI insights when the Insights tab is first opened
    _tabController.addListener(() {
      if (_tabController.index == 2 && !_insightsLoaded) {
        _loadAiInsights();
      }
    });
    _loadHealthData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadHealthData() async {
    setState(() => _isLoading = true);

    // Load all data sources in parallel
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
      widget.apiClient.getVitalHistory(days: 30).catchError(
        (_) => <dynamic>[],
      ),
      widget.apiClient.getActivities(limit: 50).catchError(
        (_) => <dynamic>[],
      ),
      widget.apiClient.getAlerts(page: 1, perPage: 50).catchError(
        (_) => <String, dynamic>{},
      ),
      widget.apiClient.getLatestRiskAssessment().catchError(
        (_) => <String, dynamic>{},
      ),
    ]);

    final profile       = results[0] as Map<String, dynamic>;
    final vitals        = results[1] as Map<String, dynamic>;
    final vitalsHistory = results[2] as List<dynamic>;
    final activities    = results[3] as List<dynamic>;
    final alertsPayload = results[4] as Map<String, dynamic>;
    final riskPayload   = results[5] as Map<String, dynamic>;

    // Extract profile fields for edge ML
    final age        = (profile['age'] as num?)?.toInt();
    final baselineHr = (profile['baseline_hr'] as num?)?.toInt();
    if (age != null && age > 0) {
      _userAge    = age;
      _baselineHr = baselineHr ?? 72;
      _maxSafeHr  = 220 - age;
    }

    // ML risk score
    final rawRisk = riskPayload['risk_score'];
    if (rawRisk != null) {
      _riskScore = (rawRisk as num).toDouble();
    }

    // Normalise alerts list from different response shapes
    List<dynamic> alertsList = [];
    if (alertsPayload['alerts'] is List) {
      alertsList = alertsPayload['alerts'] as List<dynamic>;
    } else if (alertsPayload['items'] is List) {
      alertsList = alertsPayload['items'] as List<dynamic>;
    }

    _healthData = {
      'vitals': vitals.isNotEmpty
          ? vitals
          : {
              'heart_rate': 72,
              'spo2': 98,
              'systolic_bp': 120,
              'diastolic_bp': 80,
              'hrv': 45,
            },
      'vitalsHistory': vitalsHistory,
      'activities': activities,
      'alerts': alertsList,
    };

    _lastSync = DateTime.now();
    setState(() => _isLoading = false);
  }

  /// Request personalised health insights from the AI coach.
  Future<void> _loadAiInsights() async {
    if (_isInsightsLoading || _insightsLoaded) return;
    setState(() => _isInsightsLoading = true);

    final vitals   = _healthData['vitals'] as Map<String, dynamic>? ?? {};
    final hr       = vitals['heart_rate'] ?? 72;
    final spo2     = vitals['spo2'] ?? 98;
    final systolic = vitals['systolic_bp'] ?? 120;

    final prompt =
        'As a cardiovascular health coach, provide 4 short personalised health '
        'insights for a patient whose latest readings are: heart rate $hr BPM, '
        'SpO2 $spo2%, systolic BP ${systolic}mmHg. '
        'Respond with a JSON array only, each item having "title" and '
        '"description" string fields. Keep descriptions under 20 words.';

    try {
      final raw    = await widget.apiClient.postNLChat(prompt, []);
      final parsed = _parseAiInsights(raw);
      setState(() {
        _aiInsights     = parsed;
        _insightsLoaded = true;
      });
    } catch (_) {
      // AI unavailable — static fallback will show
      setState(() => _insightsLoaded = true);
    } finally {
      setState(() => _isInsightsLoading = false);
    }
  }

  List<Map<String, dynamic>> _parseAiInsights(String response) {
    try {
      final start = response.indexOf('[');
      final end   = response.lastIndexOf(']');
      if (start < 0 || end <= start) return [];
      final dynamic decoded = jsonDecode(response.substring(start, end + 1));
      if (decoded is List) {
        return decoded
            .whereType<Map>()
            .map((m) => Map<String, dynamic>.from(m))
            .where((m) => m['title'] != null && m['description'] != null)
            .toList();
      }
    } catch (_) {}
    return [];
  }

  // -------------------------------------------------------------------------
  // Derived health score from ML risk (0 = highest risk, 100 = lowest risk)
  // -------------------------------------------------------------------------

  int get _healthScore {
    if (_riskScore == null) return 85;
    return ((1.0 - _riskScore!) * 100).round().clamp(10, 100);
  }

  String _syncLabel() {
    if (_lastSync == null) return 'Loading…';
    final diff = DateTime.now().difference(_lastSync!);
    if (diff.inSeconds < 60) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }

  // -------------------------------------------------------------------------
  // Chart helpers — build FlSpot list from vitals history
  // -------------------------------------------------------------------------

  List<FlSpot> _buildSpots(String metricKey) {
    final raw    = _healthData['vitalsHistory'] as List<dynamic>? ?? [];
    final cutoff = DateTime.now().subtract(Duration(days: _trendRange));

    final filtered = raw.where((v) {
      if (v is! Map) return false;
      final ts = v['timestamp'] as String?;
      if (ts == null) return false;
      final dt = DateTime.tryParse(ts);
      return dt != null && dt.isAfter(cutoff);
    }).toList()
      ..sort((a, b) {
        final dtA = DateTime.parse((a as Map)['timestamp'] as String);
        final dtB = DateTime.parse((b as Map)['timestamp'] as String);
        return dtA.compareTo(dtB);
      });

    if (filtered.isEmpty) {
      // Fall back to demo data as a flat-ish reference line
      return _getDemoTrends().asMap().entries.map((e) {
        final row = e.value;
        double y;
        switch (metricKey) {
          case 'hr':   y = (row['hr']   as num).toDouble(); break;
          case 'bp':   y = (row['bp']   as num).toDouble(); break;
          case 'spo2': y = (row['spo2'] as num).toDouble(); break;
          default:     y = 45.0;
        }
        return FlSpot(e.key.toDouble(), y);
      }).toList();
    }

    return filtered.asMap().entries.map((entry) {
      final v = entry.value as Map;
      double y;
      switch (metricKey) {
        case 'hr':   y = (v['heart_rate']  as num? ?? 72).toDouble();  break;
        case 'bp':   y = (v['systolic_bp'] as num? ?? 120).toDouble(); break;
        case 'spo2': y = (v['spo2']        as num? ?? 98).toDouble();  break;
        case 'hrv':  y = (v['hrv']         as num? ?? 45).toDouble();  break;
        default:     y = 0.0;
      }
      return FlSpot(entry.key.toDouble(), y);
    }).toList();
  }

  bool get _hasRealHistory {
    return (_healthData['vitalsHistory'] as List<dynamic>? ?? []).isNotEmpty;
  }

  // -------------------------------------------------------------------------
  // History tab helpers
  // -------------------------------------------------------------------------

  List<Map<String, dynamic>> _buildMergedHistory() {
    final vitalsHistory = _healthData['vitalsHistory'] as List<dynamic>? ?? [];
    final activities    = _healthData['activities']    as List<dynamic>? ?? [];
    final alerts        = _healthData['alerts']        as List<dynamic>? ?? [];

    final List<Map<String, dynamic>> combined = [];

    for (final v in vitalsHistory) {
      if (v is! Map) continue;
      combined.add({
        'type':         'vitals',
        'timestamp':    v['timestamp'] as String? ?? '',
        'heart_rate':   v['heart_rate'],
        'spo2':         v['spo2'],
        'systolic_bp':  v['systolic_bp'],
        'diastolic_bp': v['diastolic_bp'],
      });
    }

    for (final a in activities) {
      if (a is! Map) continue;
      combined.add({
        'type':              'workout',
        'timestamp':         a['start_time']   as String?
            ?? a['created_at'] as String? ?? '',
        'activity_type':     a['activity_type'],
        'duration_minutes':  a['duration_minutes'],
        'peak_heart_rate':   a['peak_heart_rate'],
        'avg_heart_rate':    a['avg_heart_rate'],
      });
    }

    for (final al in alerts) {
      if (al is! Map) continue;
      combined.add({
        'type':      'alert',
        'timestamp': al['created_at'] as String?
            ?? al['timestamp'] as String? ?? '',
        'title':     al['title'],
        'message':   al['message'],
        'severity':  al['severity'],
      });
    }

    // Sort descending
    combined.sort((a, b) =>
        _parseTs(b['timestamp'] as String?).compareTo(
            _parseTs(a['timestamp'] as String?)));

    // Apply filter
    if (_historyFilter == 'all') return combined;
    final typeKey = {'vitals': 'vitals', 'workouts': 'workout', 'alerts': 'alert'}[
        _historyFilter] ?? 'vitals';
    return combined.where((e) => e['type'] == typeKey).toList();
  }

  DateTime _parseTs(String? ts) {
    if (ts == null || ts.isEmpty) return DateTime(2000);
    return DateTime.tryParse(ts) ?? DateTime(2000);
  }

  List<Map<String, dynamic>> _groupByDate(List<Map<String, dynamic>> events) {
    final Map<String, List<Map<String, dynamic>>> sections = {};
    final now       = DateTime.now();
    final today     = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));

    const dayNames   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const monthNames = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];

    for (final e in events) {
      final dt  = _parseTs(e['timestamp'] as String?);
      final day = DateTime(dt.year, dt.month, dt.day);

      String label;
      if (day == today) {
        label = 'Today';
      } else if (day == yesterday) {
        label = 'Yesterday';
      } else {
        label = '${dayNames[day.weekday - 1]} '
            '${day.day.toString().padLeft(2, '0')} '
            '${monthNames[day.month - 1]}';
      }

      sections.putIfAbsent(label, () => []).add(e);
    }

    return sections.entries
        .map((entry) => <String, dynamic>{'label': entry.key, 'items': entry.value})
        .toList();
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

  // -------------------------------------------------------------------------
  // Share — copies a plain-text health summary to the system clipboard
  // -------------------------------------------------------------------------

  void _shareHealthSummary() {
    final vitals    = _healthData['vitals'] as Map<String, dynamic>? ?? {};
    final hr        = vitals['heart_rate'] ?? '—';
    final spo2      = vitals['spo2'] ?? '—';
    final systolic  = vitals['systolic_bp'] ?? '—';
    final diastolic = vitals['diastolic_bp'] ?? '—';
    final hrv       = vitals['hrv'] ?? '—';
    final score     = _riskScore == null ? '—' : _healthScore.toString();

    final summary =
        'AdaptivHealth Report — '
        '${DateTime.now().toLocal().toString().split('.').first}\n'
        '─────────────────────────\n'
        'Health Score   : $score / 100\n'
        'Heart Rate     : $hr BPM\n'
        'SpO2           : $spo2 %\n'
        'Blood Pressure : $systolic/$diastolic mmHg\n'
        'HRV            : $hrv ms\n'
        '─────────────────────────\n'
        'Generated by AdaptivHealth';

    Clipboard.setData(ClipboardData(text: summary));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Health summary copied to clipboard'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          foregroundColor: AdaptivColors.getTextColor(brightness),
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            color: AdaptivColors.getTextColor(brightness),
            onPressed: () => Navigator.of(context).pop(),
          ),
          title: Text(
            'Health Insights',
            style: AdaptivTypography.screenTitle.copyWith(
              color: AdaptivColors.getTextColor(brightness),
              fontSize: 20,
            ),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.share_outlined),
              color: AdaptivColors.getTextColor(brightness),
              tooltip: 'Copy health summary',
              onPressed: _shareHealthSummary,
            ),
          ],
        ),
        body: Container(
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/health_bg1.png'),
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
            : RefreshIndicator(
                onRefresh: _loadHealthData,
                child: CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(child: _buildHeader(brightness)),
                    SliverToBoxAdapter(child: _buildVitalsSection(brightness)),
                    SliverPersistentHeader(
                      pinned: true,
                      delegate: _TabBarDelegate(
                        tabController: _tabController,
                        brightness: brightness,
                      ),
                    ),
                    SliverFillRemaining(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          _buildTrendsTab(brightness),
                          _buildHistoryTab(brightness),
                          _buildInsightsTab(brightness),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
        ),
      ),
    );
  }

  Widget _buildHeader(Brightness brightness) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Container(
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
                  _riskScore == null ? '—' : _healthScore.toString(),
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
                  const Icon(Icons.sync, color: Colors.white, size: 16),
                  const SizedBox(width: 4),
                  Text(
                    _syncLabel(),
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
    );
  }

  Widget _buildVitalsSection(Brightness brightness) {
    final vitals   = _healthData['vitals'] as Map<String, dynamic>? ?? {};
    final hr       = (vitals['heart_rate'] as num?)?.toInt() ?? 72;
    final spo2     = (vitals['spo2']        as num?)?.toInt() ?? 98;
    final systolic = (vitals['systolic_bp'] as num?)?.toInt() ?? 120;
    final diastolic= (vitals['diastolic_bp'] as num?)?.toInt() ?? 80;
    final hrv      = (vitals['hrv']          as num?)?.toInt() ?? 45;

    // Feed vitals to edge AI
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
        if (kDebugMode) debugPrint('HealthScreen.feedEdgeAi: $e');
      }
    });

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Edge AI status card (brightness-aware surface)
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AdaptivColors.getSurfaceColor(brightness),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
            ),
            child: const EdgeAiStatusCard(),
          ),
          // Risk badge + target zone
          Builder(builder: (ctx) {
            RiskLevel riskLevel = RiskLevel.low;
            try {
              final edgeStore = Provider.of<EdgeAiStore>(ctx);
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
                    currentBPM: hr,
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
                style: AdaptivTypography.subtitle1.copyWith(fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              Text(
                'Just now',
                style: AdaptivTypography.labelFor(brightness)
                    .copyWith(color: AdaptivColors.stable),
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

  /// Switch to the Trends tab and expand the corresponding metric card.
  void _showVitalDetail(String vital) {
    final Map<String, String> vitalToKey = {
      'Heart Rate': 'hr',
      'SpO2':       'spo2',
      'Blood Pressure': 'bp',
      'HRV':        'hrv',
    };
    final key = vitalToKey[vital];
    if (key != null) {
      _tabController.animateTo(0); // switch to Trends tab
      setState(() => _expandedMetric = key);
    }
  }

  // -------------------------------------------------------------------------
  // Trends tab — expandable accordion cards with fl_chart LineChart
  // -------------------------------------------------------------------------

  Widget _buildTrendsTab(Brightness brightness) {
    final metrics = [
      _MetricDef(key: 'hr',   title: 'Heart Rate',      avgLabel: _avgLabel('hr'),   icon: Icons.favorite,    color: AdaptivColors.critical,          insight: 'Stable this week',            unit: 'BPM'),
      _MetricDef(key: 'bp',   title: 'Blood Pressure',  avgLabel: _avgLabel('bp'),   icon: Icons.water_drop,  color: AdaptivColors.primary,           insight: 'Monitor systolic trends',     unit: 'mmHg'),
      _MetricDef(key: 'spo2', title: 'SpO2',            avgLabel: _avgLabel('spo2'), icon: Icons.air,         color: AdaptivColors.stable,            insight: 'Consistently normal',         unit: '%'),
      _MetricDef(key: 'hrv',  title: 'HRV',             avgLabel: _avgLabel('hrv'),  icon: Icons.timeline,    color: const Color(0xFF9C27B0),         insight: 'Good recovery capacity',      unit: 'ms'),
    ];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        for (final m in metrics) ...[_buildTrendCard(m, brightness), const SizedBox(height: 12)],
      ],
    );
  }

  String _avgLabel(String metricKey) {
    final spots = _buildSpots(metricKey);
    if (spots.isEmpty) return '—';
    final avg = spots.map((s) => s.y).reduce((a, b) => a + b) / spots.length;
    switch (metricKey) {
      case 'hr':   return '${avg.round()} BPM avg';
      case 'spo2': return '${avg.round()}% avg';
      case 'bp':   return '${avg.round()} mmHg avg';
      case 'hrv':  return '${avg.round()}ms avg';
      default:     return '${avg.toStringAsFixed(1)} avg';
    }
  }

  Widget _buildTrendCard(_MetricDef m, Brightness brightness) {
    final isExpanded = _expandedMetric == m.key;
    final spots      = _buildSpots(m.key);
    final isDemoData = !_hasRealHistory;

    return GestureDetector(
      onTap: () => setState(() => _expandedMetric = isExpanded ? null : m.key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeInOut,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AdaptivColors.getSurfaceColor(brightness),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Card header row
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: m.color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(m.icon, color: m.color, size: 20),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(m.title, style: AdaptivTypography.body),
                    Text(m.avgLabel, style: AdaptivTypography.metricValueSmall),
                  ],
                ),
                const Spacer(),
                AnimatedRotation(
                  turns: isExpanded ? 0.25 : 0.0,
                  duration: const Duration(milliseconds: 280),
                  child: const Icon(Icons.chevron_right, color: AdaptivColors.text400),
                ),
              ],
            ),
            // Expandable chart section
            AnimatedSize(
              duration: const Duration(milliseconds: 280),
              curve: Curves.easeInOut,
              child: isExpanded
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 16),
                        // 7D / 30D range toggle
                        Row(
                          children: [
                            _rangeChip(7, brightness),
                            const SizedBox(width: 8),
                            _rangeChip(30, brightness),
                            const Spacer(),
                            if (isDemoData)
                              Text(
                                'Demo · syncs automatically',
                                style: AdaptivTypography.captionFor(brightness)
                                    .copyWith(fontStyle: FontStyle.italic),
                              ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        // Line chart
                        _buildLineChart(spots, m.color, isDemoData, brightness),
                        const SizedBox(height: 10),
                        // Insight caption
                        Row(
                          children: [
                            Icon(Icons.lightbulb_outline, size: 14,
                                color: AdaptivColors.getSecondaryTextColor(brightness)),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(m.insight,
                                  style: AdaptivTypography.captionFor(brightness)),
                            ),
                          ],
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _rangeChip(int days, Brightness brightness) {
    final selected = _trendRange == days;
    return GestureDetector(
      onTap: () => setState(() => _trendRange = days),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        decoration: BoxDecoration(
          color: selected ? AdaptivColors.primary : AdaptivColors.getSurfaceColor(brightness),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? AdaptivColors.primary : AdaptivColors.getBorderColor(brightness),
          ),
        ),
        child: Text(
          '${days}D',
          style: AdaptivTypography.caption.copyWith(
            color: selected ? Colors.white : AdaptivColors.getSecondaryTextColor(brightness),
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildLineChart(
    List<FlSpot> spots,
    Color color,
    bool isDemoData,
    Brightness brightness,
  ) {
    if (spots.isEmpty) {
      return Container(
        height: 100,
        decoration: BoxDecoration(
          color: color.withOpacity(0.05),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'No history yet — chart will fill as data syncs.',
            style: AdaptivTypography.captionFor(brightness),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    final minY = spots.map((s) => s.y).reduce((a, b) => a < b ? a : b) * 0.97;
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b) * 1.03;

    return SizedBox(
      height: 100,
      child: LineChart(
        LineChartData(
          gridData: const FlGridData(show: false),
          titlesData: const FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          minY: minY,
          maxY: maxY,
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              color: isDemoData ? color.withOpacity(0.45) : color,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: color.withOpacity(isDemoData ? 0.05 : 0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // History tab — clinical event timeline with filter chips
  // -------------------------------------------------------------------------

  Widget _buildHistoryTab(Brightness brightness) {
    final events = _buildMergedHistory();
    return Column(
      children: [
        _buildFilterChips(brightness),
        Expanded(
          child: events.isEmpty
              ? _buildHistoryEmptyState(brightness)
              : _buildHistoryList(events, brightness),
        ),
      ],
    );
  }

  Widget _buildFilterChips(Brightness brightness) {
    const filters = [
      ('all',      'All'),
      ('vitals',   'Vitals'),
      ('workouts', 'Workouts'),
      ('alerts',   'Alerts'),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: AdaptivColors.getSurfaceColor(brightness),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final f in filters) ...[_filterChip(f.$1, f.$2, brightness), const SizedBox(width: 8)],
          ],
        ),
      ),
    );
  }

  Widget _filterChip(String value, String label, Brightness brightness) {
    final selected = _historyFilter == value;
    return GestureDetector(
      onTap: () => setState(() => _historyFilter = value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? AdaptivColors.primary : AdaptivColors.getSurfaceColor(brightness),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? AdaptivColors.primary : AdaptivColors.getBorderColor(brightness),
          ),
        ),
        child: Text(
          label,
          style: AdaptivTypography.caption.copyWith(
            color: selected ? Colors.white : AdaptivColors.getSecondaryTextColor(brightness),
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildHistoryEmptyState(Brightness brightness) {
    final messages = <String, String>{
      'all':      'No health events recorded yet.',
      'vitals':   'No vitals readings recorded yet.',
      'workouts': 'No workouts recorded yet.',
      'alerts':   'No alerts — all clear!',
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox_outlined, size: 48,
                color: AdaptivColors.getSecondaryTextColor(brightness)),
            const SizedBox(height: 12),
            Text(
              messages[_historyFilter] ?? 'No data yet.',
              style: AdaptivTypography.captionFor(brightness),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryList(
      List<Map<String, dynamic>> events, Brightness brightness) {
    final sections = _groupByDate(events);

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sections.length,
      itemBuilder: (context, si) {
        final section = sections[si];
        final items   = section['items'] as List<Map<String, dynamic>>;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 8, top: 4),
              child: Text(
                section['label'] as String,
                style: AdaptivTypography.labelFor(brightness)
                    .copyWith(fontWeight: FontWeight.w700),
              ),
            ),
            for (final item in items) ...[_buildHistoryItem(item, brightness), const SizedBox(height: 8)],
            const SizedBox(height: 8),
          ],
        );
      },
    );
  }

  Widget _buildHistoryItem(Map<String, dynamic> item, Brightness brightness) {
    final type = item['type'] as String? ?? 'vitals';

    IconData icon;
    Color color;
    String title;
    String subtitle;
    String status;

    switch (type) {
      case 'workout':
        icon     = Icons.directions_run;
        color    = AdaptivColors.stable;
        final aType  = item['activity_type'] as String? ?? 'Workout';
        final dur    = item['duration_minutes'];
        final peakHR = item['peak_heart_rate'];
        title    = aType.isNotEmpty
            ? aType[0].toUpperCase() + aType.substring(1)
            : 'Workout';
        subtitle = [
          if (dur != null) '$dur min',
          if (peakHR != null) 'Peak HR: $peakHR BPM',
        ].join(' • ');
        if (subtitle.isEmpty) subtitle = 'Session recorded';
        status   = 'done';
        break;
      case 'alert':
        icon     = Icons.warning_amber;
        color    = AdaptivColors.warning;
        title    = item['title']   as String? ?? 'Alert';
        subtitle = item['message'] as String? ?? '';
        status   = 'alert';
        break;
      default: // vitals
        icon     = Icons.monitor_heart;
        color    = AdaptivColors.primary;
        final hr      = item['heart_rate'];
        final spo2    = item['spo2'];
        final systolic= item['systolic_bp'];
        title    = 'Vitals Reading';
        subtitle = [
          if (hr != null)       'HR: $hr BPM',
          if (spo2 != null)     'SpO2: $spo2%',
          if (systolic != null) 'BP: ${systolic}mmHg',
        ].join(' · ');
        if (subtitle.isEmpty) subtitle = 'Reading recorded';
        status   = 'normal';
    }

    final dt    = _parseTs(item['timestamp'] as String?);
    final diff  = DateTime.now().difference(dt);
    final timeLabel = diff.inMinutes < 2
        ? 'Just now'
        : diff.inHours < 1
            ? '${diff.inMinutes}m ago'
            : diff.inHours < 24
                ? '${diff.inHours}h ago'
                : '${dt.day}/${dt.month}/${dt.year}';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
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
                Text(title,
                    style: AdaptivTypography.body
                        .copyWith(fontWeight: FontWeight.w600)),
                if (subtitle.isNotEmpty) ..[
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: AdaptivTypography.bodySmallFor(brightness)),
                ],
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(timeLabel,
                  style: AdaptivTypography.captionFor(brightness)),
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

  // -------------------------------------------------------------------------
  // Insights tab — AI-powered with static fallback
  // -------------------------------------------------------------------------

  Widget _buildInsightsTab(Brightness brightness) {
    if (_isInsightsLoading) {
      return ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (int i = 0; i < 4; i++) ...[_shimmerCard(brightness), const SizedBox(height: 12)],
        ],
      );
    }

    final insights = _aiInsights.isNotEmpty ? _aiInsights : _staticInsights();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (_aiInsights.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              children: [
                const Icon(Icons.auto_awesome, size: 14, color: AdaptivColors.primary),
                const SizedBox(width: 6),
                Text(
                  'Personalised by AI Coach',
                  style: AdaptivTypography.captionFor(brightness).copyWith(
                    color: AdaptivColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        for (final insight in insights) ...[_buildInsightCard(insight, brightness), const SizedBox(height: 12)],
        if (_insightsLoaded && _aiInsights.isEmpty)
          Center(
            child: TextButton.icon(
              icon: const Icon(Icons.refresh),
              label: const Text('Load AI insights'),
              onPressed: () {
                setState(() => _insightsLoaded = false);
                _loadAiInsights();
              },
            ),
          ),
      ],
    );
  }

  List<Map<String, dynamic>> _staticInsights() {
    return [
      {'title': 'Heart Health',        'description': 'Your resting heart rate has been stable. Keep up the good work!',             'icon': Icons.favorite,            'color': AdaptivColors.stable},
      {'title': 'Recovery Readiness',  'description': 'Your HRV indicates good recovery. You\'re ready for moderate exercise.',       'icon': Icons.battery_charging_full, 'color': AdaptivColors.primary},
      {'title': 'Sleep & Heart',        'description': 'Better sleep quality correlates with lower resting HR. Aim for 7–8 hrs.',     'icon': Icons.bedtime,             'color': const Color(0xFF673AB7)},
      {'title': 'Activity Goal',        'description': 'Consistent moderate activity supports long-term cardiovascular health.',       'icon': Icons.emoji_events,        'color': AdaptivColors.warning},
    ];
  }

  Widget _buildInsightCard(Map<String, dynamic> insight, Brightness brightness) {
    final title       = insight['title']       as String? ?? 'Health Tip';
    final description = insight['description'] as String? ?? '';
    final icon        = insight['icon']        as IconData? ?? Icons.favorite;
    final color       = insight['color']       as Color? ?? AdaptivColors.primary;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
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
                Text(title,
                    style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(description,
                    style: AdaptivTypography.bodySmallFor(brightness)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Loading shimmer placeholder for AI insights.
  Widget _shimmerCard(Brightness brightness) {
    return Container(
      height: 80,
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Row(
        children: [
          const SizedBox(width: 16),
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: AdaptivColors.getBorderColor(brightness),
              borderRadius: BorderRadius.circular(10),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(height: 12, width: 120, color: AdaptivColors.getBorderColor(brightness)),
                const SizedBox(height: 8),
                Container(height: 10, color: AdaptivColors.getBorderColor(brightness)),
              ],
            ),
          ),
          const SizedBox(width: 16),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Metric definition helper — keeps trend-card data in one place
// ---------------------------------------------------------------------------

class _MetricDef {
  final String key;
  final String title;
  final String avgLabel;
  final IconData icon;
  final Color color;
  final String insight;
  final String unit;

  const _MetricDef({
    required this.key,
    required this.title,
    required this.avgLabel,
    required this.icon,
    required this.color,
    required this.insight,
    required this.unit,
  });
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  final TabController tabController;
  final Brightness brightness;

  _TabBarDelegate({required this.tabController, required this.brightness});

  @override
  Widget build(context, shrinkOffset, overlapsContent) {
    return Container(
      color: AdaptivColors.getSurfaceColor(brightness),
      child: TabBar(
        controller: tabController,
        labelColor: AdaptivColors.getPrimaryColor(brightness),
        unselectedLabelColor: AdaptivColors.getSecondaryTextColor(brightness),
        indicatorColor: AdaptivColors.getPrimaryColor(brightness),
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
  bool shouldRebuild(covariant _TabBarDelegate oldDelegate) =>
      oldDelegate.brightness != brightness;
}
