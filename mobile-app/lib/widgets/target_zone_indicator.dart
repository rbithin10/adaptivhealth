/*
TargetZoneIndicator - Heart rate zone visualization widget.

Displays a 5-zone HR bar with current position indicator.
Shows Resting, Light, Moderate, Hard, and Maximum zones
with color coding matching the design system.

Usage:
```dart
TargetZoneIndicator(
  currentBPM: 125,
  targetZone: HRZone.moderate,
  maxHR: 190,
  showLabels: true,
)
```
*/

// Flutter's main UI toolkit
import 'package:flutter/material.dart';
// Our custom color palette
import '../theme/colors.dart';
// Our custom text styles
import '../theme/typography.dart';
// Import the HRZone enum from recommendation_card
import 'recommendation_card.dart' show HRZone;

// A visual bar that shows the 5 heart rate zones with a marker for the user's current BPM
class TargetZoneIndicator extends StatelessWidget {
  // The user's current heart rate in beats per minute
  final int currentBPM;
  
  // Which zone the user should be exercising in right now (optional)
  final HRZone? targetZone;
  
  // The user's maximum heart rate (usually 220 minus their age)
  final int maxHR;
  
  // The user's resting heart rate
  final int minHR;
  
  // Whether to show text labels under each zone
  final bool showLabels;
  
  // Whether to show the BPM number above the bar
  final bool showCurrentValue;
  
  // Whether the bar is horizontal or vertical
  final Axis orientation;

  const TargetZoneIndicator({
    super.key,
    required this.currentBPM,
    this.targetZone,
    this.maxHR = 190,
    this.minHR = 50,
    this.showLabels = true,
    this.showCurrentValue = true,
    this.orientation = Axis.horizontal,
  });

  // Figure out which heart rate zone a given BPM falls into
  HRZone _getZoneForBPM(int bpm) {
    final range = maxHR - minHR;  // Total BPM range
    final normalizedBpm = bpm - minHR;  // Shift bpm so resting = 0
    final percentage = normalizedBpm / range;  // Convert to 0.0-1.0
    
    // Each zone covers a percentage of the total range
    if (percentage < 0.14) return HRZone.resting;
    if (percentage < 0.36) return HRZone.light;
    if (percentage < 0.64) return HRZone.moderate;
    if (percentage < 0.86) return HRZone.hard;
    return HRZone.maximum;
  }

  // Calculate where the position marker sits (0.0 = left, 1.0 = right)
  double _getPositionPercentage() {
    final clampedBPM = currentBPM.clamp(minHR, maxHR);  // Keep within range
    return (clampedBPM - minHR) / (maxHR - minHR);
  }

  // Get the color for a given heart rate zone
  Color _getZoneColor(HRZone zone) {
    switch (zone) {
      case HRZone.resting:
        return AdaptivColors.hrResting;
      case HRZone.light:
        return AdaptivColors.hrLight;
      case HRZone.moderate:
        return AdaptivColors.hrModerate;
      case HRZone.hard:
        return AdaptivColors.hrHard;
      case HRZone.maximum:
        return AdaptivColors.hrMaximum;
    }
  }

  // Get a short label for each zone
  String _getZoneLabel(HRZone zone) {
    switch (zone) {
      case HRZone.resting:
        return 'Rest';
      case HRZone.light:
        return 'Light';
      case HRZone.moderate:
        return 'Mod';
      case HRZone.hard:
        return 'Hard';
      case HRZone.maximum:
        return 'Max';
    }
  }

  @override
  Widget build(BuildContext context) {
    // Pick horizontal or vertical layout
    if (orientation == Axis.vertical) {
      return _buildVertical(context);
    }
    return _buildHorizontal(context);
  }

  // Build the horizontal version of the zone indicator
  Widget _buildHorizontal(BuildContext context) {
    final currentZone = _getZoneForBPM(currentBPM);  // Which zone the user is in
    final positionPercent = _getPositionPercentage();  // Where the marker sits

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Current value badge (heart icon + BPM number displayed above the bar)
        if (showCurrentValue)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Icon(
                  Icons.favorite,
                  size: 16,
                  color: _getZoneColor(currentZone),
                ),
                const SizedBox(width: 4),
                Text(
                  currentBPM.toString(),
                  style: AdaptivTypography.metricValueSmall.copyWith(
                    color: _getZoneColor(currentZone),
                  ),
                ),
                const SizedBox(width: 2),
                Text(
                  'BPM',
                  style: AdaptivTypography.label.copyWith(
                    color: AdaptivColors.text500,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: _getZoneColor(currentZone).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _getZoneLabel(currentZone),
                    style: AdaptivTypography.overline.copyWith(
                      color: _getZoneColor(currentZone),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        
        // The colored zone bar with a draggable-looking marker
        SizedBox(
          height: 24,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;  // Total available width
              final indicatorX = positionPercent * width;  // Marker X position
              
              return Stack(
                clipBehavior: Clip.none,
                children: [
                  // The 5 colored segments side by side
                  Row(
                    children: [
                      _ZoneSegment(
                        zone: HRZone.resting,
                        color: _getZoneColor(HRZone.resting),
                        isTarget: targetZone == HRZone.resting,
                        flex: 14,
                        isFirst: true,
                      ),
                      _ZoneSegment(
                        zone: HRZone.light,
                        color: _getZoneColor(HRZone.light),
                        isTarget: targetZone == HRZone.light,
                        flex: 22,
                      ),
                      _ZoneSegment(
                        zone: HRZone.moderate,
                        color: _getZoneColor(HRZone.moderate),
                        isTarget: targetZone == HRZone.moderate,
                        flex: 28,
                      ),
                      _ZoneSegment(
                        zone: HRZone.hard,
                        color: _getZoneColor(HRZone.hard),
                        isTarget: targetZone == HRZone.hard,
                        flex: 22,
                      ),
                      _ZoneSegment(
                        zone: HRZone.maximum,
                        color: _getZoneColor(HRZone.maximum),
                        isTarget: targetZone == HRZone.maximum,
                        flex: 14,
                        isLast: true,
                      ),
                    ],
                  ),
                  
                  // White slider-style marker showing where the user's BPM is
                  Positioned(
                    left: indicatorX - 8,  // Center the 16px marker on the position
                    top: -4,  // Extend slightly above the bar
                    child: Container(
                      width: 16,
                      height: 32,
                      decoration: BoxDecoration(
                        color: AdaptivColors.white,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: _getZoneColor(currentZone),
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.15),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),

        // Zone labels (Rest, Light, Mod, Hard, Max) below the bar
        if (showLabels)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                _ZoneLabel(label: _getZoneLabel(HRZone.resting), flex: 14),
                _ZoneLabel(label: _getZoneLabel(HRZone.light), flex: 22),
                _ZoneLabel(label: _getZoneLabel(HRZone.moderate), flex: 28),
                _ZoneLabel(label: _getZoneLabel(HRZone.hard), flex: 22),
                _ZoneLabel(label: _getZoneLabel(HRZone.maximum), flex: 14),
              ],
            ),
          ),
      ],
    );
  }

  // Build the vertical version of the zone indicator (rotated 90 degrees)
  Widget _buildVertical(BuildContext context) {
    final currentZone = _getZoneForBPM(currentBPM);  // Which zone the user is in
    final positionPercent = _getPositionPercentage();  // Where the marker sits

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Zone bar (vertical layout, 200px tall)
        SizedBox(
          width: 24,
          height: 200,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final height = constraints.maxHeight;
              // Flip so bottom = low BPM, top = high BPM
              final indicatorY = (1 - positionPercent) * height;
              
              return Stack(
                clipBehavior: Clip.none,
                children: [
                  // Zone segments stacked top to bottom (Max at top, Rest at bottom)
                  Column(
                    children: [
                      _VerticalZoneSegment(
                        color: _getZoneColor(HRZone.maximum),
                        isTarget: targetZone == HRZone.maximum,
                        flex: 14,
                        isFirst: true,
                      ),
                      _VerticalZoneSegment(
                        color: _getZoneColor(HRZone.hard),
                        isTarget: targetZone == HRZone.hard,
                        flex: 22,
                      ),
                      _VerticalZoneSegment(
                        color: _getZoneColor(HRZone.moderate),
                        isTarget: targetZone == HRZone.moderate,
                        flex: 28,
                      ),
                      _VerticalZoneSegment(
                        color: _getZoneColor(HRZone.light),
                        isTarget: targetZone == HRZone.light,
                        flex: 22,
                      ),
                      _VerticalZoneSegment(
                        color: _getZoneColor(HRZone.resting),
                        isTarget: targetZone == HRZone.resting,
                        flex: 14,
                        isLast: true,
                      ),
                    ],
                  ),
                  
                  // Horizontal marker showing where the user's BPM is on the vertical bar
                  Positioned(
                    left: -4,  // Extend slightly left of the bar
                    top: indicatorY - 8,  // Center the 16px marker on the position
                    child: Container(
                      width: 32,
                      height: 16,
                      decoration: BoxDecoration(
                        color: AdaptivColors.white,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: _getZoneColor(currentZone),
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.15),
                            blurRadius: 4,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
        
        // Zone labels next to the vertical bar
        if (showLabels)
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: SizedBox(
              height: 200,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: HRZone.values.reversed.map((zone) {
                  return Text(
                    _getZoneLabel(zone),
                    style: AdaptivTypography.overline.copyWith(
                      color: _getZoneColor(zone),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
      ],
    );
  }
}

// One colored segment of the horizontal zone bar
class _ZoneSegment extends StatelessWidget {
  final HRZone zone;  // Which zone this segment is for
  final Color color;  // The segment's color
  final bool isTarget;  // Whether this is the user's target zone (highlighted)
  final int flex;  // How wide this segment is relative to others
  final bool isFirst;  // Rounded left corners
  final bool isLast;  // Rounded right corners

  const _ZoneSegment({
    required this.zone,
    required this.color,
    required this.isTarget,
    required this.flex,
    this.isFirst = false,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      flex: flex,
      child: Container(
        height: double.infinity,
        decoration: BoxDecoration(
          // Target zone is fully opaque; others are slightly faded
          color: color.withOpacity(isTarget ? 1.0 : 0.6),
          borderRadius: BorderRadius.horizontal(
            left: isFirst ? const Radius.circular(4) : Radius.zero,  // Round left edge
            right: isLast ? const Radius.circular(4) : Radius.zero,  // Round right edge
          ),
          // Add a border around the target zone
          border: isTarget
              ? Border.all(color: color, width: 2)
              : null,
        ),
      ),
    );
  }
}

// One colored segment of the vertical zone bar
class _VerticalZoneSegment extends StatelessWidget {
  final Color color;  // The segment's color
  final bool isTarget;  // Whether this is the user's target zone
  final int flex;  // How tall this segment is relative to others
  final bool isFirst;  // Rounded top corners
  final bool isLast;  // Rounded bottom corners

  const _VerticalZoneSegment({
    required this.color,
    required this.isTarget,
    required this.flex,
    this.isFirst = false,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      flex: flex,
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: color.withOpacity(isTarget ? 1.0 : 0.6),
          borderRadius: BorderRadius.vertical(
            top: isFirst ? const Radius.circular(4) : Radius.zero,
            bottom: isLast ? const Radius.circular(4) : Radius.zero,
          ),
        ),
      ),
    );
  }
}

// A small text label for one zone in the horizontal layout
class _ZoneLabel extends StatelessWidget {
  final String label;
  final int flex;

  const _ZoneLabel({
    required this.label,
    required this.flex,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      flex: flex,
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: AdaptivTypography.overline.copyWith(
          color: AdaptivColors.text500,
        ),
      ),
    );
  }
}

// A tiny version of the zone indicator for use inside cards or list items
class CompactZoneIndicator extends StatelessWidget {
  final int currentBPM;  // The user's current heart rate
  final int maxHR;  // Maximum heart rate
  final int minHR;  // Resting heart rate

  const CompactZoneIndicator({
    super.key,
    required this.currentBPM,
    this.maxHR = 190,
    this.minHR = 50,
  });

  @override
  Widget build(BuildContext context) {
    // Calculate where the user's BPM falls in the range (0.0 to 1.0)
    final range = maxHR - minHR;
    final percentage = ((currentBPM - minHR) / range).clamp(0.0, 1.0);
    final zone = AdaptivColors.getHRZoneLabel(currentBPM);  // Zone name
    final color = AdaptivColors.getHRZoneColor(currentBPM);  // Zone color

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Mini bar — a tiny colored bar showing how high the BPM is
        Container(
          width: 40,
          height: 8,
          decoration: BoxDecoration(
            color: AdaptivColors.bg200,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Align(
            alignment: Alignment.centerLeft,
            child: FractionallySizedBox(
              widthFactor: percentage,
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 6),
        Text(
          zone,
          style: AdaptivTypography.overline.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
