/*
Sleep screen.

Allows manual sleep logging, shows today's sleep score,
and displays recent sleep history.
*/

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../widgets/ai_coach_overlay.dart';

class SleepScreen extends StatefulWidget {
  final ApiClient apiClient;

  const SleepScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<SleepScreen> createState() => _SleepScreenState();
}

class _SleepScreenState extends State<SleepScreen> {
  late DateTime _bedtime;
  late DateTime _wakeTime;
  int _qualityRating = 3;
  bool _isSaving = false;

  Map<String, dynamic>? _latestSleep;
  List<Map<String, dynamic>> _sleepHistory = [];
  bool _loadingHistory = true;
  String? _error;

  final TextEditingController _notesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    final bedtimeBase = DateTime(now.year, now.month, now.day, 22, 0);
    final wakeBase = DateTime(now.year, now.month, now.day, 6, 30);
    _bedtime = now.hour < 12 ? bedtimeBase.subtract(const Duration(days: 1)) : bedtimeBase;
    _wakeTime = wakeBase;
    _loadSleepData();
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadSleepData() async {
    setState(() {
      _loadingHistory = true;
      _error = null;
    });

    try {
      final results = await Future.wait([
        widget.apiClient.getLatestSleep().catchError((_) => <String, dynamic>{}),
        widget.apiClient.getSleepHistory(days: 7).catchError((_) => <String, dynamic>{}),
      ]);

      final latest = results[0];
      final history = results[1];
      final entries = history['entries'] as List<dynamic>? ?? [];

      setState(() {
        _latestSleep = latest.isEmpty ? null : latest;
        _sleepHistory = entries.cast<Map<String, dynamic>>();
        _loadingHistory = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loadingHistory = false;
      });
    }
  }

  int _calculateSleepScore(double hours, int rating) {
    final durationRatio = (hours / 8.0).clamp(0.0, 1.0);
    final qualityRatio = (rating / 5.0).clamp(0.0, 1.0);
    return ((durationRatio * 60) + (qualityRatio * 40)).round().clamp(0, 100);
  }

  double _calculateDurationHours(DateTime bedtime, DateTime wakeTime) {
    var resolvedWake = wakeTime;
    if (resolvedWake.isBefore(bedtime)) {
      resolvedWake = resolvedWake.add(const Duration(days: 1));
    }
    return resolvedWake.difference(bedtime).inMinutes / 60.0;
  }

  Future<void> _pickBedtime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_bedtime),
    );
    if (picked == null) return;

    setState(() {
      _bedtime = DateTime(
        _bedtime.year,
        _bedtime.month,
        _bedtime.day,
        picked.hour,
        picked.minute,
      );
    });
  }

  Future<void> _pickWakeTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_wakeTime),
    );
    if (picked == null) return;

    setState(() {
      _wakeTime = DateTime(
        _wakeTime.year,
        _wakeTime.month,
        _wakeTime.day,
        picked.hour,
        picked.minute,
      );
    });
  }

  Future<void> _logSleep() async {
    setState(() => _isSaving = true);
    try {
      await widget.apiClient.logSleep(
        bedtime: _bedtime,
        wakeTime: _wakeTime,
        qualityRating: _qualityRating,
        notes: _notesController.text,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Sleep logged successfully.')),
        );
      }
      await _loadSleepData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error logging sleep: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final durationHours = _calculateDurationHours(_bedtime, _wakeTime);
    final computedScore = _calculateSleepScore(durationHours, _qualityRating);

    final latestScore = _latestSleep != null
        ? (_latestSleep!['sleep_score'] as int? ?? computedScore)
        : computedScore;

    final ringColor = latestScore >= 70
        ? AdaptivColors.stable
        : latestScore >= 40
            ? AdaptivColors.warning
            : AdaptivColors.critical;

    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          title: Text('Sleep', style: AdaptivTypography.screenTitle),
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          foregroundColor: AdaptivColors.getTextColor(brightness),
          elevation: 0,
        ),
        body: _loadingHistory
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, size: 56, color: Colors.red),
                          const SizedBox(height: 12),
                          Text('Failed to load sleep data', style: AdaptivTypography.body),
                          const SizedBox(height: 8),
                          Text(_error!, style: AdaptivTypography.caption, textAlign: TextAlign.center),
                          const SizedBox(height: 16),
                          ElevatedButton(onPressed: _loadSleepData, child: const Text('Retry')),
                        ],
                      ),
                    ),
                  )
                : SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildScoreCard(latestScore, ringColor, brightness),
                        const SizedBox(height: 20),
                        _buildLogCard(durationHours, computedScore, brightness),
                        const SizedBox(height: 20),
                        Text('Sleep History', style: AdaptivTypography.sectionTitle),
                        const SizedBox(height: 12),
                        _buildHistoryList(brightness),
                      ],
                    ),
                  ),
      ),
    );
  }

  Widget _buildScoreCard(int score, Color ringColor, Brightness brightness) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AdaptivColors.getBorderColor(brightness)),
      ),
      color: AdaptivColors.getSurfaceColor(brightness),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            SizedBox(
              width: 100,
              height: 100,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: (score / 100).clamp(0.0, 1.0),
                    strokeWidth: 8,
                    color: ringColor,
                    backgroundColor: AdaptivColors.getBorderColor(brightness),
                  ),
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('$score', style: AdaptivTypography.heroNumber.copyWith(fontSize: 28)),
                      Text('/100', style: AdaptivTypography.caption),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Today\'s Sleep Score', style: AdaptivTypography.cardTitle),
                  const SizedBox(height: 6),
                  Text(
                    score >= 70
                        ? 'Well rested'
                        : score >= 40
                            ? 'Room to improve'
                            : 'Needs more sleep',
                    style: AdaptivTypography.caption.copyWith(color: ringColor),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogCard(double durationHours, int score, Brightness brightness) {
    final durationLabel = '${durationHours.toStringAsFixed(1)} h';

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AdaptivColors.getBorderColor(brightness)),
      ),
      color: AdaptivColors.getSurfaceColor(brightness),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Log Sleep', style: AdaptivTypography.sectionTitle),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildTimeButton(
                    label: 'Bedtime',
                    value: DateFormat('h:mm a').format(_bedtime),
                    onTap: _pickBedtime,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTimeButton(
                    label: 'Wake time',
                    value: DateFormat('h:mm a').format(_wakeTime),
                    onTap: _pickWakeTime,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Duration: $durationLabel', style: AdaptivTypography.caption),
            const SizedBox(height: 12),
            Text('Quality rating', style: AdaptivTypography.caption),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildRatingChip('😴', 1),
                _buildRatingChip('😕', 2),
                _buildRatingChip('🙂', 3),
                _buildRatingChip('😃', 4),
                _buildRatingChip('🤩', 5),
              ],
            ),
            const SizedBox(height: 12),
            Text('Estimated score: $score/100', style: AdaptivTypography.caption),
            const SizedBox(height: 12),
            TextField(
              controller: _notesController,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notes (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isSaving ? null : _logSleep,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AdaptivColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: _isSaving
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Log Sleep'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeButton({
    required String label,
    required String value,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AdaptivColors.primaryUltralight,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: AdaptivTypography.caption),
            const SizedBox(height: 6),
            Text(value, style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }

  Widget _buildRatingChip(String emoji, int value) {
    final isSelected = _qualityRating == value;
    return GestureDetector(
      onTap: () => setState(() => _qualityRating = value),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: isSelected ? AdaptivColors.primaryLight : AdaptivColors.background50,
          borderRadius: BorderRadius.circular(12),
          border: isSelected
              ? Border.all(color: AdaptivColors.primary, width: 2)
              : null,
        ),
        child: Center(
          child: Text(emoji, style: const TextStyle(fontSize: 20)),
        ),
      ),
    );
  }

  Widget _buildHistoryList(Brightness brightness) {
    if (_sleepHistory.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AdaptivColors.getSurfaceColor(brightness),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
        ),
        child: Text('No sleep entries yet.', style: AdaptivTypography.caption),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _sleepHistory.length,
      itemBuilder: (context, index) {
        final entry = _sleepHistory[index];
        final dateStr = entry['date']?.toString();
        final date = dateStr != null ? DateTime.tryParse(dateStr) : null;
        final duration = entry['duration_hours'] as num?;
        final rating = entry['quality_rating'] as int? ?? 0;
        final score = entry['sleep_score'] as int? ?? 0;

        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AdaptivColors.getSurfaceColor(brightness),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
          ),
          child: Row(
            children: [
              Icon(Icons.nights_stay, color: AdaptivColors.primary),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      date != null ? DateFormat('MMM dd').format(date) : 'Sleep',
                      style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${duration?.toStringAsFixed(1) ?? '0.0'} h | Quality $rating',
                      style: AdaptivTypography.caption,
                    ),
                  ],
                ),
              ),
              Text(
                '$score',
                style: AdaptivTypography.metricValueSmall.copyWith(
                  color: score >= 70
                      ? AdaptivColors.stable
                      : score >= 40
                          ? AdaptivColors.warning
                          : AdaptivColors.critical,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
