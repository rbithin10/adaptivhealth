/*
HomeRehabCard widget — shows the user's active rehab programme on the Home tab.
Renders nothing when the user is not in a rehab programme.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../services/api_client.dart';
import '../../theme/colors.dart';
import '../rehab_program_screen.dart';

/// Tappable card showing rehab-programme progress.
/// Returns [SizedBox.shrink] when the user's rehab_phase is 'not_in_rehab'.
class HomeRehabCard extends StatelessWidget {
  final ApiClient apiClient;
  final Map<String, dynamic> user;
  /// Called after the user returns from the Rehab Programme screen
  /// so the parent can refresh its data.
  final VoidCallback onReturn;

  const HomeRehabCard({
    super.key,
    required this.apiClient,
    required this.user,
    required this.onReturn,
  });

  @override
  Widget build(BuildContext context) {
    final rehabPhase = user['rehab_phase'] as String? ?? 'not_in_rehab';
    if (rehabPhase == 'not_in_rehab') return const SizedBox.shrink();

    return FutureBuilder<Map<String, dynamic>>(
      future: apiClient.getRehabProgram().catchError((_) => <String, dynamic>{}),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(
            padding: EdgeInsets.only(bottom: 24),
            child: SizedBox(
              height: 80,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            ),
          );
        }

        final data = snapshot.data;
        if (data == null || data.isEmpty) return const SizedBox.shrink();

        final progress     = data['progress_summary'] as Map<String, dynamic>?;
        final programType  = data['program_type']     as String? ?? '';
        final status       = data['status']           as String? ?? 'active';
        final currentWeek  = progress?['current_week']                   as int? ?? 1;
        final sessionsThis = progress?['sessions_completed_this_week']   as int? ?? 0;
        final sessionsReq  = progress?['sessions_required_this_week']    as int? ?? 3;

        final isPhase2    = programType == 'phase_2_light';
        final label       = isPhase2 ? 'Phase II Rehab' : 'Phase III';
        final isCompleted = status == 'completed';

        return Padding(
          padding: const EdgeInsets.only(bottom: 24),
          child: GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RehabProgramScreen(apiClient: apiClient),
                ),
              ).then((_) => onReturn());
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isCompleted
                      ? [
                          AdaptivColors.stable,
                          AdaptivColors.stable.withOpacity(0.8)
                        ]
                      : [AdaptivColors.primary, AdaptivColors.primaryDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      isCompleted ? Icons.emoji_events : Icons.fitness_center,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'My Rehab Program',
                          style: GoogleFonts.dmSans(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          isCompleted
                              ? '$label — completed'
                              : '$label • Week $currentWeek • $sessionsThis of $sessionsReq today',
                          style: GoogleFonts.dmSans(
                              fontSize: 13, color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.white70),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
