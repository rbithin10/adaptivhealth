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

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../services/edge_ai_store.dart';
import '../models/edge_prediction.dart';
import '../theme/colors.dart';

// ============================================================================
// Edge AI Status Card — For Home Screen
// ============================================================================

class EdgeAiStatusCard extends StatelessWidget {
  const EdgeAiStatusCard({super.key});

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;

    // Safely try to get EdgeAiStore — may not be provided yet
    EdgeAiStore? edgeStore;
    try {
      edgeStore = Provider.of<EdgeAiStore>(context);
    } catch (_) {
      return const SizedBox.shrink(); // Not in widget tree yet
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header row: Edge AI indicator
        _buildHeader(edgeStore, brightness),
        const SizedBox(height: 8),

        // Risk score card (if prediction available)
        if (edgeStore.latestPrediction != null)
          _buildRiskCard(edgeStore.latestPrediction!, brightness),

        // Active alerts
        if (edgeStore.activeAlerts.isNotEmpty)
          ...edgeStore.activeAlerts.map(
            (alert) => _buildAlertCard(alert, brightness),
          ),

        // GPS emergency badge
        if (edgeStore.latestEmergency != null)
          _buildGpsEmergencyBadge(edgeStore.latestEmergency!, brightness),

        // Sync status
        if (edgeStore.pendingSyncCount > 0 ||
            edgeStore.lastSyncErrorMessage != null ||
            edgeStore.lastSyncTime != null)
          _buildSyncStatus(edgeStore, brightness),
      ],
    );
  }

  // ---- Header: Edge AI status indicator ----
  Widget _buildHeader(EdgeAiStore store, Brightness brightness) {
    final bool modelReady = store.modelLoaded;
    late final Color statusColor;
    late final String statusText;

    if (store.isInitializing) {
      statusColor = Colors.orange;
      statusText = 'Edge AI Loading...';
    } else if (modelReady) {
      statusColor = AdaptivColors.stable;
      statusText = 'Edge AI Active (v${store.modelVersion})';
    } else if (store.isReady) {
      statusColor = Colors.orange;
      statusText = 'Edge Safety Active (Threshold Mode)';
    } else {
      statusColor = AdaptivColors.critical;
      statusText = 'Edge AI Unavailable — Using Cloud';
    }

    return Row(
      children: [
        // Status dot
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
        // Inference time badge (if available)
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

  // ---- Risk Score Card ----
  Widget _buildRiskCard(EdgeRiskPrediction prediction, Brightness brightness) {
    final riskColor = _getRiskColor(prediction.riskLevel);
    final riskPercent = (prediction.riskScore * 100).toStringAsFixed(0);

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
          // Risk level icon
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
          // Risk info
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
          // Source badge
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

  // ---- Alert Card ----
  Widget _buildAlertCard(ThresholdAlert alert, Brightness brightness) {
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
          // Action steps
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

  // ---- GPS Emergency Badge ----
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
          // Sync indicator
          Icon(
            emergency.synced ? Icons.cloud_done : Icons.cloud_off,
            size: 16,
            color: emergency.synced ? AdaptivColors.stable : Colors.orange,
          ),
        ],
      ),
    );
  }

  // ---- Sync Status ----
  Widget _buildSyncStatus(EdgeAiStore store, Brightness brightness) {
    final secondaryColor = AdaptivColors.getSecondaryTextColor(brightness);
    final lastErrorTime = store.lastSyncErrorAt;
    final lastSyncTime = store.lastSyncTime;
    final hasError = store.lastSyncErrorMessage != null;

    String formatTime(DateTime value) => DateFormat('h:mm a').format(value.toLocal());

    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.sync,
                size: 12,
                color: secondaryColor,
              ),
              const SizedBox(width: 4),
              Text(
                '${store.pendingSyncCount} readings pending sync',
                style: GoogleFonts.dmSans(
                  fontSize: 11,
                  color: secondaryColor,
                ),
              ),
              if (store.isSyncing) ...[
                const SizedBox(width: 8),
                SizedBox(
                  width: 10,
                  height: 10,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.5,
                    color: secondaryColor,
                  ),
                ),
              ],
            ],
          ),
          if (hasError) ...[
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
        ],
      ),
    );
  }

  // ---- Helpers ----
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
