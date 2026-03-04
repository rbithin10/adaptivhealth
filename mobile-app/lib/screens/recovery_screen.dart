/*
Recovery Screen â€” post-workout debrief for cardiovascular patients.

Shows live vitals, a scored recovery ring, session metrics sourced from the
activity API, a functional breathing exercise widget with all four techniques,
a personalised recommendation from the backend, contextual tips derived from
the session data, and bottom actions to log a meal or message the care team.
*/

import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../widgets/ai_coach_overlay.dart';

// =============================================================================
// BREATHING TECHNIQUE DEFINITIONS
// =============================================================================

enum BreathingType {
  relaxing478,  // 4-7-8  â€” 19 s cycle
  box,          // 4-4-4-4 â€” 16 s cycle
  energizing,   // 4-2-4   â€” 10 s cycle
  calm246,      // 2-4-6   â€” 12 s cycle
}

/// Per-technique metadata consumed by the UI and AnimationController.
class _BreathingConfig {
  final String label;
  final String description;
  final int inhaleSec;
  final int holdSec;
  final int exhaleSec;

  const _BreathingConfig({
    required this.label,
    required this.description,
    required this.inhaleSec,
    required this.holdSec,
    required this.exhaleSec,
  });

  int get totalSec => inhaleSec + holdSec + exhaleSec;
  double get inhaleEnd => inhaleSec / totalSec;
  double get holdEnd => (inhaleSec + holdSec) / totalSec;
}

const Map<BreathingType, _BreathingConfig> _kBreathingConfigs = {
  BreathingType.relaxing478: _BreathingConfig(
    label: '4-7-8 Relaxing',
    description:
        'Activates your parasympathetic nervous system. Ideal directly after a hard session.',
    inhaleSec: 4,
    holdSec: 7,
    exhaleSec: 8,
  ),
  BreathingType.box: _BreathingConfig(
    label: 'Box Breathing',
    description:
        'Equal phases of 4 s each. Used by athletes and clinicians to reset focus and lower HR.',
    inhaleSec: 4,
    holdSec: 4,
    exhaleSec: 4,
  ),
  BreathingType.energizing: _BreathingConfig(
    label: '4-2-4 Energising',
    description:
        'Short hold keeps breathing brisk. Good for mild fatigue when you need a gentle lift.',
    inhaleSec: 4,
    holdSec: 2,
    exhaleSec: 4,
  ),
  BreathingType.calm246: _BreathingConfig(
    label: '2-4-6 Calm',
    description:
        'Progressively longer exhale. Recommended for older or lower-fitness patients.',
    inhaleSec: 2,
    holdSec: 4,
    exhaleSec: 6,
  ),
};

// =============================================================================
// RECOVERY SCREEN WIDGET
// =============================================================================

class RecoveryScreen extends StatefulWidget {
  final ApiClient apiClient;

  /// ID of the session that just finished. When provided the screen fetches
  /// that specific session; otherwise it loads the most recent one.
  final int? sessionId;

  /// Optional callback so the bottom action bar can switch the host tab.
  /// Index 3 = Nutrition, Index 4 = Messaging (matches the main scaffold).
  final ValueChanged<int>? onNavigateToTab;

  const RecoveryScreen({
    super.key,
    required this.apiClient,
    this.sessionId,
    this.onNavigateToTab,
  });

  @override
  State<RecoveryScreen> createState() => _RecoveryScreenState();
}

// =============================================================================
// DATA MODEL
// =============================================================================

class _RecoveryData {
  final Map<String, dynamic> session;
  final Map<String, dynamic>? vitals;
  final Map<String, dynamic>? recommendation;

  const _RecoveryData({
    required this.session,
    this.vitals,
    this.recommendation,
  });
}

// =============================================================================
// STATE
// =============================================================================

class _RecoveryScreenState extends State<RecoveryScreen>
    with SingleTickerProviderStateMixin {
  // â”€â”€ async data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  late Future<_RecoveryData> _dataFuture;

  // â”€â”€ breathing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  late AnimationController _breathingController;
  BreathingType _selectedTechnique = BreathingType.relaxing478;
  String _breathingPhase = 'Ready';
  bool _isBreathingActive = false;

  _BreathingConfig get _cfg => _kBreathingConfigs[_selectedTechnique]!;

  @override
  void initState() {
    super.initState();
    _dataFuture = _loadData();
    _breathingController = AnimationController(
      duration: Duration(seconds: _cfg.totalSec),
      vsync: this,
    )..addListener(_onBreathingTick);
  }

  // ---------------------------------------------------------------------------
  // ITEM 1 â€” Data loading
  // ---------------------------------------------------------------------------

  /// Fetch session, latest vitals, and recommendation in parallel.
  Future<_RecoveryData> _loadData() async {
    final results = await Future.wait([
      _fetchSession(),
      widget.apiClient
          .getLatestVitals()
          .catchError((_) => <String, dynamic>{}),
      widget.apiClient
          .getLatestRecommendation()
          .catchError((_) => <String, dynamic>{}),
    ]);

    final session = results[0] as Map<String, dynamic>;
    final vitals = results[1] as Map<String, dynamic>;
    final recommendation = results[2] as Map<String, dynamic>;

    return _RecoveryData(
      session: session,
      vitals: vitals.isEmpty ? null : vitals,
      recommendation: recommendation.isEmpty ? null : recommendation,
    );
  }

  /// Return the specific session when a sessionId is provided, otherwise
  /// return the most recent completed session from the activity history.
  Future<Map<String, dynamic>> _fetchSession() async {
    try {
      if (widget.sessionId != null) {
        return await widget.apiClient.getActivityById(widget.sessionId!);
      }
      final list = await widget.apiClient.getActivities(limit: 1);
      if (list.isEmpty) return {};
      return Map<String, dynamic>.from(list.first as Map);
    } catch (_) {
      return {};
    }
  }

  // ---------------------------------------------------------------------------
  // ITEM 5 â€” Breathing logic
  // ---------------------------------------------------------------------------

  void _onBreathingTick() {
    if (!_isBreathingActive) return;
    final v = _breathingController.value;
    final String phase;
    if (v < _cfg.inhaleEnd) {
      phase = 'Inhale';
    } else if (v < _cfg.holdEnd) {
      phase = 'Hold';
    } else {
      phase = 'Exhale';
    }
    if (phase != _breathingPhase) setState(() => _breathingPhase = phase);
  }

  void _toggleBreathing() {
    setState(() {
      if (_isBreathingActive) {
        _breathingController.stop();
        _isBreathingActive = false;
        _breathingPhase = 'Ready';
      } else {
        _breathingController.duration = Duration(seconds: _cfg.totalSec);
        _breathingController.repeat();
        _isBreathingActive = true;
        _breathingPhase = 'Inhale';
      }
    });
  }

  void _selectTechnique(BreathingType type) {
    if (_isBreathingActive) _breathingController.stop();
    setState(() {
      _selectedTechnique = type;
      _isBreathingActive = false;
      _breathingPhase = 'Ready';
      _breathingController.duration =
          Duration(seconds: _kBreathingConfigs[type]!.totalSec);
      _breathingController.reset();
    });
  }

  String get _breathingHint {
    switch (_breathingPhase) {
      case 'Inhale':
        return 'Breathe in slowly through your nose';
      case 'Hold':
        return 'Hold gently â€” do not strain';
      case 'Exhale':
        return 'Exhale fully through your mouth';
      default:
        return 'Tap Start to begin the exercise';
    }
  }

  @override
  void dispose() {
    _breathingController
      ..removeListener(_onBreathingTick)
      ..dispose();
    super.dispose();
  }

  // ===========================================================================
  // BUILD
  // ===========================================================================

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          elevation: 0,
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          title: Text(
            'Recovery',
            style: GoogleFonts.dmSans(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: AdaptivColors.getTextColor(brightness),
            ),
          ),
        ),
        body: Container(
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/recovery_bg.png'),
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
          child: FutureBuilder<_RecoveryData>(
          future: _dataFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _buildErrorState(
                  snapshot.error.toString(), brightness);
            }
            final data = snapshot.data!;
            if (data.session.isEmpty) {
              return _buildEmptyState(brightness);
            }
            return _buildContent(data, brightness);
          },
          ),
        ),
      ),
    );
  }

  // ===========================================================================
  // CONTENT
  // ===========================================================================

  Widget _buildContent(_RecoveryData data, Brightness brightness) {
    final session = data.session;

    final int duration = _int(session['duration_minutes']) ?? 0;
    final int avgHR = _int(session['avg_heart_rate']) ?? 0;
    final int peakHR = _int(session['peak_heart_rate']) ?? 0;
    final int calories = _int(session['calories_burned']) ?? 0;
    final int recoveryTime = _int(session['recovery_time_minutes']) ?? 0;

    final vitals = data.vitals;
    final int? currentHR =
        vitals != null ? _int(vitals['heart_rate']) : null;
    final int? currentSpO2 =
        vitals != null ? _int(vitals['spo2']) : null;
    final int? hrv =
        vitals != null ? _int(vitals['hrv']) : null;

    // Derive recovery score â€” ITEM 3
    const int restingHR = 65;
    final double hrRecoveryPct = currentHR != null && avgHR > 0
        ? ((1 - ((currentHR - restingHR).clamp(0, 60) / 60)) * 100)
            .clamp(0.0, 100.0)
        : 70.0;
    final double hrvScore =
        hrv != null ? (hrv / 60.0 * 100).clamp(0.0, 100.0) : 60.0;
    final double intensityScore = peakHR > 0
        ? ((1 - ((peakHR - 120) / 80).clamp(0.0, 1.0)) * 100)
        : 70.0;
    final int recoveryScore =
        ((hrRecoveryPct * 0.4) + (hrvScore * 0.3) + (intensityScore * 0.3))
            .round()
            .clamp(0, 100);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ITEM 2 â€” Post-workout vitals banner
          if (vitals != null) ...[
            _buildVitalsBanner(
                currentHR, currentSpO2, restingHR, brightness),
            const SizedBox(height: 24),
          ],

          // ITEM 3 â€” Recovery score ring
          _buildScoreSection(
            recoveryScore,
            hrRecoveryPct.round(),
            hrvScore.round(),
            intensityScore.round(),
            brightness,
          ),
          const SizedBox(height: 28),

          // ITEM 4 â€” Session summary grid
          Text('Session Summary', style: AdaptivTypography.sectionTitle),
          const SizedBox(height: 12),
          _buildSummaryGrid(
            duration: duration,
            avgHR: avgHR,
            peakHR: peakHR,
            calories: calories,
            recoveryTime: recoveryTime,
            hrv: hrv,
            brightness: brightness,
          ),
          const SizedBox(height: 28),

          // ITEM 5 â€” Breathing exercise
          Text('Breathing Exercise', style: AdaptivTypography.sectionTitle),
          const SizedBox(height: 12),
          _buildBreathingSection(brightness),
          const SizedBox(height: 28),

          // ITEM 6 â€” Personalised recommendation
          if (data.recommendation != null) ...[
            Text('Your Recommendation',
                style: AdaptivTypography.sectionTitle),
            const SizedBox(height: 12),
            _buildRecommendationCard(data.recommendation!, brightness),
            const SizedBox(height: 28),
          ],

          // ITEM 7 â€” Contextual tips
          Text('Recovery Tips', style: AdaptivTypography.sectionTitle),
          const SizedBox(height: 12),
          ..._buildContextualTips(
            duration: duration,
            peakHR: peakHR,
            hrv: hrv,
            brightness: brightness,
          ),
          const SizedBox(height: 28),

          // ITEM 8 â€” Bottom action bar
          _buildActionBar(brightness),
        ],
      ),
    );
  }

  // ===========================================================================
  // ITEM 2 â€” Post-workout vitals banner
  // ===========================================================================

  Widget _buildVitalsBanner(
    int? currentHR,
    int? currentSpO2,
    int restingHR,
    Brightness brightness,
  ) {
    final bool hrOk =
        currentHR == null || currentHR <= restingHR + 20;
    final bool spo2Ok = currentSpO2 == null || currentSpO2 >= 94;
    final bool allOk = hrOk && spo2Ok;

    final Color statusColor =
        allOk ? AdaptivColors.stable : AdaptivColors.warning;
    final String statusLabel = allOk
        ? 'Heart is recovering well'
        : 'Still recovering â€” rest a bit more';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: allOk ? AdaptivColors.stableBg : AdaptivColors.warningBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: allOk
              ? AdaptivColors.stableBorder
              : AdaptivColors.warningBorder,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(
              allOk ? Icons.favorite : Icons.favorite_border,
              color: statusColor,
              size: 22,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Current Vitals',
                  style: AdaptivTypography.label.copyWith(
                    color: AdaptivColors.getSecondaryTextColor(brightness),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  statusLabel,
                  style: AdaptivTypography.bodySmall.copyWith(
                    color: allOk
                        ? AdaptivColors.stableText
                        : AdaptivColors.warningText,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (currentHR != null)
                _vitalChip('$currentHR BPM', Icons.favorite,
                    AdaptivColors.getHRZoneColor(currentHR)),
              if (currentSpO2 != null) ...[
                const SizedBox(height: 4),
                _vitalChip('$currentSpO2% SpOâ‚‚', Icons.air,
                    spo2Ok ? AdaptivColors.stable : AdaptivColors.critical),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _vitalChip(String label, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(label,
              style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: color)),
        ],
      ),
    );
  }

  // ===========================================================================
  // ITEM 3 â€” Recovery score ring (CustomPainter)
  // ===========================================================================

  Widget _buildScoreSection(
    int score,
    int hrComponent,
    int hrvComponent,
    int intensityComponent,
    Brightness brightness,
  ) {
    final Color ringColor = score >= 75
        ? AdaptivColors.stable
        : score >= 50
            ? AdaptivColors.warning
            : AdaptivColors.critical;
    final String label = score >= 75
        ? 'Excellent recovery'
        : score >= 50
            ? 'Good â€” keep resting'
            : 'Needs more recovery time';

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
            color: AdaptivColors.getBorderColor(brightness), width: 1),
      ),
      color: AdaptivColors.getSurfaceColor(brightness),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(
                  width: 140,
                  height: 140,
                  child: CustomPaint(
                    painter: _ArcRingPainter(
                      progress: score / 100.0,
                      ringColor: ringColor,
                      trackColor:
                          AdaptivColors.getBorderColor(brightness),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            '$score',
                            style: AdaptivTypography.heroNumber.copyWith(
                              fontSize: 36,
                              color:
                                  AdaptivColors.getTextColor(brightness),
                            ),
                          ),
                          Text(
                            '/ 100',
                            style: AdaptivTypography.caption.copyWith(
                              color: AdaptivColors.getSecondaryTextColor(
                                  brightness),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 28),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _subScore('HR Recovery', hrComponent,
                        AdaptivColors.chartBlue),
                    const SizedBox(height: 10),
                    _subScore('HRV Quality', hrvComponent,
                        AdaptivColors.chartTeal),
                    const SizedBox(height: 10),
                    _subScore('Intensity Load', intensityComponent,
                        AdaptivColors.warning),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: ringColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                label,
                style: AdaptivTypography.bodySmall.copyWith(
                  color: ringColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _subScore(String label, int value, Color color) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: AdaptivTypography.caption.copyWith(fontSize: 11)),
            Text('$value%',
                style: AdaptivTypography.metricValueSmall
                    .copyWith(fontSize: 14, color: color)),
          ],
        ),
      ],
    );
  }

  // ===========================================================================
  // ITEM 4 â€” Session summary grid
  // ===========================================================================

  Widget _buildSummaryGrid({
    required int duration,
    required int avgHR,
    required int peakHR,
    required int calories,
    required int recoveryTime,
    required int? hrv,
    required Brightness brightness,
  }) {
    final items = [
      _GridItem(
          Icons.timer_outlined, 'Duration', duration > 0 ? '$duration min' : 'â€”'),
      _GridItem(
          Icons.favorite_border, 'Avg HR', avgHR > 0 ? '$avgHR BPM' : 'â€”'),
      _GridItem(
          Icons.trending_up, 'Peak HR', peakHR > 0 ? '$peakHR BPM' : 'â€”'),
      _GridItem(Icons.local_fire_department_outlined, 'Calories',
          calories > 0 ? '$calories kcal' : 'â€”'),
      _GridItem(Icons.trending_down, 'Recovery',
          recoveryTime > 0 ? '$recoveryTime min' : 'â€”'),
      _GridItem(Icons.monitor_heart_outlined, 'HRV',
          hrv != null && hrv > 0 ? '$hrv ms' : 'â€”'),
    ];

    return GridView.count(
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      shrinkWrap: true,
      childAspectRatio: 1.6,
      physics: const NeverScrollableScrollPhysics(),
      children: items
          .map((item) => _buildSummaryCard(item, brightness))
          .toList(),
    );
  }

  Widget _buildSummaryCard(_GridItem item, Brightness brightness) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: AdaptivColors.getBorderColor(brightness), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Icon(item.icon, color: AdaptivColors.primary, size: 18),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.label, style: AdaptivTypography.overline),
              const SizedBox(height: 2),
              Text(
                item.value,
                style: AdaptivTypography.metricValueSmall.copyWith(
                  color: AdaptivColors.getTextColor(brightness),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ===========================================================================
  // ITEM 5 â€” Breathing exercise with technique selector
  // ===========================================================================

  Widget _buildBreathingSection(Brightness brightness) {
    final cfg = _cfg;
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
            color: AdaptivColors.getBorderColor(brightness), width: 1),
      ),
      color: AdaptivColors.getSurfaceColor(brightness),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Technique chip selector
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: BreathingType.values.map((type) {
                  final isSelected = type == _selectedTechnique;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(
                        _kBreathingConfigs[type]!.label,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isSelected
                              ? Colors.white
                              : AdaptivColors.getTextColor(brightness),
                        ),
                      ),
                      selected: isSelected,
                      onSelected: (_) => _selectTechnique(type),
                      selectedColor: AdaptivColors.primary,
                      backgroundColor:
                          AdaptivColors.getBackgroundColor(brightness),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                        side: BorderSide(
                          color: isSelected
                              ? AdaptivColors.primary
                              : AdaptivColors.getBorderColor(brightness),
                        ),
                      ),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 0),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),
            Text(cfg.description,
                style: AdaptivTypography.bodySmall,
                textAlign: TextAlign.center),
            const SizedBox(height: 10),
            // Timing badges
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _timingBadge('Inhale ${cfg.inhaleSec}s',
                    AdaptivColors.chartBlue),
                const SizedBox(width: 8),
                _timingBadge('Hold ${cfg.holdSec}s', AdaptivColors.warning),
                const SizedBox(width: 8),
                _timingBadge('Exhale ${cfg.exhaleSec}s',
                    AdaptivColors.chartTeal),
              ],
            ),
            const SizedBox(height: 24),
            _buildBreathingCircle(brightness),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _toggleBreathing,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _isBreathingActive
                      ? AdaptivColors.critical
                      : AdaptivColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  elevation: 0,
                ),
                child: Text(
                  _isBreathingActive ? 'Stop Exercise' : 'Start Exercise',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _timingBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildBreathingCircle(Brightness brightness) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ScaleTransition(
          scale: Tween<double>(begin: 0.55, end: 1.0).animate(
            CurvedAnimation(
                parent: _breathingController, curve: Curves.easeInOut),
          ),
          child: Container(
            width: 150,
            height: 150,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AdaptivColors.primaryUltralight,
              border:
                  Border.all(color: AdaptivColors.primary, width: 2.5),
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.air, color: AdaptivColors.primary, size: 30),
                  const SizedBox(height: 6),
                  Text(
                    _breathingPhase,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AdaptivColors.primary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (_isBreathingActive) ...[
          const SizedBox(height: 10),
          Text(
            _breathingHint,
            style: AdaptivTypography.caption.copyWith(fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ],
      ],
    );
  }

  // ===========================================================================
  // ITEM 6 â€” Personalised recommendation card
  // ===========================================================================

  Widget _buildRecommendationCard(
      Map<String, dynamic> rec, Brightness brightness) {
    final String title = rec['title']?.toString() ??
        rec['recommendation_type']?.toString() ??
        'Personalised Advice';
    final String content = rec['content']?.toString() ??
        rec['recommendation']?.toString() ??
        '';
    final String? activityRec = rec['activity_recommendation']?.toString() ??
        rec['next_activity']?.toString();

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AdaptivColors.primary.withOpacity(0.08),
            AdaptivColors.primaryLight.withOpacity(0.15),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border:
            Border.all(color: AdaptivColors.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome,
                  color: AdaptivColors.primary, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: AdaptivTypography.cardTitle
                      .copyWith(color: AdaptivColors.primary),
                ),
              ),
            ],
          ),
          if (content.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(content, style: AdaptivTypography.bodySmall),
          ],
          if (activityRec != null && activityRec.isNotEmpty) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.directions_run,
                    color: AdaptivColors.stable, size: 14),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Next: $activityRec',
                    style: AdaptivTypography.bodySmall.copyWith(
                      color: AdaptivColors.stable,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // ===========================================================================
  // ITEM 7 â€” Contextual recovery tips
  // ===========================================================================

  List<Widget> _buildContextualTips({
    required int duration,
    required int peakHR,
    required int? hrv,
    required Brightness brightness,
  }) {
    final tips = <_TipData>[];

    // Cardiac-specific tip â€” always shown first
    tips.add(const _TipData(
      Icons.favorite,
      'Cardiac Note',
      'If you experience chest tightness, shortness of breath, or unusual fatigue after exercise, rest and contact your care team.',
      isCardiac: true,
    ));

    // Intensity-based hydration tip
    if (peakHR > 150) {
      tips.add(const _TipData(
        Icons.water_drop,
        'Hydration Priority',
        'Your peak HR was high. Drink 500 ml of water in the next 30 minutes to replenish electrolytes and support HR normalisation.',
      ));
    } else {
      tips.add(const _TipData(
        Icons.water_drop,
        'Hydration',
        'Replenish fluids lost during exercise. Water or a diluted electrolyte drink within the next hour.',
      ));
    }

    // Duration-based nutrition window
    if (duration > 30) {
      tips.add(const _TipData(
        Icons.restaurant,
        'Recovery Nutrition Window',
        'Sessions over 30 min deplete glycogen. Eat lean protein and complex carbs within 45 minutes for optimal muscle repair.',
      ));
    }

    // HRV-based sleep tip
    if (hrv != null && hrv < 35) {
      tips.add(const _TipData(
        Icons.nights_stay,
        'Sleep â€” High Priority',
        'Your HRV is low, indicating your nervous system needs rest. Aim for 8â€“9 hours tonight and avoid screens 1 hour before bed.',
      ));
    } else {
      tips.add(const _TipData(
        Icons.nights_stay,
        'Sleep',
        'Quality sleep is when cardiovascular adaptation occurs. Target 7â€“9 hours for optimal recovery.',
      ));
    }

    return [
      for (int i = 0; i < tips.length; i++) ...[
        _buildTipCard(tips[i], brightness),
        if (i < tips.length - 1) const SizedBox(height: 10),
      ],
    ];
  }

  Widget _buildTipCard(_TipData tip, Brightness brightness) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tip.isCardiac
            ? AdaptivColors.warningBg
            : AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: tip.isCardiac
              ? AdaptivColors.warningBorder
              : AdaptivColors.getBorderColor(brightness),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            tip.icon,
            color: tip.isCardiac
                ? AdaptivColors.warning
                : AdaptivColors.primary,
            size: 22,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tip.title,
                    style:
                        AdaptivTypography.cardTitle.copyWith(fontSize: 14)),
                const SizedBox(height: 4),
                Text(tip.description, style: AdaptivTypography.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ===========================================================================
  // ITEM 8 â€” Bottom action bar
  // ===========================================================================

  Widget _buildActionBar(Brightness brightness) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton.icon(
          icon: const Icon(Icons.restaurant_menu,
              size: 18, color: Colors.white),
          label: const Text(
            'Log Recovery Meal',
            style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: Colors.white),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: AdaptivColors.stable,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            elevation: 0,
          ),
          onPressed: () {
            if (widget.onNavigateToTab != null) {
              Navigator.of(context).popUntil((r) => r.isFirst);
              widget.onNavigateToTab!(3); // Nutrition tab
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text(
                        'Open the Nutrition tab to log your meal.')),
              );
            }
          },
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          icon: Icon(Icons.message_outlined,
              size: 18, color: AdaptivColors.primary),
          label: Text(
            'Message Care Team',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AdaptivColors.primary,
            ),
          ),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            side: BorderSide(color: AdaptivColors.primary),
          ),
          onPressed: () {
            if (widget.onNavigateToTab != null) {
              Navigator.of(context).popUntil((r) => r.isFirst);
              widget.onNavigateToTab!(4); // Messaging tab
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text(
                        'Open the Messaging tab to contact your care team.')),
              );
            }
          },
        ),
      ],
    );
  }

  // ===========================================================================
  // EMPTY & ERROR STATES
  // ===========================================================================

  Widget _buildEmptyState(Brightness brightness) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.directions_run,
                size: 64, color: AdaptivColors.neutral400),
            const SizedBox(height: 16),
            Text(
              'No Session Data Yet',
              style: AdaptivTypography.sectionTitle
                  .copyWith(color: AdaptivColors.getTextColor(brightness)),
            ),
            const SizedBox(height: 8),
            Text(
              'Complete your first workout to see your personalised recovery debrief here.',
              style: AdaptivTypography.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(String error, Brightness brightness) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off,
                size: 56, color: AdaptivColors.neutral400),
            const SizedBox(height: 16),
            Text(
              'Could Not Load Recovery Data',
              style: AdaptivTypography.sectionTitle
                  .copyWith(color: AdaptivColors.getTextColor(brightness)),
            ),
            const SizedBox(height: 8),
            Text(
              'Check your connection and pull down to retry.',
              style: AdaptivTypography.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () =>
                  setState(() => _dataFuture = _loadData()),
              style: ElevatedButton.styleFrom(
                  backgroundColor: AdaptivColors.primary, elevation: 0),
              child: const Text('Retry',
                  style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // UTILITIES
  // ===========================================================================

  int? _int(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.round();
    return int.tryParse(value.toString());
  }
}

// =============================================================================
// CUSTOM PAINTER â€” arc progress ring  (ITEM 3)
// =============================================================================

class _ArcRingPainter extends CustomPainter {
  final double progress; // 0.0 â€“ 1.0
  final Color ringColor;
  final Color trackColor;

  const _ArcRingPainter({
    required this.progress,
    required this.ringColor,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    final radius = (size.shortestSide / 2) - 10;
    const strokeWidth = 10.0;

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final ringPaint = Paint()
      ..color = ringColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    const startAngle = -math.pi / 2; // 12 o'clock
    const fullSweep = 2 * math.pi;

    canvas.drawArc(
      Rect.fromCircle(center: centre, radius: radius),
      startAngle,
      fullSweep,
      false,
      trackPaint,
    );

    if (progress > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: centre, radius: radius),
        startAngle,
        fullSweep * progress.clamp(0.0, 1.0),
        false,
        ringPaint,
      );
    }
  }

  @override
  bool shouldRepaint(_ArcRingPainter old) =>
      old.progress != progress ||
      old.ringColor != ringColor ||
      old.trackColor != trackColor;
}

// =============================================================================
// PRIVATE DATA CLASSES
// =============================================================================

class _GridItem {
  final IconData icon;
  final String label;
  final String value;
  const _GridItem(this.icon, this.label, this.value);
}

class _TipData {
  final IconData icon;
  final String title;
  final String description;
  final bool isCardiac;
  const _TipData(this.icon, this.title, this.description,
      {this.isCardiac = false});
}
