/// Edge AI Store — Central state manager for all on-device AI features.
///
/// This is the single entry point the UI uses to interact with edge AI.
/// It orchestrates:
///   1. EdgeMLService (TFLite risk prediction)
///   2. EdgeAlertService (threshold alerts)
///   3. GpsLocationService (satellite positioning)
///   4. CloudSyncService (offline queue + sync)
///
/// USAGE FROM UI:
///   final edgeStore = Provider.of<EdgeAiStore>(context);
///   edgeStore.processVitals(heartRate: 155, spo2: 91);
///   // → Automatically runs risk prediction + threshold checks
///   // → Fires GPS emergency if critical
///   // → Queues everything for cloud sync
library;

import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import 'edge_ml_service.dart';
import 'edge_alert_service.dart';
import 'gps_location_service.dart';
import 'cloud_sync_service.dart';
import 'notification_service.dart';
import '../models/edge_prediction.dart';

// ============================================================================
// Edge AI Store
// ============================================================================

// The main brain of the on-device AI system — connects all the pieces together
class EdgeAiStore extends ChangeNotifier {
  // The machine learning model that predicts heart risk on the phone itself
  final EdgeMLService _mlService = EdgeMLService();
  // Checks if vital signs are outside safe limits (no AI needed, just math)
  final EdgeAlertService _alertService = EdgeAlertService();
  // Gets the user's GPS location for emergencies (works without internet)
  final GpsLocationService _gpsService = GpsLocationService();
  // Sends saved health data to the server when internet becomes available
  late final CloudSyncService _syncService;

  // ---- These values are shown on screen (the UI reads them) ----

  // Whether the AI system is set up and ready to make predictions
  bool isReady = false;

  // Whether the AI system is currently loading (show a spinner)
  bool isInitializing = false;

  // The most recent risk prediction from the AI model
  EdgeRiskPrediction? latestPrediction;

  // Any active health alerts (like "heart rate too high")
  List<ThresholdAlert> activeAlerts = [];

  // The most recent emergency alert with GPS location (if any)
  GpsEmergencyAlert? latestEmergency;

  // Error message to show the user (null means everything is fine)
  String? error;

  // Whether we're currently sending data to the server
  bool isSyncing = false;
  // How many health readings are waiting to be sent to the server
  int pendingSyncCount = 0;
  CloudSyncState syncState = CloudSyncState.idle;
  bool isConnectivityOnline = false;
  DateTime? lastConnectivityProbeAt;
  DateTime? lastSyncTime;
  String? lastSyncErrorType;
  String? lastSyncErrorMessage;
  DateTime? lastSyncErrorAt;
  String? lastQueueEventType;
  String? lastQueueEventMessage;
  DateTime? lastQueueEventAt;

  // Which version of the AI model is loaded
  String modelVersion = 'unknown';
  // Whether the AI model file was successfully loaded from the app's assets
  bool modelLoaded = false;
  // Safety flag to prevent updates after the screen is closed
  bool _isDisposed = false;
  // When we last showed a critical health notification (to avoid spamming)
  DateTime? _lastEdgeAlertNotificationAt;
  // Whether the PREVIOUS reading was critical (to detect new critical episodes)
  bool _wasCriticalPreviousCycle = false;

  // ---- Collect recent readings for better AI predictions ----
  // The AI model needs multiple readings to see trends (not just one number).
  // We keep the last 12 heart rate and SpO2 readings (~1 minute of data)
  // so the model can see patterns like "heart rate is rising" or "SpO2 is dropping".
  final List<int> _hrWindow = [];
  final List<int> _spo2Window = [];
  // Keep up to 12 readings in the window
  static const int _windowSize = 12;
  // When the current reading window started
  DateTime? _windowStart;

  // ---- Constructor ----

  // Set up the AI store with a connection to the server for syncing data
  EdgeAiStore(Dio dio) {
    // Create the cloud sync service with our server connection
    _syncService = CloudSyncService(dio);
    // Listen for sync status changes and update our own status to match
    _syncService.setStateListener(() {
      // Don't update if the screen was already closed
      if (_isDisposed) return;
      isSyncing = _syncService.isSyncing;
      pendingSyncCount = _syncService.pendingCount;
      syncState = _syncService.syncState;
      isConnectivityOnline = _syncService.isConnectivityOnline;
      lastConnectivityProbeAt = _syncService.lastConnectivityProbeAt;
      lastSyncTime = _syncService.lastSyncTime;
      lastSyncErrorType = _syncService.lastSyncErrorType;
      lastSyncErrorMessage = _syncService.lastSyncErrorMessage;
      lastSyncErrorAt = _syncService.lastSyncErrorAt;
      lastQueueEventType = _syncService.lastQueueEventType;
      lastQueueEventMessage = _syncService.lastQueueEventMessage;
      lastQueueEventAt = _syncService.lastQueueEventAt;
      notifyListeners();
    });
  }

  // ---- Initialization ----

  /// Initialize all edge AI services.
  /// Call once at app startup, after login.
  Future<void> initialize() async {
    if (isReady || isInitializing) return;

    isInitializing = true;
    error = null;
    notifyListeners();

    try {
      // Load ML model from assets
      await _mlService.initialize();
      modelLoaded = _mlService.isReady;
      modelVersion = _mlService.modelVersion;

      // Load pending emergencies from local storage
      await _alertService.loadPendingEmergencies();

      // Request GPS permission (user sees permission dialog)
      await _gpsService.requestPermission();

      // Initialize cloud sync (loads queue, starts timer)
      await _syncService.initialize();
      pendingSyncCount = _syncService.pendingCount;
      isSyncing = _syncService.isSyncing;
      syncState = _syncService.syncState;
      isConnectivityOnline = _syncService.isConnectivityOnline;
      lastConnectivityProbeAt = _syncService.lastConnectivityProbeAt;
      lastSyncTime = _syncService.lastSyncTime;
      lastSyncErrorType = _syncService.lastSyncErrorType;
      lastSyncErrorMessage = _syncService.lastSyncErrorMessage;
      lastSyncErrorAt = _syncService.lastSyncErrorAt;
      lastQueueEventType = _syncService.lastQueueEventType;
      lastQueueEventMessage = _syncService.lastQueueEventMessage;
      lastQueueEventAt = _syncService.lastQueueEventAt;

      isReady = true;

      // Try an immediate sync if we have pending data
      if (pendingSyncCount > 0) {
        _trySyncInBackground();
      }
    } catch (e) {
      error = 'Edge AI initialization failed: $e';
      isReady = false;
    } finally {
      isInitializing = false;
      notifyListeners();
    }
  }

  // ---- Core: Process Vitals ----

  /// Process a vital signs reading through edge AI.
  /// This is the main function the UI calls whenever new vitals arrive.
  ///
  /// It runs:
  ///   1. Threshold checks (instant, no ML)
  ///   2. TFLite risk prediction (if model loaded, ~10ms)
  ///   3. GPS emergency capture (if critical alert)
  ///   4. Queue everything for cloud sync
  Future<void> processVitals({
    required int heartRate,
    int? spo2,
    int? bpSystolic,
    int? bpDiastolic,
    // Optional: for full risk prediction (if available from profile)
    int? age,
    int? baselineHr,
    int? maxSafeHr,
    int? durationMinutes,
    int? recoveryTimeMinutes,
    String? activityType,
  }) async {
    error = null;

    // Step 1: Threshold alerts (pure math, always works)
    activeAlerts = _alertService.checkVitals(
      heartRate: heartRate,
      spo2: spo2,
      bpSystolic: bpSystolic,
    );

    // Step 2: Add this reading to our recent history window, then run the AI model
    // The AI needs multiple readings to see trends — one reading alone isn't enough
    _hrWindow.add(heartRate);
    if (spo2 != null) _spo2Window.add(spo2);
    // If we have more than 12 readings, remove the oldest one
    if (_hrWindow.length > _windowSize) _hrWindow.removeAt(0);
    if (_spo2Window.length > _windowSize) _spo2Window.removeAt(0);
    // Remember when the current window started
    _windowStart ??= DateTime.now();

    // Only run the AI model if it's loaded and we have enough data
    if (_mlService.isReady &&
        age != null &&
        baselineHr != null &&
        maxSafeHr != null &&
        _hrWindow.length >= 3) {
      // Calculate average, highest, and lowest heart rate from recent readings
      final avgHr = (_hrWindow.reduce((a, b) => a + b) / _hrWindow.length).round();
      final peakHr = _hrWindow.reduce(max);
      final minHr = _hrWindow.reduce(min);
      // Average blood oxygen level, or use current reading, or default to 97% (normal)
      final avgSpo2 = _spo2Window.isNotEmpty
          ? (_spo2Window.reduce((a, b) => a + b) / _spo2Window.length).round()
          : (spo2 ?? 97);
      // How many minutes have passed since we started collecting readings
      final elapsedMin = DateTime.now().difference(_windowStart!).inSeconds / 60.0;
      // Clamp duration between 1 and 30 minutes for the AI model
      final durationMin = max(1, min(elapsedMin.round(), durationMinutes ?? 30));

      latestPrediction = _mlService.predictRisk(
        age: age,
        baselineHr: baselineHr,
        maxSafeHr: maxSafeHr,
        avgHeartRate: avgHr,
        peakHeartRate: peakHr,
        minHeartRate: minHr,
        avgSpo2: avgSpo2,
        durationMinutes: durationMin,
        recoveryTimeMinutes: recoveryTimeMinutes ?? 5,
        activityType: activityType ?? 'walking',
      );
    }

    // Notify UI immediately — score and alerts are ready now (~10ms from start).
    // GPS capture and cloud sync happen below in the background and do NOT
    // block the UI from showing the updated risk score.
    notifyListeners();

    // Step 3: If something is critically wrong, capture the user's GPS location for emergency
    final isCritical = activeAlerts.any((a) => a.severity == 'critical') ||
        (latestPrediction != null && latestPrediction!.riskScore >= 0.80);

    _maybeNotifyCriticalDetection(isCritical);

    if (isCritical) {
      await _captureGpsEmergency(
        heartRate: heartRate,
        spo2: spo2,
        bpSystolic: bpSystolic,
      );
    }

    // Step 4: Queue prediction for 15-min background sync to backend.
    // This is a background copy for the doctor dashboard — it does NOT
    // affect the real-time score already shown to the patient above.
    final vitalsData = {
      'heart_rate': heartRate,
      if (spo2 != null) 'spo2': spo2,
      if (bpSystolic != null) 'bp_systolic': bpSystolic,
      if (bpDiastolic != null) 'bp_diastolic': bpDiastolic,
      'timestamp': DateTime.now().toIso8601String(),
    };

    await _syncService.queuePrediction(
      prediction: latestPrediction,
      vitals: vitalsData,
      alerts: activeAlerts.map((a) => a.toJson()).toList(),
      gpsData: latestEmergency?.toJson(),
    );
    pendingSyncCount = _syncService.pendingCount;
    notifyListeners(); // update sync count badge only
  }

  // ---- Manual Sync ----

  /// Manually trigger a cloud sync (e.g., user pulls to refresh)
  Future<bool> syncNow() async {
    isSyncing = true;
    notifyListeners();

    final success = await _syncService.trySync();

    isSyncing = _syncService.isSyncing;
    pendingSyncCount = _syncService.pendingCount;
    syncState = _syncService.syncState;
    isConnectivityOnline = _syncService.isConnectivityOnline;
    lastConnectivityProbeAt = _syncService.lastConnectivityProbeAt;
    lastSyncTime = _syncService.lastSyncTime;
    lastSyncErrorType = _syncService.lastSyncErrorType;
    lastSyncErrorMessage = _syncService.lastSyncErrorMessage;
    lastSyncErrorAt = _syncService.lastSyncErrorAt;
    lastQueueEventType = _syncService.lastQueueEventType;
    lastQueueEventMessage = _syncService.lastQueueEventMessage;
    lastQueueEventAt = _syncService.lastQueueEventAt;
    notifyListeners();

    return success;
  }

  // ---- Model Update Check ----

  /// Check if a new ML model is available on the server
  Future<bool> checkForModelUpdate() async {
    final update = await _syncService.checkModelUpdate(modelVersion);
    if (update != null) {
      // New model available — for now, just log it.
      // Full OTA model download is a Phase 2 feature.
      return true;
    }
    return false;
  }

  // ---- Cleanup ----

  @override
  void dispose() {
    _isDisposed = true;
    _syncService.dispose();
    super.dispose();
  }

  // ---- Private Helpers ----

  /// Capture GPS coordinates for a critical emergency
  Future<void> _captureGpsEmergency({
    required int heartRate,
    int? spo2,
    int? bpSystolic,
  }) async {
    try {
      final position = await _gpsService.getEmergencyPosition();
      if (position != null) {
        latestEmergency = await _alertService.createGpsEmergency(
          latitude: position.latitude,
          longitude: position.longitude,
          altitude: position.altitude,
          accuracy: position.accuracy,
          riskLevel: latestPrediction?.riskLevel ?? 'critical',
          riskScore: latestPrediction?.riskScore ?? 1.0,
          vitals: {
            'heart_rate': heartRate,
            if (spo2 != null) 'spo2': spo2,
            if (bpSystolic != null) 'bp_systolic': bpSystolic,
          },
        );

        // Priority sync for emergency
        await _syncService.queueGpsEmergency(latestEmergency!.toJson());
      }
    } catch (_) {
      // GPS unavailable — still show the alert, just without location
    }
  }

  /// Background sync attempt (non-blocking)
  void _trySyncInBackground() {
    Future.microtask(() async {
      await _syncService.trySync();
      pendingSyncCount = _syncService.pendingCount;
      syncState = _syncService.syncState;
      isConnectivityOnline = _syncService.isConnectivityOnline;
      lastConnectivityProbeAt = _syncService.lastConnectivityProbeAt;
      lastSyncTime = _syncService.lastSyncTime;
      lastSyncErrorType = _syncService.lastSyncErrorType;
      lastSyncErrorMessage = _syncService.lastSyncErrorMessage;
      lastSyncErrorAt = _syncService.lastSyncErrorAt;
      lastQueueEventType = _syncService.lastQueueEventType;
      lastQueueEventMessage = _syncService.lastQueueEventMessage;
      lastQueueEventAt = _syncService.lastQueueEventAt;
      notifyListeners();
    });
  }

  // Show a push notification if a NEW critical episode starts (but don't spam every 5 seconds)
  void _maybeNotifyCriticalDetection(bool isCritical) {
    final now = DateTime.now();
    // Only notify if this is a NEW critical episode (wasn't critical before)
    final isNewCriticalCycle = isCritical && !_wasCriticalPreviousCycle;
    final lastNotified = _lastEdgeAlertNotificationAt;
    // Don't send another notification if we sent one less than 5 minutes ago
    final outsideDebounce =
        lastNotified == null || now.difference(lastNotified) >= const Duration(minutes: 5);

    // Only show notification if it's a new critical episode AND we haven't notified recently
    if (isNewCriticalCycle && outsideDebounce) {
      NotificationService.instance.showAlert(
        title: 'Health Alert',
        body: 'Abnormal vitals detected — please check your readings',
        payload: 'edge_ai_critical',
      );
      _lastEdgeAlertNotificationAt = now;
    }

    _wasCriticalPreviousCycle = isCritical;
  }
}
