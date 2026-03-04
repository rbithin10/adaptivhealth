/*
HomeHeartRateRing widget — central heart rate visualisation for the Home tab.
Stateless; receives only data values so it can be tested and reused independently.
*/

import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Circular ring that displays the current heart rate with a risk-colour glow.
class HomeHeartRateRing extends StatelessWidget {
  final int heartRate;
  final String riskLevel;
  final int maxSafeHR;

  const HomeHeartRateRing({
    super.key,
    required this.heartRate,
    required this.riskLevel,
    required this.maxSafeHR,
  });

  @override
  Widget build(BuildContext context) {
    final ringColor = AdaptivColors.getRiskColor(riskLevel);

    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            // Outer glow
            Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: ringColor.withOpacity(0.3),
                    blurRadius: 30,
                    spreadRadius: 5,
                  ),
                ],
              ),
            ),
            // Main ring
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: ringColor, width: 12),
                gradient: RadialGradient(
                  colors: [Colors.white, ringColor.withOpacity(0.05)],
                ),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.favorite, color: ringColor, size: 32),
                    const SizedBox(height: 8),
                    Text(
                      heartRate.toString(),
                      style: AdaptivTypography.heroNumber.copyWith(
                        color: ringColor,
                        fontSize: 48,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'BPM',
                      style: AdaptivTypography.heroUnit.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: AdaptivColors.stable.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AdaptivColors.stable,
                              boxShadow: [
                                BoxShadow(
                                  color: AdaptivColors.stable.withOpacity(0.5),
                                  blurRadius: 4,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Live',
                            style: AdaptivTypography.caption.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
