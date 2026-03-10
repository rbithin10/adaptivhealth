/*
RiskBadge - Compact risk status indicator widget.

Displays cardiovascular risk level with color-coded badge.
Supports pulse animation for critical status to draw attention.

Usage:
```dart
RiskBadge(
  level: RiskLevel.moderate,
  label: "CV Risk",
  showPulse: false,
)
```
*/

// Flutter's main UI toolkit
import 'package:flutter/material.dart';
// Our custom color palette
import '../theme/colors.dart';
// Our custom text styles
import '../theme/typography.dart';

// How risky the patient's cardiovascular health is
enum RiskLevel {
  minimal,  // Very safe — green
  low,      // Safe — green
  moderate, // Needs monitoring — yellow/orange
  elevated, // Concerning — deep orange
  high,     // Dangerous — red
  critical, // Emergency — red with pulse animation
}

// A colored badge that shows the patient's risk level (e.g. "Low", "High", "Critical")
class RiskBadge extends StatefulWidget {
  // The risk level to display (determines color and icon)
  final RiskLevel level;
  
  // Custom text to show instead of the default level name
  final String? label;
  
  // Whether to pulse/throb the badge (auto-enabled for critical)
  final bool? showPulse;
  
  // How big the badge should be
  final RiskBadgeSize size;
  
  // What happens when the user taps the badge
  final VoidCallback? onTap;

  const RiskBadge({
    super.key,
    required this.level,
    this.label,
    this.showPulse,
    this.size = RiskBadgeSize.medium,
    this.onTap,
  });

  @override
  State<RiskBadge> createState() => _RiskBadgeState();
}

// Available badge sizes
enum RiskBadgeSize { small, medium, large }

class _RiskBadgeState extends State<RiskBadge>
    with SingleTickerProviderStateMixin {
  // Controls the pulsing/throbbing animation for critical alerts
  late AnimationController _pulseController;
  // The actual scale values the pulse animation goes through
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    // Set up a pulsing animation that scales from 100% to 115% size
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    
    _updatePulseAnimation();
  }

  @override
  void didUpdateWidget(RiskBadge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.level != widget.level || 
        oldWidget.showPulse != widget.showPulse) {
      _updatePulseAnimation();
    }
  }

  // Start or stop the pulse animation based on risk level
  void _updatePulseAnimation() {
    // Pulse if explicitly enabled, or automatically for critical risk
    final shouldPulse = widget.showPulse ?? 
        (widget.level == RiskLevel.critical);
    
    if (shouldPulse) {
      _pulseController.repeat(reverse: true);
    } else {
      _pulseController.stop();
      _pulseController.reset();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  // Pick the main color based on risk level
  Color get _statusColor {
    switch (widget.level) {
      case RiskLevel.minimal:
      case RiskLevel.low:
        return AdaptivColors.stable;
      case RiskLevel.moderate:
        return AdaptivColors.warning;
      case RiskLevel.elevated:
        return const Color(0xFFFF8C00); // Deep orange
      case RiskLevel.high:
      case RiskLevel.critical:
        return AdaptivColors.critical;
    }
  }

  // Pick a light background color to match the risk level
  Color get _bgColor {
    switch (widget.level) {
      case RiskLevel.minimal:
      case RiskLevel.low:
        return AdaptivColors.stableBg;
      case RiskLevel.moderate:
        return AdaptivColors.warningBg;
      case RiskLevel.elevated:
        return const Color(0xFFFFF3E0); // Light orange
      case RiskLevel.high:
      case RiskLevel.critical:
        return AdaptivColors.criticalBg;
    }
  }

  // Get the text to display (custom label or default level name)
  String get _levelLabel {
    if (widget.label != null) return widget.label!;
    
    switch (widget.level) {
      case RiskLevel.minimal:
        return 'Minimal';
      case RiskLevel.low:
        return 'Low';
      case RiskLevel.moderate:
        return 'Moderate';
      case RiskLevel.elevated:
        return 'Elevated';
      case RiskLevel.high:
        return 'High';
      case RiskLevel.critical:
        return 'Critical';
    }
  }

  // Pick the icon that matches the risk level
  IconData get _levelIcon {
    switch (widget.level) {
      case RiskLevel.minimal:
      case RiskLevel.low:
        return Icons.check_circle_outline;
      case RiskLevel.moderate:
        return Icons.info_outline;
      case RiskLevel.elevated:
      case RiskLevel.high:
        return Icons.warning_amber_outlined;
      case RiskLevel.critical:
        return Icons.error_outline;
    }
  }

  // Pick the padding based on badge size
  EdgeInsets get _padding {
    switch (widget.size) {
      case RiskBadgeSize.small:
        return const EdgeInsets.symmetric(horizontal: 8, vertical: 4);
      case RiskBadgeSize.medium:
        return const EdgeInsets.symmetric(horizontal: 12, vertical: 6);
      case RiskBadgeSize.large:
        return const EdgeInsets.symmetric(horizontal: 16, vertical: 8);
    }
  }

  // Pick the icon size based on badge size
  double get _iconSize {
    switch (widget.size) {
      case RiskBadgeSize.small:
        return 12;
      case RiskBadgeSize.medium:
        return 16;
      case RiskBadgeSize.large:
        return 20;
    }
  }

  // Pick the text style based on badge size
  TextStyle get _textStyle {
    switch (widget.size) {
      case RiskBadgeSize.small:
        return AdaptivTypography.overline;
      case RiskBadgeSize.medium:
        return AdaptivTypography.label;
      case RiskBadgeSize.large:
        return AdaptivTypography.bodySmall;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Build the badge content (icon + label with colored background)
    final badge = GestureDetector(
      onTap: widget.onTap,
      child: Container(
        padding: _padding,
        decoration: BoxDecoration(
          color: _bgColor,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: _statusColor.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _levelIcon,
              size: _iconSize,
              color: _statusColor,
            ),
            const SizedBox(width: 4),
            Text(
              _levelLabel,
              style: _textStyle.copyWith(
                color: _statusColor,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );

    // If pulsing is enabled, wrap the badge in a scale animation
    final shouldPulse = widget.showPulse ?? 
        (widget.level == RiskLevel.critical);
    
    if (shouldPulse) {
      return AnimatedBuilder(
        animation: _pulseAnimation,
        builder: (context, child) {
          return Transform.scale(
            scale: _pulseAnimation.value,
            child: child,
          );
        },
        child: badge,
      );
    }

    return badge;
  }
}

// A bigger version of the risk badge that includes a numeric score in a circle
class RiskScoreBadge extends StatelessWidget {
  // The risk level (determines color)
  final RiskLevel level;
  
  // The numeric risk score (0-100)
  final int score;
  
  // What happens when the user taps this
  final VoidCallback? onTap;

  const RiskScoreBadge({
    super.key,
    required this.level,
    required this.score,
    this.onTap,
  });

  // Pick the color for the score circle based on risk level
  Color get _statusColor {
    switch (level) {
      case RiskLevel.minimal:
      case RiskLevel.low:
        return AdaptivColors.stable;
      case RiskLevel.moderate:
        return AdaptivColors.warning;
      case RiskLevel.elevated:
        return const Color(0xFFFF8C00);
      case RiskLevel.high:
      case RiskLevel.critical:
        return AdaptivColors.critical;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Build a card with a score circle and a small risk badge beneath it
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AdaptivColors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AdaptivColors.border300),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Score circle
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _statusColor.withOpacity(0.1),
                border: Border.all(
                  color: _statusColor,
                  width: 3,
                ),
              ),
              child: Center(
                child: Text(
                  score.toString(),
                  style: AdaptivTypography.metricValue.copyWith(
                    color: _statusColor,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            RiskBadge(
              level: level,
              size: RiskBadgeSize.small,
            ),
          ],
        ),
      ),
    );
  }
}
