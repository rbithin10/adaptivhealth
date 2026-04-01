/*
HomeRecoveryScoreRing widget — compact recovery score ring for the Home tab.
Shows today's daily recovery score (0-100) using the backend formula
(Workout + Nutrition + Sleep × risk multiplier).
*/

import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Circular ring that displays today's daily recovery score.
class HomeRecoveryScoreRing extends StatelessWidget {
  final int score;
  final String riskLevel;

  const HomeRecoveryScoreRing({
    super.key,
    required this.score,
    required this.riskLevel,
  });

  Color get _ringColor {
    if (score >= 75) return AdaptivColors.stable;
    if (score >= 50) return AdaptivColors.warning;
    return AdaptivColors.critical;
  }

  @override
  Widget build(BuildContext context) {
    final ringColor = _ringColor;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            // Soft glow
            Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: ringColor.withOpacity(0.25),
                    blurRadius: 30,
                    spreadRadius: 5,
                  ),
                ],
              ),
            ),
            // Arc ring drawn with CustomPaint
            SizedBox(
              width: 200,
              height: 200,
              child: CustomPaint(
                painter: _RecoveryArcPainter(
                  progress: score / 100.0,
                  ringColor: ringColor,
                  trackColor: ringColor.withOpacity(0.15),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.self_improvement_rounded,
                          color: ringColor, size: 28),
                      const SizedBox(height: 6),
                      Text(
                        '$score',
                        style: AdaptivTypography.heroNumber.copyWith(
                          color: ringColor,
                          fontSize: 42,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      Text(
                        '/ 100',
                        style: AdaptivTypography.heroUnit.copyWith(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          'Recovery',
          style: AdaptivTypography.caption.copyWith(
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ],
    );
  }
}

class _RecoveryArcPainter extends CustomPainter {
  final double progress;
  final Color ringColor;
  final Color trackColor;

  const _RecoveryArcPainter({
    required this.progress,
    required this.ringColor,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - 12) / 2;
    const strokeWidth = 10.0;

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final arcPaint = Paint()
      ..color = ringColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    const startAngle = -math.pi / 2;
    const fullSweep = 2 * math.pi;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      fullSweep,
      false,
      trackPaint,
    );

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      fullSweep * progress.clamp(0.0, 1.0),
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(_RecoveryArcPainter old) =>
      old.progress != progress ||
      old.ringColor != ringColor ||
      old.trackColor != trackColor;
}
