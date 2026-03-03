/*
Medication Reminder Service.

Handles local notifications for medication reminders and scheduling.
Uses flutter_local_notifications to schedule daily reminders at user-specified times.

This is a singleton service initialized after login.
*/

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz_data;
import '../services/api_client.dart';

class MedicationReminderService {
  MedicationReminderService._internal();

  static final MedicationReminderService _instance = MedicationReminderService._internal();

  factory MedicationReminderService() {
    return _instance;
  }

  final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  /// Initialize the notification plugin.
  /// Call this once after login. Skipped on web (no local notifications).
  Future<void> init() async {
    if (_initialized) return;
    if (kIsWeb) {
      if (kDebugMode) debugPrint('MedicationReminderService: skipped on web');
      return;
    }

    // Initialize timezone data
    tz_data.initializeTimeZones();

    // Android notification settings
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');

    // iOS notification settings
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    // Request permissions on iOS
    await _notifications
        .resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(alert: true, badge: true, sound: true);

    // Request permissions on Android 13+
    await _notifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    _initialized = true;
    if (kDebugMode) debugPrint('MedicationReminderService initialized');
  }

  /// Handle notification tap.
  /// For MVP, this just opens the app. Future: navigate to profile screen.
  void _onNotificationTap(NotificationResponse response) {
    if (kDebugMode) debugPrint('Notification tapped: ${response.payload}');
    // The app opens automatically when notification is tapped.
    // Future enhancement: parse payload and navigate to specific screen.
  }

  /// Schedule daily reminders for all enabled medications.
  /// Call cancelAll() first to avoid duplicates.
  Future<void> scheduleReminders(List<Map<String, dynamic>> medications) async {
    if (!_initialized) {
      if (kDebugMode) {
        debugPrint('MedicationReminderService not initialized, skipping schedule');
      }
      return;
    }

    for (final med in medications) {
      final enabled = med['reminder_enabled'] as bool? ?? false;
      if (!enabled) continue;

      final timeStr = med['reminder_time'] as String?;
      if (timeStr == null || timeStr.isEmpty) continue;

      final medId = med['medication_id'] as int;
      final drugName = med['drug_name'] as String? ?? 'Medication';
      final dose = med['dose'] as String? ?? '';

      // Parse time string (HH:MM)
      final parts = timeStr.split(':');
      if (parts.length != 2) continue;

      final hour = int.tryParse(parts[0]) ?? 8;
      final minute = int.tryParse(parts[1]) ?? 0;

      // Schedule daily notification
      await _scheduleDailyNotification(
        id: medId,
        title: 'Medication Reminder',
        body: 'Time to take $drugName${dose.isNotEmpty ? ' $dose' : ''}',
        hour: hour,
        minute: minute,
      );

      if (kDebugMode) {
        debugPrint('Scheduled reminder: $drugName at $timeStr (id: $medId)');
      }
    }
  }

  /// Schedule a daily notification at a specific time.
  Future<void> _scheduleDailyNotification({
    required int id,
    required String title,
    required String body,
    required int hour,
    required int minute,
  }) async {
    // Calculate next occurrence of the specified time
    final now = tz.TZDateTime.now(tz.local);
    var scheduledDate = tz.TZDateTime(
      tz.local,
      now.year,
      now.month,
      now.day,
      hour,
      minute,
    );

    // If time has passed today, schedule for tomorrow
    if (scheduledDate.isBefore(now)) {
      scheduledDate = scheduledDate.add(const Duration(days: 1));
    }

    const androidDetails = AndroidNotificationDetails(
      'medication_reminders',
      'Medication Reminders',
      channelDescription: 'Daily medication reminder notifications',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.zonedSchedule(
      id,
      title,
      body,
      scheduledDate,
      details,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time, // Daily repeat
      payload: 'medication_$id',
    );
  }

  /// Cancel all scheduled notifications.
  Future<void> cancelAll() async {
    await _notifications.cancelAll();
    if (kDebugMode) debugPrint('All medication reminders cancelled');
  }

  /// Cancel a specific notification by ID.
  Future<void> cancel(int id) async {
    await _notifications.cancel(id);
    if (kDebugMode) debugPrint('Cancelled reminder id: $id');
  }

  /// Refresh reminders from the server.
  /// Fetches current medication reminders and reschedules all notifications.
  Future<void> refreshReminders(ApiClient apiClient) async {
    try {
      final medications = await apiClient.getMedicationReminders();
      await cancelAll();
      await scheduleReminders(medications);
      if (kDebugMode) {
        debugPrint('Medication reminders refreshed: ${medications.length} medications');
      }
    } catch (e) {
      if (kDebugMode) debugPrint('Failed to refresh medication reminders: $e');
    }
  }
}
