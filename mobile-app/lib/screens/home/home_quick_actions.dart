/*
HomeQuickActionsRow widget — four quick-action buttons on the Home tab.
Stateless; navigation callbacks are injected by the parent screen.
*/

import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Row of four tappable action buttons used on the Home dashboard.
class HomeQuickActionsRow extends StatelessWidget {
  final VoidCallback onWorkout;
  final VoidCallback onRecovery;
  final VoidCallback onHealth;
  final VoidCallback onAiCoach;

  const HomeQuickActionsRow({
    super.key,
    required this.onWorkout,
    required this.onRecovery,
    required this.onHealth,
    required this.onAiCoach,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick Actions',
          style: AdaptivTypography.subtitle1.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _QuickActionButton(
                icon: Icons.directions_run,
                label: 'Start Workout',
                color: AdaptivColors.primary,
                onTap: onWorkout,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _QuickActionButton(
                icon: Icons.self_improvement,
                label: 'Recovery',
                color: const Color(0xFF9C27B0),
                onTap: onRecovery,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _QuickActionButton(
                icon: Icons.monitor_heart,
                label: 'Health',
                color: AdaptivColors.critical,
                onTap: onHealth,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _QuickActionButton(
                icon: Icons.smart_toy_outlined,
                label: 'AI Coach',
                color: AdaptivColors.stable,
                onTap: onAiCoach,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _QuickActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 104),
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              label,
              style: AdaptivTypography.caption.copyWith(
                color: color,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
