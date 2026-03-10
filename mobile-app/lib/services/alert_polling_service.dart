/*
Alert Polling Service.

Checks the server every 5 minutes for new health alerts (like abnormal
vitals or messages from the care team). When a new alert is found,
it shows a push notification on the user's phone.

Only one copy of this service runs in the whole app.
*/

// Lets us run code on a repeating timer
import 'dart:async';

// Our helper that talks to the backend server
import 'api_client.dart';
// Shows push notifications on the user's phone
import 'notification_service.dart';

// This service checks the server for new health alerts on a schedule
class AlertPollingService {
  // Private constructor — only this file can create an instance
  AlertPollingService._internal();

  // The single shared instance used everywhere in the app
  static final AlertPollingService instance = AlertPollingService._internal();

  // When other files call AlertPollingService(), return the shared instance
  factory AlertPollingService() => instance;

  // The repeating timer that triggers every 5 minutes
  Timer? _pollTimer;
  // Remember the last time we checked so we only fetch NEW alerts
  DateTime _lastCheckedAt = DateTime.now();
  // The server client we use to fetch alerts
  ApiClient? _apiClient;
  // Whether the service is currently active
  bool _isRunning = false;

  // Keep track of which alert IDs we already showed, so we don't show duplicates
  final Set<int> _notifiedAlertIds = <int>{};

  // Start checking for alerts every 5 minutes
  void start(ApiClient apiClient) {
    _apiClient = apiClient;
    // Reset the "last checked" time to now so we only get future alerts
    _lastCheckedAt = DateTime.now();
    _isRunning = true;

    // Cancel any existing timer before starting a new one
    _pollTimer?.cancel();
    // Check for new alerts every 5 minutes
    _pollTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _checkForNewAlerts(),
    );
  }

  // Stop checking for alerts and clean up
  void stop() {
    _isRunning = false;
    _pollTimer?.cancel();
    _pollTimer = null;
    // Clear the list of already-notified alerts
    _notifiedAlertIds.clear();
  }

  // Ask the server if there are any new unacknowledged alerts
  Future<void> _checkForNewAlerts() async {
    // Don't check if the service was stopped or we have no server client
    if (!_isRunning || _apiClient == null) return;

    try {
      // Fetch up to 50 unacknowledged alerts from the server
      final response = await _apiClient!.getAlerts(
        page: 1,
        perPage: 50,
        acknowledged: false,
      );

      // Get the list of alerts from the response
      final alertsRaw = response['alerts'];
      // If the response doesn't contain a valid list, skip this check
      if (alertsRaw is! List) {
        _lastCheckedAt = DateTime.now();
        return;
      }

      final now = DateTime.now();

      // Go through each alert to see if it's new
      for (final item in alertsRaw) {
        // Skip if the item isn't a valid data map
        if (item is! Map) continue;

        final alert = Map<String, dynamic>.from(item);

        // Skip alerts the user already acknowledged
        final acknowledged = alert['acknowledged'] as bool? ?? false;
        if (acknowledged) continue;

        // Skip alerts we already showed a notification for
        final alertId = _safeToInt(alert['alert_id']);
        if (alertId != null && _notifiedAlertIds.contains(alertId)) {
          continue;
        }

        // Skip alerts that were created before our last check
        final createdAt = _parseDate(alert['created_at']);
        if (createdAt == null || !createdAt.isAfter(_lastCheckedAt)) {
          continue;
        }

        // Use the alert's title, or a default if none was provided
        final title = (alert['title'] as String?)?.trim().isNotEmpty == true
            ? alert['title'] as String
            : 'Health Alert';
        // Use the alert's message, or a default if none was provided
        final body = (alert['message'] as String?)?.trim().isNotEmpty == true
            ? alert['message'] as String
            : 'You have a new health alert. Please check your notifications.';

        // Show a push notification on the user's phone
        await NotificationService.instance.showAlert(
          title: title,
          body: body,
          payload: alertId?.toString(),
        );

        // Remember we already notified this alert so we don't show it again
        if (alertId != null) {
          _notifiedAlertIds.add(alertId);
        }
      }

      // Update the last checked timestamp for the next poll
      _lastCheckedAt = now;
    } catch (_) {
      // If something goes wrong, silently skip — the next poll will try again
    }
  }

  // Safely convert any value to an integer (handles strings, doubles, etc.)
  int? _safeToInt(dynamic value) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }

  // Try to parse a date string into a DateTime, or return null if it's invalid
  DateTime? _parseDate(dynamic value) {
    if (value is! String || value.trim().isEmpty) return null;
    return DateTime.tryParse(value)?.toLocal();
  }
}
