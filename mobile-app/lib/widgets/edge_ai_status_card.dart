/// Edge AI Status Widget — Compact card showing on-device AI status.
///
/// Displays:
///   - Edge AI readiness indicator (green dot = loaded, red = cloud fallback)
///   - Latest risk score from edge ML (or "Waiting for vitals")
///   - Active threshold alerts (critical/warning)
///   - GPS emergency badge (if critical alert captured location)
///   - Sync status (pending count, last sync time)
///
/// USAGE:
///   // In any screen that has EdgeAiStore in the widget tree:
///   const EdgeAiStatusCard()
///
///   // The widget auto-updates via Provider when new predictions arrive.
library;

// Flutter's main UI toolkit
import 'package:flutter/material.dart';
// Date/time formatting (e.g. "3:45 PM")
import 'package:intl/intl.dart';
// Google's font library for consistent text styling
import 'package:google_fonts/google_fonts.dart';
// State management — lets us listen for AI prediction updates
import 'package:provider/provider.dart';
// Our local AI model store (holds predictions, alerts, sync state)
import '../services/edge_ai_store.dart';
// Cloud sync states (idle, syncing, offline, etc.)
import '../services/cloud_sync_service.dart';
// Data model for AI risk predictions
import '../models/edge_prediction.dart';
// Our custom color palette
import '../theme/colors.dart';

// ============================================================================
// Edge AI Status Card — For Home Screen
// ============================================================================

// A card that shows the status of on-device AI: risk score, alerts, GPS, sync
class EdgeAiStatusCard extends StatelessWidget {
  const EdgeAiStatusCard({super.key});

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;  // Light or dark mode

    // Try to get the AI store — it might not be available yet during startup
    EdgeAiStore? edgeStore;
    try {
      edgeStore = Provider.of<EdgeAiStore>(context);
    } catch (_) {
      return const SizedBox.shrink(); // Not ready yet — show nothing
    }

    // Stack up the different status sections vertically
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Green/orange/red dot + "Edge AI Active" header
        _buildHeader(edgeStore, brightness),
        const SizedBox(height: 8),

        // Show the risk score card if we have a prediction
        if (edgeStore.latestPrediction != null)
          _buildRiskCard(edgeStore.latestPrediction!, brightness),

        // Show any active health alerts (critical BPM, etc.)
        if (edgeStore.activeAlerts.isNotEmpty)
          ...edgeStore.activeAlerts.map(
            (alert) => _buildAlertCard(alert, brightness),
          ),

        // Show the GPS location captured during an emergency
        if (edgeStore.latestEmergency != null)
          _buildGpsEmergencyBadge(edgeStore.latestEmergency!, brightness),

        // Show cloud sync status (pending uploads, errors, last sync time)
        if (edgeStore.pendingSyncCount > 0 ||
            edgeStore.lastSyncErrorMessage != null ||
          edgeStore.lastSyncTime != null ||
          edgeStore.lastQueueEventMessage != null ||
          edgeStore.syncState != CloudSyncState.idle)
          _buildSyncStatus(edgeStore, brightness),
      ],
    );
  }

  // ---- Header: green/orange/red dot showing whether the AI model is loaded ----
  Widget _buildHeader(EdgeAiStore store, Brightness brightness) {
    final bool modelReady = store.modelLoaded;  // Is the AI model loaded on-device?
    late final Color statusColor;  // Dot color
    late final String statusText;  // Text next to the dot

    // Pick status based on model state
    if (store.isInitializing) {
      statusColor = Colors.orange;  // Still loading
      statusText = 'Edge AI Loading...';
    } else if (modelReady) {
      statusColor = AdaptivColors.stable;  // Fully loaded — running locally
      statusText = 'Edge AI Active (v${store.modelVersion})';
    } else if (store.isReady) {
      statusColor = Colors.orange;  // Threshold-only mode (no ML model)
      statusText = 'Edge Safety Active (Threshold Mode)';
    } else {
      statusColor = AdaptivColors.critical;  // Can't run locally — cloud fallback
      statusText = 'Edge AI Unavailable — Using Cloud';
    }

    return Row(
      children: [
        // Colored dot (green, orange, or red)
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: statusColor,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          statusText,
          style: GoogleFonts.dmSans(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: AdaptivColors.getSecondaryTextColor(brightness),
          ),
        ),
        const Spacer(),
        // Show how fast the AI ran its prediction (e.g. "12ms")
        if (store.latestPrediction != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: AdaptivColors.stable.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              '${store.latestPrediction!.inferenceTimeMs}ms',
              style: GoogleFonts.dmSans(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: AdaptivColors.stable,
              ),
            ),
          ),
      ],
    );
  }

  // ---- Risk Score Card: shows the AI's risk assessment (low/moderate/high) ----
  Widget _buildRiskCard(EdgeRiskPrediction prediction, Brightness brightness) {
    final riskColor = _getRiskColor(prediction.riskLevel);  // Color for this risk level
    final riskPercent = (prediction.riskScore * 100).toStringAsFixed(0);  // Convert 0.XX to XX%

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: riskColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: riskColor.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          // Circle with a risk-level icon (check, info, or warning)
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: riskColor.withOpacity(0.15),
            ),
            child: Icon(
              prediction.riskLevel == 'high'
                  ? Icons.warning_rounded
                  : prediction.riskLevel == 'moderate'
                      ? Icons.info_rounded
                      : Icons.check_circle_rounded,
              color: riskColor,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          // Risk level text and score percentage
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Edge AI Risk: ${prediction.riskLevel.toUpperCase()}',
                  style: GoogleFonts.dmSans(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AdaptivColors.getTextColor(brightness),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Score: $riskPercent% • Confidence: ${(prediction.confidence * 100).toStringAsFixed(0)}%',
                  style: GoogleFonts.dmSans(
                    fontSize: 12,
                    color: AdaptivColors.getSecondaryTextColor(brightness),
                  ),
                ),
              ],
            ),
          ),
          // "ON-DEVICE" badge to show this ran locally, not in the cloud
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: riskColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              'ON-DEVICE',
              style: GoogleFonts.dmSans(
                fontSize: 9,
                fontWeight: FontWeight.w700,
                color: riskColor,
                letterSpacing: 0.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---- Alert Card: shows a critical or warning health alert ----
  Widget _buildAlertCard(ThresholdAlert alert, Brightness brightness) {
    // Red for critical, orange for warnings
    final alertColor = alert.severity == 'critical' ? AdaptivColors.critical : Colors.orange;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: alertColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: alertColor.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                alert.severity == 'critical'
                    ? Icons.error_rounded
                    : Icons.warning_amber_rounded,
                color: alertColor,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  alert.title,
                  style: GoogleFonts.dmSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: alertColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            alert.message,
            style: GoogleFonts.dmSans(
              fontSize: 12,
              color: AdaptivColors.getTextColor(brightness),
            ),
          ),
          const SizedBox(height: 8),
          // Recommended actions (show up to 2 steps)
          ...alert.actions.take(2).map((action) => Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.arrow_right, size: 14, color: alertColor),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    action,
                    style: GoogleFonts.dmSans(
                      fontSize: 11,
                      color: AdaptivColors.getSecondaryTextColor(brightness),
                    ),
                  ),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }

  // ---- GPS Emergency Badge: shows the location captured during a critical alert ----
  Widget _buildGpsEmergencyBadge(
    GpsEmergencyAlert emergency,
    Brightness brightness,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.location_on, color: Colors.red, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Emergency Location Captured',
                  style: GoogleFonts.dmSans(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Colors.red,
                  ),
                ),
                Text(
                  '${emergency.latitude.toStringAsFixed(4)}, ${emergency.longitude.toStringAsFixed(4)}'
                  '${emergency.altitude != null ? ' • ${emergency.altitude!.round()}m alt' : ''}',
                  style: GoogleFonts.dmSans(
                    fontSize: 10,
                    color: AdaptivColors.getSecondaryTextColor(brightness),
                  ),
                ),
              ],
            ),
          ),
          // Cloud icon showing whether the location has been synced to the server
          Icon(
            emergency.synced ? Icons.cloud_done : Icons.cloud_off,
            size: 16,
            color: emergency.synced ? AdaptivColors.stable : Colors.orange,  // Green = synced, orange = pending
          ),
        ],
      ),
    );
  }

  // ---- Sync Status: shows upload progress, errors, and a Force Sync button ----
  Widget _buildSyncStatus(EdgeAiStore store, Brightness brightness) {
    final secondaryColor = AdaptivColors.getSecondaryTextColor(brightness);  // Muted text color
    final lastErrorTime = store.lastSyncErrorAt;  // When the last error happened
    final lastSyncTime = store.lastSyncTime;  // When the last successful sync was
    final hasError = store.lastSyncErrorMessage != null;  // Whether there's an error to show
    // Get the icon, color, and label for the current sync state
    final status =
      _statusPresentation(store.syncState, store.pendingSyncCount, brightness);
    final queueEventTime = store.lastQueueEventAt;  // When the last queue event happened

    // Helper to format a DateTime as "3:45 PM"
    String formatTime(DateTime value) => DateFormat('h:mm a').format(value.toLocal());

    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                status.icon,
                size: 12,
                color: status.color,
              ),
              const SizedBox(width: 4),
              Text(
                status.label,
                style: GoogleFonts.dmSans(
                  fontSize: 11,
                  color: status.color,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (store.syncState == CloudSyncState.syncing) ...[
                const SizedBox(width: 8),
                SizedBox(
                  width: 10,
                  height: 10,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.5,
                    color: status.color,
                  ),
                ),
              ],
            ],
          ),
          if (hasError &&
              store.syncState != CloudSyncState.authExpired &&
              store.syncState != CloudSyncState.rateLimited &&
              store.syncState != CloudSyncState.serverError &&
              store.syncState != CloudSyncState.offline) ...[
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.error_outline, size: 12, color: Colors.orange),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    'Last sync failed: ${store.lastSyncErrorMessage!}'
                    '${lastErrorTime != null ? ' (${formatTime(lastErrorTime)})' : ''}',
                    style: GoogleFonts.dmSans(
                      fontSize: 10,
                      color: Colors.orange,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ] else if (store.syncState == CloudSyncState.authExpired ||
              store.syncState == CloudSyncState.rateLimited ||
              store.syncState == CloudSyncState.serverError ||
              store.syncState == CloudSyncState.offline) ...[
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(status.icon, size: 12, color: status.color),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    store.lastSyncErrorMessage ?? status.label,
                    style: GoogleFonts.dmSans(
                      fontSize: 10,
                      color: status.color,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            if (lastErrorTime != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  'Observed: ${formatTime(lastErrorTime)}',
                  style: GoogleFonts.dmSans(
                    fontSize: 10,
                    color: secondaryColor,
                  ),
                ),
              ),
          ] else if (lastSyncTime != null) ...[
            const SizedBox(height: 4),
            Text(
              'Last synced: ${formatTime(lastSyncTime)}',
              style: GoogleFonts.dmSans(
                fontSize: 10,
                color: secondaryColor,
              ),
            ),
          ],
          if (store.lastQueueEventMessage != null) ...[
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_outline, size: 12, color: Colors.orange),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    '${store.lastQueueEventMessage!}'
                    '${queueEventTime != null ? ' (${formatTime(queueEventTime)})' : ''}',
                    style: GoogleFonts.dmSans(
                      fontSize: 10,
                      color: Colors.orange,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: store.isSyncing
                  ? null
                  : () async {
                      await store.syncNow();
                    },
              icon: const Icon(Icons.sync, size: 14),
              label: const Text('Force Sync'),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                minimumSize: const Size(0, 0),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Map each cloud sync state to a user-friendly label, color, and icon
  _SyncStatusPresentation _statusPresentation(
    CloudSyncState state,
    int pending,
    Brightness brightness,
  ) {
    switch (state) {
      case CloudSyncState.syncing:
        return _SyncStatusPresentation(
          label: 'Syncing $pending queued reading${pending == 1 ? '' : 's'}...',
          color: Colors.blueGrey,
          icon: Icons.sync,
        );
      case CloudSyncState.offline:
        return _SyncStatusPresentation(
          label: 'Offline — $pending reading${pending == 1 ? '' : 's'} queued safely',
          color: Colors.orange,
          icon: Icons.cloud_off,
        );
      case CloudSyncState.authExpired:
        return _SyncStatusPresentation(
          label: 'Authentication required to resume sync',
          color: Colors.orange,
          icon: Icons.lock_outline,
        );
      case CloudSyncState.rateLimited:
        return _SyncStatusPresentation(
          label: 'Rate limited — retrying automatically',
          color: Colors.orange,
          icon: Icons.hourglass_bottom,
        );
      case CloudSyncState.serverError:
        return _SyncStatusPresentation(
          label: 'Server unavailable — retrying automatically',
          color: Colors.orange,
          icon: Icons.cloud_off,
        );
      case CloudSyncState.online:
        return _SyncStatusPresentation(
          label: 'Online — $pending reading${pending == 1 ? '' : 's'} pending next sync',
          color: AdaptivColors.stable,
          icon: Icons.cloud_queue,
        );
      case CloudSyncState.idle:
        return _SyncStatusPresentation(
          label: 'Sync idle — all queued readings submitted',
          color: AdaptivColors.getSecondaryTextColor(brightness),
          icon: Icons.cloud_done,
        );
    }
  }

  // ---- Helpers: pick a color based on risk level text ----
  Color _getRiskColor(String level) {
    switch (level.toLowerCase()) {
      case 'high':
      case 'critical':
        return AdaptivColors.critical;
      case 'moderate':
        return Colors.orange;
      default:
        return AdaptivColors.stable;
    }
  }
}

// Simple data class to hold the icon, color, and text for a sync state
class _SyncStatusPresentation {
  final String label;  // Text description (e.g. "Syncing 3 readings...")
  final Color color;   // Color for the status indicator
  final IconData icon;  // Icon to show next to the text

  const _SyncStatusPresentation({
    required this.label,
    required this.color,
    required this.icon,
  });
}
