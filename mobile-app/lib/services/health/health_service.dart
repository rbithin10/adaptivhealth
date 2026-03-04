import 'package:health/health.dart';
import '../../config/platform_guard.dart';

/// Singleton wrapper around HealthKit (iOS) and Google Fit / Health Connect (Android).
class HealthService {
  HealthService._internal();

  static final HealthService instance = HealthService._internal();

  factory HealthService() {
    return instance;
  }

  final Health _health = Health();
  bool _configured = false;

  Future<void> _ensureConfigured() async {
    if (!_configured) {
      await _health.configure();
      _configured = true;
    }
  }

  static const Duration _defaultLookback = Duration(hours: 1);

  static const List<HealthDataType> _allReadTypes = [
    HealthDataType.HEART_RATE,
    HealthDataType.STEPS,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
    HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
  ];

  /// Requests read authorization for all supported metrics.
  Future<bool> requestAuthorization() async {
    if (!isMobile) {
      return false;
    }

    try {
      await _ensureConfigured();

      final permissions = List<HealthDataAccess>.filled(
        _allReadTypes.length,
        HealthDataAccess.READ,
      );

      final isAuthorized = await _health.requestAuthorization(
        _allReadTypes,
        permissions: permissions,
      );

      return isAuthorized;
    } catch (_) {
      return false;
    }
  }

  /// Fetch heart rate data points within the lookback window.
  Future<List<HealthDataPoint>> getHeartRate({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.HEART_RATE, lookback: lookback);
  }

  /// Fetch step data points within the lookback window.
  Future<List<HealthDataPoint>> getSteps({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.STEPS, lookback: lookback);
  }

  /// Fetch blood oxygen (SpO2) data points within the lookback window.
  Future<List<HealthDataPoint>> getBloodOxygen({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.BLOOD_OXYGEN, lookback: lookback);
  }

  /// Fetch systolic blood pressure data points within the lookback window.
  Future<List<HealthDataPoint>> getBloodPressureSystolic({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(
      HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
      lookback: lookback,
    );
  }

  /// Fetch diastolic blood pressure data points within the lookback window.
  Future<List<HealthDataPoint>> getBloodPressureDiastolic({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(
      HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
      lookback: lookback,
    );
  }

  /// Fetch both systolic and diastolic blood pressure points in one call.
  Future<List<HealthDataPoint>> getBloodPressure({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForTypes(
      const [
        HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
        HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
      ],
      lookback: lookback,
    );
  }

  Future<List<HealthDataPoint>> _getDataForType(
    HealthDataType type, {
    required Duration lookback,
  }) async {
    return _getDataForTypes([type], lookback: lookback);
  }

  Future<List<HealthDataPoint>> _getDataForTypes(
    List<HealthDataType> types, {
    required Duration lookback,
  }) async {
    if (!isMobile) {
      return <HealthDataPoint>[];
    }

    final now = DateTime.now();
    final start = now.subtract(lookback);

    try {
      await _ensureConfigured();

      final access = List<HealthDataAccess>.filled(
        types.length,
        HealthDataAccess.READ,
      );

      final hasPermission =
          await _health.hasPermissions(types, permissions: access) ?? false;

      if (!hasPermission) {
        final granted = await requestAuthorization();
        if (!granted) {
          return <HealthDataPoint>[];
        }
      }

      final points = await _health.getHealthDataFromTypes(
        types: types,
        startTime: start,
        endTime: now,
        recordingMethodsToFilter: [],
      );

      return _health.removeDuplicates(points);
    } catch (_) {
      return <HealthDataPoint>[];
    }
  }
}
