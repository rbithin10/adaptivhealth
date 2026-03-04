/*
Notifications Screen

Displays health alerts and warnings for the current user.
Allows acknowledging alerts to mark them as read.
*/

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../services/edge_ai_store.dart';

class NotificationsScreen extends StatefulWidget {
  final ApiClient apiClient;

  const NotificationsScreen({
    super.key,
    required this.apiClient,
  });

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<Map<String, dynamic>> _alertsFuture;
  bool _showUnreadOnly = false;

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  void _loadAlerts() {
    setState(() {
      _alertsFuture = widget.apiClient.getAlerts(
        page: 1,
        perPage: 50,
        acknowledged: _showUnreadOnly ? false : null,
      );
    });
  }

  Future<void> _acknowledgeAlert(int alertId, int index) async {
    try {
      await widget.apiClient.acknowledgeAlert(alertId);
      _loadAlerts(); // Refresh the list
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Alert marked as read'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AdaptivColors.critical,
          ),
        );
      }
    }
  }

  Color _getSeverityColor(String? severity) {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'emergency':
        return AdaptivColors.critical;
      case 'warning':
        return AdaptivColors.warning;
      case 'info':
      default:
        return AdaptivColors.primary;
    }
  }

  IconData _getSeverityIcon(String? severity) {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'emergency':
        return Icons.error;
      case 'warning':
        return Icons.warning;
      case 'info':
      default:
        return Icons.info;
    }
  }

  String _formatTimestamp(String? timestamp) {
    if (timestamp == null || timestamp.isEmpty) return '';
    try {
      final dt = DateTime.parse(timestamp);
      final now = DateTime.now();
      final diff = now.difference(dt);

      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays == 1) return 'Yesterday';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.month}/${dt.day}/${dt.year}';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return Scaffold(
      backgroundColor: AdaptivColors.getBackgroundColor(brightness),
      appBar: AppBar(
        backgroundColor: AdaptivColors.getSurfaceColor(brightness),
        elevation: 0,
        title: Text(
          'Notifications',
          style: AdaptivTypography.screenTitle,
        ),
        actions: [
          // Filter toggle
          TextButton.icon(
            onPressed: () {
              setState(() {
                _showUnreadOnly = !_showUnreadOnly;
                _loadAlerts();
              });
            },
            icon: Icon(
              _showUnreadOnly ? Icons.filter_alt : Icons.filter_alt_outlined,
              size: 18,
            ),
            label: Text(_showUnreadOnly ? 'All' : 'Unread'),
            style: TextButton.styleFrom(
              foregroundColor: AdaptivColors.primary,
            ),
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _alertsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 64,
                      color: AdaptivColors.text400,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Could not load alerts',
                      style: AdaptivTypography.subtitle1.copyWith(
                        color: AdaptivColors.text600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      snapshot.error.toString(),
                      style: AdaptivTypography.caption.copyWith(
                        color: AdaptivColors.text400,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _loadAlerts,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          final data = snapshot.data!;
          final alerts = (data['alerts'] as List?) ?? [];

          if (alerts.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.notifications_none,
                      size: 64,
                      color: AdaptivColors.text400,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _showUnreadOnly
                          ? 'No unread notifications'
                          : 'No notifications yet',
                      style: AdaptivTypography.subtitle1.copyWith(
                        color: AdaptivColors.text600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'You\'re all caught up!',
                      style: AdaptivTypography.caption.copyWith(
                        color: AdaptivColors.text400,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              _loadAlerts();
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: alerts.length + 1, // +1 for edge AI section at top
              itemBuilder: (context, index) {
                // First item: Edge AI local alerts + GPS emergencies
                if (index == 0) {
                  return _buildEdgeAiAlertsSection();
                }

                // Cloud alerts (index - 1 because of edge AI section)
                final alertIdx = index - 1;
                final alert = alerts[alertIdx] as Map<String, dynamic>;
                final alertId = alert['alert_id'] as int;
                final title = alert['title'] as String? ?? 'Alert';
                final message = alert['message'] as String? ?? '';
                final severity = alert['severity'] as String?;
                final acknowledged = alert['acknowledged'] as bool? ?? false;
                final timestamp = alert['created_at'] as String?;

                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildAlertCard(
                    alertId: alertId,
                    title: title,
                    message: message,
                    severity: severity,
                    acknowledged: acknowledged,
                    timestamp: timestamp,
                    index: alertIdx,
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

  /// Build edge AI alerts section — shows local threshold alerts + GPS emergencies
  /// These are generated on-device without any network, even on a mountaintop
  Widget _buildEdgeAiAlertsSection() {
    EdgeAiStore? edgeStore;
    try {
      edgeStore = Provider.of<EdgeAiStore>(context, listen: true);
    } catch (_) {
      return const SizedBox.shrink();
    }

    final hasAlerts = edgeStore.activeAlerts.isNotEmpty;
    final hasEmergency = edgeStore.latestEmergency != null;
    final hasPending = edgeStore.pendingSyncCount > 0;

    if (!hasAlerts && !hasEmergency && !hasPending) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: edgeStore.modelLoaded ? AdaptivColors.stable : Colors.orange,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'On-Device Alerts',
                style: AdaptivTypography.subtitle2.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              if (hasPending)
                Text(
                  '${edgeStore.pendingSyncCount} pending sync',
                  style: AdaptivTypography.caption.copyWith(
                    color: AdaptivColors.text600,
                  ),
                ),
            ],
          ),
        ),

        // GPS Emergency
        if (hasEmergency)
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.red.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.location_on, color: Colors.red, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Emergency Location Recorded',
                        style: AdaptivTypography.subtitle2.copyWith(
                          color: Colors.red,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'GPS: ${edgeStore.latestEmergency!.latitude.toStringAsFixed(4)}, '
                        '${edgeStore.latestEmergency!.longitude.toStringAsFixed(4)}'
                        '${edgeStore.latestEmergency!.altitude != null ? " • ${edgeStore.latestEmergency!.altitude!.round()}m alt" : ""}',
                        style: AdaptivTypography.caption,
                      ),
                    ],
                  ),
                ),
                Icon(
                  edgeStore.latestEmergency!.synced ? Icons.cloud_done : Icons.cloud_off,
                  size: 16,
                  color: edgeStore.latestEmergency!.synced ? AdaptivColors.stable : Colors.orange,
                ),
              ],
            ),
          ),

        // Active threshold alerts
        ...edgeStore.activeAlerts.map((alert) => Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: (alert.severity == 'critical' ? AdaptivColors.critical : AdaptivColors.warning)
                .withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: (alert.severity == 'critical' ? AdaptivColors.critical : AdaptivColors.warning)
                  .withOpacity(0.3),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                alert.severity == 'critical' ? Icons.error : Icons.warning_amber,
                color: alert.severity == 'critical' ? AdaptivColors.critical : AdaptivColors.warning,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(alert.title, style: AdaptivTypography.subtitle2.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(alert.message, style: AdaptivTypography.body.copyWith(color: AdaptivColors.text700)),
                  ],
                ),
              ),
              // ON-DEVICE badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AdaptivColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'LOCAL',
                  style: AdaptivTypography.caption.copyWith(
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    color: AdaptivColors.primary,
                  ),
                ),
              ),
            ],
          ),
        )),

        // Divider between edge and cloud alerts
        if (hasAlerts || hasEmergency)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Divider(color: AdaptivColors.border300.withOpacity(0.5)),
          ),
      ],
    );
  }

  Widget _buildAlertCard({
    required int alertId,
    required String title,
    required String message,
    required String? severity,
    required bool acknowledged,
    required String? timestamp,
    required int index,
  }) {
    final severityColor = _getSeverityColor(severity);
    final severityIcon = _getSeverityIcon(severity);

    return Container(
      decoration: BoxDecoration(
        color: acknowledged
            ? AdaptivColors.white
            : severityColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: acknowledged
              ? AdaptivColors.border300
              : severityColor.withOpacity(0.3),
          width: acknowledged ? 1 : 2,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: acknowledged
              ? null
              : () => _acknowledgeAlert(alertId, index),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Severity icon
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: severityColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    severityIcon,
                    color: severityColor,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                // Content
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: AdaptivTypography.subtitle2.copyWith(
                                fontWeight: acknowledged
                                    ? FontWeight.w600
                                    : FontWeight.w700,
                                color: acknowledged
                                    ? AdaptivColors.text700
                                    : AdaptivColors.text900,
                              ),
                            ),
                          ),
                          if (!acknowledged)
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: severityColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        message,
                        style: AdaptivTypography.body.copyWith(
                          color: acknowledged
                              ? AdaptivColors.text600
                              : AdaptivColors.text700,
                        ),
                      ),
                      if (timestamp != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _formatTimestamp(timestamp),
                          style: AdaptivTypography.caption.copyWith(
                            color: AdaptivColors.text400,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Action button
                if (!acknowledged)
                  IconButton(
                    icon: const Icon(Icons.check_circle_outline),
                    color: severityColor,
                    onPressed: () => _acknowledgeAlert(alertId, index),
                    tooltip: 'Mark as read',
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
