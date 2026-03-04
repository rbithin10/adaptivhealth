/*
HomeVitalsGrid widget — secondary vitals row (SpO2, BP, HRV) on the Home tab.
Receives pre-computed sparkline arrays from the parent so the widget stays
fully stateless and the data pipeline remains in home_screen.dart.
*/

import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/widgets.dart';

/// Horizontal scrolling row of [VitalCard] widgets for SpO2, BP, and HRV.
class HomeVitalsGrid extends StatelessWidget {
  final int spo2;
  final int systolicBp;
  final int diastolicBp;
  final int hrv;
  final List<double> spo2Trend;
  final List<double> bpTrend;
  final List<double> hrvTrend;
  final VoidCallback onViewAll;

  const HomeVitalsGrid({
    super.key,
    required this.spo2,
    required this.systolicBp,
    required this.diastolicBp,
    required this.hrv,
    required this.spo2Trend,
    required this.bpTrend,
    required this.hrvTrend,
    required this.onViewAll,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header with "View All" tap target.
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              Text(
                'Vitals',
                style: AdaptivTypography.subtitle1
                    .copyWith(fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              GestureDetector(
                onTap: onViewAll,
                child: Text(
                  'View All',
                  style: AdaptivTypography.label.copyWith(
                    color: AdaptivColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),

        // Compact horizontal scroll of VitalCards.
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.air,
                  label: 'SpO2',
                  value: spo2.toString(),
                  unit: '%',
                  status: spo2 < 90
                      ? VitalStatus.critical
                      : spo2 < 95
                          ? VitalStatus.warning
                          : VitalStatus.safe,
                  trend: spo2Trend,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.water_drop,
                  label: 'BP',
                  value: '$systolicBp/$diastolicBp',
                  unit: 'mmHg',
                  status: systolicBp > 140
                      ? VitalStatus.critical
                      : systolicBp > 130
                          ? VitalStatus.warning
                          : VitalStatus.safe,
                  trend: bpTrend,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 160,
                child: VitalCard(
                  icon: Icons.timeline,
                  label: 'HRV',
                  value: hrv > 0 ? hrv.toString() : '—',
                  unit: 'ms',
                  status: hrv > 40
                      ? VitalStatus.safe
                      : hrv > 20
                          ? VitalStatus.caution
                          : VitalStatus.warning,
                  trend: hrvTrend,
                  onTap: () {},
                ),
              ),
              const SizedBox(width: 12),
            ],
          ),
        ),
      ],
    );
  }
}
