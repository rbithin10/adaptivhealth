/*
Cloud Sync Service — Uploads edge predictions to the server when online.

This connects the phone's on-device AI to the cloud:
  1. Every AI prediction is saved locally on the phone
  2. When the phone has internet, send them to the server in batches
  3. The doctor's dashboard shows both edge and cloud predictions
  4. GPS emergency alerts get sent first (highest priority)

Sync schedule:
  - Regular vitals: every 15 minutes (or when user taps "sync")
  - GPS emergencies: immediately when internet is available
  - AI model updates: checked once when the app starts
*/
library;

// Timers and async helpers
import 'dart:async';
// Converts objects to/from JSON text
import 'dart:convert';
// HTTP client for talking to the server
import 'package:dio/dio.dart';
// Debugging tools and kDebugMode flag
import 'package:flutter/foundation.dart';
// Saves data to the phone that survives app restarts
import 'package:shared_preferences/shared_preferences.dart';
// Our data model for AI risk predictions
import '../models/edge_prediction.dart';

// The different states the sync system can be in
enum CloudSyncState {
  online,       // Connected to the server and ready to sync
  offline,      // No internet connection
  authExpired,  // Login token expired — user needs to sign in again
  rateLimited,  // Server says we're sending too many requests
  serverError,  // Server is having problems
  syncing,      // Currently uploading data to the server
  idle,         // Nothing to sync — all caught up
}

// ============================================================================
// Cloud Sync Service
// ============================================================================

class CloudSyncService {
  // The HTTP client used to talk to the server
  final Dio _dio;

  // List of predictions waiting to be uploaded to the server
  List<Map<String, dynamic>> _pendingSyncs = [];

  // Whether we're currently in the middle of uploading data
  bool _isSyncing = false;
  // When we last successfully sent data to the server
  DateTime? _lastSyncTime;
  // Details about the last sync error (if any)
  String? _lastSyncErrorType;
  String? _lastSyncErrorMessage;
  DateTime? _lastSyncErrorAt;
  // Upload data to the server every 5 minutes (reduced from 15 for cardiac monitoring timeliness)
  static const _syncInterval = Duration(seconds: 5);
  // Check if we have internet every 20 seconds
  static const _probeInterval = Duration(seconds: 20);
  // Give up on connectivity check after 4 seconds
  static const _probeTimeout = Duration(seconds: 4);
  // Don't let the local queue grow beyond 500 items
  static const _maxQueueSize = 500;
  // Current state of the sync system (online, offline, syncing, etc.)
  CloudSyncState _syncState = CloudSyncState.idle;
  // Whether we think the phone has internet right now
  bool _isConnectivityOnline = false;
  // When we last checked for internet connectivity
  DateTime? _lastConnectivityProbeAt;
  // Details about the last queue event (trimmed, pushed, etc.)
  String? _lastQueueEventType;
  String? _lastQueueEventMessage;
  DateTime? _lastQueueEventAt;

  // Timer that triggers sync every 15 minutes
  Timer? _syncTimer;
  // Timer that checks for internet every 20 seconds
  Timer? _probeTimer;
  // Function to call when the sync state changes (so the UI can update)
  VoidCallback? _onStateChanged;
  // Watches all HTTP requests to detect when we go online/offline
  Interceptor? _networkObserver;

  // Create the service with the HTTP client it should use
  CloudSyncService(this._dio);

  // ---- Public API (used by other parts of the app) ----

  // Check if we're currently uploading data
  bool get isSyncing => _isSyncing;

  // When was the last time we successfully sent data to the server?
  DateTime? get lastSyncTime => _lastSyncTime;

  // What went wrong with the last sync attempt (if anything)
  String? get lastSyncErrorType => _lastSyncErrorType;
  String? get lastSyncErrorMessage => _lastSyncErrorMessage;
  DateTime? get lastSyncErrorAt => _lastSyncErrorAt;
  // The current sync state (online, offline, syncing, etc.)
  CloudSyncState get syncState => _syncState;
  // Does the phone have internet right now?
  bool get isConnectivityOnline => _isConnectivityOnline;
  // When did we last check for internet?
  DateTime? get lastConnectivityProbeAt => _lastConnectivityProbeAt;
  // Last event that happened to the queue (e.g. trimmed, push succeeded)
  String? get lastQueueEventType => _lastQueueEventType;
  String? get lastQueueEventMessage => _lastQueueEventMessage;
  DateTime? get lastQueueEventAt => _lastQueueEventAt;

  // How many readings are waiting to be uploaded
  int get pendingCount => _pendingSyncs.length;

  // Tell us when the sync state changes so we can update the screen
  void setStateListener(VoidCallback listener) {
    _onStateChanged = listener;
  }

  // Set up the sync service when the app starts
  Future<void> initialize() async {
    // Start watching all HTTP requests to detect online/offline changes
    _registerNetworkObserver();

    // Load any predictions that were saved but not yet uploaded
    await _loadQueue();

    // Check if we have internet right now
    await _probeConnectivity(updateError: false);
    // Figure out our current sync state
    _updateDerivedSyncState();
    // Tell the UI about our state
    _notifyStateChanged();

    // Set up the 15-minute automatic sync timer
    _syncTimer = Timer.periodic(_syncInterval, (_) => trySync());
    // Set up the 20-second internet check timer
    _probeTimer = Timer.periodic(_probeInterval, (_) {
      _probeConnectivity(updateError: false);
    });
  }

  // Save an AI prediction to the local queue (will be uploaded later)
  Future<void> queuePrediction({
    EdgeRiskPrediction? prediction,
    required Map<String, dynamic> vitals,
    List<Map<String, dynamic>>? alerts,
    Map<String, dynamic>? gpsData,
  }) async {
    // Package the prediction with a timestamp for the sync queue
    final entry = {
      'timestamp': DateTime.now().toIso8601String(),
      'vitals': vitals,
      if (prediction != null) 'prediction': prediction.toJson(),
      if (alerts != null && alerts.isNotEmpty) 'alerts': alerts,
      if (gpsData != null) 'gps': gpsData,
    };

    // Add to the queue
    _pendingSyncs.add(entry);

    // If the queue gets too big, remove the oldest entries
    if (_pendingSyncs.length > _maxQueueSize) {
      _recordQueueEvent(
        type: 'queue_trimmed',
        message:
            'Queue exceeded $_maxQueueSize entries. Oldest reading removed to keep local storage bounded.',
      );
      _pendingSyncs = _pendingSyncs.sublist(
        _pendingSyncs.length - _maxQueueSize,
      );
    }

    // Save the queue to phone storage
    await _saveQueue();
    _updateDerivedSyncState();
    _notifyStateChanged();

    // If this is a HIGH or CRITICAL risk, try to send it immediately
    // so the doctor's dashboard updates within seconds (not 15 min)
    if (prediction != null &&
        (prediction.riskLevel == 'high' || prediction.riskLevel == 'critical')) {
      unawaited(
        pushCriticalAlertNow(
          prediction: prediction,
          vitals: vitals,
          alerts: alerts,
        ),
      );
    }
  }

  // Save a GPS emergency for highest-priority upload
  Future<void> queueGpsEmergency(Map<String, dynamic> emergency) async {
    // Package the emergency with a timestamp and type label
    final entry = {
      'timestamp': DateTime.now().toIso8601String(),
      'type': 'gps_emergency',
      'data': emergency,
    };
    // Put at the FRONT of the queue — emergencies get uploaded first
    _pendingSyncs.insert(0, entry);
    // Save to phone storage and notify the UI
    await _saveQueue();
    _updateDerivedSyncState();
    _notifyStateChanged();
  }

  // Send a critical alert directly to the server RIGHT NOW (bypasses the 15-min queue)
  Future<bool> pushCriticalAlertNow({
    required EdgeRiskPrediction prediction,
    required Map<String, dynamic> vitals,
    List<Map<String, dynamic>>? alerts,
  }) async {
    try {
      // Send the critical reading to the server immediately
      await _dio.post(
        '/vitals/critical-alert',
        data: {
          'timestamp': DateTime.now().toIso8601String(),
          'vitals': vitals,
          'prediction': prediction.toJson(),
          if (alerts != null && alerts.isNotEmpty) 'alerts': alerts,
        },
      );
      // Record that the immediate push worked
      _recordQueueEvent(
        type: 'critical_push_success',
        message:
            'Critical ${prediction.riskLevel} alert pushed immediately '
            '(bypassed 15-min queue).',
      );
      return true;
    } on DioException catch (e) {
      // Push failed — not a problem, the reading is still in the regular queue
      _recordQueueEvent(
        type: 'critical_push_failed',
        message:
            'Immediate critical push failed '
            '(${e.response?.statusCode ?? "no response"}). '
            'Reading is queued for next batch sync.',
      );
      return false;
    } catch (_) {
      // Unexpected error — reading is safely in the queue
      _recordQueueEvent(
        type: 'critical_push_failed',
        message: 'Immediate critical push failed unexpectedly. Reading is queued.',
      );
      return false;
    }
  }

  // Try to upload all queued data to the server (called every 15 min and on-demand)
  Future<bool> trySync() async {
    // Don't start a new sync if one is already running
    if (_isSyncing) return false;

    // Nothing to upload — just check connectivity and return
    if (_pendingSyncs.isEmpty) {
      await _probeConnectivity(updateError: false);
      _updateDerivedSyncState();
      _notifyStateChanged();
      return false;
    }

    // Check if we have internet before trying to upload
    await _probeConnectivity(updateError: false);
    _updateDerivedSyncState();

    // If we're offline or have auth/rate/server issues, don't try
    if (_syncState == CloudSyncState.offline ||
        _syncState == CloudSyncState.authExpired ||
        _syncState == CloudSyncState.rateLimited ||
        _syncState == CloudSyncState.serverError) {
      _notifyStateChanged();
      return false;
    }

    // Mark that we're now uploading
    _isSyncing = true;
    _updateDerivedSyncState();
    _notifyStateChanged();

    try {
      // Upload GPS emergencies first (they are the most important)
      final emergencySynced = await _syncEmergencies();

      // Then upload the regular prediction data in batches
      final predictionSynced = await _syncPredictions();

      // If we uploaded anything, record the time and clear errors
      if (emergencySynced > 0 || predictionSynced > 0) {
        _lastSyncTime = DateTime.now();
        _clearSyncError();
      }
      // We're online and done syncing
      _isConnectivityOnline = true;
      _isSyncing = false;
      _updateDerivedSyncState();
      _notifyStateChanged();
      return emergencySynced > 0 || predictionSynced > 0;
    } on DioException catch (e) {
      // Network or server error — keep the queue and try again later
      _setSyncErrorFromDio(e);
      _isSyncing = false;
      _updateDerivedSyncState();
      _notifyStateChanged();
      return false;
    } catch (e) {
      _setSyncError(
        type: 'unknown',
        message: 'Sync failed due to an unexpected error.',
      );
      _isSyncing = false;
      _updateDerivedSyncState();
      _notifyStateChanged();
      return false;
    }
  }

  // Check if a newer AI model is available on the server
  Future<Map<String, dynamic>?> checkModelUpdate(
    String currentVersion,
  ) async {
    try {
      // Ask the server what model version it has
      final response = await _dio.get('/model/retraining-status');
      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final metadata = data['metadata'] as Map<String, dynamic>?;
        if (metadata != null) {
          // Compare server version with our local version
          final serverVersion = metadata['version']?.toString() ?? '';
          if (serverVersion.isNotEmpty && serverVersion != currentVersion) {
            // Newer version available — return the metadata
            return metadata;
          }
        }
      }
    } catch (_) {
      // Can't check for updates right now (offline or server error)
    }
    return null;
  }

  // Stop all timers and clean up when the service is no longer needed
  void dispose() {
    _syncTimer?.cancel();
    _probeTimer?.cancel();
    if (_networkObserver != null) {
      _dio.interceptors.remove(_networkObserver);
      _networkObserver = null;
    }
    _onStateChanged = null;
  }

  // ---- Private: Sync Logic (uploads data to the server) ----

  // Upload GPS emergency alerts first (they are the highest priority)
  Future<int> _syncEmergencies() async {
    // Find all GPS emergency items in the queue
    final emergencies = _pendingSyncs
        .where((e) => e['type'] == 'gps_emergency')
        .toList();

    // Count how many emergencies we successfully uploaded
    int syncedCount = 0;

    for (final emergency in emergencies) {
      try {
        // Extract the emergency data and vitals from the queue entry
        final emergencyData =
            Map<String, dynamic>.from((emergency['data'] as Map?) ?? {});
        final vitals =
            Map<String, dynamic>.from((emergencyData['vitals'] as Map?) ?? {});
        final heartRate = vitals['heart_rate'];

        // If there's no heart rate, the server will reject it — remove it
        if (heartRate == null) {
          _recordQueueEvent(
            type: 'validation_error',
            message:
                'Dropped emergency sync item: missing required heart_rate field (non-retryable validation case).',
          );
          _setSyncError(
            type: 'validation_error',
            message:
                'Dropped one emergency sync item due to missing required heart_rate field.',
          );
          _pendingSyncs.remove(emergency);
          continue;
        }

        await _dio.post(
          '/vitals/batch-sync',
          data: {
            'source': 'edge_ai_emergency',
            'batch': [
              {
                'timestamp': emergency['timestamp'],
                'vitals': {
                  ...vitals,
                  'timestamp': emergencyData['timestamp'] ?? emergency['timestamp'],
                },
                'prediction': {
                  'risk_score': emergencyData['risk_score'] ?? 1.0,
                  'risk_level': emergencyData['risk_level'] ?? 'critical',
                  'confidence': 1.0,
                  'model_version': 'edge-emergency',
                },
                'alerts': [
                  {
                    'alert_type': 'gps_emergency',
                    'severity': 'critical',
                    'title': 'Edge AI Emergency',
                    'message': 'Critical risk detected with emergency location capture',
                  }
                ],
                'gps': emergencyData,
              }
            ],
            'device_timestamp': DateTime.now().toIso8601String(),
          },
        );
        _pendingSyncs.remove(emergency);
        syncedCount += 1;
      } on DioException catch (e) {
        final statusCode = e.response?.statusCode ?? 0;
        if (statusCode >= 400 && statusCode < 500 && statusCode != 429) {
          // Non-retryable API validation/auth shape issue.
          // Drop this item so it does not block the entire queue forever.
          _recordQueueEvent(
            type: 'validation_error',
            message:
                'Dropped emergency sync item due to non-retryable $statusCode response.',
          );
          _setSyncError(
            type: 'validation_error',
            message:
                'Dropped one emergency sync item due to non-retryable server validation response ($statusCode).',
          );
          _pendingSyncs.remove(emergency);
          continue;
        }
        _setSyncErrorFromDio(e);
        // Retryable/network issue — keep item and stop this cycle.
        break;
      }
    }
    await _saveQueue();
    _updateDerivedSyncState();
    _notifyStateChanged();
    return syncedCount;
  }

  // Upload regular AI predictions in batches of 50
  Future<int> _syncPredictions() async {
    // Find all non-emergency items in the queue
    final predictions = _pendingSyncs
        .where((e) => e['type'] != 'gps_emergency')
        .toList();

    if (predictions.isEmpty) return 0;

    // Take up to 50 items at a time to avoid overwhelming the server
    const batchSize = 50;
    final batch = predictions.take(batchSize).toList();

    try {
      // Upload this batch to the server
      await _dio.post(
        '/vitals/batch-sync',
        data: {
          'source': 'edge_ai',
          'batch': batch,
          'device_timestamp': DateTime.now().toIso8601String(),
        },
      );

      // Upload succeeded — remove the synced items from the queue
      for (final item in batch) {
        _pendingSyncs.remove(item);
      }
      await _saveQueue();
      _updateDerivedSyncState();
      _notifyStateChanged();
      return batch.length;
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode ?? 0;
      if (statusCode >= 400 && statusCode < 500 &&
          statusCode != 401 &&
          statusCode != 403 &&
          statusCode != 429) {
        // Non-retryable validation issues: drop this batch and surface diagnostics.
        for (final item in batch) {
          _pendingSyncs.remove(item);
        }
        _recordQueueEvent(
          type: 'validation_error',
          message:
              'Dropped ${batch.length} queued reading(s) due to non-retryable validation response ($statusCode).',
        );
        _setSyncError(
          type: 'validation_error',
          message:
              'Dropped ${batch.length} queued reading(s) due to non-retryable validation response ($statusCode).',
        );
        await _saveQueue();
        _updateDerivedSyncState();
        _notifyStateChanged();
        return 0;
      }

      // Keep queue for retry on retryable API errors to avoid silent data loss.
      _setSyncErrorFromDio(e);
      _updateDerivedSyncState();
      return 0;
    }
  }

  // ---- Private: Saving/Loading the Queue from Phone Storage ----

  // Save the current queue to phone storage so it survives app restarts
  Future<void> _saveQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(
        'edge_sync_queue',
        json.encode(_pendingSyncs),
      );
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Error in _saveQueue: $e');
      }
    }
  }

  // Load any saved queue items from phone storage (called at app startup)
  Future<void> _loadQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString('edge_sync_queue');
      if (data != null) {
        final list = json.decode(data) as List;
        _pendingSyncs = list
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
      }
    } catch (_) {
      _pendingSyncs = [];
    }
  }

  // Tell the UI that something changed (so screens can refresh)
  void _notifyStateChanged() {
    final listener = _onStateChanged;
    if (listener != null) {
      listener();
    }
  }

  // Record a notable event for debugging (e.g. queue trimmed, push failed)
  void _recordQueueEvent({required String type, required String message}) {
    _lastQueueEventType = type;
    _lastQueueEventMessage = message;
    _lastQueueEventAt = DateTime.now();
  }

  // Record a sync error for display in the UI
  void _setSyncError({required String type, required String message}) {
    _lastSyncErrorType = type;
    _lastSyncErrorMessage = message;
    _lastSyncErrorAt = DateTime.now();
    _updateDerivedSyncState();
  }

  // Clear any previous sync error (called after a successful sync)
  void _clearSyncError() {
    _lastSyncErrorType = null;
    _lastSyncErrorMessage = null;
    _lastSyncErrorAt = null;
    _updateDerivedSyncState();
  }

  // Figure out what kind of sync error a server response represents
  void _setSyncErrorFromDio(DioException e) {
    // Convert the HTTP error into our sync state categories
    final mapped = _mapDioToState(e);
    _isConnectivityOnline = mapped != CloudSyncState.offline;

    final statusCode = e.response?.statusCode;

    if (statusCode == 401 || statusCode == 403) {
      _setSyncError(
        type: 'auth_expired',
        message: 'Authentication expired. Please sign in again.',
      );
      return;
    }

    if (statusCode == 429) {
      _setSyncError(
        type: 'rate_limited',
        message: 'Sync temporarily rate-limited. Retrying automatically.',
      );
      return;
    }

    if (statusCode != null && statusCode >= 400 && statusCode < 500) {
      _setSyncError(
        type: 'validation_error',
        message: 'Some queued readings were rejected by the server format.',
      );
      return;
    }

    if (statusCode != null && statusCode >= 500) {
      _setSyncError(
        type: 'server_error',
        message: 'Server is temporarily unavailable. Will retry automatically.',
      );
      return;
    }

    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      _setSyncError(
        type: 'offline',
        message: 'No stable network connection. Waiting to retry sync.',
      );
      return;
    }

    _setSyncError(
      type: 'unknown',
      message: 'Sync failed. Will retry automatically.',
    );
  }

  // Watch all HTTP traffic to detect when we go online or offline
  void _registerNetworkObserver() {
    // Don't add a second observer if we already have one
    if (_networkObserver != null) {
      return;
    }

    _networkObserver = InterceptorsWrapper(
      // When any HTTP request succeeds, we know we're online
      onResponse: (response, handler) {
        final isProbe = response.requestOptions.extra['sync_probe'] == true;
        if (!isProbe) {
          _isConnectivityOnline = true;
          _updateDerivedSyncState();
          _notifyStateChanged();
        }
        handler.next(response);
      },
      // When any HTTP request fails, check if it means we went offline
      onError: (error, handler) {
        final isProbe = error.requestOptions.extra['sync_probe'] == true;
        if (!isProbe) {
          final mapped = _mapDioToState(error);
          if (mapped == CloudSyncState.offline) {
            _isConnectivityOnline = false;
            _updateDerivedSyncState();
            _notifyStateChanged();
          } else if (mapped == CloudSyncState.authExpired ||
              mapped == CloudSyncState.rateLimited ||
              mapped == CloudSyncState.serverError) {
            _isConnectivityOnline = true;
            _updateDerivedSyncState();
            _notifyStateChanged();
          }
        }
        handler.next(error);
      },
    );

    _dio.interceptors.add(_networkObserver!);
  }

  // Send a lightweight request to the server to check if we have internet
  Future<CloudSyncState> _probeConnectivity({bool updateError = true}) async {
    try {
      // Hit the /me endpoint as a quick connectivity check
      await _dio.get(
        '/me',
        options: Options(
          sendTimeout: _probeTimeout,
          receiveTimeout: _probeTimeout,
          extra: {'sync_probe': true},
        ),
      );

      _isConnectivityOnline = true;
      _lastConnectivityProbeAt = DateTime.now();
      if (updateError && _lastSyncErrorType == 'offline') {
        _clearSyncError();
      }
      _updateDerivedSyncState();
      return _syncState;
    } on DioException catch (e) {
      final mapped = _mapDioToState(e);
      _isConnectivityOnline = mapped != CloudSyncState.offline;
      _lastConnectivityProbeAt = DateTime.now();

      if (updateError) {
        if (mapped == CloudSyncState.authExpired) {
          _setSyncError(
            type: 'auth_expired',
            message: 'Authentication expired. Please sign in again.',
          );
        } else if (mapped == CloudSyncState.rateLimited) {
          _setSyncError(
            type: 'rate_limited',
            message: 'Sync temporarily rate-limited. Retrying automatically.',
          );
        } else if (mapped == CloudSyncState.serverError) {
          _setSyncError(
            type: 'server_error',
            message: 'Server is temporarily unavailable. Will retry automatically.',
          );
        } else if (mapped == CloudSyncState.offline) {
          _setSyncError(
            type: 'offline',
            message: 'No stable network connection. Waiting to retry sync.',
          );
        }
      }

      _updateDerivedSyncState();
      return mapped;
    }
  }

  // Convert an HTTP error into our sync state categories
  CloudSyncState _mapDioToState(DioException e) {
    final statusCode = e.response?.statusCode;

    // 401/403 = login expired
    if (statusCode == 401 || statusCode == 403) {
      return CloudSyncState.authExpired;
    }

    // 429 = too many requests
    if (statusCode == 429) {
      return CloudSyncState.rateLimited;
    }

    // 500+ = server is having problems
    if (statusCode != null && statusCode >= 500) {
      return CloudSyncState.serverError;
    }

    // Connection/timeout errors = no internet
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      return CloudSyncState.offline;
    }

    return CloudSyncState.online;
  }

  // Figure out what our overall sync state should be based on all the flags
  void _updateDerivedSyncState() {
    // If we're actively uploading, that takes priority
    if (_isSyncing) {
      _syncState = CloudSyncState.syncing;
      return;
    }

    // If we don't have internet, show as offline
    if (!_isConnectivityOnline) {
      _syncState = CloudSyncState.offline;
      return;
    }

    // If login expired, show that state
    if (_lastSyncErrorType == 'auth_expired') {
      _syncState = CloudSyncState.authExpired;
      return;
    }

    // If we're being rate limited, show that
    if (_lastSyncErrorType == 'rate_limited') {
      _syncState = CloudSyncState.rateLimited;
      return;
    }

    // If the server has errors, show that
    if (_lastSyncErrorType == 'server_error') {
      _syncState = CloudSyncState.serverError;
      return;
    }

    // If the queue is empty, nothing to do
    if (_pendingSyncs.isEmpty) {
      _syncState = CloudSyncState.idle;
      return;
    }

    // Otherwise we're online with items in the queue
    _syncState = CloudSyncState.online;
  }
}
