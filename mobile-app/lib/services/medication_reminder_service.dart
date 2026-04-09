/*
Medication Reminder Service.

Sends phone notifications to remind the patient to take their medications.
Uses the phone's built-in notification system to schedule daily reminders
at the times the user has chosen for each medication.

Only one copy of this service exists in the whole app.
*/

// Gives us debugging tools and the kIsWeb flag
import 'package:flutter/foundation.dart';
// The plugin that sends notifications to the phone's notification tray
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
// Works with time zones so notifications fire at the right local time
import 'package:timezone/timezone.dart' as tz;
// Loads all time zone data (needed for scheduling notifications)
import 'package:timezone/data/latest.dart' as tz_data;
// Talks to the server to get the list of medications
import '../services/api_client.dart';

// Manages medication reminder notifications on the phone
class MedicationReminderService {
  // Private constructor — only this file can create an instance
  MedicationReminderService._internal();

  // The single shared instance used everywhere in the app
  static final MedicationReminderService _instance =
      MedicationReminderService._internal();

  // When other files call MedicationReminderService(), return the shared instance
  factory MedicationReminderService() {
    return _instance;
  }

  // The notification plugin that talks to the phone's notification system
  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();
  // Whether we've already set up the notification system
  bool _initialized = false;

  // Set up the notification system (call once after login)
  Future<void> init() async {
    // Don't set up twice
    if (_initialized) return;
    // Notifications don't work on web browsers
    if (kIsWeb) {
      if (kDebugMode) debugPrint('MedicationReminderService: skipped on web');
      return;
    }

    // Load time zone info so we can schedule at exact local times
    tz_data.initializeTimeZones();

    // Tell Android to use the app icon for notifications
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    // Ask iOS for permission to show alerts, badges, and sounds
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    // Combine Android and iOS settings
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    // Initialize the notification plugin
    await _notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    // Make sure we have notification permission on iOS
    await _notifications
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(alert: true, badge: true, sound: true);

    // Make sure we have notification permission on Android 13+
    await _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    _initialized = true;
    if (kDebugMode) debugPrint('MedicationReminderService initialized');
  }

  // Called when the user taps on a notification — opens the app
  void _onNotificationTap(NotificationResponse response) {
    if (kDebugMode) debugPrint('Notification tapped: ${response.payload}');
    // The app opens automatically when notification is tapped.
    // Future enhancement: parse payload and navigate to specific screen.
  }

  // Schedule daily reminders for all medications that have reminders turned on
  Future<void> scheduleReminders(List<Map<String, dynamic>> medications) async {
    // Can't schedule on web or if notifications aren't set up yet
    if (kIsWeb || !_initialized) {
      if (kDebugMode) {
        debugPrint(
            'MedicationReminderService schedule skipped (web or not initialized)');
      }
      return;
    }

    // Go through each medication and schedule a reminder if enabled
    for (final med in medications) {
      // Skip medications that don't have reminders turned on
      final enabled = med['reminder_enabled'] as bool? ?? false;
      if (!enabled) continue;

      // Skip if no reminder time is set
      final timeStr = med['reminder_time'] as String?;
      if (timeStr == null || timeStr.isEmpty) continue;

      // Get the medication details for the notification message
      final medId = med['medication_id'] as int;
      final drugName = med['drug_name'] as String? ?? 'Medication';
      final dose = med['dose'] as String? ?? '';

      // Parse the time string (format: "HH:MM")
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

  // Schedule a notification that fires at the same time every day
  Future<void> _scheduleDailyNotification({
    required int id,
    required String title,
    required String body,
    required int hour,
    required int minute,
  }) async {
    // Figure out when the next occurrence of this time is
    final now = tz.TZDateTime.now(tz.local);
    var scheduledDate = tz.TZDateTime(
      tz.local,
      now.year,
      now.month,
      now.day,
      hour,
      minute,
    );

    // If this time already passed today, schedule for tomorrow instead
    if (scheduledDate.isBefore(now)) {
      scheduledDate = scheduledDate.add(const Duration(days: 1));
    }

    // Android notification appearance settings
    const androidDetails = AndroidNotificationDetails(
      'medication_reminders',
      'Medication Reminders',
      channelDescription: 'Daily medication reminder notifications',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );

    // iOS notification appearance settings
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    // Combine Android + iOS settings
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    // Schedule the notification to repeat daily at the same time
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

  // Cancel all scheduled medication reminders
  Future<void> cancelAll() async {
    if (kIsWeb || !_initialized) {
      if (kDebugMode) {
        debugPrint(
            'MedicationReminderService cancelAll skipped (web or not initialized)');
      }
      return;
    }
    await _notifications.cancelAll();
    if (kDebugMode) debugPrint('All medication reminders cancelled');
  }

  // Cancel a specific medication reminder by its ID
  Future<void> cancel(int id) async {
    if (kIsWeb || !_initialized) {
      if (kDebugMode) {
        debugPrint(
            'MedicationReminderService cancel skipped (web or not initialized)');
      }
      return;
    }
    await _notifications.cancel(id);
    if (kDebugMode) debugPrint('Cancelled reminder id: $id');
  }

  // Download the latest medications from the server and reschedule all reminders
  Future<void> refreshReminders(ApiClient apiClient) async {
    if (kIsWeb) {
      if (kDebugMode) {
        debugPrint('MedicationReminderService refresh skipped on web');
      }
      return;
    }

    if (!_initialized) {
      if (kDebugMode) {
        debugPrint(
            'MedicationReminderService refresh skipped (not initialized)');
      }
      return;
    }

    try {
      // Get the current list of medications from the server
      final medications = await apiClient.getMedicationReminders();
      // Clear all old reminders first to avoid duplicates
      await cancelAll();
      // Schedule fresh reminders for all enabled medications
      await scheduleReminders(medications);
      if (kDebugMode) {
        debugPrint(
            'Medication reminders refreshed: ${medications.length} medications');
      }
    } catch (e) {
      if (kDebugMode) debugPrint('Failed to refresh medication reminders: $e');
    }
  }
}
