/*
Health Service.

Reads health data from the phone's built-in health system:
- Apple HealthKit on iPhones
- Google Health Connect on Android phones

This lets the app import heart rate, steps, blood oxygen, and blood
pressure data that the phone has already collected from watches,
fitness trackers, or manual entries.

Only one copy of this service exists in the whole app.
*/

// The library that talks to Apple HealthKit and Google Health Connect
import 'package:health/health.dart';
// Checks which platform we're running on (phone vs desktop)
import '../../config/platform_guard.dart';

// Reads health data from the phone's health system (HealthKit or Health Connect)
class HealthService {
  // Private constructor — only this file can create an instance
  HealthService._internal();

  // The single shared instance used everywhere in the app
  static final HealthService instance = HealthService._internal();

  // When other files call HealthService(), return the shared instance
  factory HealthService() {
    return instance;
  }

  // The health plugin that talks to Apple HealthKit or Google Health Connect
  final Health _health = Health();
  // Whether we've already set up the health plugin
  bool _configured = false;

  // Make sure the health plugin is configured before using it
  Future<void> _ensureConfigured() async {
    if (!_configured) {
      await _health.configure();
      _configured = true;
    }
  }

  // How far back to look for health data (default: last 1 hour)
  static const Duration _defaultLookback = Duration(hours: 1);

  // The types of health data we want to read from the phone
  static const List<HealthDataType> _allReadTypes = [
    HealthDataType.HEART_RATE,
    HealthDataType.STEPS,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
    HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
    HealthDataType.HEART_RATE_VARIABILITY_SDNN,
  ];

  // Ask the user for permission to read their health data
  Future<bool> requestAuthorization() async {
    // Health data is only available on phones, not desktop or web
    if (!isMobile) {
      return false;
    }

    try {
      // Make sure the health plugin is ready
      await _ensureConfigured();

      // We only need READ permission (not write) for each data type
      final permissions = List<HealthDataAccess>.filled(
        _allReadTypes.length,
        HealthDataAccess.READ,
      );

      // Show the system permission dialog to the user
      final isAuthorized = await _health.requestAuthorization(
        _allReadTypes,
        permissions: permissions,
      );

      return isAuthorized;
    } catch (_) {
      // If something goes wrong, report that we don't have permission
      return false;
    }
  }

  // Get heart rate readings from the last hour (or custom time window)
  Future<List<HealthDataPoint>> getHeartRate({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.HEART_RATE, lookback: lookback);
  }

  // Get step count data from the last hour (or custom time window)
  Future<List<HealthDataPoint>> getSteps({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.STEPS, lookback: lookback);
  }

  // Get blood oxygen (SpO2) readings from the last hour (or custom time window)
  Future<List<HealthDataPoint>> getBloodOxygen({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(HealthDataType.BLOOD_OXYGEN, lookback: lookback);
  }

  // Get the top number of blood pressure readings from the last hour
  Future<List<HealthDataPoint>> getBloodPressureSystolic({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(
      HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
      lookback: lookback,
    );
  }

  // Get the bottom number of blood pressure readings from the last hour
  Future<List<HealthDataPoint>> getBloodPressureDiastolic({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(
      HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
      lookback: lookback,
    );
  }

  // Get heart rate variability (SDNN) readings from the phone's health store
  Future<List<HealthDataPoint>> getHrv({
    Duration lookback = _defaultLookback,
  }) async {
    return _getDataForType(
      HealthDataType.HEART_RATE_VARIABILITY_SDNN,
      lookback: lookback,
    );
  }

  // Get both top and bottom blood pressure numbers in one call
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

  // Internal helper: fetch one type of health data
  Future<List<HealthDataPoint>> _getDataForType(
    HealthDataType type, {
    required Duration lookback,
  }) async {
    return _getDataForTypes([type], lookback: lookback);
  }

  // Internal helper: fetch one or more types of health data from the phone
  Future<List<HealthDataPoint>> _getDataForTypes(
    List<HealthDataType> types, {
    required Duration lookback,
  }) async {
    // Health data is only available on phones, not desktop or web
    if (!isMobile) {
      return <HealthDataPoint>[];
    }

    // Calculate the time range: from (now - lookback) to now
    final now = DateTime.now();
    final start = now.subtract(lookback);

    try {
      // Make sure the health plugin is ready
      await _ensureConfigured();

      // We only need read access for the requested data types
      final access = List<HealthDataAccess>.filled(
        types.length,
        HealthDataAccess.READ,
      );

      // Check if we already have permission to read this data
      final hasPermission =
          await _health.hasPermissions(types, permissions: access) ?? false;

      // If we don't have permission, ask the user for it
      if (!hasPermission) {
        final granted = await requestAuthorization();
        // If the user denied permission, return empty results
        if (!granted) {
          return <HealthDataPoint>[];
        }
      }

      // Fetch the actual health data points from the phone
      final points = await _health.getHealthDataFromTypes(
        types: types,
        startTime: start,
        endTime: now,
        recordingMethodsToFilter: [],
      );

      // Remove duplicate readings (e.g., from multiple sources) and return
      return _health.removeDuplicates(points);
    } catch (_) {
      // If anything goes wrong, return empty results instead of crashing
      return <HealthDataPoint>[];
    }
  }
}
