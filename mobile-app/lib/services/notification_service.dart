/*
Notification Service.

Shows push notifications on the user's phone (like "Your heart rate is high").
Handles setting up notification channels on Android and permission requests on iOS.

Only one copy of this service exists in the whole app.
*/

// Lets us check if we're in debug mode (to print tap info)
import 'package:flutter/foundation.dart';
// The library that shows actual push notifications on the phone
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

// Manages showing local push notifications on the user's device
class NotificationService {
  // Private constructor — only this file can create an instance
  NotificationService._internal();

  // The single shared instance used everywhere in the app
  static final NotificationService instance = NotificationService._internal();

  // When other files call NotificationService(), return the shared instance
  factory NotificationService() => instance;

  // The notification channel ID that Android uses to group our alerts
  static const String _channelId = 'health_alerts';
  // The human-readable channel name shown in Android's notification settings
  static const String _channelName = 'Health Alerts';
  // Description of what this notification channel is for
  static const String _channelDescription =
      'Local health alerts from Edge AI and server polling.';

  // The notification plugin that actually talks to the phone's OS
  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  // Each notification gets a unique number so they don't overwrite each other
  int _nextNotificationId = 1;
  // Whether we already ran the setup — prevents running it twice
  bool _initialized = false;

  // Set up the notification system — must be called once when the app starts
  Future<void> initialize() async {
    // Don't run setup twice
    if (_initialized) return;

    // Tell Android to use our app icon for notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    // Ask iOS for permission to show alerts, badges, and play sounds
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    // Combine Android and iOS settings into one config
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    // Start the notification plugin and tell it what to do when tapped
    await _plugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Create a notification channel on Android (required for Android 8+)
    const androidChannel = AndroidNotificationChannel(
      _channelId,
      _channelName,
      description: _channelDescription,
      importance: Importance.high,
    );

    // Get the Android-specific plugin to register the channel
    final androidImpl =
        _plugin.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();

    // Register the channel and ask for notification permission on Android 13+
    await androidImpl?.createNotificationChannel(androidChannel);
    await androidImpl?.requestNotificationsPermission();

    // Mark setup as complete so we don't run it again
    _initialized = true;
  }

  // Show a health alert notification on the user's phone
  Future<void> showAlert({
    required String title,
    required String body,
    String? payload,
  }) async {
    // Make sure the notification system is set up first
    if (!_initialized) {
      await initialize();
    }

    // Give this notification a unique ID number
    final id = _nextNotificationId++;

    // Android notification settings — high priority so it pops up immediately
    const androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDescription,
      importance: Importance.high,
      priority: Priority.high,
      playSound: true,
      autoCancel: true,
    );

    // iOS notification settings — show banner, badge number, and play sound
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    // Combine Android and iOS settings
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    // Actually show the notification on the user's phone
    await _plugin.show(id, title, body, details, payload: payload);
  }

  // Called when the user taps on a notification — currently just logs it for debugging
  void _onNotificationTapped(NotificationResponse response) {
    if (kDebugMode) {
      debugPrint(
        'Notification tapped: payload=${response.payload}, actionId=${response.actionId}',
      );
    }
  }
}
