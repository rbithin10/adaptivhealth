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
  static const _maxQueueSize = 500; // Cap local storage

  // Periodic sync timer
  Timer? _syncTimer;
  VoidCallback? _onStateChanged;

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

  // Number of predictions waiting to sync
  int get pendingCount => _pendingSyncs.length;

  /// Register a listener for queue/sync state updates.
  void setStateListener(VoidCallback listener) {
    _onStateChanged = listener;
  }

  /// Initialize the sync service. Call at app startup.
  Future<void> initialize() async {
    // Load any queued predictions from previous session
    await _loadQueue();
    _notifyStateChanged();

    // Start periodic sync timer
    _syncTimer = Timer.periodic(_syncInterval, (_) => trySync());
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
      _pendingSyncs = _pendingSyncs.sublist(
        _pendingSyncs.length - _maxQueueSize,
      );
    }

    await _saveQueue();
    _notifyStateChanged();
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
    _notifyStateChanged();
  }

  /// Attempt to sync queued data to cloud.
  /// Called periodically and on-demand. Safe to call when offline
  /// (will silently fail and retry later).
  Future<bool> trySync() async {
    if (_isSyncing || _pendingSyncs.isEmpty) return false;

    _isSyncing = true;
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
      _isSyncing = false;
      _notifyStateChanged();
      return emergencySynced > 0 || predictionSynced > 0;
    } on DioException catch (e) {
      // No connectivity — keep queue, try again later
      _setSyncErrorFromDio(e);
      _isSyncing = false;
      _notifyStateChanged();
      return false;
    } catch (e) {
      _setSyncError(
        type: 'unknown',
        message: 'Sync failed due to an unexpected error.',
      );
      _isSyncing = false;
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
          _pendingSyncs.remove(emergency);
          continue;
        }
        _setSyncErrorFromDio(e);
        // Retryable/network issue — keep item and stop this cycle.
        break;
      }
    }
    await _saveQueue();
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
      _notifyStateChanged();
      return batch.length;
    } on DioException catch (e) {
      // Keep queue for retry on all API errors to avoid silent data loss.
      _setSyncErrorFromDio(e);
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
    } catch (_) {}
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

  void _setSyncError({required String type, required String message}) {
    _lastSyncErrorType = type;
    _lastSyncErrorMessage = message;
    _lastSyncErrorAt = DateTime.now();
  }

  void _clearSyncError() {
    _lastSyncErrorType = null;
    _lastSyncErrorMessage = null;
    _lastSyncErrorAt = null;
  }

  void _setSyncErrorFromDio(DioException e) {
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
}
