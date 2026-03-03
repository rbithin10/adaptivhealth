import 'dart:async';

import 'api_client.dart';
import 'notification_service.dart';

class AlertPollingService {
  AlertPollingService._internal();

  static final AlertPollingService instance = AlertPollingService._internal();

  factory AlertPollingService() => instance;

  Timer? _pollTimer;
  DateTime _lastCheckedAt = DateTime.now();
  ApiClient? _apiClient;
  bool _isRunning = false;

  final Set<int> _notifiedAlertIds = <int>{};

  void start(ApiClient apiClient) {
    _apiClient = apiClient;
    _lastCheckedAt = DateTime.now();
    _isRunning = true;

    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _checkForNewAlerts(),
    );
  }

  void stop() {
    _isRunning = false;
    _pollTimer?.cancel();
    _pollTimer = null;
    _notifiedAlertIds.clear();
  }

  Future<void> _checkForNewAlerts() async {
    if (!_isRunning || _apiClient == null) return;

    try {
      final response = await _apiClient!.getAlerts(
        page: 1,
        perPage: 50,
        acknowledged: false,
      );

      final alertsRaw = response['alerts'];
      if (alertsRaw is! List) {
        _lastCheckedAt = DateTime.now();
        return;
      }

      final now = DateTime.now();

      for (final item in alertsRaw) {
        if (item is! Map) continue;

        final alert = Map<String, dynamic>.from(item as Map);

        final acknowledged = alert['acknowledged'] as bool? ?? false;
        if (acknowledged) continue;

        final alertId = _safeToInt(alert['alert_id']);
        if (alertId != null && _notifiedAlertIds.contains(alertId)) {
          continue;
        }

        final createdAt = _parseDate(alert['created_at']);
        if (createdAt == null || !createdAt.isAfter(_lastCheckedAt)) {
          continue;
        }

        final title = (alert['title'] as String?)?.trim().isNotEmpty == true
            ? alert['title'] as String
            : 'Health Alert';
        final body = (alert['message'] as String?)?.trim().isNotEmpty == true
            ? alert['message'] as String
            : 'You have a new health alert. Please check your notifications.';

        await NotificationService.instance.showAlert(
          title: title,
          body: body,
          payload: alertId?.toString(),
        );

        if (alertId != null) {
          _notifiedAlertIds.add(alertId);
        }
      }

      _lastCheckedAt = now;
    } catch (_) {
      // Silently fail; next poll will retry.
    }
  }

  int? _safeToInt(dynamic value) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }

  DateTime? _parseDate(dynamic value) {
    if (value is! String || value.trim().isEmpty) return null;
    return DateTime.tryParse(value)?.toLocal();
  }
}
