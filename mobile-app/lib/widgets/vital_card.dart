/*
VitalCard - Compact vital signs display widget.

A small card (approximately 80x100px) that displays a single vital sign
with an icon, current value, unit, mini trend line, and status indicator.

Usage:
```dart
VitalCard(
  icon: Icons.favorite,
  label: "Heart Rate",
  value: 105,
  unit: "BPM",
  status: VitalStatus.safe,
  trend: [95, 98, 102, 105, 103, 106],
  onTap: () => navigateToVitalsDetail(),
)
```
*/

import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';

/// Status levels for vital signs
enum VitalStatus {
  safe,
  caution,
  warning,
  critical,
}

class VitalCard extends StatelessWidget {
  /// Icon to display (e.g., Icons.favorite for heart)
  final IconData icon;
  
  /// Label text (e.g., "HR", "SpO2")
  final String label;
  
  /// Current value as string (supports integers and decimals)
  final String value;
  
  /// Unit label (e.g., "BPM", "%", "mmHg")
  final String unit;
  
  /// Status determines the color scheme
  final VitalStatus status;
  
  /// Optional trend data (list of recent values for mini sparkline)
  final List<double>? trend;
  
  /// Callback when card is tapped
  final VoidCallback? onTap;

  const VitalCard({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    required this.unit,
    this.status = VitalStatus.safe,
    this.trend,
    this.onTap,
  });

  Color get _statusColor {
    switch (status) {
      case VitalStatus.critical:
        return AdaptivColors.critical;
      case VitalStatus.warning:
        return AdaptivColors.warning;
      case VitalStatus.caution:
        return AdaptivColors.warning;
      case VitalStatus.safe:
        return AdaptivColors.stable;
    }
  }

  Color get _statusBgColor {
    switch (status) {
      case VitalStatus.critical:
        return AdaptivColors.criticalBg;
      case VitalStatus.warning:
      case VitalStatus.caution:
        return AdaptivColors.warningBg;
      case VitalStatus.safe:
        return AdaptivColors.stableBg;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AdaptivColors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AdaptivColors.border300, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Top row: Icon + Label
            Row(
              children: [
                Icon(
                  icon,
                  size: 16,
                  color: _statusColor,
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    label,
                    style: AdaptivTypography.label.copyWith(
                      color: AdaptivColors.text600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            // Value + Unit
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  value,
                  style: AdaptivTypography.metricValue.copyWith(
                    color: _statusColor,
                  ),
                ),
                const SizedBox(width: 2),
                Flexible(
                  child: Text(
                    unit,
                    style: AdaptivTypography.heroUnit.copyWith(
                      color: AdaptivColors.text500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            // Mini trend line
            if (trend != null && trend!.isNotEmpty)
              SizedBox(
                height: 20,
                child: CustomPaint(
                  size: const Size(double.infinity, 20),
                  painter: _TrendLinePainter(
                    data: trend!,
                    color: _statusColor,
                  ),
                ),
              )
            else
              // Status indicator when no trend data
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _statusBgColor,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _getStatusLabel(),
                  style: AdaptivTypography.overline.copyWith(
                    color: _statusColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _getStatusLabel() {
    switch (status) {
      case VitalStatus.critical:
        return 'Critical';
      case VitalStatus.warning:
        return 'High';
      case VitalStatus.caution:
        return 'Caution';
      case VitalStatus.safe:
        return 'Normal';
    }
  }
}

/// Custom painter for mini sparkline trend visualization
class _TrendLinePainter extends CustomPainter {
  final List<double> data;
  final Color color;

  _TrendLinePainter({
    required this.data,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withOpacity(0.3),
          color.withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final minVal = data.reduce((a, b) => a < b ? a : b);
    final maxVal = data.reduce((a, b) => a > b ? a : b);
    final range = maxVal - minVal;
    final effectiveRange = range == 0 ? 1.0 : range;

    final path = Path();
    final fillPath = Path();
    
    for (int i = 0; i < data.length; i++) {
      final x = (i / (data.length - 1)) * size.width;
      final y = size.height - ((data[i] - minVal) / effectiveRange) * size.height * 0.8 - size.height * 0.1;
      
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    // Close fill path
    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    // Draw fill first, then line
    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _TrendLinePainter oldDelegate) {
    return oldDelegate.data != data || oldDelegate.color != color;
  }
}
