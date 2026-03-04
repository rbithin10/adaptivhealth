/// Cloud Sync Service — Queue edge predictions offline, sync when connected.
///
/// This service bridges edge AI and cloud AI:
///   1. Every edge prediction is queued locally
///   2. When connectivity is detected, batch-sync to cloud
///   3. Cloud validates edge vs cloud predictions (doctor sees both)
///   4. GPS emergency alerts are prioritized in sync order
///
/// SYNC STRATEGY:
///   - Vitals + edge predictions: every 15 minutes (or on manual sync)
///   - GPS emergencies: immediately when connectivity returns
///   - Model version check: once per app launch + weekly background

import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/edge_prediction.dart';

enum CloudSyncState {
  online,
  offline,
  authExpired,
  rateLimited,
  serverError,
  syncing,
  idle,
}

// ============================================================================
// Cloud Sync Service
// ============================================================================

class CloudSyncService {
  final Dio _dio;

  // Queue of edge predictions waiting to sync
  List<Map<String, dynamic>> _pendingSyncs = [];

  // Sync state
  bool _isSyncing = false;
  DateTime? _lastSyncTime;
  String? _lastSyncErrorType;
  String? _lastSyncErrorMessage;
  DateTime? _lastSyncErrorAt;
  static const _syncInterval = Duration(minutes: 15);
  static const _probeInterval = Duration(seconds: 20);
  static const _probeTimeout = Duration(seconds: 4);
  static const _maxQueueSize = 500; // Cap local storage
  CloudSyncState _syncState = CloudSyncState.idle;
  bool _isConnectivityOnline = false;
  DateTime? _lastConnectivityProbeAt;
  String? _lastQueueEventType;
  String? _lastQueueEventMessage;
  DateTime? _lastQueueEventAt;

  // Periodic sync timer
  Timer? _syncTimer;
  Timer? _probeTimer;
  VoidCallback? _onStateChanged;
  Interceptor? _networkObserver;

  CloudSyncService(this._dio);

  // ---- Public API ----

  // Whether a sync is in progress
  bool get isSyncing => _isSyncing;

  // Last successful sync time
  DateTime? get lastSyncTime => _lastSyncTime;

  // Last sync failure details (if any)
  String? get lastSyncErrorType => _lastSyncErrorType;
  String? get lastSyncErrorMessage => _lastSyncErrorMessage;
  DateTime? get lastSyncErrorAt => _lastSyncErrorAt;
  CloudSyncState get syncState => _syncState;
  bool get isConnectivityOnline => _isConnectivityOnline;
  DateTime? get lastConnectivityProbeAt => _lastConnectivityProbeAt;
  String? get lastQueueEventType => _lastQueueEventType;
  String? get lastQueueEventMessage => _lastQueueEventMessage;
  DateTime? get lastQueueEventAt => _lastQueueEventAt;

  // Number of predictions waiting to sync
  int get pendingCount => _pendingSyncs.length;

  /// Register a listener for queue/sync state updates.
  void setStateListener(VoidCallback listener) {
    _onStateChanged = listener;
  }

  /// Initialize the sync service. Call at app startup.
  Future<void> initialize() async {
    _registerNetworkObserver();

    // Load any queued predictions from previous session
    await _loadQueue();

    await _probeConnectivity(updateError: false);
    _updateDerivedSyncState();
    _notifyStateChanged();

    // Start periodic sync timer
    _syncTimer = Timer.periodic(_syncInterval, (_) => trySync());
    _probeTimer = Timer.periodic(_probeInterval, (_) {
      _probeConnectivity(updateError: false);
    });
  }

  /// Queue an edge prediction for cloud sync.
  /// Called every time edge ML produces a result.
  Future<void> queuePrediction({
    required EdgeRiskPrediction prediction,
    required Map<String, dynamic> vitals,
    List<Map<String, dynamic>>? alerts,
    Map<String, dynamic>? gpsData,
  }) async {
    final entry = {
      'timestamp': DateTime.now().toIso8601String(),
      'prediction': prediction.toJson(),
      'vitals': vitals,
      if (alerts != null && alerts.isNotEmpty) 'alerts': alerts,
      if (gpsData != null) 'gps': gpsData,
    };

    _pendingSyncs.add(entry);

    // Trim queue if too large (keep most recent)
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

    await _saveQueue();
    _updateDerivedSyncState();
    _notifyStateChanged();

    // If edge AI flagged high or critical risk, also push immediately to the
    // cloud so the clinician's SSE dashboard is updated within 1 second
    // rather than waiting up to 15 minutes for the next batch sync cycle.
    // The item is already queued above, so no data is lost if this push fails.
    if (prediction.riskLevel == 'high' || prediction.riskLevel == 'critical') {
      unawaited(
        pushCriticalAlertNow(
          prediction: prediction,
          vitals: vitals,
          alerts: alerts,
        ),
      );
    }
  }

  /// Queue a GPS emergency for priority sync.
  /// These are synced first when connectivity returns.
  Future<void> queueGpsEmergency(Map<String, dynamic> emergency) async {
    final entry = {
      'timestamp': DateTime.now().toIso8601String(),
      'type': 'gps_emergency',
      'data': emergency,
    };
    // Insert at front — emergencies sync first
    _pendingSyncs.insert(0, entry);
    await _saveQueue();
    _updateDerivedSyncState();
    _notifyStateChanged();
  }

  /// Push a single high or critical-risk reading directly to the cloud,
  /// bypassing the 15-minute batch queue.
  ///
  /// Called automatically by [queuePrediction] when edge AI detects 'high'
  /// or 'critical' risk. The item is still added to the regular queue so
  /// the batch-sync retains a copy — this is intentional (no data loss).
  ///
  /// Returns true if the push succeeded, false on any network or auth error.
  Future<bool> pushCriticalAlertNow({
    required EdgeRiskPrediction prediction,
    required Map<String, dynamic> vitals,
    List<Map<String, dynamic>>? alerts,
  }) async {
    try {
      await _dio.post(
        '/vitals/critical-alert',
        data: {
          'timestamp': DateTime.now().toIso8601String(),
          'vitals': vitals,
          'prediction': prediction.toJson(),
          if (alerts != null && alerts.isNotEmpty) 'alerts': alerts,
        },
      );
      _recordQueueEvent(
        type: 'critical_push_success',
        message:
            'Critical ${prediction.riskLevel} alert pushed immediately '
            '(bypassed 15-min queue).',
      );
      return true;
    } on DioException catch (e) {
      // Non-blocking failure — the queued copy retries on the next batch cycle.
      _recordQueueEvent(
        type: 'critical_push_failed',
        message:
            'Immediate critical push failed '
            '(${e.response?.statusCode ?? "no response"}). '
            'Reading is queued for next batch sync.',
      );
      return false;
    } catch (_) {
      _recordQueueEvent(
        type: 'critical_push_failed',
        message: 'Immediate critical push failed unexpectedly. Reading is queued.',
      );
      return false;
    }
  }

  /// Attempt to sync queued data to cloud.
  /// Called periodically and on-demand. Safe to call when offline
  /// (will silently fail and retry later).
  Future<bool> trySync() async {
    if (_isSyncing) return false;

    if (_pendingSyncs.isEmpty) {
      await _probeConnectivity(updateError: false);
      _updateDerivedSyncState();
      _notifyStateChanged();
      return false;
    }

    await _probeConnectivity(updateError: false);
    _updateDerivedSyncState();

    if (_syncState == CloudSyncState.offline ||
        _syncState == CloudSyncState.authExpired ||
        _syncState == CloudSyncState.rateLimited ||
        _syncState == CloudSyncState.serverError) {
      _notifyStateChanged();
      return false;
    }

    _isSyncing = true;
    _updateDerivedSyncState();
    _notifyStateChanged();

    try {
      // Sync GPS emergencies first (highest priority)
      final emergencySynced = await _syncEmergencies();

      // Then sync prediction batches
      final predictionSynced = await _syncPredictions();

      if (emergencySynced > 0 || predictionSynced > 0) {
        _lastSyncTime = DateTime.now();
        _clearSyncError();
      }
      _isConnectivityOnline = true;
      _isSyncing = false;
      _updateDerivedSyncState();
      _notifyStateChanged();
      return emergencySynced > 0 || predictionSynced > 0;
    } on DioException catch (e) {
      // No connectivity — keep queue, try again later
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

  /// Check if a new ML model version is available on the server.
  /// Returns model metadata if update available, null otherwise.
  Future<Map<String, dynamic>?> checkModelUpdate(
    String currentVersion,
  ) async {
    try {
      final response = await _dio.get('/model/retraining-status');
      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final metadata = data['metadata'] as Map<String, dynamic>?;
        if (metadata != null) {
          final serverVersion = metadata['version']?.toString() ?? '';
          if (serverVersion.isNotEmpty && serverVersion != currentVersion) {
            return metadata;
          }
        }
      }
    } catch (_) {
      // Offline or server error — skip update check
    }
    return null;
  }

  /// Stop the periodic sync timer
  void dispose() {
    _syncTimer?.cancel();
    _probeTimer?.cancel();
    if (_networkObserver != null) {
      _dio.interceptors.remove(_networkObserver);
      _networkObserver = null;
    }
    _onStateChanged = null;
  }

  // ---- Private: Sync Logic ----

  /// Sync GPS emergency alerts to cloud (priority)
  Future<int> _syncEmergencies() async {
    final emergencies = _pendingSyncs
        .where((e) => e['type'] == 'gps_emergency')
        .toList();

    int syncedCount = 0;

    for (final emergency in emergencies) {
      try {
        final emergencyData =
            Map<String, dynamic>.from((emergency['data'] as Map?) ?? {});
        final vitals =
            Map<String, dynamic>.from((emergencyData['vitals'] as Map?) ?? {});
        final heartRate = vitals['heart_rate'];

        // If no heart rate is available, this item cannot be accepted by
        // batch-sync validation. Drop it to prevent permanent queue blocking.
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
                'Dropped emergency sync item due to non-retryable ${statusCode} response.',
          );
          _setSyncError(
            type: 'validation_error',
            message:
                'Dropped one emergency sync item due to non-retryable server validation response (${statusCode}).',
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

  /// Sync edge predictions in batches
  Future<int> _syncPredictions() async {
    final predictions = _pendingSyncs
        .where((e) => e['type'] != 'gps_emergency')
        .toList();

    if (predictions.isEmpty) return 0;

    // Batch sync: send up to 50 at a time
    const batchSize = 50;
    final batch = predictions.take(batchSize).toList();

    try {
      await _dio.post(
        '/vitals/batch-sync',
        data: {
          'source': 'edge_ai',
          'batch': batch,
          'device_timestamp': DateTime.now().toIso8601String(),
        },
      );

      // Remove synced items from queue
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
              'Dropped ${batch.length} queued reading(s) due to non-retryable validation response (${statusCode}).',
        );
        _setSyncError(
          type: 'validation_error',
          message:
              'Dropped ${batch.length} queued reading(s) due to non-retryable validation response (${statusCode}).',
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

  // ---- Private: Local Queue Persistence ----

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

  void _notifyStateChanged() {
    final listener = _onStateChanged;
    if (listener != null) {
      listener();
    }
  }

  void _recordQueueEvent({required String type, required String message}) {
    _lastQueueEventType = type;
    _lastQueueEventMessage = message;
    _lastQueueEventAt = DateTime.now();
  }

  void _setSyncError({required String type, required String message}) {
    _lastSyncErrorType = type;
    _lastSyncErrorMessage = message;
    _lastSyncErrorAt = DateTime.now();
    _updateDerivedSyncState();
  }

  void _clearSyncError() {
    _lastSyncErrorType = null;
    _lastSyncErrorMessage = null;
    _lastSyncErrorAt = null;
    _updateDerivedSyncState();
  }

  void _setSyncErrorFromDio(DioException e) {
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

  void _registerNetworkObserver() {
    if (_networkObserver != null) {
      return;
    }

    _networkObserver = InterceptorsWrapper(
      onResponse: (response, handler) {
        final isProbe = response.requestOptions.extra['sync_probe'] == true;
        if (!isProbe) {
          _isConnectivityOnline = true;
          _updateDerivedSyncState();
          _notifyStateChanged();
        }
        handler.next(response);
      },
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

  Future<CloudSyncState> _probeConnectivity({bool updateError = true}) async {
    try {
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

  CloudSyncState _mapDioToState(DioException e) {
    final statusCode = e.response?.statusCode;

    if (statusCode == 401 || statusCode == 403) {
      return CloudSyncState.authExpired;
    }

    if (statusCode == 429) {
      return CloudSyncState.rateLimited;
    }

    if (statusCode != null && statusCode >= 500) {
      return CloudSyncState.serverError;
    }

    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      return CloudSyncState.offline;
    }

    return CloudSyncState.online;
  }

  void _updateDerivedSyncState() {
    if (_isSyncing) {
      _syncState = CloudSyncState.syncing;
      return;
    }

    if (!_isConnectivityOnline) {
      _syncState = CloudSyncState.offline;
      return;
    }

    if (_lastSyncErrorType == 'auth_expired') {
      _syncState = CloudSyncState.authExpired;
      return;
    }

    if (_lastSyncErrorType == 'rate_limited') {
      _syncState = CloudSyncState.rateLimited;
      return;
    }

    if (_lastSyncErrorType == 'server_error') {
      _syncState = CloudSyncState.serverError;
      return;
    }

    if (_pendingSyncs.isEmpty) {
      _syncState = CloudSyncState.idle;
      return;
    }

    _syncState = CloudSyncState.online;
  }
}
