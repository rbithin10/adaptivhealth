/*
HomeSparkline widget — heart-rate sparkline chart on the Home tab.
Renders from a live ValueNotifier (mock/BLE readings) with API history as a
richer fallback when available.
*/

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../providers/vitals_provider.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Line chart showing heart-rate readings from the current session or
/// the last 50 backend-stored readings, whichever has data.
class HomeSparkline extends StatelessWidget {
  final ValueNotifier<List<VitalsReading>> vitalsHistoryNotifier;
  final Future<List<dynamic>> vitalHistoryFuture;

  const HomeSparkline({
    super.key,
    required this.vitalsHistoryNotifier,
    required this.vitalHistoryFuture,
  });

  @override
  Widget build(BuildContext context) {
    // Try to load historical vitals from the API, fall back to live readings
    return FutureBuilder<List<dynamic>>(
      future: vitalHistoryFuture,
      builder: (context, snapshot) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.9),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AdaptivColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.show_chart,
                          color: AdaptivColors.primary, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Text('Heart Rate Today',
                        style: AdaptivTypography.cardTitle.copyWith(
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                // Re-render the chart whenever new live readings arrive from BLE/mock
                // ValueListenableBuilder re-renders when new live readings arrive.
                ValueListenableBuilder<List<VitalsReading>>(
                  valueListenable: vitalsHistoryNotifier,
                  builder: (context, _, __) => SizedBox(
                    height: 100,
                    child: _SparklineContent(
                        snapshot: snapshot,
                        liveHistory: vitalsHistoryNotifier.value),
                  ),
                ),
                const SizedBox(height: 12),
                _SparklineTimeLabels(
                    snapshot: snapshot,
                    liveHistory: vitalsHistoryNotifier.value),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ─── internal helpers ────────────────────────────────────────────────────────

class _SparklineContent extends StatelessWidget {
  final AsyncSnapshot<List<dynamic>> snapshot;
  final List<VitalsReading> liveHistory;

  const _SparklineContent({
    required this.snapshot,
    required this.liveHistory,
  });

  @override
  Widget build(BuildContext context) {
    if (snapshot.connectionState == ConnectionState.waiting) {
      return _placeholder();
    }

    if (snapshot.hasError || !snapshot.hasData) {
      if (liveHistory.isNotEmpty) return _fromLive(liveHistory);
      return _emptyState();
    }

    final vitals = snapshot.data!;
    if (vitals.isEmpty) {
      if (liveHistory.isNotEmpty) return _fromLive(liveHistory);
      return _emptyState();
    }

    final dataPoints = <FlSpot>[];
    for (int i = 0; i < vitals.length && i < 50; i++) {
      final v  = vitals[i] as Map<String, dynamic>;
      final hr = v['heart_rate'] as int?;
      if (hr != null && hr > 0) dataPoints.add(FlSpot(i.toDouble(), hr.toDouble()));
    }

    if (dataPoints.isEmpty) {
      if (liveHistory.isNotEmpty) return _fromLive(liveHistory);
      return _emptyState();
    }

    return _SparklineChart(points: dataPoints.reversed.toList());
  }

  Widget _fromLive(List<VitalsReading> readings) {
    final pts = readings
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.heartRate.toDouble()))
        .toList();
    return _SparklineChart(points: pts);
  }

  Widget _placeholder() {
    return Container(
      decoration: _gradientBox(),
      child: const Center(
        child: SizedBox(
          width: 20, height: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
    );
  }

  Widget _emptyState() {
    return Container(
      decoration: _gradientBox(),
      child: Center(
        child: Text('No heart rate data yet',
            style: AdaptivTypography.caption
                .copyWith(color: AdaptivColors.text600)),
      ),
    );
  }

  BoxDecoration _gradientBox() => BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AdaptivColors.primary.withOpacity(0.1),
            AdaptivColors.primary.withOpacity(0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(8),
      );
}

class _SparklineChart extends StatelessWidget {
  final List<FlSpot> points;

  const _SparklineChart({required this.points});

  @override
  Widget build(BuildContext context) {
    final hrValues  = points.map((p) => p.y).toList();
    final minHR     = hrValues.reduce((a, b) => a < b ? a : b);
    final maxHR     = hrValues.reduce((a, b) => a > b ? a : b);
    final pad       = (maxHR - minHR) * 0.2;

    return Padding(
      padding: const EdgeInsets.only(right: 8, top: 8, bottom: 4),
      child: LineChart(
        LineChartData(
          minY: (minHR - pad).clamp(40, 200),
          maxY: (maxHR + pad).clamp(60, 220),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: 20,
            getDrawingHorizontalLine: (value) => FlLine(
              color: AdaptivColors.border300.withOpacity(0.3),
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (spots) => spots
                  .map((s) => LineTooltipItem(
                        '${s.y.toInt()} BPM',
                        const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 12),
                      ))
                  .toList(),
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: points,
              isCurved: true,
              curveSmoothness: 0.3,
              color: AdaptivColors.primary,
              barWidth: 2,
              isStrokeCapRound: true,
              dotData: FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AdaptivColors.primary.withOpacity(0.3),
                    AdaptivColors.primary.withOpacity(0.05),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SparklineTimeLabels extends StatelessWidget {
  final AsyncSnapshot<List<dynamic>> snapshot;
  final List<VitalsReading> liveHistory;

  const _SparklineTimeLabels({
    required this.snapshot,
    required this.liveHistory,
  });

  @override
  Widget build(BuildContext context) {
    if (!snapshot.hasData || snapshot.data!.isEmpty) {
      if (liveHistory.isNotEmpty) {
        return _labels('Sim start', '', 'Now');
      }
      return _labels('24h ago', '12h ago', 'Now');
    }

    final vitals = snapshot.data!;
    if (vitals.isEmpty) return _labels('24h ago', '12h ago', 'Now');

    String oldest = '24h ago';
    try {
      final last  = vitals.last as Map<String, dynamic>;
      final tsStr = last['timestamp'] as String?;
      if (tsStr != null) {
        final diff = DateTime.now().difference(DateTime.parse(tsStr));
        if (diff.inHours < 1)       oldest = '${diff.inMinutes}m ago';
        else if (diff.inHours < 24) oldest = '${diff.inHours}h ago';
        else                        oldest = '${diff.inDays}d ago';
      }
    } catch (e) {
      if (kDebugMode) debugPrint('HomeSparkline._labels: $e');
    }

    return _labels(oldest, '', 'Now');
  }

  Widget _labels(String left, String mid, String right) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(left,  style: AdaptivTypography.caption),
        Text(mid,   style: AdaptivTypography.caption),
        Text(right, style: AdaptivTypography.caption.copyWith(
          fontWeight: FontWeight.w600,
          color: AdaptivColors.primary,
        )),
      ],
    );
  }
}
