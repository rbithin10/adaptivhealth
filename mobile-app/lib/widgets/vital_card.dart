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

// Flutter's main UI toolkit for building visual elements
import 'package:flutter/material.dart';
// Our custom color palette
import '../theme/colors.dart';
// Our custom text styles
import '../theme/typography.dart';

// How healthy/dangerous a vital sign reading is
enum VitalStatus {
  safe,     // Normal range — green
  caution,  // Slightly off — yellow
  warning,  // Needs attention — orange
  critical, // Dangerous — red
}

// A small card that displays one vital sign (heart rate, SpO2, etc.)
class VitalCard extends StatelessWidget {
  // The icon shown next to the label (e.g. a heart icon)
  final IconData icon;
  
  // Short label like "HR" or "SpO2"
  final String label;
  
  // The current reading as text (e.g. "105")
  final String value;
  
  // The unit after the number (e.g. "BPM" or "%")
  final String unit;
  
  // How healthy this reading is (changes the card's color)
  final VitalStatus status;
  
  // Recent values to draw a mini trend line (optional)
  final List<double>? trend;
  
  // What happens when the user taps the card (optional)
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

  // Pick the accent color based on how healthy the reading is
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

  // Pick a light background color to match the status
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
    // Make the whole card tappable
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

  // Convert the status enum to a readable label for the badge
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

// Draws a mini sparkline chart showing recent trend data
class _TrendLinePainter extends CustomPainter {
  // The list of recent values to plot
  final List<double> data;
  // The color of the line (matches the vital status color)
  final Color color;

  _TrendLinePainter({
    required this.data,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    // Set up the line style (solid colored line)
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Set up a gradient fill underneath the line (fades to transparent)
    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withOpacity(0.3),
          color.withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    // Find the range of values to scale the chart properly
    final minVal = data.reduce((a, b) => a < b ? a : b);
    final maxVal = data.reduce((a, b) => a > b ? a : b);
    final range = maxVal - minVal;
    // Avoid division by zero if all values are the same
    final effectiveRange = range == 0 ? 1.0 : range;

    // Build the line path and the fill path point by point
    final path = Path();
    final fillPath = Path();
    
    for (int i = 0; i < data.length; i++) {
      // Spread data points evenly across the width
      final x = (i / (data.length - 1)) * size.width;
      // Map value to vertical position (higher value = higher on screen)
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

    // Close the fill area at the bottom
    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    // Draw the gradient fill first, then the line on top
    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);
  }

  // Only repaint when the data or color changes
  @override
  bool shouldRepaint(covariant _TrendLinePainter oldDelegate) {
    return oldDelegate.data != data || oldDelegate.color != color;
  }
}
